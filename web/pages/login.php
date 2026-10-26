<?php

declare(strict_types=1);

if (current_user() !== null) {
    redirect('/');
}

$status = api()->call('GET', '/setup/status');
if ($status->ok() && empty($status->data['completed'])) {
    redirect('/setup');
}

$username = '';
$error = null;
if (is_post()) {
    $username = (string) input('username');
    $response = api()->call('POST', '/auth/login', [
        'username' => $username,
        'password' => (string) ($_POST['password'] ?? ''),
    ], ['X-Client-IP' => $_SERVER['REMOTE_ADDR'] ?? '']);
    if ($response->ok()) {
        session_regenerate_id(true);
        $_SESSION['token'] = $response->data['token'];
        $_SESSION['user'] = $response->data['user'];
        $_SESSION['locale'] = $response->data['user']['locale'];
        $target = $_SESSION['after_login'] ?? '/';
        unset($_SESSION['after_login']);
        if (!empty($response->data['user']['must_change_pw'])) {
            flash('warning', t('profile.must_change'));
            redirect('/profile');
        }
        redirect(is_string($target) && str_starts_with($target, '/') && !str_starts_with($target, '//') ? $target : '/');
    }
    $error = error_message($response);
}

render('login', ['title' => t('login.title'), 'username' => $username, 'error' => $error], 'layout_plain');
