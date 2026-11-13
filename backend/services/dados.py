"""Leitura dos arquivos do RPA e montagem das respostas da API.

Toda contagem é calculada a partir dos arquivos reais; nada é fixo no código.
"""
from __future__ import annotations

from collections import Counter, defaultdict
from pathlib import Path

from models.schemas import (
    EventoHistorico,
    InfoArquivo,
    LinhaInvalidaSaida,
    NovaSolicitacao,
    Publicavel,
    Resultado,
    Solicitacao,
)

from .csv_contrato import (
    COLUNAS_ENTRADA,
    COLUNAS_HISTORICO,
    COLUNAS_PROCESSADOS,
    COLUNAS_PUBLICAVEIS,
    LeituraCSV,
    gravar_atomico,
    ler_csv,
)

RAIZ = Path(__file__).resolve().parents[2]
# Lote fixo do teste inicial (11 pedidos), usado pelo botão "Restaurar lote de teste".
EXEMPLO_ENTRADA = RAIZ / "tests" / "dados_teste" / "pedidos_entrada.csv"
RESULTADOS = ("APROVADO", "REPROVADO", "DUPLICADO", "IGNORADO")


class ErroDados(Exception):
    def __init__(self, status_http: int, mensagem: str):
        super().__init__(mensagem)
        self.status_http = status_http
        self.mensagem = mensagem


def info_arquivo(leitura: LeituraCSV) -> InfoArquivo:
    return InfoArquivo(
        nome=leitura.caminho.name,
        existe=leitura.existe,
        valido=leitura.valido,
        erro=leitura.erro,
        modificado_em=leitura.modificado_em,
        total_linhas=len(leitura.linhas),
        linhas_invalidas=[LinhaInvalidaSaida(**vars(l)) for l in leitura.linhas_invalidas],
    )


def _chave(linha: dict) -> tuple:
    return (linha["numero_pedido"], linha["categoria"], linha["descricao"], linha["bairro"])


class ServicoDados:
    def __init__(self, cfg, execucoes):
        self.cfg = cfg
        self.execucoes = execucoes

    # ------------------------------------------------------------- leituras
    def entrada(self) -> LeituraCSV:
        leitura = ler_csv(self.cfg.caminho_entrada, COLUNAS_ENTRADA)
        if not leitura.existe:
            alternativo = self.cfg.caminho_entrada.with_name(self.cfg.caminho_entrada.name + ".csv")
            if alternativo.exists():
                leitura.erro = (f"Arquivo não encontrado. Existe '{alternativo.name}' (extensão duplicada): "
                                f"renomeie para '{self.cfg.caminho_entrada.name}', pois é esse o nome lido pelo fluxo.")
        return leitura

    def processados(self) -> LeituraCSV:
        return ler_csv(self.cfg.caminho_processados, COLUNAS_PROCESSADOS)

    def publicaveis_csv(self) -> LeituraCSV:
        return ler_csv(self.cfg.caminho_publicaveis, COLUNAS_PUBLICAVEIS)

    def historico_csv(self) -> LeituraCSV:
        return ler_csv(self.cfg.caminho_historico, COLUNAS_HISTORICO)

    @staticmethod
    def correspondem(entrada: LeituraCSV, processados: LeituraCSV) -> bool:
        """Os resultados são do lote atual? Compara pedido a pedido, na ordem do arquivo."""
        if not (entrada.valido and processados.valido) or not entrada.linhas:
            return False
        if entrada.linhas_invalidas or processados.linhas_invalidas:
            return False
        return [_chave(l) for l in entrada.linhas] == [_chave(l) for l in processados.linhas]

    def edicao_bloqueada(self) -> bool:
        return self.execucoes.ativa() is not None or self.execucoes.robo_ativo()

    # ----------------------------------------------------------- solicitações
    def listar_solicitacoes(self) -> dict:
        entrada = self.entrada()
        processados = self.processados()
        corresponde = self.correspondem(entrada, processados)
        itens = []
        for i, linha in enumerate(entrada.linhas):
            resultado = processados.linhas[i] if corresponde else None
            itens.append(Solicitacao(
                linha=int(linha["_linha"]),
                **{c: linha[c] for c in COLUNAS_ENTRADA},
                ultimo_resultado=resultado["resultado"] if resultado else None,
                ultimo_motivo=resultado["motivo"] if resultado else None,
            ))
        return {
            "arquivo": info_arquivo(entrada),
            "resultados_correspondem_ao_lote": corresponde,
            "edicao_bloqueada": self.edicao_bloqueada(),
            "itens": itens,
        }

    def _verificar_edicao(self) -> None:
        if self.edicao_bloqueada():
            raise ErroDados(423, "O arquivo de entrada está bloqueado: há um processamento do RPA em andamento.")

    def adicionar_solicitacao(self, nova: NovaSolicitacao) -> Solicitacao:
        self._verificar_edicao()
        entrada = self.entrada()
        if not entrada.existe:
            raise ErroDados(404, entrada.erro or "Arquivo de entrada não encontrado.")
        if not entrada.valido:
            raise ErroDados(422, f"Arquivo de entrada inválido; corrija antes de cadastrar: {entrada.erro}")
        texto = self.cfg.caminho_entrada.read_bytes().decode("utf-8-sig")  # preserva \r\n
        if texto and not texto.endswith(("\n", "\r")):
            texto += "\r\n" if "\r\n" in texto else "\n"
        quebra = "\r\n" if "\r\n" in texto else "\n"
        valores = [getattr(nova, c) for c in COLUNAS_ENTRADA]
        texto += ",".join(valores) + quebra
        bom = "﻿" if entrada.tem_bom else ""
        gravar_atomico(self.cfg.caminho_entrada, bom + texto)
        return Solicitacao(linha=len(entrada.linhas) + len(entrada.linhas_invalidas) + 2, **nova.model_dump())

    def restaurar_exemplo(self) -> int:
        """Restaura o lote de 11 pedidos do teste inicial (o atual é arquivado antes)."""
        self._verificar_edicao()
        if not EXEMPLO_ENTRADA.is_file():
            raise ErroDados(500, "Lote de exemplo não encontrado no repositório.")
        if self.cfg.caminho_entrada.is_file():
            destino = Path(self.cfg.pasta_estado) / "arquivo" / "entradas_substituidas"
            destino.mkdir(parents=True, exist_ok=True)
            from datetime import datetime
            (destino / f"pedidos_entrada_{datetime.now():%Y%m%d-%H%M%S}.csv").write_bytes(
                self.cfg.caminho_entrada.read_bytes())
        gravar_atomico(self.cfg.caminho_entrada, EXEMPLO_ENTRADA.read_bytes().decode("utf-8-sig"))
        return len(ler_csv(self.cfg.caminho_entrada, COLUNAS_ENTRADA).linhas)

    # -------------------------------------------------------------- resultados
    def listar_resultados(self) -> dict:
        leitura = self.processados()
        itens = [Resultado(linha=int(l["_linha"]), **{c: l[c] for c in COLUNAS_PROCESSADOS}) for l in leitura.linhas]
        contagem = Counter(i.resultado for i in itens)
        return {"arquivo": info_arquivo(leitura),
                "contagem": {r: contagem.get(r, 0) for r in RESULTADOS} | {"TOTAL": len(itens)},
                "itens": itens}

    def listar_publicaveis(self) -> dict:
        leitura = self.publicaveis_csv()
        itens = [
            Publicavel(
                linha=int(l["_linha"]), numero_pedido=l["numero_pedido"], categoria=l["categoria"],
                descricao=l["descricao"], bairro=l["bairro"], situacao_rpa=l["situacao"],
                situacao_exibida="Apto para publicação" if l["situacao"] == "PUBLICADO" else l["situacao"],
            )
            for l in leitura.linhas
        ]
        return {"arquivo": info_arquivo(leitura), "itens": itens}

    def listar_historico(self, id_execucao: str | None = None) -> dict:
        """Histórico atual ou o arquivado de uma execução específica."""
        if id_execucao:
            execucao = self.execucoes.obter(id_execucao)
            if execucao is None:
                raise ErroDados(404, "Execução não encontrada.")
            caminho = self.execucoes.pasta_arquivo / id_execucao / "saida" / self.cfg.caminho_historico.name
            leitura = ler_csv(caminho, COLUNAS_HISTORICO)
            id_arquivo = id_execucao
        else:
            leitura = self.historico_csv()
            id_arquivo = self.identificar_execucao_do_historico(leitura)
        eventos = [EventoHistorico(linha=int(l["_linha"]), **{c: l[c] for c in COLUNAS_HISTORICO}) for l in leitura.linhas]
        return {"arquivo": info_arquivo(leitura), "id_execucao_arquivo": id_arquivo,
                "eventos": eventos, "execucoes": self.execucoes.listar(50)}

    def identificar_execucao_do_historico(self, leitura: LeituraCSV) -> str | None:
        if not leitura.valido or not leitura.linhas:
            return None
        marca = leitura.linhas[0]["data_hora"]
        for execucao in self.execucoes.listar(50):
            if execucao.evidencias.marca_execucao_rpa == marca:
                return execucao.id_execucao
        # Execução iniciada direto no PAD, sem passar pela interface.
        return "PAD-" + marca.replace("-", "").replace(":", "").replace(" ", "-")

    # ------------------------------------------------------------ estatísticas
    def estatisticas(self) -> dict:
        entrada = self.entrada()
        processados = self.processados()
        publicaveis = self.publicaveis_csv()
        historico = self.historico_csv()
        contagem = Counter(l["resultado"] for l in processados.linhas)

        ultimo, fonte = None, None
        for linha in reversed(historico.linhas):
            if linha["etapa"] == "Resumo" and linha["resultado"] == "CONCLUIDO":
                ultimo, fonte = linha["data_hora"], "historico_execucao.csv (resumo gravado pelo RPA)"
                break

        categorias: dict[str, dict[str, int]] = defaultdict(lambda: {r: 0 for r in RESULTADOS} | {"total": 0})
        for linha in processados.linhas:
            nome = linha["categoria"] or "(não informada)"
            categorias[nome]["total"] += 1
            if linha["resultado"] in RESULTADOS:
                categorias[nome][linha["resultado"]] += 1
        lista_categorias = sorted(
            ({"categoria": k, **v} for k, v in categorias.items()), key=lambda c: (-c["total"], c["categoria"])
        )

        ativa = self.execucoes.ativa()
        execucoes = self.execucoes.listar(8)
        if ativa:
            situacao = ativa.situacao
        elif self.execucoes.robo_ativo():
            situacao = "robo_ocupado"
        else:
            situacao = "ociosa"

        return {
            "total_solicitacoes": len(entrada.linhas),
            "pendentes": sum(1 for l in entrada.linhas if l["situacao"] == "PENDENTE"),
            "aprovados": contagem.get("APROVADO", 0),
            "reprovados": contagem.get("REPROVADO", 0),
            "duplicados": contagem.get("DUPLICADO", 0),
            "ignorados": contagem.get("IGNORADO", 0),
            "publicaveis": len(publicaveis.linhas),
            "ultimo_processamento": ultimo,
            "ultimo_processamento_fonte": fonte,
            "resultados_correspondem_ao_lote": self.correspondem(entrada, processados),
            "situacao_automacao": situacao,
            "execucao_ativa": ativa,
            "ultima_execucao": execucoes[0] if execucoes else None,
            "categorias": lista_categorias,
            "execucoes_recentes": execucoes,
        }
