<?php

declare(strict_types=1);

$user = current_user();
if ($user === null) {
    redirect('/login');
}
$errors = [];

if (is_post()) {
    $action = (string) input('action');
    if ($action === 'profile') {
        $response = call('PUT', '/me', ['email' => input('email'), 'locale' => input('locale')]);
        if ($response->ok()) {
            $_SESSION['user'] = $response->data['user'];
            $_SESSION['locale'] = $response->data['user']['locale'];
            flash('success', t('common.saved'));
            redirect('/profile');
        }
        $errors = field_errors($response);
    } elseif ($action === 'password') {
        if (($_POST['new'] ?? '') !== ($_POST['new_confirm'] ?? '')) {
            $errors['new_confirm'] = t('field.mismatch');
        } else {
            $response = call('POST', '/me/password', [
                'current' => (string) ($_POST['current'] ?? ''),
                'new' => (string) ($_POST['new'] ?? ''),
            ]);
            if ($response->ok()) {
                session_regenerate_id(true);
                $_SESSION['token'] = $response->data['token'];
                $_SESSION['user'] = $response->data['user'];
                flash('success', t('profile.password_changed'));
                redirect('/');
            }
            $errors = field_errors($response);
            if (!$errors) {
                flash('danger', error_message($response));
            }
        }
    }
}

$user = current_user();
render('profile', [
    'title' => t('nav.profile'),
    'user' => $user,
    'errors' => $errors,
    'forced' => !empty($user['must_change_pw']),
]);
