<?php

declare(strict_types=1);

$me = require_role('admin');
$errors = [];
$newValues = ['username' => '', 'email' => '', 'role' => 'operator', 'locale' => I18n::locale()];

if (is_post()) {
    $action = (string) input('action');
    $id = (int) input('id');
    switch ($action) {
        case 'create':
            $newValues = [
                'username' => input('username'),
                'email' => input('email'),
                'role' => input('role'),
                'locale' => input('locale'),
            ];
            $response = call('POST', '/users', $newValues);
            if ($response->ok()) {
                flash('success', t('user.created_password', [
                    'user' => $newValues['username'],
                    'password' => $response->data['temporary_password'],
                ]));
                redirect('/users');
            }
            $errors = field_errors($response);
            break;
        case 'update':
            $response = call('PUT', '/users/' . $id, [
                'email' => input('email'),
                'role' => input('role'),
                'locale' => input('locale'),
                'disabled' => checkbox('disabled'),
            ]);
            $response->ok() ? flash('success', t('common.saved')) : flash('danger', error_message($response) . ($response->fields() ? ' ' . implode(', ', field_errors($response)) : ''));
            redirect('/users');
        case 'reset':
            $response = call('POST', '/users/' . $id . '/reset-password', []);
            $response->ok()
                ? flash('success', t('user.reset_password_done', ['user' => input('username'), 'password' => $response->data['temporary_password']]))
                : flash('danger', error_message($response));
            redirect('/users');
        case 'unlock':
            $response = call('POST', '/users/' . $id . '/unlock', []);
            $response->ok() ? flash('success', t('user.unlocked')) : flash('danger', error_message($response));
            redirect('/users');
        case 'delete':
            $response = call('DELETE', '/users/' . $id);
            $response->ok() ? flash('success', t('common.deleted')) : flash('danger', error_message($response));
            redirect('/users');
    }
}

$users = call('GET', '/users')->data['users'] ?? [];
render('users', [
    'title' => t('nav.users'),
    'users' => $users,
    'me' => $me,
    'errors' => $errors,
    'nv' => $newValues,
]);
