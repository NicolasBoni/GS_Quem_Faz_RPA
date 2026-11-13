"""Leitura e validação dos CSVs que formam o contrato com o Power Automate.

O fluxo PAD grava as linhas por concatenação simples (sem aspas). Por isso a
leitura aqui é tolerante: uma linha com quantidade de colunas diferente do
cabeçalho é reportada como inválida, em vez de derrubar a leitura do arquivo.
"""
from __future__ import annotations

import csv
import hashlib
import io
import os
import tempfile
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

COLUNAS_ENTRADA = ["numero_pedido", "categoria", "descricao", "bairro", "codigo_cliente", "situacao"]
COLUNAS_PROCESSADOS = ["numero_pedido", "categoria", "descricao", "bairro", "resultado", "motivo"]
COLUNAS_PUBLICAVEIS = ["numero_pedido", "categoria", "descricao", "bairro", "situacao"]
COLUNAS_HISTORICO = ["data_hora", "etapa", "numero_pedido", "resultado", "mensagem"]


@dataclass
class LinhaInvalida:
    numero_linha: int
    conteudo: str
    motivo: str


@dataclass
class LeituraCSV:
    caminho: Path
    existe: bool = False
    valido: bool = False
    erro: str | None = None
    linhas: list[dict[str, str]] = field(default_factory=list)
    linhas_invalidas: list[LinhaInvalida] = field(default_factory=list)
    modificado_em: datetime | None = None
    tamanho_bytes: int = 0
    hash_conteudo: str | None = None
    tem_bom: bool = False


def _decodificar(bruto: bytes) -> tuple[str, bool]:
    tem_bom = bruto.startswith(b"\xef\xbb\xbf")
    texto = bruto.decode("utf-8-sig")
    return texto, tem_bom


def ler_csv(caminho: Path, colunas_esperadas: list[str]) -> LeituraCSV:
    """Lê um CSV do contrato, validando o cabeçalho exatamente."""
    leitura = LeituraCSV(caminho=caminho)
    if not caminho.is_file():
        leitura.erro = "Arquivo não encontrado."
        return leitura

    leitura.existe = True
    try:
        estado = caminho.stat()
        leitura.modificado_em = datetime.fromtimestamp(estado.st_mtime)
        leitura.tamanho_bytes = estado.st_size
        bruto = caminho.read_bytes()
    except OSError:
        leitura.erro = "Não foi possível ler o arquivo (pode estar em uso ou sem permissão)."
        return leitura

    leitura.hash_conteudo = hashlib.sha256(bruto).hexdigest()
    try:
        texto, leitura.tem_bom = _decodificar(bruto)
    except UnicodeDecodeError:
        leitura.erro = "O arquivo não está em UTF-8."
        return leitura

    if not texto.strip():
        leitura.erro = "Arquivo vazio (sem cabeçalho)."
        return leitura

    leitor = csv.reader(io.StringIO(texto, newline=""))
    try:
        cabecalho = [c.strip() for c in next(leitor)]
    except (StopIteration, csv.Error):
        leitura.erro = "Cabeçalho ilegível."
        return leitura

    if cabecalho != colunas_esperadas:
        leitura.erro = (
            "Cabeçalho inesperado. Esperado: " + ",".join(colunas_esperadas)
            + " | Encontrado: " + ",".join(cabecalho)
        )
        return leitura

    numero_linha = 1
    try:
        for valores in leitor:
            numero_linha += 1
            if not valores or all(not v.strip() for v in valores) and len(valores) <= 1:
                continue  # linha em branco (ex.: quebra final)
            if len(valores) != len(colunas_esperadas):
                leitura.linhas_invalidas.append(
                    LinhaInvalida(
                        numero_linha=numero_linha,
                        conteudo=",".join(valores)[:300],
                        motivo=f"Esperadas {len(colunas_esperadas)} colunas, encontradas {len(valores)}.",
                    )
                )
                continue
            linha = {col: (val or "").strip() for col, val in zip(colunas_esperadas, valores)}
            linha["_linha"] = str(numero_linha)
            leitura.linhas.append(linha)
    except csv.Error as exc:
        leitura.linhas_invalidas.append(LinhaInvalida(numero_linha, "", f"Erro de formato CSV: {exc}"))

    leitura.valido = True
    return leitura


def hash_arquivo(caminho: Path) -> str | None:
    try:
        return hashlib.sha256(caminho.read_bytes()).hexdigest()
    except OSError:
        return None


def gravar_atomico(caminho: Path, conteudo: str) -> None:
    """Grava o conteúdo num temporário e substitui o arquivo de uma só vez."""
    caminho.parent.mkdir(parents=True, exist_ok=True)
    descritor, temporario = tempfile.mkstemp(dir=str(caminho.parent), prefix=".tmp_", suffix=".csv")
    try:
        with os.fdopen(descritor, "w", encoding="utf-8", newline="") as arquivo:
            arquivo.write(conteudo)
        os.replace(temporario, caminho)
    except BaseException:
        try:
            os.unlink(temporario)
        except OSError:
            pass
        raise


# ------------------------------------------------------- proteção na exportação
PREFIXOS_PERIGOSOS = ("=", "+", "-", "@", "\t", "\r")


def neutralizar_celula(valor: str) -> str:
    """Proteção contra CSV/Formula injection em arquivos exportados para planilhas."""
    if valor and valor.startswith(PREFIXOS_PERIGOSOS):
        return "'" + valor
    return valor


def exportar_csv(colunas: list[str], linhas: list[dict[str, str]]) -> str:
    saida = io.StringIO()
    escritor = csv.writer(saida, lineterminator="\r\n", quoting=csv.QUOTE_MINIMAL)
    escritor.writerow(colunas)
    for linha in linhas:
        escritor.writerow([neutralizar_celula(str(linha.get(c, ""))) for c in colunas])
    return "﻿" + saida.getvalue()
