"""[SIMULADO] Orquestração e detecção de término — sem Power Automate real."""
import time

import pytest

from conftest import ControladorSimulado, PadSimulado, copiar_saida_real, criar_cfg, esperar_fim
from integrations.power_automate.base import FALHA_AO_INICIAR, PAD_INDISPONIVEL, ErroControlador
from services.execucoes import ErroExecucao, ServicoExecucoes


def servico_com(cfg, pad, **kw):
    controlador = ControladorSimulado(pad, **kw)
    return ServicoExecucoes(cfg, fabrica_controlador=lambda modo, c: controlador, robo_ativo=pad.robo_ativo)


def test_execucao_concluida_11_pedidos(cfg, pasta_rpa):
    pad = PadSimulado(pasta_rpa, "sucesso")
    servico = servico_com(cfg, pad)
    execucao = servico.iniciar("atalho")
    final = esperar_fim(servico, execucao.id_execucao)
    assert final.situacao == "concluido", final.motivo_erro
    assert final.resumo.total == 11
    assert (final.resumo.aprovados, final.resumo.reprovados, final.resumo.duplicados, final.resumo.ignorados) == (4, 5, 1, 1)
    assert final.resumo.publicaveis == 4
    assert final.evidencias.robo_detectado and final.evidencias.linha_resumo
    situacoes = [e.situacao for e in final.etapas]
    assert situacoes.index("processamento_em_andamento") < situacoes.index("conferindo_resultados") < situacoes.index("concluido")
    # resultados arquivados antes e depois
    pasta = servico.pasta_arquivo / execucao.id_execucao
    assert (pasta / "antes" / "pedidos_entrada.csv").exists()
    assert (pasta / "saida" / "pedidos_processados.csv").exists()


def test_resultados_antigos_nao_sao_aceitos(cfg, pasta_rpa):
    """Arquivos de uma execução anterior presentes e o PAD não roda -> nunca 'concluido'."""
    copiar_saida_real(pasta_rpa)  # marca 2026-11-10 23:14:02
    pad = PadSimulado(pasta_rpa, "nao_inicia")
    servico = servico_com(cfg, pad, automatico=False)
    final = esperar_fim(servico, servico.iniciar("assistido").id_execucao)
    assert final.situacao == "indeterminado"
    assert final.motivo_erro == "tempo_limite_inicio"
    assert final.resumo is None


def test_arquivo_tocado_com_marca_antiga_nao_vale(cfg, pasta_rpa):
    copiar_saida_real(pasta_rpa)
    pad = PadSimulado(pasta_rpa, "nao_inicia")
    servico = servico_com(cfg, pad, automatico=False)
    execucao = servico.iniciar("assistido")
    time.sleep(0.2)
    copiar_saida_real(pasta_rpa)  # regravado, mas com a marca antiga
    final = esperar_fim(servico, execucao.id_execucao)
    assert final.situacao != "concluido"


def test_execucao_simultanea_bloqueada(cfg, pasta_rpa):
    pad = PadSimulado(pasta_rpa, "sucesso", atraso=0.2)
    servico = servico_com(cfg, pad)
    primeira = servico.iniciar("atalho")
    with pytest.raises(ErroExecucao) as erro:
        servico.iniciar("atalho")
    assert erro.value.status_http == 409
    esperar_fim(servico, primeira.id_execucao)


def test_bloqueia_quando_robo_ja_ocupado(cfg, pasta_rpa):
    pad = PadSimulado(pasta_rpa)
    pad.robo = True
    servico = servico_com(cfg, pad)
    with pytest.raises(ErroExecucao) as erro:
        servico.iniciar("atalho")
    assert erro.value.status_http == 409


def test_pad_indisponivel(cfg, pasta_rpa):
    pad = PadSimulado(pasta_rpa)
    servico = servico_com(cfg, pad, falha=ErroControlador(PAD_INDISPONIVEL, "Console fechado"))
    final = esperar_fim(servico, servico.iniciar("atalho").id_execucao)
    assert final.situacao == "falha_automacao"
    assert final.motivo_erro == PAD_INDISPONIVEL


def test_falha_ao_iniciar_com_fallback_para_assistido(pasta_rpa, tmp_path):
    cfg = criar_cfg(pasta_rpa, tmp_path / "estado", PAD_FALLBACK_ASSISTIDO="true")
    pad = PadSimulado(pasta_rpa)
    servico = servico_com(cfg, pad, falha=ErroControlador(FALHA_AO_INICIAR, "Botão desabilitado"))
    execucao = servico.iniciar("interface_grafica")
    time.sleep(0.3)
    atual = servico.obter(execucao.id_execucao)
    assert atual.modo == "assistido" and atual.modo_solicitado == "interface_grafica"
    assert atual.situacao == "aguardando_execucao"
    pad.disparar()  # o usuário executa o fluxo manualmente
    final = esperar_fim(servico, execucao.id_execucao)
    assert final.situacao == "concluido"


def test_atalho_sem_evidencia_de_inicio(cfg, pasta_rpa):
    pad = PadSimulado(pasta_rpa, "nao_inicia")
    servico = servico_com(cfg, pad)
    final = esperar_fim(servico, servico.iniciar("atalho").id_execucao)
    assert final.situacao == "falha_automacao"
    assert final.motivo_erro == "falha_ao_iniciar"


def test_falha_tecnica_na_leitura(cfg, pasta_rpa):
    copiar_saida_real(pasta_rpa)  # resultados antigos não podem ser confundidos com sucesso
    pad = PadSimulado(pasta_rpa, "erro_leitura")
    servico = servico_com(cfg, pad)
    final = esperar_fim(servico, servico.iniciar("atalho").id_execucao)
    assert final.situacao == "falha_automacao"
    assert "Leitura dos pedidos" in final.motivo_erro


def test_falha_tecnica_durante_processamento(cfg, pasta_rpa):
    pad = PadSimulado(pasta_rpa, "erro_processamento")
    servico = servico_com(cfg, pad)
    final = esperar_fim(servico, servico.iniciar("atalho").id_execucao)
    assert final.situacao == "falha_automacao"
    assert "sem gravar o resumo" in final.motivo_erro


def test_saida_inconsistente_nao_e_sucesso(cfg, pasta_rpa):
    pad = PadSimulado(pasta_rpa, "inconsistente")
    servico = servico_com(cfg, pad)
    final = esperar_fim(servico, servico.iniciar("atalho").id_execucao)
    assert final.situacao == "falha_automacao"
    assert "Publicáveis" in final.motivo_erro


def test_conclusao_sem_processo_do_robo_visivel(cfg, pasta_rpa):
    pad = PadSimulado(pasta_rpa, "robo_invisivel")
    servico = servico_com(cfg, pad)
    final = esperar_fim(servico, servico.iniciar("atalho").id_execucao)
    assert final.situacao == "concluido"
    assert not final.evidencias.robo_detectado


def test_tempo_limite_de_execucao(pasta_rpa, tmp_path):
    cfg = criar_cfg(pasta_rpa, tmp_path / "estado", PAD_TEMPO_LIMITE_EXECUCAO_S="0.5")
    pad = PadSimulado(pasta_rpa, "nao_inicia")
    servico = servico_com(cfg, pad)
    execucao = servico.iniciar("atalho")
    pad.robo = True  # robô "travado", nunca termina
    final = esperar_fim(servico, execucao.id_execucao)
    assert final.situacao == "indeterminado" and final.motivo_erro == "tempo_limite_execucao"
    pad.robo = False


def test_cancelar_monitoramento(cfg, pasta_rpa):
    pad = PadSimulado(pasta_rpa, "nao_inicia")
    servico = servico_com(cfg, pad, automatico=False)
    execucao = servico.iniciar("assistido")
    servico.cancelar(execucao.id_execucao)
    assert esperar_fim(servico, execucao.id_execucao).situacao == "cancelado"


def test_entrada_inexistente_nao_aciona(cfg, pasta_rpa):
    (pasta_rpa / "dados" / "pedidos_entrada.csv").rename(pasta_rpa / "dados" / "pedidos_entrada.csv.csv")
    pad = PadSimulado(pasta_rpa)
    servico = servico_com(cfg, pad)
    with pytest.raises(ErroExecucao) as erro:
        servico.iniciar("atalho")
    assert erro.value.status_http == 422 and "extensão duplicada" in erro.value.mensagem
    assert pad.acionamentos == 0


def test_modo_nao_permitido(cfg, pasta_rpa):
    servico = servico_com(cfg, PadSimulado(pasta_rpa))
    with pytest.raises(ErroExecucao) as erro:
        servico.iniciar("url_local")
    assert erro.value.status_http == 400


def test_reinicio_do_backend_nao_deixa_execucao_presa(cfg, pasta_rpa):
    pad = PadSimulado(pasta_rpa, "nao_inicia")
    controlador = ControladorSimulado(pad, automatico=False)
    servico = ServicoExecucoes(cfg, lambda m, c: controlador, pad.robo_ativo, iniciar_thread=False)
    execucao = servico.iniciar("assistido")
    novo = ServicoExecucoes(cfg, lambda m, c: controlador, pad.robo_ativo, iniciar_thread=False)
    assert novo.obter(execucao.id_execucao).situacao == "indeterminado"


def test_status_json_opcional_com_erro(cfg, pasta_rpa):
    import json
    pad = PadSimulado(pasta_rpa, "nao_inicia")
    servico = servico_com(cfg, pad, automatico=False)
    execucao = servico.iniciar("assistido")
    assert (pasta_rpa / "controle" / "execucao_atual.txt").read_text() == execucao.id_execucao
    (pasta_rpa / "controle" / "status_execucao.json").write_text(json.dumps({
        "identificador_execucao": execucao.id_execucao, "situacao": "ERRO",
        "etapa": "Leitura dos pedidos pendentes", "motivo_erro": "Nao foi possivel abrir"}), encoding="utf-8")
    final = esperar_fim(servico, execucao.id_execucao)
    assert final.situacao == "falha_automacao" and "Nao foi possivel" in final.motivo_erro


def test_acionamento_travado_nao_congela_execucao(pasta_rpa, tmp_path):
    """Console do PAD travado (ex.: diálogo aberto): o acionamento não pode ficar preso para sempre."""
    import threading
    cfg = criar_cfg(pasta_rpa, tmp_path / "estado", PAD_TEMPO_LIMITE_ACIONAMENTO_S="0.3")
    pad = PadSimulado(pasta_rpa)
    liberar = threading.Event()

    class ControladorTravado(ControladorSimulado):
        def acionar(self):
            liberar.wait(5)
            return super().acionar()

    controlador = ControladorTravado(pad)
    servico = ServicoExecucoes(cfg, fabrica_controlador=lambda m, c: controlador, robo_ativo=pad.robo_ativo)
    final = esperar_fim(servico, servico.iniciar("interface_grafica").id_execucao, limite=5)
    liberar.set()
    assert final.situacao == "falha_automacao"
    assert final.motivo_erro == FALHA_AO_INICIAR
    assert "não respondeu" in final.mensagem
