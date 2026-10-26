<?php

declare(strict_types=1);

$user = require_role('manager');

$smtpErrors = [];
$ruleErrors = [];
$smtpValues = null;
$ruleValues = null;
$editRule = isset($_GET['rule']) ? (int) $_GET['rule'] : null;

if (is_post()) {
    $action = (string) input('action');
    switch ($action) {
        case 'smtp_save':
            $response = call('PUT', '/smtp', smtp_form_body());
            if ($response->ok()) {
                flash('success', t('common.saved'));
                redirect('/notifications');
            }
            $smtpErrors = smtp_field_errors($response);
            $smtpValues = posted_smtp_values();
            break;
        case 'smtp_test':
            $response = call('POST', '/smtp/test', ['to' => input('test_to')]);
            if (!$response->ok()) {
                flash('danger', $response->fields() ? t('field.invalid') : error_message($response));
            } elseif (empty($response->data['ok'])) {
                flash('danger', t('smtp.test_failed', ['error' => $response->data['error'] ?? '']));
            } else {
                flash('success', t('smtp.test_sent'));
            }
            redirect('/notifications');
        case 'rule_save':
            $id = (int) input('id');
            $body = [
                'name' => input('name'),
                'events' => array_values(array_filter((array) ($_POST['events'] ?? []), 'is_string')),
                'pattern' => input('pattern', '*'),
                'recipients' => input('recipients'),
                'mode' => input('mode', 'instant'),
                'digest_minutes' => (int) input('digest_minutes', '60'),
                'enabled' => checkbox('enabled'),
            ];
            $response = $id > 0 ? call('PUT', '/rules/' . $id, $body) : call('POST', '/rules', $body);
            if ($response->ok()) {
                flash('success', t('common.saved'));
                redirect('/notifications');
            }
            $ruleErrors = field_errors($response);
            $ruleValues = $body + ['id' => $id];
            $editRule = $id ?: 0;
            break;
        case 'rule_delete':
            $response = call('DELETE', '/rules/' . (int) input('id'));
            $response->ok() ? flash('success', t('common.deleted')) : flash('danger', error_message($response));
            redirect('/notifications');
    }
}

$smtp = call('GET', '/smtp')->data['smtp'] ?? [];
$rulesData = call('GET', '/rules')->data;
$rules = $rulesData['rules'] ?? [];
$queue = call('GET', '/mail-queue?limit=20')->data['mails'] ?? [];

if ($ruleValues === null) {
    $ruleValues = ['id' => 0, 'name' => '', 'events' => ['uploaded', 'upload_failed'], 'pattern' => '*',
        'recipients' => $user['email'] ?? '', 'mode' => 'instant', 'digest_minutes' => 60, 'enabled' => true];
    foreach ($rules as $rule) {
        if ($rule['id'] === $editRule) {
            $ruleValues = $rule;
            $ruleValues['recipients'] = implode(', ', $rule['recipients']);
        }
    }
}

render('notifications', [
    'title' => t('nav.notifications'),
    'v' => $smtpValues ?? smtp_form_values($smtp),
    'errors' => $smtpErrors,
    'rules' => $rules,
    'eventTypes' => $rulesData['event_types'] ?? [],
    'rv' => $ruleValues,
    'ruleErrors' => $ruleErrors,
    'showRuleForm' => $editRule !== null,
    'queue' => $queue,
    'userEmail' => $user['email'] ?? '',
]);
