<?php

declare(strict_types=1);

/*
 * Setup wizard. The one-time setup code is verified first and then kept in
 * the PHP session; every step is sent to the service with that code. The
 * service remembers the current step, so the wizard resumes after a break.
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

$steps = $status->data['steps'];
$step = $status->data['step'];
$errors = [];
$old = $_POST;
$notice = null;
$testResult = null;

/** Handle a lost or invalid code: back to the code screen. */
$codeFailed = static function (ApiResponse $response): void {
    if (in_array($response->error(), ['setup_code_invalid', 'setup_done'], true)) {
        unset($_SESSION['setup_code']);
        flash('danger', error_message($response));
        redirect('/setup');
    }
};

if (empty($_SESSION['setup_code'])) {
    if (is_post()) {
        $_SESSION['setup_code'] = (string) input('code');
        $response = setup_call('POST', '/setup/verify', []);
        if ($response->ok()) {
            redirect('/setup');
        }
        unset($_SESSION['setup_code']);
        $errors['code'] = error_message($response);
    }
    render('setup', ['title' => t('setup.title'), 'screen' => 'code', 'steps' => $steps, 'step' => null,
        'errors' => $errors, 'old' => $old, 'simulated' => !empty($status->data['simulated'])], 'layout_plain');
    exit;
}

if (isset($_GET['goto']) && in_array($_GET['goto'], $steps, true)) {
    $response = setup_call('POST', '/setup/step', ['step' => $_GET['goto']]);
    $codeFailed($response);
    redirect('/setup');
}

if (is_post()) {
    $action = (string) input('action');
    $response = null;
    switch ($step) {
        case 'admin':
            if (($_POST['password'] ?? '') !== ($_POST['password_confirm'] ?? '')) {
                $response = new ApiResponse(422, ['error' => 'validation', 'fields' => ['password_confirm' => 'mismatch']]);
                break;
            }
            $response = setup_call('POST', '/setup/admin', [
                'username' => input('username'),
                'email' => input('email'),
                'password' => (string) ($_POST['password'] ?? ''),
                'locale' => I18n::locale(),
            ]);
            break;
        case 'system':
            $response = setup_call('POST', '/setup/system', [
                'hostname' => input('hostname'),
                'timezone' => input('timezone'),
            ]);
            break;
        case 'usb':
            $response = setup_call('POST', '/setup/usb', [
                'size_mb' => (int) input('size_mb'),
                'filesystem' => input('filesystem'),
                'label' => input('label'),
                'sync_mode' => input('sync_mode'),
                'idle_seconds' => (int) input('idle_seconds'),
            ]);
            break;
        case 'target':
            if ($action === 'skip') {
                $response = setup_call('POST', '/setup/target', ['skip' => true]);
                break;
            }
            $body = target_form_body();
            if ($action === 'test') {
                $body['test_only'] = true;
                $response = setup_call('POST', '/setup/target', $body);
                if ($response->ok()) {
                    $testResult = $response->data;
                    $response = null;
                }
            } else {
                $response = setup_call('POST', '/setup/target', $body);
            }
            break;
        case 'smtp':
            if ($action === 'skip') {
                $response = setup_call('POST', '/setup/smtp', ['skip' => true]);
                break;
            }
            $body = smtp_form_body();
            $body['locale'] = I18n::locale();
            if ($action === 'test') {
                $body['test_to'] = input('test_to');
                $body['test_only'] = true;
            }
            $response = setup_call('POST', '/setup/smtp', $body);
            if ($response->ok() && isset($response->data['ok']) && !$response->data['ok']) {
                $notice = ['danger', t('smtp.test_failed', ['error' => $response->data['error'] ?? ''])];
                $response = null;
            } elseif ($response->ok() && $action === 'test') {
                $notice = ['success', t('smtp.test_sent')];
                $response = null;
            }
            break;
        case 'finish':
            $response = setup_call('POST', '/setup/finish', []);
            if ($response->ok()) {
                unset($_SESSION['setup_code']);
                flash('success', t('setup.done'));
                if (!empty($response->data['gadget_error'])) {
                    flash('warning', t('usb.gadget_error', ['error' => $response->data['gadget_error']]));
                }
                redirect('/login');
            }
            break;
    }
    if ($response !== null) {
        $codeFailed($response);
        if ($response->ok()) {
            redirect('/setup');
        }
        $errors = match ($step) {
            'target' => target_field_errors($response),
            'smtp' => smtp_field_errors($response),
            default => field_errors($response),
        };
        if (!$errors) {
            $notice = ['danger', error_message($response)];
        }
    }
}

$data = [];
if ($step === 'system') {
    $response = setup_call('GET', '/setup/timezones');
    $codeFailed($response);
    $data = $response->data;
} elseif ($step === 'usb') {
    $response = setup_call('GET', '/setup/usb');
    $codeFailed($response);
    $data = $response->data;
}

render('setup', [
    'title' => t('setup.title'),
    'screen' => 'step',
    'steps' => $steps,
    'step' => $step,
    'errors' => $errors,
    'old' => $old,
    'data' => $data,
    'notice' => $notice,
    'testResult' => $testResult,
    'simulated' => !empty($status->data['simulated']),
], 'layout_plain');
