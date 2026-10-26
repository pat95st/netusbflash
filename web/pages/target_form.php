<?php

declare(strict_types=1);

$isNew = $params[0] === 'new';
require_role($isNew || is_post() ? 'manager' : 'viewer');
$id = $isNew ? null : (int) $params[0];

$errors = [];
$testResult = null;
$sshKey = null;

if (is_post()) {
    $action = (string) input('action');
    $body = target_form_body();
    if ($action === 'test') {
        if ($id !== null) {
            $body['id'] = $id;
        }
        $response = call('POST', '/targets/test', $body);
        if ($response->ok()) {
            $testResult = $response->data;
        } else {
            $errors = target_field_errors($response);
        }
    } elseif ($action === 'generate_key') {
        $response = call('POST', '/system/ssh-key', []);
        $response->ok() ? flash('success', t('target.key_generated')) : flash('danger', error_message($response));
    } else {
        $response = $isNew ? call('POST', '/targets', $body) : call('PUT', '/targets/' . $id, $body);
        if ($response->ok()) {
            flash('success', t('common.saved'));
            redirect('/targets');
        }
        $errors = target_field_errors($response);
        if (!$errors) {
            flash('danger', error_message($response));
        }
    }
    $v = posted_target_values();
    if ($id !== null) {
        $existing = call('GET', '/targets/' . $id);
        $v['has_password'] = !empty($existing->data['target']['has_password']);
    }
} elseif ($isNew) {
    $v = target_form_values(['protocol' => 'smb', 'enabled' => true, 'options' => []]);
} else {
    $response = call('GET', '/targets/' . $id);
    if (!$response->ok()) {
        http_response_code(404);
        render('error', ['code' => 404, 'message' => t('error.not_found')]);
        exit;
    }
    $v = target_form_values($response->data['target']);
}

if (has_role('manager')) {
    $sshKey = call('GET', '/system/ssh-key')->data['public_key'] ?? '';
}

render('target_form', [
    'title' => $isNew ? t('target.add') : t('target.edit'),
    'isNew' => $isNew,
    'id' => $id,
    'v' => $v,
    'errors' => $errors,
    'testResult' => $testResult,
    'sshKey' => $sshKey,
]);
