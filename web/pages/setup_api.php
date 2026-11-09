<?php

declare(strict_types=1);

/*
 * JSON endpoints for the setup wizard (used by assets/js/pages/setup.js).
 *
 *   GET  /setup/api/state    current step and the data it needs
 *   POST /setup/api/verify   check the one-time setup code       {"code"}
 *   POST /setup/api/submit   save the current step               {"step", "action", ...fields}
 *   POST /setup/api/goto     go back to an earlier step          {"step"}
 *
 * POST bodies are JSON and carry the CSRF token in the X-CSRF-Token header
 * (checked in index.php). All messages are translated here.
 */

$action = $params[0];
$in = json_input();

/** Answer with JSON; a lost or invalid setup code sends the browser back to the code screen. */
$respond = static function (ApiResponse $response, array $extra = []): never {
    if (in_array($response->error(), ['setup_code_invalid', 'setup_done'], true)) {
        unset($_SESSION['setup_code']);
        json_out(['ok' => false, 'reload' => true, 'message' => error_message($response)]);
    }
    if ($response->ok()) {
        json_out($extra + ['ok' => true]);
    }
    $fields = field_errors($response);
    json_out($extra + ($fields
        ? ['ok' => false, 'fields' => $fields]
        : ['ok' => false, 'message' => error_message($response)]));
};

$status = api()->call('GET', '/setup/status');
if (!$status->ok()) {
    json_out(['ok' => false, 'message' => error_message($status)], 503);
}
if (!empty($status->data['completed'])) {
    unset($_SESSION['setup_code']);
    json_out(['ok' => false, 'redirect' => '/login']);
}
$step = (string) $status->data['step'];

if ($action === 'state') {
    $state = [
        'ok' => true,
        'verified' => !empty($_SESSION['setup_code']),
        'step' => $step,
        'steps' => $status->data['steps'],
        'simulated' => !empty($status->data['simulated']),
        'data' => new stdClass(),
    ];
    if ($state['verified']) {
        $check = setup_call('POST', '/setup/verify', []);
        if (!$check->ok()) {
            unset($_SESSION['setup_code']);
            $state['verified'] = false;
            $state['message'] = error_message($check);
        } elseif ($step === 'system') {
            $state['data'] = setup_call('GET', '/setup/timezones')->data;
        } elseif ($step === 'usb') {
            $data = setup_call('GET', '/setup/usb')->data;
            if (isset($data['available']) && !$data['available']) {
                $data['unavailable_message'] = t('usb.unavailable', ['reason' => $data['unavailable_reason'] ?? '']);
            }
            $state['data'] = $data;
        }
    }
    json_out($state);
}

if (!is_post()) {
    json_out(['ok' => false], 405);
}

if ($action === 'verify') {
    $_SESSION['setup_code'] = trim((string) ($in['code'] ?? ''));
    $response = setup_call('POST', '/setup/verify', []);
    if ($response->ok()) {
        json_out(['ok' => true]);
    }
    unset($_SESSION['setup_code']);
    json_out(['ok' => false, 'fields' => ['code' => error_message($response)]]);
}

if ($action === 'goto') {
    $respond(setup_call('POST', '/setup/step', ['step' => (string) ($in['step'] ?? '')]));
}

// submit: the browser may show an outdated step (e.g. a second tab): reload instead of saving.
if (($in['step'] ?? '') !== $step) {
    json_out(['ok' => false, 'reload' => true]);
}
$submit = (string) ($in['action'] ?? 'save');
$fields = $in;
unset($fields['step'], $fields['action']);

switch ($step) {
    case 'admin':
        if (($in['password'] ?? '') !== ($in['password_confirm'] ?? '')) {
            json_out(['ok' => false, 'fields' => ['password_confirm' => t('field.mismatch')]]);
        }
        unset($fields['password_confirm']);
        $respond(setup_call('POST', '/setup/admin', $fields + ['locale' => I18n::locale()]));

    case 'system':
        $respond(setup_call('POST', '/setup/system', $fields));

    case 'usb':
        $respond(setup_call('POST', '/setup/usb', $fields));

    case 'target':
        if ($submit === 'skip') {
            $respond(setup_call('POST', '/setup/target', ['skip' => true]));
        }
        if ($submit === 'test') {
            $response = setup_call('POST', '/setup/target', $fields + ['test_only' => true]);
            $respond($response, $response->ok() ? ['stay' => true, 'test' => $response->data] : []);
        }
        $respond(setup_call('POST', '/setup/target', $fields));

    case 'smtp':
        if ($submit === 'skip') {
            $respond(setup_call('POST', '/setup/smtp', ['skip' => true]));
        }
        $testTo = (string) ($fields['test_to'] ?? '');
        unset($fields['test_to']);
        $body = $fields + ['locale' => I18n::locale()];
        if ($submit === 'test') {
            $body += ['test_to' => $testTo, 'test_only' => true];
        }
        $response = setup_call('POST', '/setup/smtp', $body);
        if ($response->ok() && isset($response->data['ok']) && !$response->data['ok']) {
            json_out(['ok' => false, 'stay' => true,
                'message' => t('smtp.test_failed', ['error' => $response->data['error'] ?? ''])]);
        }
        $respond($response, $submit === 'test' && $response->ok()
            ? ['stay' => true, 'notice' => t('smtp.test_sent')]
            : []);

    case 'finish':
        $response = setup_call('POST', '/setup/finish', []);
        if ($response->ok()) {
            unset($_SESSION['setup_code']);
            flash('success', t('setup.done'));
            if (!empty($response->data['gadget_error'])) {
                flash('warning', t('usb.gadget_error', ['error' => $response->data['gadget_error']]));
            }
            json_out(['ok' => true, 'redirect' => '/login']);
        }
        $respond($response);
}

json_out(['ok' => false, 'reload' => true]);
