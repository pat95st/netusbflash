<?php

declare(strict_types=1);

require_role('viewer');

if (is_post()) {
    $action = (string) input('action');
    $id = (int) input('id');
    if ($action === 'retry_all') {
        require_role('operator');
        $response = call('POST', '/uploads/retry-failed', []);
        $response->ok()
            ? flash('success', t('upload.retried', ['n' => $response->data['retried'] ?? 0]))
            : flash('danger', error_message($response));
    } elseif ($action === 'retry') {
        require_role('operator');
        $response = call('POST', '/uploads/' . $id . '/retry', []);
        $response->ok() ? flash('success', t('upload.retried', ['n' => 1])) : flash('danger', error_message($response));
    } elseif ($action === 'discard') {
        require_role('manager');
        $response = call('POST', '/uploads/' . $id . '/discard', []);
        $response->ok() ? flash('success', t('upload.discarded')) : flash('danger', error_message($response));
    }
    redirect('/uploads' . (isset($_GET['status']) ? '?status=' . urlencode((string) $_GET['status']) : ''));
}

$filter = in_array($_GET['status'] ?? '', ['pending', 'failed', 'done'], true) ? $_GET['status'] : '';
$response = call('GET', '/uploads?limit=300' . ($filter !== '' ? '&status=' . $filter : ''));
render('uploads', [
    'title' => t('nav.uploads'),
    'uploads' => $response->data['uploads'] ?? [],
    'filter' => $filter,
]);
