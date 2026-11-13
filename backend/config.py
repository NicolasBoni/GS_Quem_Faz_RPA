"""Configuração central do backend Quem Faz RPA.

Os valores usados na apresentação ficam definidos diretamente neste arquivo.
Não há leitura de arquivo de ambiente. Os aliases permitem sobrescritas nos testes.
"""
from __future__ import annotations

import re
from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

RAIZ_REPOSITORIO = Path(__file__).resolve().parents[1]
TOKEN_ADMIN = "mbgf_gPfTLZU0LKbVLmWzAc2_ONHe9ZS"  # Mesmo valor em frontend/config/config.php.

ModoAcionamento = Literal["assistido", "atalho", "interface_grafica", "url_local"]

FORMATO_ATALHO = re.compile(r"^(?:(?:ctrl|alt|shift|win)\+){1,4}(?:[a-z0-9]|f(?:[1-9]|1[0-2]))$")


class Configuracao(BaseSettings):
    model_config = SettingsConfigDict(
        extra="ignore",
    )

    # ---------------------------------------------------------------- caminhos
    pasta_base: Path = Field(RAIZ_REPOSITORIO, alias="QUEMFAZ_PASTA_BASE")  # padrão: raiz do projeto
    arquivo_entrada: str = Field(r"dados\pedidos_entrada.csv", alias="QUEMFAZ_ARQUIVO_ENTRADA")
    arquivo_processados: str = Field(r"resultados\pedidos_processados.csv", alias="QUEMFAZ_ARQUIVO_PROCESSADOS")
    arquivo_publicaveis: str = Field(r"resultados\pedidos_publicaveis.csv", alias="QUEMFAZ_ARQUIVO_PUBLICAVEIS")
    arquivo_historico: str = Field(r"logs\historico_execucao.csv", alias="QUEMFAZ_ARQUIVO_HISTORICO")
    # Pasta de controle dentro da pasta do RPA (ID da execução e status opcional).
    pasta_controle_rpa: str = Field("controle", alias="QUEMFAZ_PASTA_CONTROLE_RPA")
    # Estado interno da aplicação (execuções e arquivamento). Fora do Git.
    pasta_estado: Path = Field(RAIZ_REPOSITORIO / "var", alias="QUEMFAZ_PASTA_ESTADO")

    # ------------------------------------------------------------ servidor/API
    origens_permitidas: str = Field(
        "http://127.0.0.1:8080,http://localhost:8080", alias="QUEMFAZ_ORIGENS_PERMITIDAS"
    )
    token_admin: str = Field(TOKEN_ADMIN, alias="QUEMFAZ_TOKEN_ADMIN")

    # -------------------------------------------------------- Power Automate
    modo_padrao: ModoAcionamento = Field("interface_grafica", alias="PAD_MODO")
    modos_permitidos: str = Field("interface_grafica", alias="PAD_MODOS_PERMITIDOS")
    fallback_assistido: bool = Field(False, alias="PAD_FALLBACK_ASSISTIDO")
    nome_fluxo: str = Field("Quem_Faz_RPA", alias="PAD_NOME_FLUXO")
    atalho: str = Field("ctrl+alt+shift+q", alias="PAD_ATALHO")
    url_execucao: str = Field("", alias="PAD_URL_EXECUCAO")
    caminho_console: str = Field("", alias="PAD_CAMINHO_CONSOLE")
    processos_console: str = Field("PAD.Console.Host.exe", alias="PAD_PROCESSOS_CONSOLE")
    processos_robo: str = Field("PAD.Robot.exe,PAD.RobotV2.exe", alias="PAD_PROCESSOS_ROBO")

    # --------------------------------------------------------------- tempos
    intervalo_verificacao: float = Field(1.0, alias="PAD_INTERVALO_VERIFICACAO_S")
    # Tempo máximo para o controlador (atalho/UI/URL) concluir o acionamento.
    tempo_limite_acionamento: float = Field(90.0, alias="PAD_TEMPO_LIMITE_ACIONAMENTO_S")
    tempo_limite_inicio: float = Field(30.0, alias="PAD_TEMPO_LIMITE_INICIO_S")
    tempo_limite_assistido: float = Field(900.0, alias="PAD_TEMPO_LIMITE_ASSISTIDO_S")
    tempo_limite_execucao: float = Field(600.0, alias="PAD_TEMPO_LIMITE_EXECUCAO_S")
    # Após o resumo ser gravado o fluxo mostra um diálogo (12 s) antes de encerrar.
    tempo_espera_encerramento: float = Field(40.0, alias="PAD_TEMPO_ESPERA_ENCERRAMENTO_S")
    tolerancia_relogio: float = Field(2.0, alias="PAD_TOLERANCIA_RELOGIO_S")

    @field_validator("atalho")
    @classmethod
    def _validar_atalho(cls, valor: str) -> str:
        valor = valor.strip().lower().replace(" ", "")
        if not FORMATO_ATALHO.match(valor):
            raise ValueError("PAD_ATALHO deve ter o formato ctrl+alt+shift+q (modificadores + uma tecla).")
        return valor

    @field_validator("url_execucao")
    @classmethod
    def _validar_url(cls, valor: str) -> str:
        valor = valor.strip()
        if valor and not valor.lower().startswith("ms-powerautomate:/console/flow/run"):
            raise ValueError("PAD_URL_EXECUCAO deve começar com ms-powerautomate:/console/flow/run")
        return valor

    @model_validator(mode="after")
    def _validar_caminhos(self) -> "Configuracao":
        base = self.pasta_base.resolve()
        for nome in ("arquivo_entrada", "arquivo_processados", "arquivo_publicaveis", "arquivo_historico", "pasta_controle_rpa"):
            caminho = (base / getattr(self, nome)).resolve()
            if base != caminho and base not in caminho.parents:
                raise ValueError(f"{nome} precisa ficar dentro de QUEMFAZ_PASTA_BASE.")
        return self

    # ------------------------------------------------------------- derivados
    def _dentro_da_base(self, relativo: str) -> Path:
        return (self.pasta_base / relativo).resolve()

    @property
    def caminho_entrada(self) -> Path:
        return self._dentro_da_base(self.arquivo_entrada)

    @property
    def caminho_processados(self) -> Path:
        return self._dentro_da_base(self.arquivo_processados)

    @property
    def caminho_publicaveis(self) -> Path:
        return self._dentro_da_base(self.arquivo_publicaveis)

    @property
    def caminho_historico(self) -> Path:
        return self._dentro_da_base(self.arquivo_historico)

    @property
    def caminho_controle_rpa(self) -> Path:
        return self._dentro_da_base(self.pasta_controle_rpa)

    @property
    def lista_origens(self) -> list[str]:
        return [o.strip() for o in self.origens_permitidas.split(",") if o.strip()]

    @property
    def lista_modos(self) -> list[str]:
        validos = {"assistido", "atalho", "interface_grafica", "url_local"}
        modos = [m.strip() for m in self.modos_permitidos.split(",") if m.strip() in validos]
        if self.modo_padrao not in modos:
            modos.insert(0, self.modo_padrao)  # o modo padrão sempre é permitido
        return modos

    @property
    def lista_processos_robo(self) -> list[str]:
        return [p.strip() for p in self.processos_robo.split(",") if p.strip()]

    @property
    def lista_processos_console(self) -> list[str]:
        return [p.strip() for p in self.processos_console.split(",") if p.strip()]


@lru_cache
def obter_configuracao() -> Configuracao:
    return Configuracao()
