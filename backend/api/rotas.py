"""Endpoints REST do módulo administrativo Quem Faz RPA."""
from __future__ import annotations

import hmac
from typing import Literal

from fastapi import APIRouter, Depends, Header, HTTPException, Request
from fastapi.responses import Response

from integrations.power_automate.controladores import criar_controlador
from integrations.power_automate.processos import algum_ativo
from models.schemas import (
    Diagnostico,
    Estatisticas,
    Execucao,
    NovaSolicitacao,
    PedidoExecucao,
    RespostaHistorico,
    RespostaPublicaveis,
    RespostaResultados,
    RespostaSolicitacoes,
    Saude,
    Solicitacao,
)
from services.csv_contrato import COLUNAS_PROCESSADOS, COLUNAS_PUBLICAVEIS, exportar_csv
from services.dados import ErroDados
from services.execucoes import ErroExecucao

VERSAO = "1.0.0"
rotas = APIRouter(prefix="/api")


def servicos(request: Request):
    return request.app.state.servicos


def exigir_admin(request: Request, x_quemfaz_admin: str | None = Header(default=None)) -> None:
    """Ações administrativas: exige o token definido em backend/config.py."""
    token = request.app.state.servicos.cfg.token_admin
    if token and not hmac.compare_digest(x_quemfaz_admin or "", token):
        raise HTTPException(status_code=403, detail="Ação administrativa não autorizada.")


def _tratar(erro: Exception):
    if isinstance(erro, (ErroDados, ErroExecucao)):
        raise HTTPException(status_code=erro.status_http, detail=erro.mensagem)
    raise erro


@rotas.get("/health", response_model=Saude, summary="Saúde da API e diagnóstico do ambiente")
def health(s=Depends(servicos)):
    cfg = s.cfg
    diagnosticos = []
    entrada = s.dados.entrada()
    diagnosticos.append(Diagnostico(nome="Arquivo de entrada", ok=entrada.valido,
                                    detalhe=entrada.erro or f"{len(entrada.linhas)} pedido(s) em {entrada.caminho.name}."))
    for rotulo, caminho in (("Pasta de resultados", cfg.caminho_processados.parent),
                            ("Pasta de logs", cfg.caminho_historico.parent)):
        diagnosticos.append(Diagnostico(nome=rotulo, ok=caminho.is_dir(),
                                        detalhe="Encontrada." if caminho.is_dir() else "Não encontrada."))
    for modo in cfg.lista_modos:
        ok, detalhe = criar_controlador(modo, cfg).verificar()
        diagnosticos.append(Diagnostico(nome=f"Modo {modo}", ok=ok, detalhe=detalhe))
    ativa = s.execucoes.ativa()
    return Saude(
        api="ok", versao=VERSAO, modo_padrao=cfg.modo_padrao, modos_permitidos=cfg.lista_modos,
        nome_fluxo=cfg.nome_fluxo, console_pad_ativo=algum_ativo(cfg.lista_processos_console),
        robo_pad_ativo=s.execucoes.robo_ativo(), execucao_ativa=ativa.id_execucao if ativa else None,
        diagnosticos=diagnosticos,
    )


@rotas.get("/solicitacoes", response_model=RespostaSolicitacoes, summary="Pedidos do pedidos_entrada.csv")
def listar_solicitacoes(s=Depends(servicos)):
    return s.dados.listar_solicitacoes()


@rotas.post("/solicitacoes", response_model=Solicitacao, status_code=201,
            dependencies=[Depends(exigir_admin)], summary="Cadastra uma solicitação de teste")
def criar_solicitacao(nova: NovaSolicitacao, s=Depends(servicos)):
    try:
        return s.dados.adicionar_solicitacao(nova)
    except Exception as erro:  # noqa: BLE001
        _tratar(erro)


@rotas.post("/solicitacoes/restaurar-exemplo", dependencies=[Depends(exigir_admin)],
            summary="Restaura o lote de 11 pedidos do teste inicial")
def restaurar_exemplo(s=Depends(servicos)):
    try:
        total = s.dados.restaurar_exemplo()
    except Exception as erro:  # noqa: BLE001
        _tratar(erro)
    return {"mensagem": f"Lote de exemplo restaurado com {total} pedidos. O arquivo anterior foi arquivado.", "total": total}


@rotas.get("/resultados", response_model=RespostaResultados, summary="Conteúdo do pedidos_processados.csv")
def listar_resultados(s=Depends(servicos)):
    return s.dados.listar_resultados()


@rotas.get("/publicaveis", response_model=RespostaPublicaveis, summary="Conteúdo do pedidos_publicaveis.csv")
def listar_publicaveis(s=Depends(servicos)):
    return s.dados.listar_publicaveis()


@rotas.get("/estatisticas", response_model=Estatisticas, summary="Indicadores calculados dos arquivos reais")
def estatisticas(s=Depends(servicos)):
    return s.dados.estatisticas()


@rotas.get("/historico", response_model=RespostaHistorico, summary="Log de auditoria do RPA")
def historico(id_execucao: str | None = None, s=Depends(servicos)):
    try:
        return s.dados.listar_historico(id_execucao)
    except Exception as erro:  # noqa: BLE001
        _tratar(erro)


@rotas.get("/exportar/{tipo}", summary="Exporta resultados em CSV protegido contra CSV injection")
def exportar(tipo: Literal["resultados", "publicaveis"], s=Depends(servicos)):
    if tipo == "resultados":
        colunas, linhas = COLUNAS_PROCESSADOS, s.dados.processados().linhas
    else:
        colunas, linhas = COLUNAS_PUBLICAVEIS, s.dados.publicaveis_csv().linhas
    return Response(
        content=exportar_csv(colunas, linhas).encode("utf-8"),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="quemfaz_{tipo}.csv"'},
    )


@rotas.post("/rpa/executar", response_model=Execucao, status_code=202,
            dependencies=[Depends(exigir_admin)], summary="Prepara o lote e aciona o Power Automate Desktop")
def executar(pedido: PedidoExecucao | None = None, s=Depends(servicos)):
    try:
        return s.execucoes.iniciar(pedido.modo if pedido else None)
    except Exception as erro:  # noqa: BLE001
        _tratar(erro)


@rotas.get("/rpa/status/{id_execucao}", response_model=Execucao, summary="Estado de uma execução (polling)")
def status(id_execucao: str, s=Depends(servicos)):
    execucao = s.execucoes.obter(id_execucao)
    if execucao is None:
        raise HTTPException(status_code=404, detail="Execução não encontrada.")
    return execucao


@rotas.get("/rpa/execucoes", response_model=list[Execucao], summary="Execuções registradas pela interface")
def execucoes(limite: int = 30, s=Depends(servicos)):
    return s.execucoes.listar(max(1, min(limite, 100)))


@rotas.post("/rpa/cancelar/{id_execucao}", response_model=Execucao, dependencies=[Depends(exigir_admin)],
            summary="Cancela o monitoramento (não interrompe o PAD)")
def cancelar(id_execucao: str, s=Depends(servicos)):
    try:
        return s.execucoes.cancelar(id_execucao)
    except Exception as erro:  # noqa: BLE001
        _tratar(erro)
