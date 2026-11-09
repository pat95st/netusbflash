<?php

declare(strict_types=1);

/*
 * Setup wizard page. This only delivers the HTML skeleton of all steps;
 * setup.js loads the current state from /setup/api/state and submits every
 * step via AJAX to /setup/api/* (see pages/setup_api.php).
 */

$status = api()->call('GET', '/setup/status');
if (!$status->ok()) {
    http_response_code(503);
    render('error', ['code' => 503, 'message' => error_message($status)], 'layout_plain');
    exit;
}
if (!empty($status->data['completed'])) {
    unset($_SESSION['setup_code']);
    redirect('/login');
}

render('setup', [
    'title' => t('setup.title'),
    'steps' => $status->data['steps'],
    'hideLanguageFooter' => true,
    'scripts' => ['/assets/js/pages/setup.js'],
], 'layout_plain');
