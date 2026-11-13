<?php
declare(strict_types=1);

/**
 * Configuração direta do frontend para a apresentação acadêmica.
 * Mantenha o token igual a TOKEN_ADMIN em backend/config.py.
 */
$apiUrl = 'http://127.0.0.1:8000';
// Só aceitamos API local: o controlador do PAD nunca deve ser exposto à internet.
if (!preg_match('#^https?://(127\.0\.0\.1|localhost)(:\d+)?/?$#', $apiUrl)) {
    $apiUrl = 'http://127.0.0.1:8000';
}

define('QF_API_URL', rtrim($apiUrl, '/'));
define('QF_TOKEN_ADMIN', 'mbgf_gPfTLZU0LKbVLmWzAc2_ONHe9ZS');
define('QF_VERSAO', '1.0.0');

const QF_PAGINAS = [
    'dashboard'     => ['titulo' => 'Dashboard',              'icone' => 'painel',     'arquivo' => 'dashboard.php'],
    'solicitacoes'  => ['titulo' => 'Solicitações recebidas', 'icone' => 'entrada',    'arquivo' => 'solicitacoes.php'],
    'processamento' => ['titulo' => 'Processamento RPA',      'icone' => 'robo',       'arquivo' => 'processamento.php'],
    'resultados'    => ['titulo' => 'Resultados',             'icone' => 'resultados', 'arquivo' => 'resultados.php'],
    'publicaveis'   => ['titulo' => 'Pedidos publicáveis',    'icone' => 'publicar',   'arquivo' => 'publicaveis.php'],
    'logs'          => ['titulo' => 'Logs e auditoria',       'icone' => 'auditoria',  'arquivo' => 'logs.php'],
];
