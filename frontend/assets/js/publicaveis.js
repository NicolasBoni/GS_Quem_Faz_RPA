/* Pedidos publicáveis (pedidos_publicaveis.csv). */
(function () {
  "use strict";
  const { $, esc, icone, valorOuVazio, estadoVazio, esqueleto, infoArquivo, avisosArquivo, abrirDetalhe, contem, preencherSelect } = QF_UI;
  let dados = null;
  const busca = $("#busca"), fCat = $("#filtro-categoria"), fBairro = $("#filtro-bairro");
  $("#exportar").href = QF_API.urlExportar("publicaveis");
  const selo = (p) => p.situacao_rpa === "PUBLICADO"
    ? `<span class="selo aprovado">${icone("aprovado")}Apto para publicação</span>`
    : `<span class="selo neutro">${esc(p.situacao_exibida)}</span>`;

  function render() {
    const itens = dados.itens.filter((p) => (!fCat.value || p.categoria === fCat.value) && (!fBairro.value || p.bairro === fBairro.value) &&
      contem(p, busca.value.trim(), ["numero_pedido", "descricao", "bairro", "categoria"]));
    $("#contagem").textContent = `${itens.length} de ${dados.itens.length} pedido(s) aptos`;
    if (!dados.itens.length) {
      $("#tabela-publicaveis").innerHTML = estadoVazio("Nenhum pedido apto para publicação", "Os pedidos aprovados pelo RPA aparecem aqui após o processamento.", "publicar");
      return;
    }
    if (!itens.length) {
      $("#tabela-publicaveis").innerHTML = estadoVazio("Nenhum pedido para os filtros", "Ajuste a categoria, o bairro ou a busca.", "busca");
      return;
    }
    $("#tabela-publicaveis").innerHTML = `<table><thead><tr><th>Nº do pedido</th><th>Categoria</th><th>Descrição</th><th>Bairro</th><th>Situação</th></tr></thead>
      <tbody>${itens.map((p) => `<tr class="clicavel" tabindex="0" data-linha="${p.linha}"><td class="codigo">${esc(p.numero_pedido)}</td><td>${esc(p.categoria)}</td>
      <td>${valorOuVazio(p.descricao)}</td><td>${valorOuVazio(p.bairro)}</td><td>${selo(p)}</td></tr>`).join("")}</tbody></table>`;
  }

  function detalhe(linha) {
    const p = dados.itens.find((x) => String(x.linha) === String(linha));
    if (!p) return;
    abrirDetalhe("Pedido " + p.numero_pedido, [
      ["Categoria", esc(p.categoria)], ["Descrição", valorOuVazio(p.descricao)], ["Bairro", valorOuVazio(p.bairro)],
      ["Situação exibida", selo(p)], ["Valor técnico no CSV", `<span class="codigo">${esc(p.situacao_rpa)}</span>`],
      ["Observação", "Resultado do processamento demonstrativo do RPA. Nenhuma notificação foi enviada a profissionais."],
    ]);
  }

  [busca, fCat, fBairro].forEach((el) => el.addEventListener("input", render));
  $("#tabela-publicaveis").addEventListener("click", (e) => { const tr = e.target.closest("tr[data-linha]"); if (tr) detalhe(tr.dataset.linha); });
  $("#tabela-publicaveis").addEventListener("keydown", (e) => { const tr = e.target.closest("tr[data-linha]"); if (tr && e.key === "Enter") detalhe(tr.dataset.linha); });

  (async function () {
    $("#tabela-publicaveis").innerHTML = esqueleto(4);
    try {
      dados = await QF_API.publicaveis();
      avisosArquivo(dados.arquivo, "Execute o processamento para que o RPA gere o arquivo.");
      $("#meta-publicaveis").innerHTML = infoArquivo(dados.arquivo);
      preencherSelect(fCat, dados.itens.map((p) => p.categoria), "Todas as categorias");
      preencherSelect(fBairro, dados.itens.map((p) => p.bairro), "Todos os bairros");
      render();
    } catch (erro) {
      QF_UI.erroDeCarga(erro, "Não foi possível carregar os pedidos publicáveis");
      $("#tabela-publicaveis").innerHTML = estadoVazio("Dados indisponíveis", "", "alerta");
    }
  })();
})();
