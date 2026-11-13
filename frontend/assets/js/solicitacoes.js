/* Solicitações recebidas (pedidos_entrada.csv): consulta, filtros, detalhes e cadastro de teste. */
(function () {
  "use strict";
  const { $, esc, icone, seloResultado, seloSituacaoPedido, valorOuVazio, estadoVazio, esqueleto,
    infoArquivo, avisosArquivo, abrirDetalhe, contem, preencherSelect, aviso, limparAvisos } = QF_UI;

  let dados = null;
  const busca = $("#busca"), fCat = $("#filtro-categoria"), fSit = $("#filtro-situacao");
  const janelaNova = $("#janela-nova"), janelaRestaurar = $("#janela-restaurar");

  function bloqueio(bloqueada) {
    $("#botao-nova").disabled = bloqueada;
    $("#botao-restaurar").disabled = bloqueada;
    $("#aviso-bloqueio").innerHTML = bloqueada
      ? `<div class="aviso alerta" role="status">${icone("alerta")}<p><strong>Edição bloqueada.</strong>
         O Power Automate Desktop está processando o lote. O arquivo de entrada não pode ser alterado até o término.</p></div>`
      : "";
  }

  function render() {
    if (!dados) return;
    const termo = busca.value.trim();
    const itens = dados.itens.filter((s) =>
      contem(s, termo, ["numero_pedido", "descricao", "bairro", "codigo_cliente", "categoria"]) &&
      (!fCat.value || s.categoria === fCat.value) && (!fSit.value || s.situacao === fSit.value));
    const comResultado = dados.resultados_correspondem_ao_lote;
    $("#contagem").textContent = `${itens.length} de ${dados.itens.length} solicitação(ões)`;
    if (!dados.itens.length) {
      $("#tabela-solicitacoes").innerHTML = estadoVazio("Nenhuma solicitação no arquivo de entrada", "Cadastre uma solicitação de teste ou restaure o lote de exemplo.", "entrada");
      return;
    }
    if (!itens.length) {
      $("#tabela-solicitacoes").innerHTML = estadoVazio("Nenhum resultado para os filtros", "Ajuste a busca ou limpe os filtros.", "busca");
      return;
    }
    $("#tabela-solicitacoes").innerHTML = `<table>
      <thead><tr><th>Linha</th><th>Nº do pedido</th><th>Categoria</th><th>Descrição</th><th>Bairro</th><th>Contratante</th><th>Situação</th>
      <th>Último resultado RPA</th></tr></thead>
      <tbody>${itens.map((s) => `<tr class="clicavel" tabindex="0" data-linha="${s.linha}">
        <td class="num">${s.linha}</td><td class="codigo">${valorOuVazio(s.numero_pedido)}</td><td>${valorOuVazio(s.categoria)}</td>
        <td>${valorOuVazio(s.descricao)}</td><td>${valorOuVazio(s.bairro)}</td><td class="codigo">${valorOuVazio(s.codigo_cliente)}</td>
        <td>${seloSituacaoPedido(s.situacao)}</td>
        <td>${comResultado && s.ultimo_resultado ? seloResultado(s.ultimo_resultado) : '<span class="vazio-celula">não processado neste lote</span>'}</td>
      </tr>`).join("")}</tbody></table>`;
  }

  function detalhe(linha) {
    const s = dados.itens.find((x) => String(x.linha) === String(linha));
    if (!s) return;
    const pares = [
      ["Linha no CSV", String(s.linha)], ["Número do pedido", valorOuVazio(s.numero_pedido)],
      ["Categoria", valorOuVazio(s.categoria)], ["Descrição", valorOuVazio(s.descricao)],
      ["Bairro", valorOuVazio(s.bairro)], ["Código do contratante", valorOuVazio(s.codigo_cliente)],
      ["Situação", seloSituacaoPedido(s.situacao)],
    ];
    if (dados.resultados_correspondem_ao_lote && s.ultimo_resultado) {
      pares.push(["Resultado do RPA", seloResultado(s.ultimo_resultado)], ["Justificativa", esc(s.ultimo_motivo)]);
    } else {
      pares.push(["Resultado do RPA", '<span class="vazio-celula">Este lote ainda não foi processado pelo RPA.</span>']);
    }
    abrirDetalhe("Solicitação " + (s.numero_pedido || "sem número"), pares);
  }

  async function carregar() {
    $("#tabela-solicitacoes").innerHTML = esqueleto(6);
    try {
      dados = await QF_API.solicitacoes();
      limparAvisos();
      avisosArquivo(dados.arquivo, "Confira o caminho configurado em backend/config.py.");
      $("#meta-entrada").innerHTML = infoArquivo(dados.arquivo);
      if (!dados.resultados_correspondem_ao_lote && dados.itens.length) {
        aviso("info", "Lote ainda não processado. ", "Os resultados atuais do RPA não correspondem a este arquivo de entrada.");
      }
      preencherSelect(fCat, dados.itens.map((s) => s.categoria), "Todas as categorias");
      preencherSelect(fSit, dados.itens.map((s) => s.situacao), "Todas as situações");
      bloqueio(dados.edicao_bloqueada);
      render();
    } catch (erro) {
      QF_UI.erroDeCarga(erro, "Não foi possível carregar as solicitações");
      $("#tabela-solicitacoes").innerHTML = estadoVazio("Dados indisponíveis", "", "alerta");
    }
  }

  [busca, fCat, fSit].forEach((el) => el.addEventListener("input", render));
  $("#tabela-solicitacoes").addEventListener("click", (e) => { const tr = e.target.closest("tr[data-linha]"); if (tr) detalhe(tr.dataset.linha); });
  $("#tabela-solicitacoes").addEventListener("keydown", (e) => {
    const tr = e.target.closest("tr[data-linha]");
    if (tr && (e.key === "Enter" || e.key === " ")) { e.preventDefault(); detalhe(tr.dataset.linha); }
  });

  // ------------------------------------------------------- cadastro
  const form = $("#form-nova");
  document.querySelectorAll("dialog [data-fechar]").forEach((b) => b.addEventListener("click", () => b.closest("dialog").close()));
  $("#botao-nova").addEventListener("click", () => {
    form.reset(); limparAvisos("#avisos-form");
    form.querySelectorAll("[aria-invalid]").forEach((el) => el.removeAttribute("aria-invalid"));
    form.querySelectorAll(".erro-campo").forEach((el) => el.remove());
    janelaNova.showModal();
    form.querySelector("input").focus();
  });

  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    form.querySelectorAll(".erro-campo").forEach((el) => el.remove());
    form.querySelectorAll("[aria-invalid]").forEach((el) => el.removeAttribute("aria-invalid"));
    limparAvisos("#avisos-form");
    const corpo = Object.fromEntries(new FormData(form).entries());
    const botao = $("#botao-salvar");
    botao.disabled = true;
    try {
      const criada = await QF_API.criarSolicitacao(corpo);
      janelaNova.close();
      aviso("sucesso", "Solicitação adicionada ao lote. ", `Pedido ${criada.numero_pedido || "(sem número)"} gravado na linha ${criada.linha} do pedidos_entrada.csv.`);
      await carregar();
    } catch (erro) {
      if (erro.erros && erro.erros.length) {
        erro.erros.forEach((x) => {
          const campo = form.elements[x.campo];
          if (campo) {
            campo.setAttribute("aria-invalid", "true");
            const msg = document.createElement("span");
            msg.className = "erro-campo";
            msg.textContent = x.mensagem;
            campo.insertAdjacentElement("afterend", msg);
          }
        });
        aviso("erro", "Corrija os campos destacados. ", "", { alvo: "#avisos-form", fixo: true });
      } else {
        aviso("erro", "Não foi possível salvar. ", erro.message, { alvo: "#avisos-form", fixo: true });
      }
    } finally {
      botao.disabled = false;
    }
  });

  $("#botao-restaurar").addEventListener("click", () => janelaRestaurar.showModal());
  $("#confirmar-restaurar").addEventListener("click", async () => {
    janelaRestaurar.close();
    try {
      const r = await QF_API.restaurarExemplo();
      aviso("sucesso", "Lote restaurado. ", r.mensagem);
      await carregar();
    } catch (erro) {
      aviso("erro", "Não foi possível restaurar o lote. ", erro.message, { fixo: true });
    }
  });

  carregar();
  setInterval(async () => {
    try { const d = await QF_API.solicitacoes(); bloqueio(d.edicao_bloqueada); } catch (e) { /* estado global já informa */ }
  }, 5000);
})();
