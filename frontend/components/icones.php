<?php
declare(strict_types=1);

/** Ícones SVG inline (traço 2px, 24x24). Sempre acompanhados de texto na interface. */
function qf_icone(string $nome, string $classe = 'icone'): string
{
    $caminhos = [
        'painel'     => '<rect x="3" y="3" width="7" height="9" rx="1.5"/><rect x="14" y="3" width="7" height="5" rx="1.5"/><rect x="14" y="12" width="7" height="9" rx="1.5"/><rect x="3" y="16" width="7" height="5" rx="1.5"/>',
        'entrada'    => '<path d="M4 4h16v12H4z"/><path d="M4 12h4l2 3h4l2-3h4"/><path d="M8 20h8"/>',
        'robo'       => '<rect x="4" y="8" width="16" height="12" rx="3"/><path d="M12 4v4"/><circle cx="12" cy="3" r="1"/><circle cx="9" cy="14" r="1.3"/><circle cx="15" cy="14" r="1.3"/><path d="M2 13v3M22 13v3"/>',
        'resultados' => '<path d="M9 11l2 2 4-4"/><rect x="4" y="3" width="16" height="18" rx="2"/><path d="M8 17h8"/>',
        'publicar'   => '<path d="M12 3l8 4.5v9L12 21l-8-4.5v-9z"/><path d="M8.5 12l2.5 2.5 4.5-5"/>',
        'auditoria'  => '<path d="M14 3H6a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V9z"/><path d="M14 3v6h6"/><path d="M8 13h8M8 17h5"/>',
        'aprovado'   => '<circle cx="12" cy="12" r="9"/><path d="M8 12.5l2.7 2.7L16 9.8"/>',
        'reprovado'  => '<circle cx="12" cy="12" r="9"/><path d="M9 9l6 6M15 9l-6 6"/>',
        'duplicado'  => '<rect x="8" y="8" width="12" height="12" rx="2"/><path d="M16 8V6a2 2 0 0 0-2-2H6a2 2 0 0 0-2 2v8a2 2 0 0 0 2 2h2"/>',
        'ignorado'   => '<circle cx="12" cy="12" r="9"/><path d="M5.7 5.7l12.6 12.6"/>',
        'pendente'   => '<circle cx="12" cy="12" r="9"/><path d="M12 7v5l3 2"/>',
        'total'      => '<path d="M4 6h16M4 12h16M4 18h10"/>',
        'busca'      => '<circle cx="11" cy="11" r="7"/><path d="M20 20l-3.5-3.5"/>',
        'mais'       => '<path d="M12 5v14M5 12h14"/>',
        'play'       => '<path d="M7 4.5v15l12-7.5z"/>',
        'alerta'     => '<path d="M12 3l10 18H2z"/><path d="M12 10v5M12 18h.01"/>',
        'info'       => '<circle cx="12" cy="12" r="9"/><path d="M12 11v6M12 7.5h.01"/>',
        'fechar'     => '<path d="M6 6l12 12M18 6L6 18"/>',
        'menu'       => '<path d="M4 6h16M4 12h16M4 18h16"/>',
        'atualizar'  => '<path d="M20 11a8 8 0 1 0-2.3 5.7"/><path d="M20 5v6h-6"/>',
        'baixar'     => '<path d="M12 4v11M7 10l5 5 5-5"/><path d="M5 20h14"/>',
        'relogio'    => '<circle cx="12" cy="12" r="9"/><path d="M12 7v5l3 2"/>',
        'pasta'      => '<path d="M3 7a2 2 0 0 1 2-2h4l2 2h8a2 2 0 0 1 2 2v8a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"/>',
        'restaurar'  => '<path d="M4 12a8 8 0 1 0 2.3-5.7"/><path d="M4 5v5h5"/>',
    ];
    $conteudo = $caminhos[$nome] ?? $caminhos['info'];
    return '<svg class="' . htmlspecialchars($classe) . '" viewBox="0 0 24 24" fill="none" stroke="currentColor" '
        . 'stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true" focusable="false">'
        . $conteudo . '</svg>';
}

/** Exporta os ícones para o JavaScript (mesmos desenhos em componentes dinâmicos). */
function qf_icones_js(): string
{
    $nomes = ['aprovado', 'reprovado', 'duplicado', 'ignorado', 'pendente', 'alerta', 'info', 'fechar', 'relogio', 'robo', 'pasta'];
    $mapa = [];
    foreach ($nomes as $nome) {
        $mapa[$nome] = qf_icone($nome);
    }
    return json_encode($mapa, JSON_UNESCAPED_SLASHES | JSON_HEX_TAG | JSON_HEX_AMP);
}
