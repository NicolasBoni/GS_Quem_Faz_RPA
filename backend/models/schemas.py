"""Contratos de entrada e saída da API (Pydantic)."""
from __future__ import annotations

import re
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, field_validator

# --------------------------------------------------------------------------
# Regras de compatibilidade com o fluxo PAD.
# O fluxo grava "%numero%,%categoria%,%descricao%,..." sem aspas: uma vírgula,
# aspas ou quebra de linha num campo deslocaria as colunas da saída.
# Também bloqueamos prefixos de fórmula (CSV injection).
# --------------------------------------------------------------------------
TEXTO_SEGURO = re.compile(r"^[0-9A-Za-zÀ-ÖØ-öø-ÿ .()/ºª°'_-]*$")
CODIGO_SEGURO = re.compile(r"^[A-Z0-9_-]*$")
SITUACAO_SEGURA = re.compile(r"^[A-Z_]*$")
PREFIXOS_FORMULA = ("=", "+", "-", "@")

ResultadoRPA = Literal["APROVADO", "REPROVADO", "DUPLICADO", "IGNORADO"]

SituacaoExecucao = Literal[
    "aguardando_execucao",
    "iniciando_automacao",
    "processamento_em_andamento",
    "conferindo_resultados",
    "concluido",
    "falha_automacao",
    "indeterminado",
    "cancelado",
]


def _validar_texto(valor: str, campo: str) -> str:
    if any(ch in valor for ch in (",", '"', "\n", "\r", ";", "\t")):
        raise ValueError(f"{campo}: não use vírgulas, aspas, ponto e vírgula nem quebras de linha "
                         "(o fluxo RPA grava o CSV sem escapar esses caracteres).")
    if valor.startswith(PREFIXOS_FORMULA):
        raise ValueError(f"{campo}: não pode começar com = + - ou @.")
    if not TEXTO_SEGURO.match(valor):
        raise ValueError(f"{campo}: contém caracteres não permitidos.")
    return valor


class NovaSolicitacao(BaseModel):
    """Solicitação de teste a ser anexada ao `pedidos_entrada.csv`.

    Campos podem ficar vazios de propósito, para testar as regras de reprovação
    do RPA — exatamente como no lote de exemplo.
    """

    numero_pedido: str = Field("", max_length=20, description="Ex.: PED-010. Vazio testa a reprovação.")
    categoria: str = Field("", max_length=30, description="LIMPEZA, PINTURA, MANUTENCAO ou outra (teste).")
    descricao: str = Field("", max_length=120)
    bairro: str = Field("", max_length=60)
    codigo_cliente: str = Field("", max_length=20)
    situacao: str = Field("PENDENTE", max_length=20)

    @field_validator("numero_pedido", "codigo_cliente", "categoria")
    @classmethod
    def _codigo(cls, valor: str, info) -> str:
        valor = valor.strip().upper()
        if valor.startswith(PREFIXOS_FORMULA) or not CODIGO_SEGURO.match(valor):
            raise ValueError(f"{info.field_name}: use apenas letras sem acento, números, hífen ou sublinhado.")
        return valor

    @field_validator("situacao")
    @classmethod
    def _situacao(cls, valor: str) -> str:
        valor = valor.strip().upper()
        if not SITUACAO_SEGURA.match(valor):
            raise ValueError("situacao: use apenas letras maiúsculas sem acento (ex.: PENDENTE).")
        return valor

    @field_validator("descricao", "bairro")
    @classmethod
    def _texto(cls, valor: str, info) -> str:
        _validar_texto(valor, info.field_name)  # rejeita \n, \r, \t antes de normalizar
        return " ".join(valor.split())


class LinhaInvalidaSaida(BaseModel):
    numero_linha: int
    conteudo: str
    motivo: str


class InfoArquivo(BaseModel):
    nome: str
    existe: bool
    valido: bool
    erro: str | None = None
    modificado_em: datetime | None = None
    total_linhas: int = 0
    linhas_invalidas: list[LinhaInvalidaSaida] = []


class Solicitacao(BaseModel):
    linha: int
    numero_pedido: str
    categoria: str
    descricao: str
    bairro: str
    codigo_cliente: str
    situacao: str
    ultimo_resultado: str | None = None
    ultimo_motivo: str | None = None


class RespostaSolicitacoes(BaseModel):
    arquivo: InfoArquivo
    resultados_correspondem_ao_lote: bool
    edicao_bloqueada: bool
    itens: list[Solicitacao]


class Resultado(BaseModel):
    linha: int
    numero_pedido: str
    categoria: str
    descricao: str
    bairro: str
    resultado: str
    motivo: str


class RespostaResultados(BaseModel):
    arquivo: InfoArquivo
    contagem: dict[str, int]
    itens: list[Resultado]


class Publicavel(BaseModel):
    linha: int
    numero_pedido: str
    categoria: str
    descricao: str
    bairro: str
    situacao_rpa: str
    situacao_exibida: str


class RespostaPublicaveis(BaseModel):
    arquivo: InfoArquivo
    itens: list[Publicavel]


class EventoHistorico(BaseModel):
    linha: int
    data_hora: str
    etapa: str
    numero_pedido: str
    resultado: str
    mensagem: str


class EtapaExecucao(BaseModel):
    data_hora: datetime
    situacao: SituacaoExecucao
    mensagem: str


class Evidencias(BaseModel):
    robo_detectado: bool = False
    robo_encerrado: bool = False
    historico_atualizado: bool = False
    processados_atualizado: bool = False
    publicaveis_atualizado: bool = False
    marca_execucao_rpa: str | None = None
    linha_resumo: str | None = None
    status_json: dict | None = None


class ResumoExecucao(BaseModel):
    total: int = 0
    aprovados: int = 0
    reprovados: int = 0
    duplicados: int = 0
    ignorados: int = 0
    publicaveis: int = 0


class Execucao(BaseModel):
    id_execucao: str
    modo: str
    modo_solicitado: str
    nome_fluxo: str
    situacao: SituacaoExecucao
    data_inicio: datetime
    data_fim: datetime | None = None
    mensagem: str = ""
    motivo_erro: str | None = None
    etapas: list[EtapaExecucao] = []
    evidencias: Evidencias = Evidencias()
    resumo: ResumoExecucao | None = None
    hash_entrada: str | None = None
    pasta_arquivo: str | None = None
    externa: bool = False

    @property
    def ativa(self) -> bool:
        return self.situacao in ("aguardando_execucao", "iniciando_automacao",
                                 "processamento_em_andamento", "conferindo_resultados")


class PedidoExecucao(BaseModel):
    modo: Literal["assistido", "atalho", "interface_grafica", "url_local"] | None = Field(
        None, description="Modo de acionamento. Vazio usa modo_padrao de backend/config.py."
    )


class RespostaHistorico(BaseModel):
    arquivo: InfoArquivo
    id_execucao_arquivo: str | None
    eventos: list[EventoHistorico]
    execucoes: list[Execucao]


class Diagnostico(BaseModel):
    nome: str
    ok: bool
    detalhe: str


class Saude(BaseModel):
    api: str
    versao: str
    modo_padrao: str
    modos_permitidos: list[str]
    nome_fluxo: str
    console_pad_ativo: bool
    robo_pad_ativo: bool
    execucao_ativa: str | None
    diagnosticos: list[Diagnostico]


class Estatisticas(BaseModel):
    total_solicitacoes: int
    pendentes: int
    aprovados: int
    reprovados: int
    duplicados: int
    ignorados: int
    publicaveis: int
    ultimo_processamento: str | None
    ultimo_processamento_fonte: str | None
    resultados_correspondem_ao_lote: bool
    situacao_automacao: str
    execucao_ativa: Execucao | None
    ultima_execucao: Execucao | None
    categorias: list[dict]
    execucoes_recentes: list[Execucao]
