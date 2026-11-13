<?php declare(strict_types=1); ?>
<section class="painel-execucao">
    <article class="cartao acionador">
        <div>
            <h2>Validação de solicitações pelo RPA</h2>
            <p>O backend valida o lote, arquiva os resultados anteriores e aciona o fluxo autorizado
               <strong class="codigo" id="nome-fluxo">…</strong> no Power Automate Desktop. A conclusão só é aceita
               quando o próprio RPA grava o resumo do lote e os arquivos conferem entre si.</p>
        </div>

        <button class="botao primario botao-processar" id="botao-processar" disabled>
            <?= qf_icone('play') ?>Processar solicitações
        </button>
        <div id="pre-requisitos" class="evidencias" aria-label="Diagnóstico do ambiente"></div>
    </article>

    <article class="cartao" aria-live="polite">
        <div class="situacao-atual" id="situacao">
            <span class="indicador"><?= qf_icone('robo') ?></span>
            <div>
                <h3 id="situacao-titulo">Aguardando execução</h3>
                <p id="situacao-texto">Nenhuma execução em andamento.</p>
            </div>
        </div>
        <div class="progresso-indeterminado" id="progresso" hidden role="progressbar" aria-label="Processamento em andamento (sem percentual disponível)"></div>
        <div id="instrucoes-assistido" hidden class="cartao-corpo">
            <div class="aviso info">
                <?= qf_icone('info') ?>
                <div>
                    <strong>Modo assistido: inicie o fluxo manualmente</strong>
                    <ol class="passos-manuais">
                        <li>Abra o <strong>Power Automate Desktop</strong>.</li>
                        <li>Em <em>Meus fluxos</em>, localize <strong class="codigo" data-nome-fluxo></strong>.</li>
                        <li>Clique em <strong>Executar</strong> (▶) e aguarde as mensagens do fluxo.</li>
                        <li>Esta tela detecta o término automaticamente pelos arquivos gerados.</li>
                    </ol>
                </div>
            </div>
        </div>
        <div class="cartao-cab"><div><h2>Etapas comprovadas</h2><p id="id-execucao">—</p></div>
            <button class="botao perigo" id="botao-cancelar" hidden>Cancelar monitoramento</button></div>
        <ol class="linha-tempo" id="linha-tempo"></ol>
        <div class="cartao-cab"><div><h2>Evidências coletadas</h2><p>Sinais reais observados no computador</p></div></div>
        <div class="evidencias secao" id="evidencias"></div>
        <div id="resumo-final" class="cartao-corpo" hidden></div>
    </article>
</section>

<section class="cartao secao">
    <div class="cartao-cab"><div><h2>Histórico de execuções</h2><p>Execuções iniciadas por esta interface</p></div></div>
    <div class="tabela-rolagem" id="tabela-execucoes"></div>
</section>
