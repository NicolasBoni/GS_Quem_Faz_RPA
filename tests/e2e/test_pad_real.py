"""[REAL] Teste de ponta a ponta com o Power Automate Desktop VERDADEIRO.

NÃO é executado por padrão. Requisitos:
  * Windows com sessão desbloqueada e o PAD instalado e conectado;
  * backend em execução (scripts\\iniciar_backend.bat);
  * nome_fluxo em backend/config.py igual ao nome do fluxo em "Meus fluxos";
  * lote de entrada = lote de exemplo de 11 pedidos.

Execução:
  $env:QUEMFAZ_E2E_REAL="1"; $env:QUEMFAZ_E2E_MODO="interface_grafica"
  .venv\\Scripts\\python.exe -m pytest tests\\e2e -m e2e_real -s

O teste aciona o RPA pela API (o mesmo caminho do botão da interface) e confere
os arquivos REALMENTE gravados pelo PAD com o resultado esperado.
"""
from __future__ import annotations

import os
import time

import httpx
import pytest

from conftest import EXEMPLOS
from config import TOKEN_ADMIN

pytestmark = [
    pytest.mark.e2e_real,
    pytest.mark.skipif(os.environ.get("QUEMFAZ_E2E_REAL") != "1", reason="Defina QUEMFAZ_E2E_REAL=1 para usar o PAD real."),
]

API = os.environ.get("QUEMFAZ_API_URL", "http://127.0.0.1:8000")


def test_execucao_real_do_fluxo_com_11_pedidos():
    cabecalho = {"X-QuemFaz-Admin": TOKEN_ADMIN}
    cliente = httpx.Client(base_url=API, timeout=30)
    saude = cliente.get("/api/health").json()
    assert saude["execucao_ativa"] is None, "Há outra execução ativa."

    restaurado = cliente.post("/api/solicitacoes/restaurar-exemplo", headers=cabecalho)
    assert restaurado.status_code == 200, restaurado.text

    modo = os.environ.get("QUEMFAZ_E2E_MODO", saude["modo_padrao"])
    inicio = cliente.post("/api/rpa/executar", json={"modo": modo}, headers=cabecalho)
    assert inicio.status_code == 202, inicio.text
    id_execucao = inicio.json()["id_execucao"]
    print(f"\nExecução {id_execucao} (modo {modo}). Se o modo for assistido, execute o fluxo no PAD agora.")

    limite = time.monotonic() + float(os.environ.get("QUEMFAZ_E2E_LIMITE_S", "900"))
    situacao = None
    while time.monotonic() < limite:
        execucao = cliente.get(f"/api/rpa/status/{id_execucao}").json()
        if execucao["situacao"] != situacao:
            situacao = execucao["situacao"]
            print(f"  -> {situacao}: {execucao['mensagem']}")
        if situacao not in ("aguardando_execucao", "iniciando_automacao", "processamento_em_andamento", "conferindo_resultados"):
            break
        time.sleep(2)

    assert situacao == "concluido", f"Execução terminou como {situacao}: {execucao.get('motivo_erro')}"
    resumo = execucao["resumo"]
    assert (resumo["total"], resumo["aprovados"], resumo["reprovados"], resumo["duplicados"], resumo["ignorados"]) == (11, 4, 5, 1, 1)
    assert execucao["evidencias"]["linha_resumo"]

    resultados = cliente.get("/api/resultados").json()["itens"]
    esperado = [l.split(",") for l in (EXEMPLOS / "resultado_esperado.csv").read_text(encoding="utf-8").splitlines()[1:]]
    assert [(r["numero_pedido"], r["resultado"]) for r in resultados] == [(n, r) for n, r in esperado]

    publicaveis = cliente.get("/api/publicaveis").json()["itens"]
    assert [p["numero_pedido"] for p in publicaveis] == ["PED-001", "PED-002", "PED-003", "PED-008"]

    estatisticas = cliente.get("/api/estatisticas").json()
    assert estatisticas["resultados_correspondem_ao_lote"] is True
    assert estatisticas["ultima_execucao"]["id_execucao"] == id_execucao
