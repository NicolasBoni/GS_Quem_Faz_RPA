<?php declare(strict_types=1); ?>
<section class="cartao">
    <div class="cartao-cab">
        <div>
            <h2>Execuções e status final</h2>
            <p>Identificador, modo, situação final e motivo da falha registrados pelo backend</p>
        </div>
    </div>
    <div class="tabela-rolagem" id="tabela-execucoes"></div>
</section>

<section class="cartao secao">
    <div class="cartao-cab">
        <div>
            <h2>Histórico gravado pelo RPA</h2>
            <p id="meta-historico">historico_execucao.csv</p>
        </div>
        <label><span class="visualmente-oculto">Arquivo de histórico</span>
            <select id="seletor-arquivo"><option value="">Arquivo atual do RPA</option></select>
        </label>
    </div>
    <div class="filtros" role="search">
        <label class="campo-busca">
            <span class="visualmente-oculto">Buscar</span><?= qf_icone('busca') ?>
            <input type="search" id="busca" placeholder="Buscar por pedido ou mensagem">
        </label>
        <label><span class="visualmente-oculto">Etapa</span><select id="filtro-etapa"></select></label>
        <label><span class="visualmente-oculto">Resultado</span><select id="filtro-resultado"></select></label>
    </div>
    <div class="tabela-rolagem" id="tabela-historico"></div>
    <div class="tabela-rodape"><span id="contagem"></span>
        <span>O log do RPA não registra o código do contratante (minimização de dados).</span></div>
</section>
