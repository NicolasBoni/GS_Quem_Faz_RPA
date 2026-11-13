/* Logs e auditoria: execuções registradas + historico_execucao.csv (atual ou arquivado). */
(function () {
  "use strict";
  const { $, esc, seloResultado, seloSituacaoExecucao, dataHora, estadoVazio, esqueleto, infoArquivo, avisosArquivo,
    contem, preencherSelect, MODOS, limparAvisos } = QF_UI;
  let dados = null;
  const busca = $("#busca"), fEtapa = $("#filtro-etapa"), fRes = $("#filtro-resultado"), seletor = $("#seletor-arquivo");

  function renderExecucoes(lista) {
    if (!lista.length) {
      $("#tabela-execucoes").innerHTML = estadoVazio("Nenhuma execução registrada pela interface", "Execuções iniciadas direto no PAD aparecem apenas no histórico abaixo.", "robo");
      return;
    }
    $("#tabela-execucoes").innerHTML = `<table><thead><tr><th>Identificador</th><th>Início</th><th>Fim</th><th>Modo</th><th>Status final</th><th>Marca do RPA</th><th>Mensagem</th><th>Motivo da falha</th></tr></thead>
      <tbody>${lista.map((x) => `<tr><td class="codigo">${esc(x.id_execucao)}</td><td>${dataHora(x.data_inicio)}</td><td>${dataHora(x.data_fim)}</td>
      <td>${esc((MODOS[x.modo] || x.modo).split(" (")[0])}</td><td>${seloSituacaoExecucao(x.situacao)}</td>
      <td class="codigo">${esc(x.evidencias.marca_execucao_rpa || "—")}</td><td>${esc(x.mensagem)}</td><td>${esc(x.motivo_erro || "—")}</td></tr>`).join("")}</tbody></table>`;
  }

  const seloLog = (r) => r === "CONCLUIDO" ? `<span class="selo aprovado">Concluído</span>` : seloResultado(r);

  function render() {
    const itens = dados.eventos.filter((e) => (!fEtapa.value || e.etapa === fEtapa.value) && (!fRes.value || e.resultado === fRes.value) &&
      contem(e, busca.value.trim(), ["numero_pedido", "mensagem", "etapa"]));
    $("#contagem").textContent = `${itens.length} de ${dados.eventos.length} registro(s)`;
    if (!dados.eventos.length) {
      $("#tabela-historico").innerHTML = estadoVazio("Histórico vazio", "O RPA grava o histórico durante o processamento.", "auditoria");
      return;
    }
    if (!itens.length) { $("#tabela-historico").innerHTML = estadoVazio("Nenhum registro para os filtros", "", "busca"); return; }
    $("#tabela-historico").innerHTML = `<table><thead><tr><th>Data e hora</th><th>Execução</th><th>Etapa</th><th>Pedido</th><th>Resultado</th><th>Mensagem</th></tr></thead>
      <tbody>${itens.map((e) => `<tr><td class="codigo">${esc(e.data_hora)}</td><td class="codigo">${esc(dados.id_execucao_arquivo || "—")}</td>
      <td>${esc(e.etapa)}</td><td class="codigo">${e.numero_pedido ? esc(e.numero_pedido) : '<span class="vazio-celula">sem número</span>'}</td>
      <td>${seloLog(e.resultado)}</td><td>${esc(e.mensagem)}</td></tr>`).join("")}</tbody></table>`;
  }

  async function carregar(id) {
    $("#tabela-historico").innerHTML = esqueleto(6);
    limparAvisos();
    try {
      dados = await QF_API.historico(id);
      avisosArquivo(dados.arquivo, id ? "Esta execução não arquivou o histórico." : "O RPA ainda não gerou o histórico.");
      const origem = id ? "Cópia arquivada da execução " + id : (dados.id_execucao_arquivo && dados.id_execucao_arquivo.startsWith("PAD-")
        ? "Execução iniciada diretamente no PAD (sem registro na interface)" : "Arquivo atual do RPA");
      $("#meta-historico").innerHTML = infoArquivo(dados.arquivo) + " · " + esc(origem);
      if (seletor.options.length === 1) {
        const ativas = ["aguardando_execucao", "iniciando_automacao", "processamento_em_andamento", "conferindo_resultados"];
        dados.execucoes.filter((x) => !ativas.includes(x.situacao)).forEach((x) => seletor.add(new Option(`${x.id_execucao} · ${QF_UI.SITUACOES[x.situacao]?.rotulo || x.situacao}`, x.id_execucao)));
      }
      renderExecucoes(dados.execucoes);
      preencherSelect(fEtapa, dados.eventos.map((e) => e.etapa), "Todas as etapas");
      preencherSelect(fRes, dados.eventos.map((e) => e.resultado), "Todos os resultados");
      render();
    } catch (erro) {
      QF_UI.erroDeCarga(erro, "Não foi possível carregar o histórico");
      $("#tabela-historico").innerHTML = estadoVazio("Dados indisponíveis", "", "alerta");
    }
  }

  [busca, fEtapa, fRes].forEach((el) => el.addEventListener("input", render));
  seletor.addEventListener("change", () => carregar(seletor.value || undefined));
  carregar();
})();
