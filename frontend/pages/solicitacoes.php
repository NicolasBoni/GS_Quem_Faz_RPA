<?php declare(strict_types=1); ?>
<div id="aviso-bloqueio"></div>

<section class="cartao">
    <div class="cartao-cab">
        <div>
            <h2>Pedidos de entrada do RPA</h2>
            <p id="meta-entrada">Conteúdo do arquivo pedidos_entrada.csv</p>
        </div>
        <div class="topo-acoes">
            <button class="botao" id="botao-restaurar"><?= qf_icone('restaurar') ?>Restaurar lote de teste (11)</button>
            <button class="botao primario" id="botao-nova"><?= qf_icone('mais') ?>Nova solicitação de teste</button>
        </div>
    </div>
    <div class="filtros" role="search">
        <label class="campo-busca">
            <span class="visualmente-oculto">Buscar</span>
            <?= qf_icone('busca') ?>
            <input type="search" id="busca" placeholder="Buscar por número, descrição, bairro ou contratante">
        </label>
        <label><span class="visualmente-oculto">Categoria</span><select id="filtro-categoria"></select></label>
        <label><span class="visualmente-oculto">Situação</span><select id="filtro-situacao"></select></label>
    </div>
    <div class="tabela-rolagem" id="tabela-solicitacoes"></div>
    <div class="tabela-rodape"><span id="contagem"></span><span>Clique em uma linha para ver os detalhes.</span></div>
</section>

<dialog class="detalhe" id="janela-nova" aria-labelledby="titulo-nova">
    <form id="form-nova" novalidate>
        <div class="detalhe-cab">
            <h2 id="titulo-nova">Nova solicitação de teste</h2>
            <button type="button" class="botao-icone" data-fechar aria-label="Fechar"><?= qf_icone('fechar') ?></button>
        </div>
        <div class="detalhe-corpo">
            <div class="aviso info">
                <?= qf_icone('info') ?>
                <p>A linha será anexada ao <strong>pedidos_entrada.csv</strong> e validada pelo RPA no próximo processamento.
                Campos podem ficar vazios para testar as regras de reprovação. Por compatibilidade com o fluxo, vírgulas,
                aspas, ponto e vírgula e quebras de linha não são aceitos.</p>
            </div>
            <div class="formulario secao">
                <label>Número do pedido <small>Ex.: PED-010</small>
                    <input type="text" name="numero_pedido" maxlength="20" autocomplete="off" pattern="[A-Za-z0-9_\-]*">
                </label>
                <label>Categoria <small>Permitidas: LIMPEZA, PINTURA, MANUTENCAO</small>
                    <input type="text" name="categoria" maxlength="30" list="categorias-rpa" autocomplete="off">
                    <datalist id="categorias-rpa">
                        <option value="LIMPEZA"><option value="PINTURA"><option value="MANUTENCAO"><option value="JARDINAGEM">
                    </datalist>
                </label>
                <label class="largo">Descrição do serviço
                    <input type="text" name="descricao" maxlength="120" autocomplete="off">
                </label>
                <label>Bairro <small>São Paulo</small>
                    <input type="text" name="bairro" maxlength="60" autocomplete="off">
                </label>
                <label>Código do contratante <small>Ex.: CLI-012 (dado fictício)</small>
                    <input type="text" name="codigo_cliente" maxlength="20" autocomplete="off">
                </label>
                <label>Situação
                    <select name="situacao">
                        <option value="PENDENTE">PENDENTE (será validado)</option>
                        <option value="PUBLICADO">PUBLICADO (será ignorado)</option>
                        <option value="CANCELADO">CANCELADO (será ignorado)</option>
                    </select>
                </label>
            </div>
            <div id="avisos-form" class="avisos secao"></div>
        </div>
        <div class="detalhe-rodape">
            <button type="button" class="botao" data-fechar>Cancelar</button>
            <button type="submit" class="botao primario" id="botao-salvar"><?= qf_icone('mais') ?>Adicionar ao lote</button>
        </div>
    </form>
</dialog>

<dialog class="detalhe" id="janela-restaurar" aria-labelledby="titulo-restaurar">
    <div class="detalhe-cab"><h2 id="titulo-restaurar">Restaurar lote de teste?</h2></div>
    <div class="detalhe-corpo">
        <p>O arquivo <strong>pedidos_entrada.csv</strong> será substituído pelos 11 pedidos do teste inicial
        (resultado esperado: 4 aprovados, 5 reprovados, 1 duplicado e 1 ignorado).
        O arquivo atual será copiado para a pasta de arquivamento do backend antes da substituição.</p>
    </div>
    <div class="detalhe-rodape">
        <button class="botao" data-fechar>Cancelar</button>
        <button class="botao primario" id="confirmar-restaurar"><?= qf_icone('restaurar') ?>Restaurar</button>
    </div>
</dialog>
