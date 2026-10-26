<?php

declare(strict_types=1);

require_role('viewer');
$errors = [];

if (is_post()) {
    $action = (string) input('action');
    switch ($action) {
        case 'sync':
        case 'attach':
        case 'detach':
            require_role('operator');
            $response = call('POST', '/usb/' . $action, []);
            $response->ok()
                ? flash('success', t('usb.done_' . $action))
                : flash('danger', error_message($response));
            $from = (string) parse_url((string) ($_SERVER['HTTP_REFERER'] ?? ''), PHP_URL_PATH);
            redirect($from === '/' ? '/' : '/usb');
        case 'save':
            require_role('manager');
            $body = [
                'enabled' => checkbox('enabled'),
                'size_mb' => (int) input('size_mb'),
                'filesystem' => input('filesystem'),
                'label' => input('label'),
                'removable' => checkbox('removable'),
                'read_only' => checkbox('read_only'),
                'manufacturer' => input('manufacturer'),
                'product' => input('product'),
                'vendor_id' => input('vendor_id'),
                'product_id' => input('product_id'),
                'serial' => input('serial'),
                'max_power_ma' => (int) input('max_power_ma'),
                'sync_mode' => input('sync_mode'),
                'idle_seconds' => (int) input('idle_seconds'),
                'delete_after_upload' => checkbox('delete_after_upload'),
                'include' => input('include'),
                'exclude' => input('exclude'),
            ];
            $response = call('PUT', '/usb', $body);
            if ($response->ok()) {
                flash('success', t('common.saved'));
                if (!empty($response->data['gadget_error'])) {
                    flash('warning', t('usb.gadget_error', ['error' => $response->data['gadget_error']]));
                }
                if (!empty($response->data['image_rebuild_needed'])) {
                    flash('info', t('usb.rebuild_needed'));
                }
                redirect('/usb');
            }
            $errors = field_errors($response);
            if (!$errors) {
                flash('danger', error_message($response));
            }
            break;
        case 'image':
            require_role('admin');
            if (mb_strtoupper((string) input('confirm_text')) !== t('usb.recreate_word')) {
                flash('danger', t('usb.image_confirm_wrong'));
                redirect('/usb');
            }
            $response = call('POST', '/usb/image', ['confirm' => true]);
            if ($response->ok()) {
                flash('success', t('usb.image_created'));
                if (!empty($response->data['gadget_error'])) {
                    flash('warning', t('usb.gadget_error', ['error' => $response->data['gadget_error']]));
                }
            } else {
                flash('danger', error_message($response));
            }
            redirect('/usb');
    }
}

$usb = call('GET', '/usb');
$files = call('GET', '/files?limit=500');
render('usb', [
    'title' => t('nav.usb'),
    'u' => $usb->data,
    'v' => is_post() ? array_merge($usb->data['settings'], $_POST) : $usb->data['settings'],
    'files' => $files->data['files'] ?? [],
    'errors' => $errors,
]);
