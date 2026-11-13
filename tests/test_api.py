"""[SIMULADO] Endpoints REST: conversão para JSON, dashboard, cadastro e segurança."""
import pytest
from fastapi.testclient import TestClient

from conftest import ControladorSimulado, PadSimulado, copiar_saida_real, criar_cfg, esperar_fim
from main import criar_app
from services.execucoes import ServicoExecucoes


def montar(cfg, pad):
    controlador = ControladorSimulado(pad)
    execucoes = ServicoExecucoes(cfg, fabrica_controlador=lambda m, c: controlador, robo_ativo=pad.robo_ativo)
    return TestClient(criar_app(cfg, execucoes)), execucoes


@pytest.fixture
def cliente(cfg, pasta_rpa):
    pad = PadSimulado(pasta_rpa)
    c, execucoes = montar(cfg, pad)
    c.pad, c.execucoes = pad, execucoes
    return c


def test_health(cliente):
    dados = cliente.get("/api/health").json()
    assert dados["api"] == "ok"
    assert "assistido" in dados["modos_permitidos"]


def test_solicitacoes(cliente):
    dados = cliente.get("/api/solicitacoes").json()
    assert dados["arquivo"]["valido"] and len(dados["itens"]) == 11
    assert dados["itens"][0]["codigo_cliente"] == "CLI-001"
    assert dados["resultados_correspondem_ao_lote"] is False


def test_resultados_e_publicaveis_vazios_sem_execucao(cliente):
    assert cliente.get("/api/resultados").json()["arquivo"]["existe"] is False
    assert cliente.get("/api/publicaveis").json()["itens"] == []
    est = cliente.get("/api/estatisticas").json()
    assert est["aprovados"] == 0 and est["ultimo_processamento"] is None


def test_dashboard_atualiza_apos_execucao(cliente):
    antes = cliente.get("/api/estatisticas").json()
    assert antes["total_solicitacoes"] == 11 and antes["pendentes"] == 10
    resposta = cliente.post("/api/rpa/executar", json={"modo": "atalho"})
    assert resposta.status_code == 202
    final = esperar_fim(cliente.execucoes, resposta.json()["id_execucao"])
    assert final.situacao == "concluido"
    depois = cliente.get("/api/estatisticas").json()
    assert (depois["aprovados"], depois["reprovados"], depois["duplicados"], depois["ignorados"]) == (4, 5, 1, 1)
    assert depois["publicaveis"] == 4 and depois["resultados_correspondem_ao_lote"]
    categorias = {c["categoria"]: c for c in depois["categorias"]}
    assert categorias["JARDINAGEM"]["REPROVADO"] == 1
    status = cliente.get(f"/api/rpa/status/{final.id_execucao}").json()
    assert status["situacao"] == "concluido"
    pub = cliente.get("/api/publicaveis").json()["itens"]
    assert [p["numero_pedido"] for p in pub] == ["PED-001", "PED-002", "PED-003", "PED-008"]
    assert all(p["situacao_exibida"] == "Apto para publicação" for p in pub)
    hist = cliente.get("/api/historico").json()
    assert hist["id_execucao_arquivo"] == final.id_execucao
    sol = cliente.get("/api/solicitacoes").json()["itens"]
    assert sol[3]["ultimo_resultado"] == "REPROVADO"


def test_execucao_simultanea_via_api(cfg, pasta_rpa):
    pad = PadSimulado(pasta_rpa, atraso=0.2)
    c, execucoes = montar(cfg, pad)
    primeira = c.post("/api/rpa/executar", json={"modo": "atalho"})
    segunda = c.post("/api/rpa/executar", json={"modo": "atalho"})
    assert primeira.status_code == 202 and segunda.status_code == 409
    esperar_fim(execucoes, primeira.json()["id_execucao"])


def test_cadastro_de_solicitacao(cliente, pasta_rpa):
    nova = {"numero_pedido": "ped-010", "categoria": "limpeza", "descricao": "Limpeza de garagem",
            "bairro": "Butantã", "codigo_cliente": "CLI-011", "situacao": "PENDENTE"}
    resposta = cliente.post("/api/solicitacoes", json=nova)
    assert resposta.status_code == 201, resposta.text
    texto = (pasta_rpa / "dados" / "pedidos_entrada.csv").read_text(encoding="utf-8")
    assert texto.endswith("PED-010,LIMPEZA,Limpeza de garagem,Butantã,CLI-011,PENDENTE\n")
    assert len(cliente.get("/api/solicitacoes").json()["itens"]) == 12


@pytest.mark.parametrize("campo,valor", [
    ("descricao", "Pintura de sala, quarto"),
    ("descricao", 'Pintura "premium"'),
    ("descricao", "linha1\nlinha2"),
    ("descricao", "=HYPERLINK(\"x\")"),
    ("bairro", "@Mooca"),
    ("numero_pedido", "PED 01;"),
    ("categoria", "LIMPEZA,PINTURA"),
])
def test_cadastro_rejeita_conteudo_incompativel_com_o_rpa(cliente, pasta_rpa, campo, valor):
    antes = (pasta_rpa / "dados" / "pedidos_entrada.csv").read_bytes()
    nova = {"numero_pedido": "PED-020", "categoria": "LIMPEZA", "descricao": "Limpeza", "bairro": "Mooca",
            "codigo_cliente": "CLI-1", "situacao": "PENDENTE", campo: valor}
    resposta = cliente.post("/api/solicitacoes", json=nova)
    assert resposta.status_code == 422
    assert (pasta_rpa / "dados" / "pedidos_entrada.csv").read_bytes() == antes


def test_cadastro_bloqueado_durante_processamento(cfg, pasta_rpa):
    pad = PadSimulado(pasta_rpa, atraso=0.2)
    c, execucoes = montar(cfg, pad)
    execucao = c.post("/api/rpa/executar", json={"modo": "atalho"}).json()
    resposta = c.post("/api/solicitacoes", json={"numero_pedido": "PED-030", "descricao": "x", "bairro": "y"})
    assert resposta.status_code == 423
    assert c.get("/api/solicitacoes").json()["edicao_bloqueada"] is True
    esperar_fim(execucoes, execucao["id_execucao"])


def test_restaurar_exemplo(cliente, pasta_rpa):
    (pasta_rpa / "dados" / "pedidos_entrada.csv").write_text("numero_pedido,categoria,descricao,bairro,codigo_cliente,situacao\n", encoding="utf-8")
    resposta = cliente.post("/api/solicitacoes/restaurar-exemplo")
    assert resposta.status_code == 200 and resposta.json()["total"] == 11


def test_token_admin_exigido(pasta_rpa, tmp_path):
    cfg = criar_cfg(pasta_rpa, tmp_path / "estado", QUEMFAZ_TOKEN_ADMIN="segredo-local")
    c, _ = montar(cfg, PadSimulado(pasta_rpa, "nao_inicia"))
    assert c.post("/api/rpa/executar", json={}).status_code == 403
    assert c.post("/api/solicitacoes", json={}).status_code == 403
    assert c.get("/api/estatisticas").status_code == 200  # leitura continua livre


def test_cors_restrito(cliente):
    permitido = cliente.options("/api/rpa/executar", headers={
        "Origin": "http://127.0.0.1:8080", "Access-Control-Request-Method": "POST"})
    negado = cliente.options("/api/rpa/executar", headers={
        "Origin": "http://site-malicioso.example", "Access-Control-Request-Method": "POST"})
    assert permitido.headers.get("access-control-allow-origin") == "http://127.0.0.1:8080"
    assert "access-control-allow-origin" not in negado.headers


def test_path_traversal_no_id(cliente):
    assert cliente.get("/api/rpa/status/..%2F..%2Fsegredo").status_code == 404
    assert cliente.get("/api/historico", params={"id_execucao": "../../etc"}).status_code == 404
    assert cliente.get("/api/exportar/..%2F.env").status_code in (404, 422)


def test_exportacao_protegida(cliente, pasta_rpa):
    copiar_saida_real(pasta_rpa)
    resposta = cliente.get("/api/exportar/resultados")
    assert resposta.status_code == 200
    assert resposta.text.lstrip("﻿").startswith("numero_pedido,categoria")


def test_execucao_externa_identificada(cliente, pasta_rpa):
    copiar_saida_real(pasta_rpa)
    assert cliente.get("/api/historico").json()["id_execucao_arquivo"] == "PAD-20261110-231402"


def test_caminho_fora_da_base_rejeitado(pasta_rpa, tmp_path):
    with pytest.raises(ValueError):
        criar_cfg(pasta_rpa, tmp_path / "e", QUEMFAZ_ARQUIVO_ENTRADA="..\\..\\Windows\\win.ini")
