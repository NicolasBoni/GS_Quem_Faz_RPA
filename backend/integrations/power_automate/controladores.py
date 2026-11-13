"""Controladores de acionamento local do Power Automate Desktop (sem Premium).

Ordem de preferência documentada:
1. atalho            -> envia o atalho de teclado configurado nas propriedades do fluxo;
2. interface_grafica -> pywinauto (UI Automation) localiza o fluxo pelo nome exato e
                        invoca o botão "Executar" da linha (sem coordenadas fixas);
3. assistido         -> o usuário inicia o fluxo manualmente; o backend detecta o resultado.
(opcional) url_local -> abre a URL ms-powerautomate copiada das propriedades do fluxo.

Nenhum controlador aceita comandos vindos do cliente: o fluxo, o atalho e a URL
vêm apenas da configuração em backend/config.py.
"""
from __future__ import annotations

import os
import subprocess
import sys
import time
from pathlib import Path

from .base import (
    CONFIGURACAO_INVALIDA,
    DEPENDENCIA_AUSENTE,
    FALHA_AO_INICIAR,
    FLUXO_AMBIGUO,
    FLUXO_NAO_ENCONTRADO,
    PAD_INDISPONIVEL,
    ControladorPAD,
    ErroControlador,
    ResultadoAcionamento,
)
from .processos import algum_ativo

# Identificadores de UI Automation do console do PAD (independentes do idioma),
# levantados por inspeção da versão 2.x / pacote 11.2611 instalado.
TITULO_CONSOLE = r"^Power Automate$"
CLASSE_JANELA = "WinAutomationWindow"
ID_ABA_FLUXOS = "FlowsTab"
ID_ABA_MEUS_FLUXOS = "MyFlowsTab"
ID_GRADE_FLUXOS = "MyFlowsListGrid"
ID_BUSCA = "SearchFlowTextField"
ID_NOME_FLUXO = "FlowNameTextBox"
ID_BOTAO_EXECUTAR = "StartFlowButton"
ID_ROTULO_ESTADO = "ProcessStateStatusLabel"
AUMID_CONSOLE = "Microsoft.PowerAutomateDesktop_8wekyb3d8bbwe!PAD.Console"


# =========================================================== modo assistido
class ControladorAssistido(ControladorPAD):
    modo = "assistido"
    descricao = "Execução assistida: o lote é preparado e o fluxo é iniciado manualmente no Power Automate Desktop."

    def verificar(self) -> tuple[bool, str]:
        return True, "Sempre disponível. Requer que o usuário clique em Executar no Power Automate Desktop."

    def acionar(self) -> ResultadoAcionamento:
        return ResultadoAcionamento(
            automatico=False,
            mensagem=(f"Abra o Power Automate Desktop e execute o fluxo '{self.nome_fluxo}'. "
                      "O sistema está monitorando os arquivos de saída e detectará o término."),
        )


# ======================================================= atalho de teclado
def _converter_atalho_pywinauto(atalho: str) -> str:
    partes = atalho.split("+")
    tecla = partes[-1]
    mods = partes[:-1]
    prefixo = ""
    win = "win" in mods
    for mod in mods:
        prefixo += {"ctrl": "^", "alt": "%", "shift": "+"}.get(mod, "")
    tecla_fmt = "{" + tecla.upper() + "}" if tecla.startswith("f") and len(tecla) > 1 else tecla
    sequencia = prefixo + tecla_fmt
    if win:
        sequencia = "{VK_LWIN down}" + sequencia + "{VK_LWIN up}"
    return sequencia


class ControladorAtalho(ControladorPAD):
    modo = "atalho"
    descricao = "Atalho de teclado configurado nas propriedades do fluxo no Power Automate Desktop."

    def __init__(self, nome_fluxo: str, atalho: str, processos_console: list[str], enviar=None):
        super().__init__(nome_fluxo)
        self.atalho = atalho
        self.processos_console = processos_console
        self._enviar = enviar  # injeção para testes

    def verificar(self) -> tuple[bool, str]:
        if sys.platform != "win32":
            return False, "Disponível somente no Windows."
        if not algum_ativo(self.processos_console):
            return False, "O console do Power Automate Desktop não está aberto (os atalhos só funcionam com ele em execução)."
        return True, f"Console ativo. Atalho configurado: {self.atalho}."

    def _enviar_teclas(self) -> None:
        if self._enviar:
            self._enviar(self.atalho)
            return
        try:
            from pywinauto import keyboard  # type: ignore

            keyboard.send_keys(_converter_atalho_pywinauto(self.atalho), pause=0.05)
            return
        except ImportError:
            pass
        try:
            import pyautogui  # type: ignore

            pyautogui.hotkey(*self.atalho.split("+"))
        except ImportError as exc:
            raise ErroControlador(DEPENDENCIA_AUSENTE, "pywinauto/PyAutoGUI não instalados.") from exc

    def acionar(self) -> ResultadoAcionamento:
        ok, detalhe = self.verificar()
        if not ok:
            raise ErroControlador(PAD_INDISPONIVEL, detalhe)
        try:
            self._enviar_teclas()
        except ErroControlador:
            raise
        except Exception as exc:  # noqa: BLE001 - falhas do SO ao injetar teclas
            raise ErroControlador(FALHA_AO_INICIAR, f"Não foi possível enviar o atalho: {type(exc).__name__}.") from exc
        return ResultadoAcionamento(
            automatico=True,
            mensagem=f"Atalho {self.atalho} enviado. Aguardando evidência de que o fluxo iniciou.",
        )


# ==================================================== interface gráfica (UIA)
class AdaptadorConsoleUIA:
    """Isola o pywinauto para permitir testes do controlador sem a interface real."""

    def __init__(self, caminho_console: str, processos_console: list[str]):
        self.caminho_console = caminho_console
        self.processos_console = processos_console

    def _desktop(self):
        try:
            from pywinauto import Desktop  # type: ignore
        except ImportError as exc:
            raise ErroControlador(DEPENDENCIA_AUSENTE, "pywinauto não está instalado.") from exc
        return Desktop(backend="uia")

    def console_ativo(self) -> bool:
        return algum_ativo(self.processos_console)

    def abrir_console(self) -> None:
        caminho = self.caminho_console.strip()
        try:
            if caminho:
                arquivo = Path(caminho)
                if arquivo.name.lower() != "pad.console.host.exe" or not arquivo.is_file():
                    raise ErroControlador(CONFIGURACAO_INVALIDA, "PAD_CAMINHO_CONSOLE deve apontar para PAD.Console.Host.exe.")
                subprocess.Popen([str(arquivo)], close_fds=True)
            else:
                # Versão da Microsoft Store (MSIX): abre pelo identificador do aplicativo.
                subprocess.Popen(["explorer.exe", f"shell:AppsFolder\\{AUMID_CONSOLE}"], close_fds=True)
        except OSError as exc:
            raise ErroControlador(PAD_INDISPONIVEL, "Não foi possível abrir o Power Automate Desktop.") from exc

    def obter_janela(self, espera: float):
        desktop = self._desktop()
        limite = time.monotonic() + espera
        while True:
            janelas = desktop.windows(title_re=TITULO_CONSOLE, class_name=CLASSE_JANELA)
            if len(janelas) == 1:
                return desktop.window(handle=janelas[0].handle)
            if time.monotonic() > limite:
                if not janelas:
                    raise ErroControlador(PAD_INDISPONIVEL, "Janela do console do Power Automate não encontrada.")
                raise ErroControlador(FLUXO_AMBIGUO, "Mais de uma janela do console foi encontrada.")
            time.sleep(1)

    def localizar_itens(self, janela, nome_fluxo: str) -> list:
        for aba in (ID_ABA_FLUXOS, ID_ABA_MEUS_FLUXOS):
            try:
                janela.child_window(auto_id=aba, control_type="TabItem").select()
            except Exception:  # noqa: BLE001 - layout sem abas
                pass
        try:
            busca = janela.child_window(auto_id=ID_BUSCA, control_type="Edit")
            busca.set_edit_text(nome_fluxo)
            time.sleep(1.0)
        except Exception:  # noqa: BLE001 - sem campo de busca, usa a grade completa
            pass
        grade = janela.child_window(auto_id=ID_GRADE_FLUXOS, control_type="DataGrid")
        if not grade.exists(timeout=10):
            raise ErroControlador(PAD_INDISPONIVEL, "Lista de fluxos não encontrada no console.")
        encontrados = []
        for item in grade.children(control_type="DataItem"):
            if (item.element_info.name or "").strip() == nome_fluxo.strip():
                encontrados.append(item)
        return encontrados

    def limpar_busca(self, janela) -> None:
        try:
            janela.child_window(auto_id=ID_BUSCA, control_type="Edit").set_edit_text("")
        except Exception:  # noqa: BLE001
            pass

    @staticmethod
    def _descendente(item, auto_id: str):
        for elemento in item.descendants():
            if elemento.element_info.automation_id == auto_id:
                return elemento
        return None

    def estado_item(self, item) -> str:
        try:
            rotulo = self._descendente(item, ID_ROTULO_ESTADO)
            return rotulo.window_text() if rotulo else ""
        except Exception:  # noqa: BLE001
            return ""

    def executar_item(self, item) -> None:
        botao = self._descendente(item, ID_BOTAO_EXECUTAR)
        if botao is None:
            raise ErroControlador(FALHA_AO_INICIAR, "Botão Executar não encontrado na linha do fluxo.")
        if not botao.is_enabled():
            raise ErroControlador(FALHA_AO_INICIAR, "Botão Executar está desabilitado (o fluxo pode já estar em execução).")
        botao.invoke()  # padrão Invoke da UI Automation: sem mouse e sem coordenadas


class ControladorInterfaceGrafica(ControladorPAD):
    modo = "interface_grafica"
    descricao = "Automação da interface do console do Power Automate Desktop com pywinauto (UI Automation)."

    def __init__(self, nome_fluxo: str, adaptador: AdaptadorConsoleUIA, espera_console: float = 60.0):
        super().__init__(nome_fluxo)
        self.adaptador = adaptador
        self.espera_console = espera_console

    def verificar(self) -> tuple[bool, str]:
        if sys.platform != "win32":
            return False, "Disponível somente no Windows."
        try:
            import pywinauto  # type: ignore  # noqa: F401
        except ImportError:
            return False, "pywinauto não está instalado."
        if not self.adaptador.console_ativo():
            return True, "Console fechado: será aberto automaticamente ao processar."
        return True, "Console do Power Automate em execução."

    def acionar(self) -> ResultadoAcionamento:
        if sys.platform != "win32":
            raise ErroControlador(PAD_INDISPONIVEL, "A automação da interface exige Windows.")
        if not self.adaptador.console_ativo():
            self.adaptador.abrir_console()
        janela = self.adaptador.obter_janela(self.espera_console)
        try:
            itens = self.adaptador.localizar_itens(janela, self.nome_fluxo)
            if not itens:
                raise ErroControlador(
                    FLUXO_NAO_ENCONTRADO,
                    f"O fluxo '{self.nome_fluxo}' não foi encontrado em Meus fluxos. Confira nome_fluxo em backend/config.py.",
                )
            if len(itens) > 1:
                raise ErroControlador(
                    FLUXO_AMBIGUO,
                    f"Há {len(itens)} fluxos chamados '{self.nome_fluxo}'. Por segurança nenhum foi executado.",
                )
            estado = self.adaptador.estado_item(itens[0])
            self.adaptador.executar_item(itens[0])
        except ErroControlador:
            raise
        except Exception as exc:  # noqa: BLE001 - erros internos da UI Automation
            raise ErroControlador(FALHA_AO_INICIAR, f"Falha na automação da interface: {type(exc).__name__}.") from exc
        finally:
            self.adaptador.limpar_busca(janela)
        detalhe = f" (estado anterior no console: {estado})" if estado else ""
        return ResultadoAcionamento(
            automatico=True,
            mensagem=f"Botão Executar do fluxo '{self.nome_fluxo}' acionado via UI Automation{detalhe}.",
        )


# ============================================================ URL local
class ControladorUrlLocal(ControladorPAD):
    modo = "url_local"
    descricao = "Abre a URL ms-powerautomate do fluxo (copiada das propriedades do fluxo). Opcional."

    def __init__(self, nome_fluxo: str, url: str):
        super().__init__(nome_fluxo)
        self.url = url

    def verificar(self) -> tuple[bool, str]:
        if sys.platform != "win32":
            return False, "Disponível somente no Windows."
        if not self.url:
            return False, "PAD_URL_EXECUCAO não configurada."
        return True, "URL de execução configurada."

    def acionar(self) -> ResultadoAcionamento:
        ok, detalhe = self.verificar()
        if not ok:
            raise ErroControlador(CONFIGURACAO_INVALIDA, detalhe)
        try:
            os.startfile(self.url)  # type: ignore[attr-defined]
        except OSError as exc:
            raise ErroControlador(FALHA_AO_INICIAR, "O Windows não conseguiu abrir a URL do Power Automate.") from exc
        return ResultadoAcionamento(True, "URL de execução local aberta. Aguardando evidência de início.")


def criar_controlador(modo: str, cfg) -> ControladorPAD:
    if modo == "atalho":
        return ControladorAtalho(cfg.nome_fluxo, cfg.atalho, cfg.lista_processos_console)
    if modo == "interface_grafica":
        return ControladorInterfaceGrafica(
            cfg.nome_fluxo, AdaptadorConsoleUIA(cfg.caminho_console, cfg.lista_processos_console)
        )
    if modo == "url_local":
        return ControladorUrlLocal(cfg.nome_fluxo, cfg.url_execucao)
    return ControladorAssistido(cfg.nome_fluxo)
