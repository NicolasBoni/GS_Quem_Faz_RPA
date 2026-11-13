<?php
declare(strict_types=1);

require __DIR__ . '/config/config.php';
require __DIR__ . '/components/layout.php';

header('X-Content-Type-Options: nosniff');
header('X-Frame-Options: DENY');
header('Referrer-Policy: no-referrer');
header("Content-Security-Policy: default-src 'self'; script-src 'self'; style-src 'self'; "
    . "img-src 'self' data:; connect-src 'self' " . QF_API_URL . "; frame-ancestors 'none'");

// Lista fechada de páginas: o parâmetro nunca é usado como caminho de arquivo.
$pagina = $_GET['pagina'] ?? 'dashboard';
if (!is_string($pagina) || !array_key_exists($pagina, QF_PAGINAS)) {
    $pagina = 'dashboard';
}

qf_cabecalho($pagina);
require __DIR__ . '/pages/' . QF_PAGINAS[$pagina]['arquivo'];
qf_rodape($pagina);
