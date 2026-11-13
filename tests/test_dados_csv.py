"""[SIMULADO] Leitura e validação dos CSVs do contrato com o RPA."""
from collections import Counter

from conftest import EXEMPLOS, SAIDA_REAL
from services.csv_contrato import (
    COLUNAS_ENTRADA,
    COLUNAS_HISTORICO,
    COLUNAS_PROCESSADOS,
    COLUNAS_PUBLICAVEIS,
    exportar_csv,
    ler_csv,
    neutralizar_celula,
)


def test_leitura_entrada_exemplo():
    leitura = ler_csv(EXEMPLOS / "pedidos_entrada.csv", COLUNAS_ENTRADA)
    assert leitura.valido and leitura.erro is None
    assert len(leitura.linhas) == 11
    assert leitura.linhas[0]["numero_pedido"] == "PED-001"


def test_saida_real_com_bom_e_crlf():
    leitura = ler_csv(SAIDA_REAL / "pedidos_processados.csv", COLUNAS_PROCESSADOS)
    assert leitura.tem_bom
    assert leitura.valido and len(leitura.linhas) == 11
    assert leitura.linhas[0]["numero_pedido"] == "PED-001"  # BOM não contamina o cabeçalho


def test_cabecalho_inesperado(tmp_path):
    arquivo = tmp_path / "x.csv"
    arquivo.write_text("numero,categoria\nPED-1,LIMPEZA\n", encoding="utf-8")
    leitura = ler_csv(arquivo, COLUNAS_ENTRADA)
    assert not leitura.valido
    assert "Cabeçalho inesperado" in leitura.erro


def test_arquivo_vazio(tmp_path):
    arquivo = tmp_path / "vazio.csv"
    arquivo.write_text("", encoding="utf-8")
    leitura = ler_csv(arquivo, COLUNAS_ENTRADA)
    assert leitura.existe and not leitura.valido
    assert "vazio" in leitura.erro.lower()


def test_somente_cabecalho(tmp_path):
    arquivo = tmp_path / "cab.csv"
    arquivo.write_text(",".join(COLUNAS_ENTRADA) + "\n", encoding="utf-8")
    leitura = ler_csv(arquivo, COLUNAS_ENTRADA)
    assert leitura.valido and leitura.linhas == []


def test_arquivo_inexistente(tmp_path):
    leitura = ler_csv(tmp_path / "nao_existe.csv", COLUNAS_ENTRADA)
    assert not leitura.existe and not leitura.valido
    assert leitura.erro == "Arquivo não encontrado."


def test_estrutura_invalida_colunas_deslocadas(tmp_path):
    """Uma vírgula na descrição desloca as colunas na saída do PAD."""
    arquivo = tmp_path / "proc.csv"
    arquivo.write_text(
        ",".join(COLUNAS_PROCESSADOS) + "\n"
        "PED-1,PINTURA,Pintura,sala e quarto,Mooca,APROVADO,ok\n"
        "PED-2,LIMPEZA,Limpeza,Mooca,APROVADO,ok\n",
        encoding="utf-8",
    )
    leitura = ler_csv(arquivo, COLUNAS_PROCESSADOS)
    assert leitura.valido
    assert len(leitura.linhas) == 1
    assert len(leitura.linhas_invalidas) == 1
    assert leitura.linhas_invalidas[0].numero_linha == 2


def test_valores_ausentes():
    leitura = ler_csv(EXEMPLOS / "pedidos_entrada.csv", COLUNAS_ENTRADA)
    sem_numero = [l for l in leitura.linhas if l["numero_pedido"] == ""]
    sem_descricao = [l for l in leitura.linhas if l["descricao"] == ""]
    assert len(sem_numero) == 1 and len(sem_descricao) == 1


def test_nao_utf8(tmp_path):
    arquivo = tmp_path / "latin1.csv"
    arquivo.write_bytes((",".join(COLUNAS_ENTRADA) + "\nPED-1,LIMPEZA,Limpeza,Butantã,C1,PENDENTE\n").encode("latin-1"))
    leitura = ler_csv(arquivo, COLUNAS_ENTRADA)
    assert not leitura.valido and "UTF-8" in leitura.erro


def test_caracteres_especiais_utf8(tmp_path):
    arquivo = tmp_path / "acentos.csv"
    arquivo.write_text(",".join(COLUNAS_ENTRADA) + "\nPED-1,LIMPEZA,Limpeza de área,Butantã,C1,PENDENTE\n", encoding="utf-8")
    leitura = ler_csv(arquivo, COLUNAS_ENTRADA)
    assert leitura.linhas[0]["bairro"] == "Butantã"


def test_protecao_csv_injection():
    assert neutralizar_celula("=HYPERLINK(1)") == "'=HYPERLINK(1)"
    assert neutralizar_celula("@SUM") == "'@SUM"
    assert neutralizar_celula("PED-001") == "PED-001"
    saida = exportar_csv(["a", "b"], [{"a": "=1+1", "b": "x,y"}])
    assert "'=1+1" in saida and '"x,y"' in saida


def test_resultado_inicial_11_pedidos():
    """[DADOS REAIS] Saída gravada pelo PAD em 2026-11-10 23:14:02 (teste inicial)."""
    processados = ler_csv(SAIDA_REAL / "pedidos_processados.csv", COLUNAS_PROCESSADOS)
    publicaveis = ler_csv(SAIDA_REAL / "pedidos_publicaveis.csv", COLUNAS_PUBLICAVEIS)
    historico = ler_csv(SAIDA_REAL / "historico_execucao.csv", COLUNAS_HISTORICO)
    contagem = Counter(l["resultado"] for l in processados.linhas)
    assert len(processados.linhas) == 11
    assert contagem == {"APROVADO": 4, "REPROVADO": 5, "DUPLICADO": 1, "IGNORADO": 1}
    assert [l["numero_pedido"] for l in publicaveis.linhas] == ["PED-001", "PED-002", "PED-003", "PED-008"]
    assert historico.linhas[-1]["etapa"] == "Resumo" and historico.linhas[-1]["resultado"] == "CONCLUIDO"
    esperado = ler_csv(EXEMPLOS / "resultado_esperado.csv", ["numero_pedido", "resultado"])
    assert [(l["numero_pedido"], l["resultado"]) for l in processados.linhas] == \
           [(l["numero_pedido"], l["resultado"]) for l in esperado.linhas]
