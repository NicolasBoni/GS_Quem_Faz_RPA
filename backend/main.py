"""API do módulo administrativo Quem Faz RPA.

Execute a partir da raiz do repositório:
    uvicorn main:app --app-dir backend --host 127.0.0.1 --port 8000
Documentação automática: http://127.0.0.1:8000/docs
"""
from __future__ import annotations

import logging
from dataclasses import dataclass

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from api.rotas import VERSAO, rotas
from config import Configuracao, obter_configuracao
from services.dados import ServicoDados
from services.execucoes import ServicoExecucoes

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
log = logging.getLogger("quemfaz")


@dataclass
class Servicos:
    cfg: Configuracao
    execucoes: ServicoExecucoes
    dados: ServicoDados


def criar_app(cfg: Configuracao | None = None, execucoes: ServicoExecucoes | None = None) -> FastAPI:
    cfg = cfg or obter_configuracao()
    execucoes = execucoes or ServicoExecucoes(cfg)
    app = FastAPI(
        title="Quem Faz — Módulo administrativo RPA",
        version=VERSAO,
        description=("Integra a interface administrativa ao fluxo **QuemFaz_Validacao_Pedidos** do "
                     "Power Automate Desktop. A API não processa pedidos: ela aciona o RPA e lê os "
                     "arquivos que ele gera."),
    )
    app.state.servicos = Servicos(cfg=cfg, execucoes=execucoes, dados=ServicoDados(cfg, execucoes))
    app.add_middleware(
        CORSMiddleware,
        allow_origins=cfg.lista_origens,
        allow_methods=["GET", "POST"],
        allow_headers=["Content-Type", "X-QuemFaz-Admin"],
    )

    @app.exception_handler(RequestValidationError)
    async def _validacao(_: Request, exc: RequestValidationError):
        erros = []
        for erro in exc.errors():
            campo = ".".join(str(p) for p in erro.get("loc", []) if p != "body")
            mensagem = str(erro.get("msg", "")).removeprefix("Value error, ")
            erros.append({"campo": campo, "mensagem": mensagem})
        return JSONResponse(status_code=422, content={"detail": "Dados inválidos.", "erros": erros})

    @app.exception_handler(Exception)
    async def _inesperado(_: Request, exc: Exception):
        log.exception("Erro inesperado: %s", type(exc).__name__)
        return JSONResponse(status_code=500, content={"detail": "Erro interno no backend. Consulte o log do servidor."})

    app.include_router(rotas)
    return app


app = criar_app()
