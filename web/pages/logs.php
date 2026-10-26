<?php

declare(strict_types=1);

require_role('viewer');

$tab = ($_GET['tab'] ?? 'events') === 'audit' && has_role('admin') ? 'audit' : 'events';
$level = in_array($_GET['level'] ?? '', ['info', 'warning', 'error'], true) ? $_GET['level'] : '';

if ($tab === 'audit') {
    $rows = call('GET', '/audit?limit=500')->data['audit'] ?? [];
} else {
    $rows = call('GET', '/events?limit=500' . ($level !== '' ? '&level=' . $level : ''))->data['events'] ?? [];
}

if (isset($_GET['download'])) {
    header('Content-Type: text/csv; charset=utf-8');
    header('Content-Disposition: attachment; filename="netusbflash-' . $tab . '-' . date('Ymd-His') . '.csv"');
    $out = fopen('php://output', 'wb');
    if ($rows) {
        fputcsv($out, array_keys($rows[0]), ',', '"', '\\');
        foreach ($rows as $row) {
            $row['time'] = date('c', (int) $row['time']);
            fputcsv($out, $row, ',', '"', '\\');
        }
    }
    exit;
}

render('logs', ['title' => t('nav.logs'), 'tab' => $tab, 'level' => $level, 'rows' => $rows]);
