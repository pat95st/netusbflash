<?php

declare(strict_types=1);

require_role('viewer');

$testResult = null;
$testedName = null;
if (is_post()) {
    require_role('manager');
    $id = (int) input('id');
    $action = (string) input('action');
    if ($action === 'delete') {
        $response = call('DELETE', '/targets/' . $id);
        $response->ok() ? flash('success', t('target.deleted')) : flash('danger', error_message($response));
        redirect('/targets');
    }
    if ($action === 'test') {
        $response = call('POST', '/targets/' . $id . '/test', []);
        if ($response->ok()) {
            $testResult = $response->data;
            $testedName = (string) input('name');
        } else {
            flash('danger', error_message($response));
        }
    }
}

$response = call('GET', '/targets');
render('targets', [
    'title' => t('nav.targets'),
    'targets' => $response->data['targets'] ?? [],
    'testResult' => $testResult,
    'testedName' => $testedName,
]);
