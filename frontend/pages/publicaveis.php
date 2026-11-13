<?php declare(strict_types=1); ?>
<div class="aviso info">
    <?= qf_icone('info') ?>
    <p><strong>Apto para publicação</strong>
    Estes pedidos foram aprovados pelo RPA e gravados em <span class="codigo">pedidos_publicaveis.csv</span> com a situação
    técnica <span class="codigo">PUBLICADO</span>. Isso representa o resultado do processamento demonstrativo:
    não significa que o pedido já foi publicado em um marketplace externo nem que profissionais foram notificados.</p>
</div>

<section class="cartao secao">
    <div class="cartao-cab">
        <div>
            <h2>Pedidos aptos para publicação</h2>
            <p id="meta-publicaveis">Conteúdo de pedidos_publicaveis.csv</p>
        </div>
        <a class="botao" id="exportar" href="#"><?= qf_icone('baixar') ?>Exportar CSV</a>
    </div>
    <div class="filtros" role="search">
        <label class="campo-busca">
            <span class="visualmente-oculto">Buscar</span><?= qf_icone('busca') ?>
            <input type="search" id="busca" placeholder="Buscar por número ou descrição">
        </label>
        <label><span class="visualmente-oculto">Categoria</span><select id="filtro-categoria"></select></label>
        <label><span class="visualmente-oculto">Bairro</span><select id="filtro-bairro"></select></label>
    </div>
    <div class="tabela-rolagem" id="tabela-publicaveis"></div>
    <div class="tabela-rodape"><span id="contagem"></span><span>O código do contratante não é enviado para esta saída (LGPD).</span></div>
</section>
