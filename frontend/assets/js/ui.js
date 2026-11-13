/* Utilitários de interface compartilhados por todas as páginas. */
(function () {
  "use strict";
  const ICONES = JSON.parse(document.getElementById("qf-icones")?.textContent || "{}");

  const esc = (v) => String(v ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
  const icone = (nome) => ICONES[nome] || "";
  const $ = (sel, raiz = document) => raiz.querySelector(sel);

  const RESULTADOS = {
    APROVADO: { classe: "aprovado", icone: "aprovado", rotulo: "Aprovado" },
    REPROVADO: { classe: "reprovado", icone: "reprovado", rotulo: "Reprovado" },
    DUPLICADO: { classe: "duplicado", icone: "duplicado", rotulo: "Duplicado" },
    IGNORADO: { classe: "ignorado", icone: "ignorado", rotulo: "Ignorado" },
  };

  const SITUACOES = {
    aguardando_execucao: { rotulo: "Aguardando execução", tom: "ativa", icone: "relogio" },
    iniciando_automacao: { rotulo: "Iniciando automação", tom: "ativa", icone: "robo" },
    processamento_em_andamento: { rotulo: "Processamento em andamento", tom: "ativa", icone: "robo" },
    conferindo_resultados: { rotulo: "Conferindo resultados", tom: "ativa", icone: "info" },
    concluido: { rotulo: "Concluído", tom: "ok", icone: "aprovado" },
    falha_automacao: { rotulo: "Falha na automação", tom: "erro", icone: "alerta" },
    indeterminado: { rotulo: "Resultado indeterminado", tom: "alerta", icone: "alerta" },
    cancelado: { rotulo: "Monitoramento cancelado", tom: "neutro", icone: "ignorado" },
    ociosa: { rotulo: "Ociosa", tom: "neutro", icone: "robo" },
    robo_ocupado: { rotulo: "PAD executando outro fluxo", tom: "alerta", icone: "robo" },
  };

  const MODOS = {
    assistido: "Assistido (início manual no PAD)",
    atalho: "Atalho de teclado",
    interface_grafica: "Automação da interface (pywinauto)",
    url_local: "URL local do PAD",
  };

  function seloResultado(resultado) {
    const r = RESULTADOS[resultado];
    if (!r) return `<span class="selo neutro">${esc(resultado || "—")}</span>`;
    return `<span class="selo ${r.classe}">${icone(r.icone)}${r.rotulo}</span>`;
  }

  function seloSituacaoPedido(situacao) {
    if (situacao === "PENDENTE") return `<span class="selo pendente">${icone("pendente")}Pendente</span>`;
    if (situacao === "PUBLICADO") return `<span class="selo neutro">${icone("info")}Já publicado</span>`;
    if (!situacao) return `<span class="selo neutro">Não informada</span>`;
    return `<span class="selo neutro">${esc(situacao)}</span>`;
  }

  function seloSituacaoExecucao(situacao) {
    const s = SITUACOES[situacao] || { rotulo: situacao, tom: "neutro", icone: "info" };
    const classe = { ok: "aprovado", erro: "reprovado", alerta: "duplicado", ativa: "info", neutro: "ignorado" }[s.tom];
    return `<span class="selo ${classe}">${icone(s.icone)}${esc(s.rotulo)}</span>`;
  }

  const valorOuVazio = (v) => (v ? esc(v) : `<span class="vazio-celula">não informado</span>`);

  function dataHora(iso) {
    if (!iso) return "—";
    const d = new Date(iso);
    if (isNaN(d)) return esc(iso);
    return d.toLocaleString("pt-BR", { dateStyle: "short", timeStyle: "medium" });
  }

  function aviso(tipo, titulo, texto, { fixo = false, alvo = "#avisos" } = {}) {
    const caixa = $(alvo);
    if (!caixa) return;
    const nomeIcone = { sucesso: "aprovado", erro: "alerta", alerta: "alerta", info: "info" }[tipo];
    const el = document.createElement("div");
    el.className = `aviso ${tipo}`;
    el.setAttribute("role", tipo === "erro" ? "alert" : "status");
    el.innerHTML = `${icone(nomeIcone)}<p><strong>${esc(titulo)}</strong>${texto ? esc(texto) : ""}</p>
      <button class="fechar-aviso" aria-label="Fechar aviso">${icone("fechar")}</button>`;
    el.querySelector(".fechar-aviso").addEventListener("click", () => el.remove());
    caixa.prepend(el);
    if (!fixo) setTimeout(() => el.remove(), 9000);
    return el;
  }

  function limparAvisos(alvo = "#avisos") { const c = $(alvo); if (c) c.innerHTML = ""; }

  function estadoVazio(titulo, texto, nomeIcone = "pasta") {
    return `<div class="estado-vazio">${icone(nomeIcone)}<strong>${esc(titulo)}</strong>${esc(texto || "")}</div>`;
  }

  function esqueleto(linhas = 4) {
    return `<div class="carregando-linha" aria-busy="true" aria-label="Carregando">${'<div class="esqueleto"></div>'.repeat(linhas)}</div>`;
  }

  function infoArquivo(arquivo) {
    if (!arquivo) return "";
    if (!arquivo.existe) return `<span class="meta-arquivo">${icone("pasta")}${esc(arquivo.nome)} · não encontrado</span>`;
    return `<span class="meta-arquivo">${icone("pasta")}${esc(arquivo.nome)} · atualizado em ${dataHora(arquivo.modificado_em)}</span>`;
  }

  /** Avisos sobre o arquivo: inexistente, inválido ou com linhas deslocadas. */
  function avisosArquivo(arquivo, contexto) {
    if (!arquivo) return;
    if (!arquivo.existe) {
      aviso("alerta", `${arquivo.nome} ainda não existe. `, contexto || "", { fixo: true });
    } else if (!arquivo.valido) {
      aviso("erro", `Não foi possível interpretar ${arquivo.nome}. `, arquivo.erro || "", { fixo: true });
    } else if (arquivo.linhas_invalidas && arquivo.linhas_invalidas.length) {
      const nums = arquivo.linhas_invalidas.map((l) => l.numero_linha).join(", ");
      aviso("alerta", `${arquivo.linhas_invalidas.length} linha(s) de ${arquivo.nome} com colunas deslocadas (linhas ${nums}). `,
        "Provável vírgula dentro de um campo. Essas linhas não foram exibidas.", { fixo: true });
    }
  }

  /** Barras (larguras aplicadas via CSSOM, compatível com a CSP sem estilos inline). */
  function aplicarLarguras(raiz = document) {
    raiz.querySelectorAll("[data-largura]").forEach((el) => {
      el.style.flexBasis = el.dataset.largura + "%";
      el.style.flexGrow = "0";
    });
  }

  // Dica de passagem do mouse para segmentos de barra
  let dica;
  document.addEventListener("pointerover", (e) => {
    const alvo = e.target.closest("[data-dica]");
    if (!alvo) return;
    if (!dica) { dica = document.createElement("div"); dica.className = "dica"; document.body.appendChild(dica); }
    dica.textContent = alvo.dataset.dica;
    dica.hidden = false;
  });
  document.addEventListener("pointermove", (e) => {
    if (!dica || dica.hidden) return;
    dica.style.left = Math.min(e.clientX + 12, window.innerWidth - dica.offsetWidth - 8) + "px";
    dica.style.top = e.clientY - 34 + "px";
  });
  document.addEventListener("pointerout", (e) => { if (dica && e.target.closest("[data-dica]")) dica.hidden = true; });

  /** Janela de detalhes acessível (<dialog>). */
  function abrirDetalhe(titulo, pares, seloHtml = "") {
    let dlg = $("#janela-detalhe");
    if (!dlg) {
      dlg = document.createElement("dialog");
      dlg.id = "janela-detalhe";
      dlg.className = "detalhe";
      dlg.setAttribute("aria-labelledby", "detalhe-titulo");
      document.body.appendChild(dlg);
      dlg.addEventListener("click", (e) => { if (e.target === dlg) dlg.close(); });
    }
    dlg.innerHTML = `<div class="detalhe-cab"><h2 id="detalhe-titulo">${esc(titulo)}</h2>${seloHtml}</div>
      <div class="detalhe-corpo"><dl>${pares.map(([k, v]) => `<dt>${esc(k)}</dt><dd>${v}</dd>`).join("")}</dl></div>
      <div class="detalhe-rodape"><button class="botao" data-fechar>Fechar</button></div>`;
    dlg.querySelector("[data-fechar]").addEventListener("click", () => dlg.close());
    dlg.showModal();
  }

  /** Filtro textual simples, sem acentos e sem diferenciar maiúsculas. */
  const normalizar = (t) => String(t || "").normalize("NFD").replace(/[̀-ͯ]/g, "").toLowerCase();
  const contem = (registro, termo, campos) => !termo || campos.some((c) => normalizar(registro[c]).includes(normalizar(termo)));

  function preencherSelect(select, valores, rotuloTodos) {
    const atual = select.value;
    const unicos = [...new Set(valores.filter((v) => v !== undefined))].sort((a, b) => String(a).localeCompare(String(b), "pt-BR"));
    select.innerHTML = `<option value="">${esc(rotuloTodos)}</option>` +
      unicos.map((v) => `<option value="${esc(v)}">${v ? esc(v) : "(não informado)"}</option>`).join("");
    if (unicos.includes(atual)) select.value = atual;
  }

  // ------------------------------------------------------- menu móvel
  const lateral = $("#menu-lateral"), cortina = $("#cortina"), botaoMenu = $("#abrir-menu");
  function menu(aberto) {
    lateral.classList.toggle("aberta", aberto);
    cortina.hidden = !aberto;
    botaoMenu.setAttribute("aria-expanded", String(aberto));
  }
  botaoMenu?.addEventListener("click", () => menu(!lateral.classList.contains("aberta")));
  cortina?.addEventListener("click", () => menu(false));
  document.addEventListener("keydown", (e) => { if (e.key === "Escape") menu(false); });

  // ------------------------------------------- estado da API e do RPA
  async function atualizarEstadoGlobal() {
    const caixa = $("#estado-api"), selo = $("#selo-automacao");
    try {
      const saude = await QF_API.saude();
      caixa.className = "estado-api ok";
      caixa.querySelector(".texto").textContent = "API conectada · v" + saude.versao;
      let texto, ativa = false;
      if (saude.execucao_ativa) { texto = "Automação: execução em andamento"; ativa = true; }
      else if (saude.robo_pad_ativo) { texto = "Automação: PAD ocupado"; ativa = true; }
      else if (saude.console_pad_ativo) texto = "Automação: PAD disponível · modo " + (MODOS[saude.modo_padrao] || saude.modo_padrao).split(" (")[0].toLowerCase();
      else texto = "Automação: console do PAD fechado";
      selo.classList.toggle("ativa", ativa);
      selo.querySelector("span").textContent = texto;
      return saude;
    } catch (erro) {
      caixa.className = "estado-api erro";
      caixa.querySelector(".texto").textContent = "API indisponível";
      selo.classList.remove("ativa");
      selo.querySelector("span").textContent = "Automação: sem conexão com o backend";
      return null;
    }
  }
  atualizarEstadoGlobal();
  setInterval(atualizarEstadoGlobal, 10000);

  function erroDeCarga(erro, contexto) {
    aviso("erro", contexto + ". ", erro.message, { fixo: true });
  }

  window.QF_UI = {
    esc, icone, $, RESULTADOS, SITUACOES, MODOS, seloResultado, seloSituacaoPedido, seloSituacaoExecucao,
    valorOuVazio, dataHora, aviso, limparAvisos, estadoVazio, esqueleto, infoArquivo, avisosArquivo,
    aplicarLarguras, abrirDetalhe, contem, preencherSelect, atualizarEstadoGlobal, erroDeCarga,
  };
})();
