/* Resultados (pedidos_processados.csv) divididos por classificação. */
(function () {
  "use strict";
  const { $, esc, icone, seloResultado, valorOuVazio, estadoVazio, esqueleto, infoArquivo, avisosArquivo,
    abrirDetalhe, contem, preencherSelect, RESULTADOS } = QF_UI;
  const ABAS = [["", "Todos"], ["APROVADO", "Aprovados"], ["REPROVADO", "Reprovados"], ["DUPLICADO", "Duplicados"], ["IGNORADO", "Ignorados"]];
  const EXPLICACAO = {
    APROVADO: "Pedido completo segundo as regras da POC e apto para publicação.",
    REPROVADO: "Pedido incompleto ou com categoria não atendida: decisão de regra de negócio.",
    DUPLICADO: "Número de pedido já analisado no mesmo lote.",
    IGNORADO: "Pedido fora da situação PENDENTE; não foi validado.",
  };
  const TOM = { APROVADO: "ok", REPROVADO: "erro", DUPLICADO: "alerta", IGNORADO: "neutro" };
  let dados = null, aba = "";
  const busca = $("#busca"), fCat = $("#filtro-categoria");
  $("#exportar").href = QF_API.urlExportar("resultados");

  function renderKpis() {
    $("#kpis-resultados").innerHTML = Object.entries(RESULTADOS).map(([chave, r]) => `
      <article class="cartao kpi"><span class="kpi-rotulo"><span class="chip-icone ${TOM[chave]}">${icone(r.icone)}</span>${r.rotulo}s</span>
      <span class="kpi-valor">${dados.contagem[chave] ?? 0}</span><span class="kpi-detalhe">${esc(EXPLICACAO[chave])}</span></article>`).join("");
  }

  function renderAbas() {
    $("#abas").innerHTML = ABAS.map(([valor, rotulo]) => `<button class="aba" role="tab" aria-selected="${aba === valor}" data-aba="${valor}">
      ${valor ? icone(RESULTADOS[valor].icone) : ""}${rotulo}<span class="contador">${valor ? dados.contagem[valor] ?? 0 : dados.contagem.TOTAL}</span></button>`).join("");
  }

  function render() {
    const itens = dados.itens.filter((r) => (!aba || r.resultado === aba) && (!fCat.value || r.categoria === fCat.value) &&
      contem(r, busca.value.trim(), ["numero_pedido", "descricao", "bairro", "motivo", "categoria"]));
    $("#contagem").textContent = `${itens.length} de ${dados.itens.length} pedido(s)`;
    if (!dados.itens.length) {
      $("#tabela-resultados").innerHTML = estadoVazio("Nenhum resultado disponível", "Execute o processamento RPA para gerar pedidos_processados.csv.", "resultados");
      return;
    }
    if (!itens.length) {
      $("#tabela-resultados").innerHTML = estadoVazio("Nenhum pedido nesta visão", "Ajuste a aba, a busca ou o filtro de categoria.", "busca");
      return;
    }
    $("#tabela-resultados").innerHTML = `<table><thead><tr><th>Nº do pedido</th><th>Classificação</th><th>Categoria</th><th>Descrição</th><th>Bairro</th><th>Justificativa do RPA</th></tr></thead>
      <tbody>${itens.map((r) => `<tr class="clicavel" tabindex="0" data-linha="${r.linha}"><td class="codigo">${valorOuVazio(r.numero_pedido)}</td>
      <td>${seloResultado(r.resultado)}</td><td>${valorOuVazio(r.categoria)}</td><td>${valorOuVazio(r.descricao)}</td><td>${valorOuVazio(r.bairro)}</td>
      <td>${esc(r.motivo)}</td></tr>`).join("")}</tbody></table>`;
  }

  function detalhe(linha) {
    const r = dados.itens.find((x) => String(x.linha) === String(linha));
    if (!r) return;
    abrirDetalhe("Pedido " + (r.numero_pedido || "sem número"), [
      ["Classificação", seloResultado(r.resultado)], ["Justificativa", esc(r.motivo)],
      ["Categoria", valorOuVazio(r.categoria)], ["Descrição", valorOuVazio(r.descricao)], ["Bairro", valorOuVazio(r.bairro)],
      ["Linha no CSV", String(r.linha)], ["O que significa", esc(EXPLICACAO[r.resultado] || "Classificação não reconhecida.")],
    ], seloResultado(r.resultado));
  }

  $("#abas").addEventListener("click", (e) => { const b = e.target.closest("[data-aba]"); if (!b) return; aba = b.dataset.aba; renderAbas(); render(); });
  [busca, fCat].forEach((el) => el.addEventListener("input", render));
  $("#tabela-resultados").addEventListener("click", (e) => { const tr = e.target.closest("tr[data-linha]"); if (tr) detalhe(tr.dataset.linha); });
  $("#tabela-resultados").addEventListener("keydown", (e) => { const tr = e.target.closest("tr[data-linha]"); if (tr && e.key === "Enter") detalhe(tr.dataset.linha); });

  (async function () {
    $("#tabela-resultados").innerHTML = esqueleto(6);
    try {
      dados = await QF_API.resultados();
      avisosArquivo(dados.arquivo, "Execute o processamento para que o RPA gere o arquivo.");
      $("#meta-resultados").innerHTML = infoArquivo(dados.arquivo);
      preencherSelect(fCat, dados.itens.map((r) => r.categoria), "Todas as categorias");
      renderKpis(); renderAbas(); render();
    } catch (erro) {
      QF_UI.erroDeCarga(erro, "Não foi possível carregar os resultados");
      $("#tabela-resultados").innerHTML = estadoVazio("Dados indisponíveis", "", "alerta");
    }
  })();
})();
