<?php

declare(strict_types=1);

require_role('viewer');

$status = call('GET', '/status');
if (!$status->ok()) {
    render('error', ['code' => $status->status, 'message' => error_message($status)]);
    exit;
}
$events = call('GET', '/file-events?limit=10');
$problems = call('GET', '/uploads?status=failed&limit=5');

render('dashboard', [
    'title' => t('nav.dashboard'),
    's' => $status->data,
    'events' => $events->data['events'] ?? [],
    'failed' => $problems->data['uploads'] ?? [],
]);
