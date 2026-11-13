"""Orquestração das execuções do RPA: execução única, arquivamento e monitoramento.

Este módulo NÃO processa pedidos. Ele aciona o Power Automate Desktop e observa
as evidências reais deixadas pelo fluxo (processo do robô e arquivos de saída).
"""
from __future__ import annotations

import json
import logging
import secrets
import shutil
import threading
import time
from datetime import datetime
from pathlib import Path
from typing import Callable

from integrations.power_automate.base import FALHA_AO_INICIAR, ControladorPAD, ErroControlador
from integrations.power_automate.controladores import criar_controlador
from integrations.power_automate.processos import algum_ativo
from models.schemas import EtapaExecucao, Evidencias, Execucao, ResumoExecucao

from .csv_contrato import COLUNAS_ENTRADA, ler_csv
from .detector import EstadoArquivo, Marco, analisar_saidas, conferir_consistencia, ler_status_json

log = logging.getLogger("quemfaz.execucoes")

ROTULOS = {
    "aguardando_execucao": "Aguardando execução",
    "iniciando_automacao": "Iniciando automação",
    "processamento_em_andamento": "Processamento em andamento",
    "conferindo_resultados": "Conferindo resultados",
    "concluido": "Concluído",
    "falha_automacao": "Falha na automação",
    "indeterminado": "Resultado indeterminado",
    "cancelado": "Monitoramento cancelado",
}


class ErroExecucao(Exception):
    def __init__(self, status_http: int, mensagem: str):
        super().__init__(mensagem)
        self.status_http = status_http
        self.mensagem = mensagem


def _agora() -> datetime:
    return datetime.now()


class ServicoExecucoes:
    def __init__(
        self,
        cfg,
        fabrica_controlador: Callable[[str, object], ControladorPAD] = criar_controlador,
        robo_ativo: Callable[[], bool] | None = None,
        iniciar_thread: bool = True,
    ):
        self.cfg = cfg
        self.fabrica_controlador = fabrica_controlador
        self.robo_ativo = robo_ativo or (lambda: algum_ativo(cfg.lista_processos_robo))
        self.iniciar_thread = iniciar_thread
        self._trava = threading.Lock()
        self._trava_arquivos = threading.RLock()
        self._cancelar: set[str] = set()
        self._threads: dict[str, threading.Thread] = {}
        self.pasta_execucoes = Path(cfg.pasta_estado) / "execucoes"
        self.pasta_arquivo = Path(cfg.pasta_estado) / "arquivo"
        self.pasta_execucoes.mkdir(parents=True, exist_ok=True)
        self.pasta_arquivo.mkdir(parents=True, exist_ok=True)
        self._recuperar_execucoes_interrompidas()

    # ------------------------------------------------------------ persistência
    def _caminho(self, id_execucao: str) -> Path:
        return self.pasta_execucoes / f"{id_execucao}.json"

    @staticmethod
    def _com_repeticao(operacao):
        """No Windows, antivírus/indexador podem segurar o arquivo por instantes."""
        for tentativa in range(20):
            try:
                return operacao()
            except PermissionError:
                if tentativa == 19:
                    raise
                time.sleep(0.05)

    def _salvar(self, execucao: Execucao, marco: Marco | None = None) -> None:
        dados = json.loads(execucao.model_dump_json())
        caminho = self._caminho(execucao.id_execucao)
        with self._trava_arquivos:
            if marco is not None:
                dados["_marco"] = marco.para_dict()
            elif caminho.exists():
                antigo = self._com_repeticao(lambda: json.loads(caminho.read_text(encoding="utf-8")))
                if "_marco" in antigo:
                    dados["_marco"] = antigo["_marco"]
            temporario = caminho.with_suffix(".tmp")
            temporario.write_text(json.dumps(dados, ensure_ascii=False, indent=2), encoding="utf-8")
            self._com_repeticao(lambda: temporario.replace(caminho))

    def _carregar_bruto(self, id_execucao: str) -> dict | None:
        if not id_execucao.replace("-", "").isalnum():
            return None  # impede path traversal no identificador
        caminho = self._caminho(id_execucao)
        with self._trava_arquivos:
            if not caminho.is_file():
                return None
            return self._com_repeticao(lambda: json.loads(caminho.read_text(encoding="utf-8")))

    def _ler_registro(self, arquivo: Path) -> dict:
        with self._trava_arquivos:
            return self._com_repeticao(lambda: json.loads(arquivo.read_text(encoding="utf-8")))

    def obter(self, id_execucao: str) -> Execucao | None:
        bruto = self._carregar_bruto(id_execucao)
        if bruto is None:
            return None
        bruto.pop("_marco", None)
        return Execucao.model_validate(bruto)

    def listar(self, limite: int = 50) -> list[Execucao]:
        arquivos = sorted(self.pasta_execucoes.glob("EXE-*.json"), reverse=True)[:limite]
        execucoes = []
        for arquivo in arquivos:
            try:
                bruto = self._ler_registro(arquivo)
                bruto.pop("_marco", None)
                execucoes.append(Execucao.model_validate(bruto))
            except (OSError, ValueError):
                continue
        return execucoes

    def ativa(self) -> Execucao | None:
        for execucao in self.listar(10):
            if execucao.ativa:
                return execucao
        return None

    def ultima_concluida(self) -> Execucao | None:
        for execucao in self.listar(50):
            if execucao.situacao == "concluido":
                return execucao
        return None

    def _recuperar_execucoes_interrompidas(self) -> None:
        for execucao in self.listar(50):
            if execucao.ativa:
                self._registrar(execucao, "indeterminado",
                                "O backend foi reiniciado durante o monitoramento. Confira os arquivos antes de repetir.",
                                motivo="Monitoramento interrompido")

    def _registrar(self, execucao: Execucao, situacao: str, mensagem: str, motivo: str | None = None) -> None:
        execucao.situacao = situacao  # type: ignore[assignment]
        execucao.mensagem = mensagem
        execucao.etapas.append(EtapaExecucao(data_hora=_agora(), situacao=situacao, mensagem=mensagem))
        if motivo:
            execucao.motivo_erro = motivo
        if not execucao.ativa:
            execucao.data_fim = _agora()
        self._salvar(execucao)
        log.info("execucao=%s situacao=%s", execucao.id_execucao, situacao)

    # ---------------------------------------------------------------- início
    def _validar_entrada(self) -> int:
        entrada = ler_csv(self.cfg.caminho_entrada, COLUNAS_ENTRADA)
        if not entrada.existe:
            alternativo = self.cfg.caminho_entrada.with_name(self.cfg.caminho_entrada.name + ".csv")
            dica = (f" Foi encontrado '{alternativo.name}' (extensão duplicada): renomeie para "
                    f"'{self.cfg.caminho_entrada.name}'.") if alternativo.exists() else ""
            raise ErroExecucao(422, f"Arquivo de entrada não encontrado: {self.cfg.caminho_entrada.name}.{dica}")
        if not entrada.valido:
            raise ErroExecucao(422, f"Arquivo de entrada inválido: {entrada.erro}")
        total = len(entrada.linhas) + len(entrada.linhas_invalidas)
        if total == 0:
            raise ErroExecucao(422, "O arquivo de entrada não possui pedidos.")
        for pasta in (self.cfg.caminho_processados.parent, self.cfg.caminho_historico.parent):
            if not pasta.is_dir():
                raise ErroExecucao(422, f"A pasta '{pasta.name}' não existe na pasta do RPA.")
        return total

    def _arquivar(self, id_execucao: str, subpasta: str) -> Path:
        destino = self.pasta_arquivo / id_execucao / subpasta
        destino.mkdir(parents=True, exist_ok=True)
        for origem in (self.cfg.caminho_entrada, self.cfg.caminho_processados,
                       self.cfg.caminho_publicaveis, self.cfg.caminho_historico):
            if origem.is_file():
                shutil.copy2(origem, destino / origem.name)
        return destino

    def _gravar_controle(self, id_execucao: str) -> None:
        """Grava o ID atual para o trecho OPCIONAL de status no fluxo (não exigido)."""
        try:
            self.cfg.caminho_controle_rpa.mkdir(parents=True, exist_ok=True)
            (self.cfg.caminho_controle_rpa / "execucao_atual.txt").write_text(id_execucao, encoding="utf-8")
        except OSError:
            log.warning("Não foi possível gravar o arquivo de controle opcional.")

    def iniciar(self, modo: str | None = None) -> Execucao:
        modo = modo or self.cfg.modo_padrao
        if modo not in self.cfg.lista_modos:
            raise ErroExecucao(400, f"Modo '{modo}' não está habilitado em PAD_MODOS_PERMITIDOS.")

        if not self._trava.acquire(blocking=False):
            raise ErroExecucao(409, "Outra solicitação de processamento está sendo preparada.")
        try:
            ativa = self.ativa()
            if ativa:
                raise ErroExecucao(409, f"Já existe uma execução em andamento ({ativa.id_execucao}).")
            if self.robo_ativo():
                raise ErroExecucao(409, "O Power Automate Desktop já está executando um fluxo. Aguarde o término.")
            total_entrada = self._validar_entrada()

            agora = _agora()
            id_execucao = f"EXE-{agora:%Y%m%d-%H%M%S}-{secrets.token_hex(2)}"
            pasta = self._arquivar(id_execucao, "antes")
            self._gravar_controle(id_execucao)
            # Garante que a marca do fluxo (resolução de 1 s) seja posterior ao marco.
            marco = Marco(
                inicio=_agora(),
                historico=EstadoArquivo.capturar(self.cfg.caminho_historico),
                processados=EstadoArquivo.capturar(self.cfg.caminho_processados),
                publicaveis=EstadoArquivo.capturar(self.cfg.caminho_publicaveis),
                total_entrada=total_entrada,
            )
            execucao = Execucao(
                id_execucao=id_execucao,
                modo=modo,
                modo_solicitado=modo,
                nome_fluxo=self.cfg.nome_fluxo,
                situacao="aguardando_execucao",
                data_inicio=agora,
                hash_entrada=EstadoArquivo.capturar(self.cfg.caminho_entrada).hash,
                pasta_arquivo=str(pasta.parent.name),
                mensagem="Lote validado e resultados anteriores arquivados.",
                etapas=[EtapaExecucao(data_hora=agora, situacao="aguardando_execucao",
                                      mensagem=f"Lote com {total_entrada} pedido(s) validado; resultados anteriores arquivados.")],
            )
            self._salvar(execucao, marco)
        finally:
            self._trava.release()

        if self.iniciar_thread:
            thread = threading.Thread(target=self._executar, args=(id_execucao,), daemon=True, name=id_execucao)
            self._threads[id_execucao] = thread
            thread.start()
        return execucao

    def cancelar(self, id_execucao: str) -> Execucao:
        execucao = self.obter(id_execucao)
        if execucao is None:
            raise ErroExecucao(404, "Execução não encontrada.")
        if not execucao.ativa:
            raise ErroExecucao(409, "A execução não está ativa.")
        self._cancelar.add(id_execucao)
        if id_execucao not in self._threads:
            self._registrar(execucao, "cancelado", "Monitoramento cancelado pelo usuário. O fluxo no PAD não foi interrompido.")
        return execucao

    # ---------------------------------------------------------- monitoramento
    def _executar(self, id_execucao: str) -> None:
        try:
            self._executar_monitoramento(id_execucao)
        except Exception:  # noqa: BLE001 - nunca deixar a execução "ativa" para sempre
            log.exception("Erro interno no monitoramento")
            execucao = self.obter(id_execucao)
            if execucao and execucao.ativa:
                self._registrar(execucao, "indeterminado", "Erro interno do monitoramento. Confira os arquivos de saída.",
                                motivo="Erro de integração no backend")
        finally:
            self._threads.pop(id_execucao, None)
            self._cancelar.discard(id_execucao)

    def _acionar_com_limite(self, controlador: ControladorPAD):
        """Executa o acionamento numa thread própria para que uma UI travada não congele a execução."""
        saida: dict = {}

        def alvo():
            try:
                saida["resultado"] = controlador.acionar()
            except BaseException as exc:  # noqa: BLE001 - repassado ao chamador
                saida["erro"] = exc

        thread = threading.Thread(target=alvo, daemon=True, name="acionamento-pad")
        thread.start()
        thread.join(self.cfg.tempo_limite_acionamento)
        if thread.is_alive():
            raise ErroControlador(
                FALHA_AO_INICIAR,
                f"O acionamento não respondeu em {self.cfg.tempo_limite_acionamento:.0f} s "
                "(o console do PAD pode estar com uma janela/diálogo aberto ou travado).",
            )
        if "erro" in saida:
            erro = saida["erro"]
            if isinstance(erro, ErroControlador):
                raise erro
            raise ErroControlador(FALHA_AO_INICIAR, f"Erro inesperado no acionamento: {type(erro).__name__}.") from erro
        return saida["resultado"]

    def _acionar(self, execucao: Execucao) -> bool:
        """Aciona o PAD. Retorna True se o acionamento foi automático."""
        self._registrar(execucao, "iniciando_automacao", f"Acionando o Power Automate Desktop (modo: {execucao.modo}).")
        controlador = self.fabrica_controlador(execucao.modo, self.cfg)
        try:
            resultado = self._acionar_com_limite(controlador)
        except ErroControlador as erro:
            if self.cfg.fallback_assistido and execucao.modo != "assistido":
                execucao.modo = "assistido"
                self._registrar(execucao, "aguardando_execucao",
                                f"Acionamento automático falhou ({erro.mensagem}). Modo assistido ativado: "
                                f"execute o fluxo '{self.cfg.nome_fluxo}' manualmente no Power Automate Desktop.")
                return False
            self._registrar(execucao, "falha_automacao", f"Falha ao iniciar o fluxo: {erro.mensagem}", motivo=erro.codigo)
            raise
        if resultado.automatico:
            self._registrar(execucao, "iniciando_automacao", resultado.mensagem)
        else:
            self._registrar(execucao, "aguardando_execucao", resultado.mensagem)
        return resultado.automatico

    def _executar_monitoramento(self, id_execucao: str) -> None:
        cfg = self.cfg
        execucao = self.obter(id_execucao)
        marco = Marco.de_dict(self._carregar_bruto(id_execucao)["_marco"])
        try:
            automatico = self._acionar(execucao)
        except ErroControlador:
            return

        def prazo_inicio_para(auto: bool) -> float:
            return time.monotonic() + (cfg.tempo_limite_inicio if auto else cfg.tempo_limite_assistido)

        prazo_inicio = prazo_inicio_para(automatico)
        prazo_execucao: float | None = None
        robo_encerrado_em: float | None = None
        resumo_visto_em: float | None = None
        ev = execucao.evidencias

        while True:
            if id_execucao in self._cancelar:
                self._registrar(execucao, "cancelado",
                                "Monitoramento cancelado pelo usuário. O fluxo no PAD não foi interrompido.")
                return

            robo = self.robo_ativo()
            analise = analisar_saidas(cfg, marco)
            status_json = ler_status_json(cfg, id_execucao)
            agora = time.monotonic()

            if robo:
                ev.robo_detectado = True
                robo_encerrado_em = None
            elif ev.robo_detectado and robo_encerrado_em is None:
                robo_encerrado_em = agora
                ev.robo_encerrado = True
            ev.historico_atualizado = analise.marca_pertence_execucao
            ev.processados_atualizado = analise.processados_alterado
            ev.publicaveis_atualizado = analise.publicaveis_alterado
            ev.marca_execucao_rpa = analise.marca_rpa if analise.marca_pertence_execucao else None
            ev.linha_resumo = analise.linha_resumo
            ev.status_json = status_json

            iniciou = ev.robo_detectado or analise.iniciou or status_json is not None
            if iniciou and execucao.situacao in ("aguardando_execucao", "iniciando_automacao"):
                motivo = "processo do robô do PAD detectado" if ev.robo_detectado else "histórico regravado pelo fluxo"
                self._registrar(execucao, "processamento_em_andamento", f"Fluxo em execução ({motivo}).")
                prazo_execucao = agora + cfg.tempo_limite_execucao

            # 1) Status opcional informando erro técnico
            if status_json and status_json.get("situacao", "").upper() in ("ERRO", "FALHA"):
                self._registrar(execucao, "falha_automacao",
                                f"O fluxo informou erro na etapa '{status_json.get('etapa', '?')}'.",
                                motivo=status_json.get("motivo_erro") or status_json.get("mensagem"))
                return

            # 2) Resumo gravado -> conferir resultados
            if analise.concluiu:
                if resumo_visto_em is None:
                    resumo_visto_em = agora
                    self._registrar(execucao, "conferindo_resultados",
                                    "Resumo do lote gravado pelo RPA. Conferindo os arquivos de resultado.")
                if not robo or agora - resumo_visto_em > cfg.tempo_espera_encerramento:
                    problemas = conferir_consistencia(cfg, marco, analise)
                    c = analise.contagem_resumo or {}
                    execucao.resumo = ResumoExecucao(
                        total=c.get("total", 0), aprovados=c.get("aprovados", 0), reprovados=c.get("reprovados", 0),
                        duplicados=c.get("duplicados", 0), ignorados=c.get("ignorados", 0),
                        publicaveis=analise.total_publicaveis,
                    )
                    self._arquivar(id_execucao, "saida")
                    if problemas:
                        self._registrar(execucao, "falha_automacao",
                                        "O RPA terminou, mas os arquivos de saída estão inconsistentes.",
                                        motivo=" ".join(problemas))
                    else:
                        self._registrar(execucao, "concluido",
                                        f"Processamento concluído pelo RPA. {analise.linha_resumo}")
                    return

            # 3) Robô encerrou sem resumo -> caminho FINALIZACAO_ERRO
            elif robo_encerrado_em is not None and agora - robo_encerrado_em > max(3.0, cfg.intervalo_verificacao * 3):
                if not analise.iniciou:
                    motivo = ("O fluxo encerrou sem regravar os arquivos de saída. Provável falha na etapa "
                              "'Leitura dos pedidos pendentes' ou 'Preparação dos arquivos de saída' "
                              "(veja a mensagem 'Quem Faz - Erro na automacao' exibida pelo PAD).")
                else:
                    motivo = (f"O fluxo encerrou após registrar {analise.linhas_validacao} validação(ões), "
                              "sem gravar o resumo do lote. Provável falha no processamento ou no registro do resumo. "
                              "Os arquivos de saída podem estar parciais.")
                self._arquivar(id_execucao, "saida")
                self._registrar(execucao, "falha_automacao", "O fluxo terminou pelo caminho de erro.", motivo=motivo)
                return

            # 4) Tempos limite
            if not iniciou and agora > prazo_inicio:
                if automatico and cfg.fallback_assistido:
                    automatico = False
                    execucao.modo = "assistido"
                    prazo_inicio = prazo_inicio_para(False)
                    self._registrar(execucao, "aguardando_execucao",
                                    "Nenhuma evidência de início após o acionamento automático. Modo assistido ativado: "
                                    f"execute o fluxo '{cfg.nome_fluxo}' manualmente no Power Automate Desktop.")
                elif automatico:
                    self._registrar(execucao, "falha_automacao",
                                    "Falha ao iniciar: nenhuma evidência de execução (robô não detectado e arquivos não atualizados).",
                                    motivo="falha_ao_iniciar")
                    return
                else:
                    self._registrar(execucao, "indeterminado",
                                    "Tempo limite excedido: o fluxo não foi iniciado no Power Automate Desktop.",
                                    motivo="tempo_limite_inicio")
                    return
            if prazo_execucao is not None and agora > prazo_execucao:
                self._registrar(execucao, "indeterminado",
                                "Tempo limite de execução excedido sem confirmação de término. Os resultados não foram aceitos.",
                                motivo="tempo_limite_execucao")
                return

            self._salvar(execucao)
            time.sleep(cfg.intervalo_verificacao)
