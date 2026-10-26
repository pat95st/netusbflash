<?php

declare(strict_types=1);

require_role('admin');
$errors = [];

if (is_post()) {
    $action = (string) input('action');
    switch ($action) {
        case 'save':
            $response = call('PUT', '/system', ['hostname' => input('hostname'), 'timezone' => input('timezone')]);
            if ($response->ok()) {
                flash('success', t('common.saved'));
                redirect('/system');
            }
            $errors = field_errors($response);
            if (!$errors) {
                flash('danger', error_message($response));
            }
            break;
        case 'reboot':
        case 'poweroff':
            $response = call('POST', '/system/' . $action, []);
            $response->ok() ? flash('info', t('system.' . $action . '_started')) : flash('danger', error_message($response));
            redirect('/system');
        case 'setup_reset':
            $response = call('POST', '/system/setup-reset', ['wipe_users' => checkbox('wipe_users')]);
            if ($response->ok()) {
                $locale = $_SESSION['locale'] ?? null;
                $_SESSION = ['locale' => $locale];
                flash('info', t('system.setup_reset_done'));
                redirect('/setup');
            }
            flash('danger', error_message($response));
            redirect('/system');
        case 'regenerate_key':
            $response = call('POST', '/system/ssh-key', ['regenerate' => true]);
            $response->ok() ? flash('success', t('target.key_generated')) : flash('danger', error_message($response));
            redirect('/system');
    }
}

$system = call('GET', '/system')->data;
$status = call('GET', '/status')->data;
$sshKey = call('GET', '/system/ssh-key')->data['public_key'] ?? '';
render('system', [
    'title' => t('nav.system'),
    'sys' => $system,
    's' => $status,
    'sshKey' => $sshKey,
    'errors' => $errors,
    'v' => is_post() ? ['hostname' => input('hostname'), 'timezone' => input('timezone')] : $system,
]);
