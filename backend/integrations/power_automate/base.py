"""Contrato comum dos controladores de acionamento do Power Automate Desktop."""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass


class ErroControlador(Exception):
    """Falha técnica ao acionar o PAD (não confundir com reprovação de pedido)."""

    def __init__(self, codigo: str, mensagem: str):
        super().__init__(mensagem)
        self.codigo = codigo
        self.mensagem = mensagem


# Códigos de erro padronizados
PAD_INDISPONIVEL = "pad_indisponivel"
FLUXO_NAO_ENCONTRADO = "fluxo_nao_encontrado"
FLUXO_AMBIGUO = "fluxo_ambiguo"
FALHA_AO_INICIAR = "falha_ao_iniciar"
DEPENDENCIA_AUSENTE = "dependencia_ausente"
CONFIGURACAO_INVALIDA = "configuracao_invalida"


@dataclass
class ResultadoAcionamento:
    automatico: bool  # False = o usuário precisa iniciar o fluxo manualmente
    mensagem: str


class ControladorPAD(ABC):
    """Cada controlador só sabe acionar o fluxo autorizado em configuração."""

    modo: str = ""
    descricao: str = ""

    def __init__(self, nome_fluxo: str):
        self.nome_fluxo = nome_fluxo

    @abstractmethod
    def verificar(self) -> tuple[bool, str]:
        """Diagnóstico rápido e sem efeitos colaterais."""

    @abstractmethod
    def acionar(self) -> ResultadoAcionamento:
        """Aciona o fluxo. Levanta ErroControlador em caso de falha técnica."""
