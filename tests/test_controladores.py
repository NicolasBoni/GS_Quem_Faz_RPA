"""[SIMULADO] Controladores do Power Automate com adaptadores falsos (sem clicar em nada)."""
import pytest

from integrations.power_automate.base import (
    FALHA_AO_INICIAR,
    FLUXO_AMBIGUO,
    FLUXO_NAO_ENCONTRADO,
    PAD_INDISPONIVEL,
    ErroControlador,
)
from integrations.power_automate import controladores as ctl


class ItemFalso:
    def __init__(self, nome):
        self.nome = nome
        self.executado = False


class AdaptadorFalso:
    def __init__(self, nomes, console=True, botao_habilitado=True):
        self.itens = [ItemFalso(n) for n in nomes]
        self.console = console
        self.botao_habilitado = botao_habilitado
        self.aberto = False
        self.busca_limpa = False

    def console_ativo(self):
        return self.console

    def abrir_console(self):
        self.aberto = True

    def obter_janela(self, espera):
        if not self.console and not self.aberto:
            raise ErroControlador(PAD_INDISPONIVEL, "sem janela")
        return object()

    def localizar_itens(self, janela, nome):
        return [i for i in self.itens if i.nome.strip() == nome.strip()]

    def limpar_busca(self, janela):
        self.busca_limpa = True

    def estado_item(self, item):
        return "Not running"

    def executar_item(self, item):
        if not self.botao_habilitado:
            raise ErroControlador(FALHA_AO_INICIAR, "desabilitado")
        item.executado = True


@pytest.fixture(autouse=True)
def windows(monkeypatch):
    monkeypatch.setattr(ctl.sys, "platform", "win32")


def test_interface_executa_somente_o_fluxo_exato():
    adaptador = AdaptadorFalso(["Outro_Fluxo", "QuemFaz_Validacao_Pedidos", "QuemFaz_Validacao_Pedidos_v2"])
    resultado = ctl.ControladorInterfaceGrafica("QuemFaz_Validacao_Pedidos", adaptador).acionar()
    assert resultado.automatico
    assert [i.nome for i in adaptador.itens if i.executado] == ["QuemFaz_Validacao_Pedidos"]
    assert adaptador.busca_limpa


def test_fluxo_nao_encontrado():
    adaptador = AdaptadorFalso(["RPA_Monitoramento_Clima_Espacial "])
    with pytest.raises(ErroControlador) as erro:
        ctl.ControladorInterfaceGrafica("QuemFaz_Validacao_Pedidos", adaptador).acionar()
    assert erro.value.codigo == FLUXO_NAO_ENCONTRADO
    assert not any(i.executado for i in adaptador.itens)


def test_fluxo_ambiguo_nao_executa_nada():
    adaptador = AdaptadorFalso(["QuemFaz_Validacao_Pedidos", "QuemFaz_Validacao_Pedidos "])
    with pytest.raises(ErroControlador) as erro:
        ctl.ControladorInterfaceGrafica("QuemFaz_Validacao_Pedidos", adaptador).acionar()
    assert erro.value.codigo == FLUXO_AMBIGUO
    assert not any(i.executado for i in adaptador.itens)


def test_botao_desabilitado_falha_ao_iniciar():
    adaptador = AdaptadorFalso(["QuemFaz_Validacao_Pedidos"], botao_habilitado=False)
    with pytest.raises(ErroControlador) as erro:
        ctl.ControladorInterfaceGrafica("QuemFaz_Validacao_Pedidos", adaptador).acionar()
    assert erro.value.codigo == FALHA_AO_INICIAR


def test_console_fechado_e_aberto():
    adaptador = AdaptadorFalso(["QuemFaz_Validacao_Pedidos"], console=False)
    ctl.ControladorInterfaceGrafica("QuemFaz_Validacao_Pedidos", adaptador).acionar()
    assert adaptador.aberto


def test_atalho_pad_indisponivel(monkeypatch):
    monkeypatch.setattr(ctl, "algum_ativo", lambda nomes: False)
    enviados = []
    with pytest.raises(ErroControlador) as erro:
        ctl.ControladorAtalho("F", "ctrl+alt+shift+q", ["PAD.Console.Host.exe"], enviar=enviados.append).acionar()
    assert erro.value.codigo == PAD_INDISPONIVEL and enviados == []


def test_atalho_enviado(monkeypatch):
    monkeypatch.setattr(ctl, "algum_ativo", lambda nomes: True)
    enviados = []
    resultado = ctl.ControladorAtalho("F", "ctrl+alt+shift+q", ["x"], enviar=enviados.append).acionar()
    assert enviados == ["ctrl+alt+shift+q"] and resultado.automatico


def test_conversao_atalho():
    assert ctl._converter_atalho_pywinauto("ctrl+alt+shift+q") == "^%+q"
    assert ctl._converter_atalho_pywinauto("ctrl+shift+f9") == "^+{F9}"


def test_assistido_nao_aciona_nada():
    resultado = ctl.ControladorAssistido("QuemFaz_Validacao_Pedidos").acionar()
    assert resultado.automatico is False and "execute o fluxo" in resultado.mensagem


def test_atalho_invalido_na_configuracao(pasta_rpa, tmp_path):
    from conftest import criar_cfg
    with pytest.raises(ValueError):
        criar_cfg(pasta_rpa, tmp_path / "e", PAD_ATALHO="rm -rf")


def test_url_local_somente_esquema_pad(pasta_rpa, tmp_path):
    from conftest import criar_cfg
    with pytest.raises(ValueError):
        criar_cfg(pasta_rpa, tmp_path / "e", PAD_URL_EXECUCAO="cmd.exe /c calc")
