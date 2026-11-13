/* Processamento RPA: aciona o backend e acompanha APENAS etapas comprovadas (sem % fictício). */
(function () {
  "use strict";
  const { $, esc, icone, seloSituacaoExecucao, dataHora, estadoVazio, aviso, MODOS, SITUACOES } = QF_UI;
  const ATIVAS = ["aguardando_execucao", "iniciando_automacao", "processamento_em_andamento", "conferindo_resultados"];
  let saude = null, execucaoAtual = null, temporizador = null;

  function renderPreRequisitos() {
    const itens = saude.diagnosticos.filter((d) => !d.nome.startsWith("Modo "));
    itens.push({ nome: "Console do PAD", ok: saude.console_pad_ativo, detalhe: saude.console_pad_ativo ? "Aberto" : "Fechado" });
    $("#pre-requisitos").innerHTML = itens.map((d) =>
      `<div class="evidencia ${d.ok ? "sim" : "nao"}" title="${esc(d.detalhe)}">${icone(d.ok ? "aprovado" : "alerta")}<span><strong>${esc(d.nome)}</strong><br>${esc(d.detalhe)}</span></div>`).join("");
    const entradaOk = saude.diagnosticos.find((d) => d.nome === "Arquivo de entrada")?.ok;
    $("#botao-processar").disabled = !entradaOk || !!saude.execucao_ativa || saude.robo_pad_ativo;
    document.querySelectorAll("[data-nome-fluxo]").forEach((el) => { el.textContent = saude.nome_fluxo; });
    $("#nome-fluxo").textContent = saude.nome_fluxo;
  }

  function tomEtapa(situacao) {
    const tom = (SITUACOES[situacao] || {}).tom;
    return tom === "ok" ? "ok" : tom === "erro" ? "erro" : tom === "alerta" ? "alerta" : "";
  }

  function renderExecucao(x) {
    execucaoAtual = x;
    const s = SITUACOES[x.situacao] || { rotulo: x.situacao, tom: "neutro", icone: "info" };
    const ativa = ATIVAS.includes(x.situacao);
    const painel = $("#situacao");
    painel.className = "situacao-atual " + (s.tom === "neutro" ? "" : s.tom);
    painel.querySelector(".indicador").innerHTML = icone(s.icone);
    $("#situacao-titulo").textContent = s.rotulo;
    $("#situacao-texto").textContent = x.mensagem || "";
    $("#progresso").hidden = !ativa;
    $("#botao-cancelar").hidden = !ativa;
    $("#instrucoes-assistido").hidden = !(ativa && x.modo === "assistido" && !x.evidencias.robo_detectado && !x.evidencias.historico_atualizado);
    $("#id-execucao").innerHTML = `<span class="codigo">${esc(x.id_execucao)}</span> · modo ${esc((MODOS[x.modo] || x.modo).toLowerCase())}` +
      (x.modo !== x.modo_solicitado ? ` (solicitado: ${esc(MODOS[x.modo_solicitado] || x.modo_solicitado)})` : "");

    $("#linha-tempo").innerHTML = x.etapas.map((e) => `<li><span class="marcador ${tomEtapa(e.situacao)}">${icone((SITUACOES[e.situacao] || {}).icone || "info")}</span>
      <div><strong>${esc((SITUACOES[e.situacao] || {}).rotulo || e.situacao)}</strong> <time>${dataHora(e.data_hora)}</time><p>${esc(e.mensagem)}</p></div></li>`).join("");

    const ev = x.evidencias;
    const sinais = [
      ["Processo do robô do PAD detectado", ev.robo_detectado],
      ["Robô encerrado", ev.robo_encerrado],
      ["Histórico regravado nesta execução", ev.historico_atualizado],
      ["Resultados atualizados", ev.processados_atualizado],
      ["Publicáveis atualizados", ev.publicaveis_atualizado],
      ["Resumo do lote gravado pelo RPA", !!ev.linha_resumo],
    ];
    $("#evidencias").innerHTML = sinais.map(([t, ok]) => `<div class="evidencia ${ok ? "sim" : "nao"}">${icone(ok ? "aprovado" : "pendente")}<span>${esc(t)}<span class="visualmente-oculto">: ${ok ? "sim" : "ainda não"}</span></span></div>`).join("") +
      (ev.marca_execucao_rpa ? `<div class="evidencia sim">${icone("relogio")}<span>Marca do RPA: <span class="codigo">${esc(ev.marca_execucao_rpa)}</span></span></div>` : "");

    const final = $("#resumo-final");
    if (x.situacao === "concluido" && x.resumo) {
      const r = x.resumo;
      final.hidden = false;
      final.innerHTML = `<div class="aviso sucesso">${icone("aprovado")}<div><strong>Processamento concluído pelo Power Automate Desktop</strong>
        <p>${r.total} pedidos analisados: ${r.aprovados} aprovados, ${r.reprovados} reprovados, ${r.duplicados} duplicados e ${r.ignorados} ignorados.
        ${r.publicaveis} pedido(s) aptos para publicação.</p>
        <p class="secao"><a class="botao" href="?pagina=resultados">Ver resultados</a> <a class="botao" href="?pagina=publicaveis">Pedidos publicáveis</a></p></div></div>`;
    } else if (x.situacao === "falha_automacao" || x.situacao === "indeterminado") {
      final.hidden = false;
      final.innerHTML = `<div class="aviso ${x.situacao === "falha_automacao" ? "erro" : "alerta"}">${icone("alerta")}<div>
        <strong>${x.situacao === "falha_automacao" ? "Falha técnica na automação" : "Não foi possível confirmar a conclusão"}</strong>
        <p>${esc(x.motivo_erro || x.mensagem)}</p>
        <p>Isto é um problema técnico da execução, não uma reprovação de pedidos. Nenhum resultado desta execução foi aceito como válido.</p></div></div>`;
    } else {
      final.hidden = true;
    }
  }

  async function acompanhar(id) {
    clearTimeout(temporizador);
    try {
      const x = await QF_API.status(id);
      renderExecucao(x);
      if (ATIVAS.includes(x.situacao)) {
        temporizador = setTimeout(() => acompanhar(id), 1500);
      } else {
        await atualizarTudo();
        if (x.situacao === "concluido") aviso("sucesso", "Execução concluída. ", "Indicadores atualizados com os arquivos gerados pelo RPA.");
      }
    } catch (erro) {
      aviso("erro", "Falha ao consultar o andamento. ", erro.message);
      temporizador = setTimeout(() => acompanhar(id), 4000);
    }
  }

  function renderHistorico(lista) {
    if (!lista.length) {
      $("#tabela-execucoes").innerHTML = estadoVazio("Nenhuma execução registrada", "Clique em Processar solicitações para iniciar.", "robo");
      return;
    }
    $("#tabela-execucoes").innerHTML = `<table><thead><tr><th>Identificador</th><th>Início</th><th>Fim</th><th>Modo</th><th>Situação</th>
      <th class="num">Total</th><th class="num">Aprov.</th><th class="num">Reprov.</th><th class="num">Dupl.</th><th class="num">Ign.</th><th>Motivo da falha</th></tr></thead>
      <tbody>${lista.map((x) => `<tr class="clicavel" tabindex="0" data-id="${esc(x.id_execucao)}"><td class="codigo">${esc(x.id_execucao)}</td><td>${dataHora(x.data_inicio)}</td>
      <td>${dataHora(x.data_fim)}</td><td>${esc((MODOS[x.modo] || x.modo).split(" (")[0])}</td><td>${seloSituacaoExecucao(x.situacao)}</td>
      ${x.resumo ? `<td class="num">${x.resumo.total}</td><td class="num">${x.resumo.aprovados}</td><td class="num">${x.resumo.reprovados}</td><td class="num">${x.resumo.duplicados}</td><td class="num">${x.resumo.ignorados}</td>`
        : '<td class="num">—</td><td class="num">—</td><td class="num">—</td><td class="num">—</td><td class="num">—</td>'}
      <td>${x.motivo_erro ? esc(x.motivo_erro) : "—"}</td></tr>`).join("")}</tbody></table>`;
  }

  async function atualizarTudo() {
    try {
      const [s, lista] = await Promise.all([QF_API.saude(), QF_API.execucoes()]);
      saude = s;
      renderPreRequisitos();
      renderHistorico(lista);
      QF_UI.atualizarEstadoGlobal();
      return lista;
    } catch (erro) {
      QF_UI.erroDeCarga(erro, "Backend indisponível");
      $("#botao-processar").disabled = true;
      return [];
    }
  }

  $("#botao-processar").addEventListener("click", async () => {
    const botao = $("#botao-processar");
    botao.disabled = true;
    QF_UI.limparAvisos();
    try {
      const x = await QF_API.executar();  // modo_padrao definido em backend/config.py
      renderExecucao(x);
      acompanhar(x.id_execucao);
    } catch (erro) {
      aviso("erro", "Processamento não iniciado. ", erro.message, { fixo: true });
      botao.disabled = false;
    }
  });

  $("#botao-cancelar").addEventListener("click", async () => {
    if (!execucaoAtual) return;
    try { await QF_API.cancelar(execucaoAtual.id_execucao); acompanhar(execucaoAtual.id_execucao); }
    catch (erro) { aviso("erro", "Não foi possível cancelar. ", erro.message); }
  });

  $("#tabela-execucoes").addEventListener("click", (e) => {
    const tr = e.target.closest("tr[data-id]");
    if (tr) acompanhar(tr.dataset.id);
  });

  (async function iniciar() {
    $("#linha-tempo").innerHTML = '<li><span class="marcador">' + icone("relogio") + "</span><div><strong>Aguardando execução</strong><p>Clique em Processar solicitações.</p></div></li>";
    const lista = await atualizarTudo();
    const ativa = lista.find((x) => ATIVAS.includes(x.situacao));
    if (ativa) acompanhar(ativa.id_execucao);
    else if (lista[0]) renderExecucao(lista[0]);
    setInterval(() => { if (!execucaoAtual || !ATIVAS.includes(execucaoAtual.situacao)) atualizarTudo(); }, 15000);
  })();
})();
