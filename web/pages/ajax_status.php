<?php

declare(strict_types=1);

if (current_user() === null) {
    json_out(['error' => 'session_expired'], 401);
}
$response = api()->call('GET', '/status', null, ['X-Session-Token' => $_SESSION['token'] ?? null]);
if (!$response->ok()) {
    json_out(['error' => $response->error()], $response->status);
}
$s = $response->data;
$usb = $s['usb'];
json_out([
    'usb_state' => usb_state_label($usb),
    'usb_state_class' => usb_state_class($usb),
    'monitor' => t('monitor.' . ($usb['monitor']['phase'] ?? 'idle')),
    'last_sync' => fmt_time($usb['last_sync']['time'] ?? null),
    'pending' => (string) $s['uploads']['pending'],
    'failed' => (string) $s['uploads']['failed'],
    'done' => (string) $s['uploads']['done'],
    'current' => $s['uploads']['current']
        ? t('dashboard.uploading', ['file' => $s['uploads']['current']['path'], 'target' => $s['uploads']['current']['target']])
        : t('dashboard.no_upload'),
    'cpu_temp' => $s['cpu_temp'] !== null ? number_format((float) $s['cpu_temp'], 1) . ' °C' : '–',
]);
