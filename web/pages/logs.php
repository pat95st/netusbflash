<?php

declare(strict_types=1);

require_role('viewer');

// CSV download stays a plain request (a file, not page content).
if (isset($_GET['download'])) {
    $tab = ($_GET['tab'] ?? 'events') === 'audit' && has_role('admin') ? 'audit' : 'events';
    $level = in_array($_GET['level'] ?? '', ['info', 'warning', 'error'], true) ? $_GET['level'] : '';
    $rows = $tab === 'audit'
        ? call('GET', '/audit?limit=1000')->data['audit'] ?? []
        : call('GET', '/events?limit=1000' . ($level !== '' ? '&level=' . $level : ''))->data['events'] ?? [];
    header('Content-Type: text/csv; charset=utf-8');
    header('Content-Disposition: attachment; filename="netusbflash-' . $tab . '-' . date('Ymd-His') . '.csv"');
    $out = fopen('php://output', 'wb');
    if ($rows) {
        fputcsv($out, array_keys($rows[0]), ',', '"', '\\');
        foreach ($rows as $row) {
            $row['time'] = date('c', (int) $row['time']);
            // Neutralise values a spreadsheet would run as a formula.
            $row = array_map(static fn($v) => is_string($v) && preg_match('/^[=+\-@]/', $v) ? "'" . $v : $v, $row);
            fputcsv($out, $row, ',', '"', '\\');
        }
    }
    exit;
}

render('logs', ['title' => t('nav.logs'), 'scripts' => ['/assets/js/pages/logs.js']]);
