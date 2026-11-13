"""Detecção dos processos do Power Automate Desktop.

Usa somente o utilitário `tasklist` do Windows, com argumentos fixos.
Nenhum dado vindo do cliente é repassado para a linha de comando.
"""
from __future__ import annotations

import csv
import io
import subprocess
import sys


def listar_processos() -> set[str]:
    """Retorna os nomes (em minúsculas) dos processos em execução na sessão."""
    if sys.platform != "win32":
        return set()
    try:
        saida = subprocess.run(
            ["tasklist", "/FO", "CSV", "/NH"],
            capture_output=True,
            text=True,
            timeout=10,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            check=False,
        ).stdout
    except (OSError, subprocess.SubprocessError):
        return set()
    nomes = set()
    for linha in csv.reader(io.StringIO(saida)):
        if linha:
            nomes.add(linha[0].strip().lower())
    return nomes


def algum_ativo(nomes_processos: list[str], processos: set[str] | None = None) -> bool:
    processos = listar_processos() if processos is None else processos
    return any(n.lower() in processos for n in nomes_processos)
