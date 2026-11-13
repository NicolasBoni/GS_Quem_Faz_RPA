<?php declare(strict_types=1); ?>
<section class="grade grade-kpi" id="kpis-resultados" aria-label="Contagem por classificação"></section>

<section class="cartao secao">
    <div class="cartao-cab">
        <div>
            <h2>Classificação dos pedidos pelo RPA</h2>
            <p id="meta-resultados">Conteúdo de pedidos_processados.csv</p>
        </div>
        <a class="botao" id="exportar" href="#"><?= qf_icone('baixar') ?>Exportar CSV</a>
    </div>
    <div class="abas" role="tablist" aria-label="Filtrar por classificação" id="abas"></div>
    <div class="filtros" role="search">
        <label class="campo-busca">
            <span class="visualmente-oculto">Buscar</span><?= qf_icone('busca') ?>
            <input type="search" id="busca" placeholder="Buscar por número, descrição, bairro ou justificativa">
        </label>
        <label><span class="visualmente-oculto">Categoria</span><select id="filtro-categoria"></select></label>
    </div>
    <div class="tabela-rolagem" id="tabela-resultados" role="tabpanel"></div>
    <div class="tabela-rodape">
        <span id="contagem"></span>
        <span>Reprovações são decisões das regras de negócio do RPA, não falhas técnicas.</span>
    </div>
</section>
