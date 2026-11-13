"""Detecção de término do fluxo QuemFaz_Validacao_Pedidos, sem alterar o fluxo.

Fatos do fluxo exportado usados aqui (ver power-automate/export fluxo/GS_quem_faz_Automate.txt):

* `dataehoradaexecucao` é capturada UMA vez na REGION inicializacao e gravada
  em todas as linhas do log -> funciona como "marca" da execução do RPA.
* A REGION preparacao sobrescreve os três arquivos de saída com o cabeçalho.
* A linha `<marca>,Resumo,LOTE,CONCLUIDO,Total analisado: ...` é a ÚLTIMA
  gravação antes do GOTO FINALIZACAO_SUCESSO. Ela só existe no caminho de sucesso.
* FINALIZACAO_SUCESSO e FINALIZACAO_ERRO terminam com `EXIT Code: 0` -> o código
  de saída NÃO prova sucesso.
* Uma falha na leitura do CSV desvia para FINALIZACAO_ERRO antes de tocar nos
  arquivos de saída -> os arquivos antigos continuam lá e não podem ser aceitos.

O detector também aceita `controle/status_execucao.json`, se esse recurso for
adicionado ao PAD; quando o identificador bate, ele é usado como confirmação
adicional. O fluxo exportado atualmente não grava esse arquivo.
"""
from __future__ import annotations

import json
import re
from collections import Counter
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path

from .csv_contrato import (
    COLUNAS_HISTORICO,
    COLUNAS_PROCESSADOS,
    COLUNAS_PUBLICAVEIS,
    hash_arquivo,
    ler_csv,
)

FORMATO_MARCA = "%Y-%m-%d %H:%M:%S"
REGEX_RESUMO = re.compile(
    r"Total analisado:\s*(\d+);\s*aprovados:\s*(\d+);\s*reprovados:\s*(\d+);"
    r"\s*duplicados:\s*(\d+);\s*ignorados:\s*(\d+)",
    re.IGNORECASE,
)


@dataclass
class EstadoArquivo:
    existe: bool
    mtime_ns: int | None
    hash: str | None

    @classmethod
    def capturar(cls, caminho: Path) -> "EstadoArquivo":
        if not caminho.is_file():
            return cls(False, None, None)
        return cls(True, caminho.stat().st_mtime_ns, hash_arquivo(caminho))

    def para_dict(self) -> dict:
        return {"existe": self.existe, "mtime_ns": self.mtime_ns, "hash": self.hash}

    @classmethod
    def de_dict(cls, d: dict) -> "EstadoArquivo":
        return cls(d.get("existe", False), d.get("mtime_ns"), d.get("hash"))


@dataclass
class Marco:
    """Fotografia tirada imediatamente antes de acionar o RPA."""

    inicio: datetime
    historico: EstadoArquivo
    processados: EstadoArquivo
    publicaveis: EstadoArquivo
    total_entrada: int

    def para_dict(self) -> dict:
        return {
            "inicio": self.inicio.isoformat(),
            "historico": self.historico.para_dict(),
            "processados": self.processados.para_dict(),
            "publicaveis": self.publicaveis.para_dict(),
            "total_entrada": self.total_entrada,
        }

    @classmethod
    def de_dict(cls, d: dict) -> "Marco":
        return cls(
            inicio=datetime.fromisoformat(d["inicio"]),
            historico=EstadoArquivo.de_dict(d["historico"]),
            processados=EstadoArquivo.de_dict(d["processados"]),
            publicaveis=EstadoArquivo.de_dict(d["publicaveis"]),
            total_entrada=d.get("total_entrada", 0),
        )


@dataclass
class AnaliseSaidas:
    historico_alterado: bool = False
    processados_alterado: bool = False
    publicaveis_alterado: bool = False
    marca_rpa: str | None = None          # data_hora gravada pelo fluxo nesta execução
    marca_pertence_execucao: bool = False  # marca >= início da execução
    linha_resumo: str | None = None
    contagem_resumo: dict[str, int] | None = None
    linhas_validacao: int = 0
    problemas: list[str] = field(default_factory=list)
    contagem_processados: dict[str, int] = field(default_factory=dict)
    total_processados: int = 0
    total_publicaveis: int = 0

    @property
    def iniciou(self) -> bool:
        return self.marca_pertence_execucao

    @property
    def concluiu(self) -> bool:
        return self.marca_pertence_execucao and self.contagem_resumo is not None


def _alterado(caminho: Path, antes: EstadoArquivo) -> bool:
    depois = EstadoArquivo.capturar(caminho)
    if not depois.existe:
        return False
    return (not antes.existe) or depois.mtime_ns != antes.mtime_ns or depois.hash != antes.hash


def ler_marca(texto: str) -> datetime | None:
    try:
        return datetime.strptime(texto.strip(), FORMATO_MARCA)
    except ValueError:
        return None


def analisar_saidas(cfg, marco: Marco) -> AnaliseSaidas:
    analise = AnaliseSaidas(
        historico_alterado=_alterado(cfg.caminho_historico, marco.historico),
        processados_alterado=_alterado(cfg.caminho_processados, marco.processados),
        publicaveis_alterado=_alterado(cfg.caminho_publicaveis, marco.publicaveis),
    )
    if not analise.historico_alterado:
        return analise

    historico = ler_csv(cfg.caminho_historico, COLUNAS_HISTORICO)
    if not historico.valido:
        # Pode ser o instante em que o PAD está regravando o arquivo.
        analise.problemas.append(f"Histórico ilegível no momento: {historico.erro}")
        return analise
    if not historico.linhas:
        return analise  # só cabeçalho: preparação concluída, nenhuma linha ainda

    marca_texto = historico.linhas[0]["data_hora"]
    marca = ler_marca(marca_texto)
    analise.marca_rpa = marca_texto
    limite = marco.inicio.replace(microsecond=0) - timedelta(seconds=cfg.tolerancia_relogio)
    analise.marca_pertence_execucao = marca is not None and marca >= limite
    if not analise.marca_pertence_execucao:
        analise.problemas.append("O histórico foi alterado, mas a marca de data/hora é anterior ao início desta execução.")
        return analise

    analise.linhas_validacao = sum(1 for l in historico.linhas if l["etapa"] == "Validacao")
    for linha in historico.linhas:
        if (linha["etapa"] == "Resumo" and linha["numero_pedido"] == "LOTE"
                and linha["resultado"] == "CONCLUIDO" and linha["data_hora"] == marca_texto):
            m = REGEX_RESUMO.search(linha["mensagem"])
            if m:
                analise.linha_resumo = linha["mensagem"]
                analise.contagem_resumo = {
                    "total": int(m.group(1)), "aprovados": int(m.group(2)), "reprovados": int(m.group(3)),
                    "duplicados": int(m.group(4)), "ignorados": int(m.group(5)),
                }
    return analise


def conferir_consistencia(cfg, marco: Marco, analise: AnaliseSaidas) -> list[str]:
    """Confere se os três arquivos são da mesma execução e batem entre si."""
    problemas: list[str] = []
    if not analise.concluiu:
        return ["Resumo do lote não encontrado no histórico desta execução."]
    if not analise.processados_alterado:
        problemas.append("pedidos_processados.csv não foi atualizado nesta execução.")
    if not analise.publicaveis_alterado:
        problemas.append("pedidos_publicaveis.csv não foi atualizado nesta execução.")

    processados = ler_csv(cfg.caminho_processados, COLUNAS_PROCESSADOS)
    publicaveis = ler_csv(cfg.caminho_publicaveis, COLUNAS_PUBLICAVEIS)
    if not processados.valido:
        problemas.append(f"pedidos_processados.csv inválido: {processados.erro}")
    if not publicaveis.valido:
        problemas.append(f"pedidos_publicaveis.csv inválido: {publicaveis.erro}")
    if problemas:
        return problemas

    if processados.linhas_invalidas:
        problemas.append(f"{len(processados.linhas_invalidas)} linha(s) de pedidos_processados.csv com colunas deslocadas.")
    if publicaveis.linhas_invalidas:
        problemas.append(f"{len(publicaveis.linhas_invalidas)} linha(s) de pedidos_publicaveis.csv com colunas deslocadas.")

    contagem = Counter(l["resultado"] for l in processados.linhas)
    analise.contagem_processados = dict(contagem)
    analise.total_processados = len(processados.linhas) + len(processados.linhas_invalidas)
    analise.total_publicaveis = len(publicaveis.linhas) + len(publicaveis.linhas_invalidas)
    resumo = analise.contagem_resumo or {}

    if analise.total_processados != resumo.get("total"):
        problemas.append(f"Resumo informa {resumo.get('total')} pedidos, mas o arquivo de resultados tem {analise.total_processados}.")
    if marco.total_entrada and resumo.get("total") != marco.total_entrada:
        problemas.append(f"O lote enviado tinha {marco.total_entrada} pedidos, o RPA analisou {resumo.get('total')}.")
    for chave, rotulo in (("aprovados", "APROVADO"), ("reprovados", "REPROVADO"),
                          ("duplicados", "DUPLICADO"), ("ignorados", "IGNORADO")):
        if not processados.linhas_invalidas and contagem.get(rotulo, 0) != resumo.get(chave):
            problemas.append(f"Divergência em {rotulo}: resumo={resumo.get(chave)}, arquivo={contagem.get(rotulo, 0)}.")
    if analise.total_publicaveis != resumo.get("aprovados"):
        problemas.append(f"Publicáveis ({analise.total_publicaveis}) diferente de aprovados ({resumo.get('aprovados')}).")
    return problemas


def ler_status_json(cfg, id_execucao: str) -> dict | None:
    """Lê o status opcional gravado pelo fluxo (se o trecho opcional foi adicionado)."""
    caminho = cfg.caminho_controle_rpa / "status_execucao.json"
    try:
        dados = json.loads(caminho.read_text(encoding="utf-8-sig"))
    except (OSError, ValueError):
        return None
    if not isinstance(dados, dict) or str(dados.get("identificador_execucao", "")).strip() != id_execucao:
        return None
    return {k: str(v)[:500] for k, v in dados.items()}
