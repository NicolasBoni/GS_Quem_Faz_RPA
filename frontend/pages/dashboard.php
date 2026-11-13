<?php declare(strict_types=1); ?>
<section class="grade grade-kpi" aria-label="Indicadores" id="kpis">
    <?php
    $kpis = [
        ['total',      'Total de solicitações', 'total',     'azul',   'no arquivo de entrada'],
        ['pendentes',  'Pendentes',             'pendente',  'azul',   'situação PENDENTE'],
        ['aprovados',  'Aprovados',             'aprovado',  'ok',     'último processamento'],
        ['reprovados', 'Reprovados',            'reprovado', 'erro',   'regras de negócio'],
        ['duplicados', 'Duplicados',            'duplicado', 'alerta', 'número repetido no lote'],
        ['ignorados',  'Ignorados',             'ignorado',  'neutro', 'não pendentes'],
    ];
    foreach ($kpis as [$id, $rotulo, $icone, $tom, $detalhe]): ?>
        <article class="cartao kpi">
            <span class="kpi-rotulo"><span class="chip-icone <?= $tom ?>"><?= qf_icone($icone) ?></span><?= qf_e($rotulo) ?></span>
            <span class="kpi-valor" id="kpi-<?= $id ?>" aria-live="polite">—</span>
            <span class="kpi-detalhe"><?= qf_e($detalhe) ?></span>
        </article>
    <?php endforeach; ?>
</section>

<section class="grade grade-2 secao">
    <article class="cartao">
        <div class="cartao-cab">
            <div>
                <h2>Distribuição do último processamento</h2>
                <p id="ultimo-processamento">Carregando…</p>
            </div>
            <a class="botao" href="?pagina=resultados">Ver resultados</a>
        </div>
        <div class="cartao-corpo" id="distribuicao"><?= '' ?></div>
    </article>
    <article class="cartao">
        <div class="cartao-cab">
            <div>
                <h2>Situação da automação</h2>
                <p>Power Automate Desktop · fluxo autorizado</p>
            </div>
            <a class="botao primario" href="?pagina=processamento"><?= qf_icone('play') ?>Processar</a>
        </div>
        <div class="cartao-corpo" id="situacao-automacao"></div>
    </article>
</section>

<section class="grade grade-2-igual secao">
    <article class="cartao">
        <div class="cartao-cab">
            <div>
                <h2>Resumo por categoria</h2>
                <p>Resultados do RPA agrupados por categoria do serviço</p>
            </div>
        </div>
        <div class="cartao-corpo" id="categorias"></div>
    </article>
    <article class="cartao">
        <div class="cartao-cab">
            <div>
                <h2>Execuções recentes</h2>
                <p>Registradas pela interface administrativa</p>
            </div>
            <a class="botao" href="?pagina=logs">Auditoria</a>
        </div>
        <div class="tabela-rolagem" id="execucoes-recentes"></div>
    </article>
</section>
