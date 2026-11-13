/* Cliente da API FastAPI do módulo Quem Faz RPA. */
(function () {
  "use strict";
  const meta = (nome) => document.querySelector(`meta[name="${nome}"]`)?.content || "";
  const BASE = meta("qf-api").replace(/\/$/, "");
  const TOKEN = meta("qf-token");

  class ErroApi extends Error {
    constructor(status, mensagem, erros) {
      super(mensagem);
      this.status = status;
      this.erros = erros || [];
    }
  }

  async function requisitar(metodo, caminho, corpo) {
    const opcoes = { method: metodo, headers: { Accept: "application/json" } };
    if (corpo !== undefined) {
      opcoes.headers["Content-Type"] = "application/json";
      opcoes.body = JSON.stringify(corpo);
    }
    if (metodo !== "GET" && TOKEN) opcoes.headers["X-QuemFaz-Admin"] = TOKEN;
    let resposta;
    try {
      resposta = await fetch(BASE + caminho, opcoes);
    } catch (e) {
      throw new ErroApi(0, "Não foi possível conectar ao backend Python em " + BASE + ". Verifique se a API está em execução.");
    }
    let dados = null;
    try { dados = await resposta.json(); } catch (e) { /* resposta sem JSON */ }
    if (!resposta.ok) {
      const detalhe = dados && typeof dados.detail === "string" ? dados.detail : `Erro ${resposta.status} na API.`;
      throw new ErroApi(resposta.status, detalhe, dados && dados.erros);
    }
    return dados;
  }

  window.QF_API = {
    base: BASE,
    ErroApi,
    saude: () => requisitar("GET", "/api/health"),
    estatisticas: () => requisitar("GET", "/api/estatisticas"),
    solicitacoes: () => requisitar("GET", "/api/solicitacoes"),
    criarSolicitacao: (dados) => requisitar("POST", "/api/solicitacoes", dados),
    restaurarExemplo: () => requisitar("POST", "/api/solicitacoes/restaurar-exemplo"),
    resultados: () => requisitar("GET", "/api/resultados"),
    publicaveis: () => requisitar("GET", "/api/publicaveis"),
    historico: (id) => requisitar("GET", "/api/historico" + (id ? "?id_execucao=" + encodeURIComponent(id) : "")),
    executar: (modo) => requisitar("POST", "/api/rpa/executar", modo ? { modo } : {}),
    status: (id) => requisitar("GET", "/api/rpa/status/" + encodeURIComponent(id)),
    execucoes: () => requisitar("GET", "/api/rpa/execucoes"),
    cancelar: (id) => requisitar("POST", "/api/rpa/cancelar/" + encodeURIComponent(id)),
    urlExportar: (tipo) => BASE + "/api/exportar/" + encodeURIComponent(tipo),
  };
})();
