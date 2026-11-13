/* Dashboard: indicadores calculados pela API a partir dos CSVs reais. */
(function () {
  "use strict";
  const { $, esc, icone, seloSituacaoExecucao, dataHora, estadoVazio, esqueleto, aplicarLarguras, MODOS } = QF_UI;
  const ORDEM = ["APROVADO", "REPROVADO", "DUPLICADO", "IGNORADO"];
  const ROTULO = { APROVADO: "Aprovados", REPROVADO: "Reprovados", DUPLICADO: "Duplicados", IGNORADO: "Ignorados" };

  $("#distribuicao").innerHTML = esqueleto(3);
  $("#categorias").innerHTML = esqueleto(4);
  $("#situacao-automacao").innerHTML = esqueleto(3);
  $("#execucoes-recentes").innerHTML = esqueleto(4);

  function kpis(e) {
    const valores = { total: e.total_solicitacoes, pendentes: e.pendentes, aprovados: e.aprovados,
      reprovados: e.reprovados, duplicados: e.duplicados, ignorados: e.ignorados };
    Object.entries(valores).forEach(([k, v]) => { $("#kpi-" + k).textContent = v.toLocaleString("pt-BR"); });
  }

  function distribuicao(e) {
    const total = e.aprovados + e.reprovados + e.duplicados + e.ignorados;
    $("#ultimo-processamento").textContent = e.ultimo_processamento
      ? `Último resumo gravado pelo RPA: ${e.ultimo_processamento}` +
        (e.resultados_correspondem_ao_lote ? " · corresponde ao lote atual" : " · lote de entrada foi alterado depois")
      : "Nenhum processamento concluído encontrado nos arquivos do RPA.";
    if (!total) {
      $("#distribuicao").innerHTML = estadoVazio("Sem resultados ainda", "Execute o processamento para gerar pedidos_processados.csv.", "resultados");
      return;
    }
    const valores = { APROVADO: e.aprovados, REPROVADO: e.reprovados, DUPLICADO: e.duplicados, IGNORADO: e.ignorados };
    const segs = ORDEM.filter((r) => valores[r] > 0).map((r) => {
      const pct = (valores[r] / total) * 100;
      return `<span class="barra-seg ${r}" data-largura="${pct.toFixed(2)}" data-dica="${ROTULO[r]}: ${valores[r]} de ${total} (${pct.toFixed(0)}%)"></span>`;
    }).join("");
    const linhas = ORDEM.map((r) => `<tr><td>${QF_UI.seloResultado(r)}</td><td class="num">${valores[r]}</td>
      <td class="num">${((valores[r] / total) * 100).toFixed(0)}%</td></tr>`).join("");
    $("#distribuicao").innerHTML = `
      <div class="distribuicao" role="img" aria-label="Distribuição: ${ORDEM.map((r) => `${ROTULO[r]} ${valores[r]}`).join(", ")}">${segs}</div>
      <div class="tabela-rolagem"><table><caption class="visualmente-oculto">Distribuição dos resultados</caption>
        <thead><tr><th>Classificação</th><th class="num">Pedidos</th><th class="num">Participação</th></tr></thead>
        <tbody>${linhas}<tr><td><strong>Total analisado</strong></td><td class="num"><strong>${total}</strong></td><td class="num">100%</td></tr></tbody>
      </table></div>
      <p class="kpi-detalhe">${e.publicaveis} pedido(s) aptos para publicação em pedidos_publicaveis.csv.</p>`;
    aplicarLarguras($("#distribuicao"));
  }

  function categorias(e) {
    if (!e.categorias.length) {
      $("#categorias").innerHTML = estadoVazio("Sem categorias para exibir", "Os dados aparecem após o primeiro processamento.", "painel");
      return;
    }
    const maior = Math.max(...e.categorias.map((c) => c.total));
    $("#categorias").innerHTML = `<div class="barras">${e.categorias.map((c) => {
      const segs = ORDEM.filter((r) => c[r] > 0).map((r) =>
        `<span class="barra-seg ${r}" data-largura="${((c[r] / maior) * 100).toFixed(2)}" data-dica="${esc(c.categoria)} · ${ROTULO[r]}: ${c[r]}"></span>`).join("");
      const descricao = ORDEM.filter((r) => c[r] > 0).map((r) => `${ROTULO[r].toLowerCase()} ${c[r]}`).join(", ");
      return `<div class="barra-linha"><span class="barra-rotulo" title="${esc(c.categoria)}">${esc(c.categoria)}</span>
        <span class="barra-trilho" role="img" aria-label="${esc(c.categoria)}: ${descricao}">${segs}</span>
        <span class="barra-valor">${c.total}</span></div>`;
    }).join("")}</div>
    <div class="legenda" aria-hidden="true">${ORDEM.map((r) => `<span><i class="${r}"></i>${ROTULO[r]}</span>`).join("")}</div>`;
    aplicarLarguras($("#categorias"));
  }

  function situacao(e, saude) {
    const exe = e.execucao_ativa || e.ultima_execucao;
    const linhas = [];
    linhas.push(["Estado atual", e.execucao_ativa ? seloSituacaoExecucao(e.execucao_ativa.situacao) : seloSituacaoExecucao(e.situacao_automacao)]);
    if (saude) {
      linhas.push(["Fluxo autorizado", `<span class="codigo">${esc(saude.nome_fluxo)}</span>`]);
      linhas.push(["Modo padrão", esc(MODOS[saude.modo_padrao] || saude.modo_padrao)]);
      linhas.push(["Console do PAD", saude.console_pad_ativo ? "Aberto" : "Fechado"]);
    }
    if (exe) {
      linhas.push(["Última execução", `<span class="codigo">${esc(exe.id_execucao)}</span> · ${dataHora(exe.data_inicio)}`]);
      if (!e.execucao_ativa) linhas.push(["Resultado", seloSituacaoExecucao(exe.situacao)]);
    }
    $("#situacao-automacao").innerHTML = `<table><tbody>${linhas.map(([k, v]) => `<tr><th scope="row">${esc(k)}</th><td>${v}</td></tr>`).join("")}</tbody></table>`;
  }

  function execucoes(e) {
    if (!e.execucoes_recentes.length) {
      $("#execucoes-recentes").innerHTML = estadoVazio("Nenhuma execução registrada pela interface", "Use a página Processamento RPA para iniciar.", "robo");
      return;
    }
    $("#execucoes-recentes").innerHTML = `<table><thead><tr><th>Início</th><th>Modo</th><th>Situação</th><th class="num">Aprov./Total</th></tr></thead>
      <tbody>${e.execucoes_recentes.map((x) => `<tr><td>${dataHora(x.data_inicio)}</td><td>${esc((MODOS[x.modo] || x.modo).split(" (")[0])}</td>
      <td>${seloSituacaoExecucao(x.situacao)}</td><td class="num">${x.resumo ? `${x.resumo.aprovados}/${x.resumo.total}` : "—"}</td></tr>`).join("")}</tbody></table>`;
  }

  async function carregar() {
    try {
      const [e, saude] = await Promise.all([QF_API.estatisticas(), QF_API.saude().catch(() => null)]);
      kpis(e); distribuicao(e); categorias(e); situacao(e, saude); execucoes(e);
      if (saude) saude.diagnosticos.filter((d) => !d.ok && d.nome === "Arquivo de entrada")
        .forEach((d) => { QF_UI.limparAvisos(); QF_UI.aviso("erro", "Arquivo de entrada: ", d.detalhe, { fixo: true }); });
      return e;
    } catch (erro) {
      QF_UI.limparAvisos();
      QF_UI.erroDeCarga(erro, "Não foi possível carregar os indicadores");
      ["#distribuicao", "#categorias", "#situacao-automacao", "#execucoes-recentes"].forEach((s) => { $(s).innerHTML = estadoVazio("Dados indisponíveis", "", "alerta"); });
      return null;
    }
  }

  // Atualiza sozinho enquanto houver execução ativa (dashboard reflete o término do RPA).
  async function ciclo() {
    const e = await carregar();
    setTimeout(ciclo, e && e.execucao_ativa ? 3000 : 20000);
  }
  ciclo();
})();
