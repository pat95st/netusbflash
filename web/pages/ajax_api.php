<?php

declare(strict_types=1);

/*
 * JSON gateway for the page scripts: /ajax/api/<path> is forwarded to the
 * service's /api/v1/<path> with the user's session token. The service checks
 * roles and input; this file only restricts the reachable paths, translates
 * error messages and keeps the PHP session in sync.
 *
 * Response: {"ok": bool, "data": {...}, "message": "...", "fields": {"name": "..."}}
 * or {"ok": false, "redirect": "/login"} when the browser has to change page.
 */

if (current_user() === null) {
    json_out(['ok' => false, 'redirect' => '/login'], 401);
}

$path = $params[0];
$method = $_SERVER['REQUEST_METHOD'] ?? 'GET';

const AJAX_ALLOWED = '#^/('
    . 'status|files|file-events|mail-queue|events|audit'
    . '|usb(/(attach|detach|sync|image))?'
    . '|targets(/test|/\d+(/test)?)?'
    . '|uploads(/retry-failed|/\d+/(retry|discard))?'
    . '|smtp(/test)?|rules(/\d+|/preview)?'
    . '|browser(/refresh)?'
    . '|update(/(check|software|os-check|os))?'
    . '|backup(/(run|export|restore))?'
    . '|users(/\d+(/(reset-password|unlock))?)?'
    . '|me(/password)?'
    . '|system(/(reboot|poweroff|setup-reset|ssh-key))?'
    . ')$#';

if (!preg_match(AJAX_ALLOWED, $path)) {
    json_out(['ok' => false, 'message' => t('error.not_found')], 404);
}
if (!in_array($method, ['GET', 'POST', 'PUT', 'DELETE'], true)) {
    json_out(['ok' => false, 'message' => t('error.not_found')], 405);
}

$query = (string) ($_SERVER['QUERY_STRING'] ?? '');
$body = $method === 'GET' ? null : json_input();
$response = api()->call($method, $path . ($query !== '' ? '?' . $query : ''), $body, session_headers());

switch ($response->error()) {
    case 'session_expired':
        unset($_SESSION['token'], $_SESSION['user']);
        flash('warning', t('error.session_expired'));
        json_out(['ok' => false, 'redirect' => '/login'], 401);
    case 'setup_required':
        json_out(['ok' => false, 'redirect' => '/setup'], 409);
    case 'password_change_required':
        json_out(['ok' => false, 'redirect' => '/profile'], 403);
}

if ($response->ok()) {
    // Keep the cached user in the PHP session up to date.
    if ($path === '/me' && $method === 'PUT') {
        $_SESSION['user'] = $response->data['user'];
        $_SESSION['locale'] = $response->data['user']['locale'];
    } elseif ($path === '/me/password') {
        session_regenerate_id(true);
        $_SESSION['token'] = $response->data['token'];
        $_SESSION['user'] = $response->data['user'];
    } elseif ($path === '/system/setup-reset') {
        $locale = $_SESSION['locale'] ?? null;
        $_SESSION = ['locale' => $locale];
        flash('info', t('system.setup_reset_done'));
        json_out(['ok' => true, 'redirect' => '/setup']);
    } elseif ($path === '/backup/restore') {
        // The service ends all sessions when settings are restored.
        $locale = $_SESSION['locale'] ?? null;
        $_SESSION = ['locale' => $locale];
        session_regenerate_id(true);
        flash('success', t(!empty($response->data['secrets_restored']) ? 'backup.restored' : 'backup.restored_no_secrets'));
        json_out(['ok' => true, 'redirect' => '/login']);
    }
    $data = $response->data;
    unset($data['token']);
    json_out(['ok' => true, 'data' => $data]);
}

json_out([
    'ok' => false,
    'error' => $response->error(),
    'message' => error_message($response),
    'fields' => field_errors($response),
    'data' => $response->data,
], $response->status >= 400 ? $response->status : 500);
