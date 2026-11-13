<?php
declare(strict_types=1);

require_once __DIR__ . '/icones.php';

function qf_e(string $texto): string
{
    return htmlspecialchars($texto, ENT_QUOTES | ENT_SUBSTITUTE, 'UTF-8');
}

function qf_cabecalho(string $paginaAtual): void
{
    $pagina = QF_PAGINAS[$paginaAtual];
    ?>
<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title><?= qf_e($pagina['titulo']) ?> · Quem Faz Admin</title>
    <meta name="qf-api" content="<?= qf_e(QF_API_URL) ?>">
    <meta name="qf-token" content="<?= qf_e(QF_TOKEN_ADMIN) ?>">
    <link rel="icon" href="data:image/svg+xml,<?= rawurlencode('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 32 32"><rect width="32" height="32" rx="8" fill="#1d5fd1"/><path d="M10 16.5l4 4 8-9" stroke="#fff" stroke-width="3.2" fill="none" stroke-linecap="round" stroke-linejoin="round"/></svg>') ?>">
    <link rel="stylesheet" href="assets/css/app.css?v=<?= QF_VERSAO ?>">
</head>
<body data-pagina="<?= qf_e($paginaAtual) ?>">
<a class="pular" href="#conteudo">Ir para o conteúdo</a>
<div class="estrutura">
    <aside class="lateral" id="menu-lateral" aria-label="Menu principal">
        <div class="marca">
            <span class="marca-logo" aria-hidden="true">
                <svg viewBox="0 0 32 32"><rect width="32" height="32" rx="9" fill="currentColor"/><path d="M10 16.5l4 4 8-9" stroke="#fff" stroke-width="3.2" fill="none" stroke-linecap="round" stroke-linejoin="round"/></svg>
            </span>
            <span class="marca-texto"><strong>Quem Faz</strong><small>Admin · Validação RPA</small></span>
        </div>
        <nav>
            <ul>
            <?php foreach (QF_PAGINAS as $chave => $item): ?>
                <li>
                    <a href="?pagina=<?= qf_e($chave) ?>" class="<?= $chave === $paginaAtual ? 'ativo' : '' ?>"
                       <?= $chave === $paginaAtual ? 'aria-current="page"' : '' ?>>
                        <?= qf_icone($item['icone']) ?><span><?= qf_e($item['titulo']) ?></span>
                    </a>
                </li>
            <?php endforeach; ?>
            </ul>
        </nav>
        <div class="lateral-rodape">
            <div class="estado-api" id="estado-api" role="status">
                <span class="ponto" aria-hidden="true"></span><span class="texto">Verificando API…</span>
            </div>
            <p>Global Solution 2026.2 · FIAP<br>Robotic Process Automation</p>
        </div>
    </aside>
    <div class="cortina" id="cortina" hidden></div>
    <div class="principal">
        <header class="topo">
            <button class="botao-icone menu-movel" id="abrir-menu" aria-label="Abrir menu" aria-controls="menu-lateral" aria-expanded="false">
                <?= qf_icone('menu') ?>
            </button>
            <div class="topo-titulo">
                <span class="migalha">Quem Faz · Módulo administrativo</span>
                <h1><?= qf_e($pagina['titulo']) ?></h1>
            </div>
            <div class="topo-acoes">
                <span class="selo-automacao" id="selo-automacao" role="status" aria-live="polite">
                    <?= qf_icone('robo') ?><span>Automação: verificando…</span>
                </span>
            </div>
        </header>
        <main id="conteudo" tabindex="-1">
            <div id="avisos" class="avisos" aria-live="polite"></div>
    <?php
}

function qf_rodape(string $paginaAtual): void
{
    ?>
        </main>
        <footer class="rodape">
            Dados exibidos a partir dos arquivos gerados pelo fluxo <strong>Power Automate Desktop</strong>.
            Nenhum resultado é simulado pela interface.
        </footer>
    </div>
</div>
<script type="application/json" id="qf-icones"><?= qf_icones_js() ?></script>
<script src="assets/js/api.js?v=<?= QF_VERSAO ?>"></script>
<script src="assets/js/ui.js?v=<?= QF_VERSAO ?>"></script>
<script src="assets/js/<?= qf_e($paginaAtual) ?>.js?v=<?= QF_VERSAO ?>"></script>
</body>
</html>
    <?php
}
