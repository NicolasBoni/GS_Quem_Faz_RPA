"""Fixtures dos testes automatizados (SIMULADOS).

Nenhum teste aqui aciona o Power Automate Desktop. O "PAD simulado" apenas
REPRODUZ os arquivos gravados por uma execução real do fluxo (tests/dados_teste/
saida_real_2026-11-10), atualizando a marca de data/hora, como o fluxo faz.
Ele não reimplementa as regras de validação.

Testes reais de ponta a ponta ficam em tests/e2e e só rodam com QUEMFAZ_E2E_REAL=1.
"""
from __future__ import annotations

import os
import shutil
import sys
import tempfile
import threading
import time
from datetime import datetime
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "backend"))
# Impede que importar main.py toque no estado real do backend.
os.environ["QUEMFAZ_PASTA_ESTADO"] = tempfile.mkdtemp(prefix="quemfaz_estado_import_")
os.environ["QUEMFAZ_TOKEN_ADMIN"] = ""

from config import Configuracao  # noqa: E402
from integrations.power_automate.base import ControladorPAD, ErroControlador, ResultadoAcionamento  # noqa: E402

EXEMPLOS = RAIZ / "tests" / "dados_teste"
SAIDA_REAL = EXEMPLOS / "saida_real_2026-11-10"


@pytest.fixture
def pasta_rpa(tmp_path: Path) -> Path:
    base = tmp_path / "QuemFaz_RPA"
    for sub in ("dados", "resultados", "logs"):
        (base / sub).mkdir(parents=True)
    shutil.copy(EXEMPLOS / "pedidos_entrada.csv", base / "dados" / "pedidos_entrada.csv")
    return base


def criar_cfg(base: Path, estado: Path, **extra) -> Configuracao:
    valores = dict(
        QUEMFAZ_PASTA_BASE=str(base),
        QUEMFAZ_PASTA_ESTADO=str(estado),
        QUEMFAZ_TOKEN_ADMIN="",
        PAD_NOME_FLUXO="QuemFaz_Validacao_Pedidos",
        PAD_MODO="assistido",
        PAD_MODOS_PERMITIDOS="assistido,atalho,interface_grafica",
        PAD_FALLBACK_ASSISTIDO="false",
        PAD_INTERVALO_VERIFICACAO_S="0.05",
        PAD_TEMPO_LIMITE_ACIONAMENTO_S="2",
        PAD_TEMPO_LIMITE_INICIO_S="1",
        PAD_TEMPO_LIMITE_ASSISTIDO_S="1.5",
        PAD_TEMPO_LIMITE_EXECUCAO_S="6",
        PAD_TEMPO_ESPERA_ENCERRAMENTO_S="0.5",
        PAD_TOLERANCIA_RELOGIO_S="2",
    )
    valores.update(extra)
    return Configuracao(**valores)


@pytest.fixture
def cfg(pasta_rpa: Path, tmp_path: Path) -> Configuracao:
    return criar_cfg(pasta_rpa, tmp_path / "estado")


def copiar_saida_real(base: Path, marca: str | None = None) -> None:
    """Coloca os arquivos de uma execução real na pasta (opcionalmente com outra marca)."""
    for nome, sub in (("pedidos_processados.csv", "resultados"), ("pedidos_publicaveis.csv", "resultados"),
                      ("historico_execucao.csv", "logs")):
        texto = (SAIDA_REAL / nome).read_bytes().decode("utf-8-sig")
        if marca:
            texto = texto.replace("2026-11-10 23:14:02", marca)
        (base / sub / nome).write_bytes(("﻿" + texto).encode("utf-8"))


class PadSimulado:
    """Imita o comportamento OBSERVÁVEL do PAD, reproduzindo saídas reais gravadas.

    cenario:
      sucesso            -> regrava os 3 arquivos linha a linha e grava o resumo
      erro_leitura       -> robô abre e fecha sem tocar nos arquivos (ON BLOCK ERROR da leitura)
      erro_processamento -> grava cabeçalhos e algumas linhas, encerra sem resumo
      inconsistente      -> grava tudo, mas publicaveis com uma linha a menos
      nao_inicia         -> nada acontece
      robo_invisivel     -> sucesso sem que o processo do robô seja detectável
    """

    def __init__(self, base: Path, cenario: str = "sucesso", atraso: float = 0.02):
        self.base = base
        self.cenario = cenario
        self.atraso = atraso
        self.robo = False
        self.acionamentos = 0
        self.thread: threading.Thread | None = None

    def robo_ativo(self) -> bool:
        return self.robo

    def disparar(self) -> None:
        self.acionamentos += 1
        if self.cenario == "nao_inicia":
            return
        self.thread = threading.Thread(target=self._rodar, daemon=True)
        self.thread.start()

    def _linhas(self, nome: str) -> list[str]:
        return (SAIDA_REAL / nome).read_bytes().decode("utf-8-sig").splitlines()

    def _escrever(self, caminho: Path, linhas: list[str]) -> None:
        caminho.write_bytes(("﻿" + "\r\n".join(linhas) + "\r\n").encode("utf-8"))

    def _rodar(self) -> None:
        self.robo = self.cenario != "robo_invisivel"
        time.sleep(0.1)
        marca = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        proc = self.base / "resultados" / "pedidos_processados.csv"
        pub = self.base / "resultados" / "pedidos_publicaveis.csv"
        hist = self.base / "logs" / "historico_execucao.csv"
        if self.cenario == "erro_leitura":
            time.sleep(0.2)
            self.robo = False
            return
        p_linhas = self._linhas("pedidos_processados.csv")
        u_linhas = self._linhas("pedidos_publicaveis.csv")
        h_linhas = [l.replace("2026-11-10 23:14:02", marca) for l in self._linhas("historico_execucao.csv")]
        for caminho, cab in ((proc, p_linhas[0]), (pub, u_linhas[0]), (hist, h_linhas[0])):
            self._escrever(caminho, [cab])
        limite = 4 if self.cenario == "erro_processamento" else len(p_linhas)
        for i in range(1, limite):
            self._escrever(proc, p_linhas[: i + 1])
            self._escrever(hist, h_linhas[: i + 1])
            time.sleep(self.atraso)
        if self.cenario != "erro_processamento":
            publicaveis = u_linhas[:-1] if self.cenario == "inconsistente" else u_linhas
            self._escrever(pub, publicaveis)
            self._escrever(hist, h_linhas)  # inclui a linha Resumo,LOTE,CONCLUIDO
            time.sleep(0.2)  # diálogo final do fluxo
        self.robo = False


class ControladorSimulado(ControladorPAD):
    modo = "atalho"

    def __init__(self, pad: PadSimulado, falha: ErroControlador | None = None, automatico: bool = True):
        super().__init__("QuemFaz_Validacao_Pedidos")
        self.pad = pad
        self.falha = falha
        self.automatico = automatico

    def verificar(self):
        return True, "simulado"

    def acionar(self):
        if self.falha:
            raise self.falha
        self.pad.disparar()
        return ResultadoAcionamento(self.automatico, "simulado")


def esperar_fim(servico, id_execucao: str, limite: float = 10.0):
    fim = time.monotonic() + limite
    while time.monotonic() < fim:
        execucao = servico.obter(id_execucao)
        if not execucao.ativa:
            return execucao
        time.sleep(0.05)
    raise AssertionError("A execução não terminou dentro do limite do teste.")
