<?php

declare(strict_types=1);

/*
 * Form <-> API mapping shared by the setup wizard and the settings pages.
 */

const PROTOCOLS = ['smb', 'webdav', 'ftp', 'ftps', 'sftp', 'sshfs', 'scp', 'local'];

/** Build the API body for a target from the posted form. */
function target_form_body(): array
{
    $port = input('port');
    $body = [
        'name' => input('name'),
        'protocol' => input('protocol'),
        'host' => input('protocol') === 'webdav' ? input('host_url') : input('host'),
        'port' => $port === '' ? null : (int) $port,
        'path' => input('path'),
        'username' => input('username'),
        'enabled' => checkbox('enabled') || !isset($_POST['enabled_present']),
        'options' => [
            'domain' => input('opt_domain'),
            'vendor' => input('opt_vendor', 'other'),
            'tls_mode' => input('opt_tls_mode', 'explicit'),
            'insecure_tls' => checkbox('opt_insecure_tls'),
            'auth' => input('opt_auth', 'password'),
            'subfolder' => input('opt_subfolder'),
            'keep_structure' => checkbox('opt_keep_structure'),
            'bwlimit' => strtoupper((string) input('opt_bwlimit')),
        ],
    ];
    $password = (string) ($_POST['password'] ?? '');
    if ($password !== '') {
        $body['password'] = $password;
    }
    if (checkbox('clear_password')) {
        $body['clear_password'] = true;
    }
    return $body;
}

/** Flatten a target from the API into form values. */
function target_form_values(array $target): array
{
    $o = $target['options'] ?? [];
    return [
        'name' => $target['name'] ?? '',
        'protocol' => $target['protocol'] ?? 'smb',
        'host' => $target['host'] ?? '',
        'port' => $target['port'] ?? '',
        'path' => $target['path'] ?? '',
        'username' => $target['username'] ?? '',
        'enabled' => !empty($target['enabled']),
        'has_password' => !empty($target['has_password']),
        'opt_domain' => $o['domain'] ?? '',
        'opt_vendor' => $o['vendor'] ?? 'other',
        'opt_tls_mode' => $o['tls_mode'] ?? 'explicit',
        'opt_insecure_tls' => !empty($o['insecure_tls']),
        'opt_auth' => $o['auth'] ?? 'password',
        'opt_subfolder' => $o['subfolder'] ?? '{date}',
        'opt_keep_structure' => $o['keep_structure'] ?? true,
        'opt_bwlimit' => $o['bwlimit'] ?? '',
    ];
}

/** Values of a re-displayed form after a failed POST. */
function posted_target_values(): array
{
    $v = target_form_values(['options' => []]);
    foreach (array_keys($v) as $key) {
        if (str_starts_with($key, 'opt_') && in_array($key, ['opt_insecure_tls', 'opt_keep_structure'], true)) {
            $v[$key] = checkbox($key);
        } elseif ($key === 'enabled') {
            $v[$key] = checkbox('enabled');
        } elseif ($key !== 'has_password') {
            $v[$key] = (string) input($key, $v[$key]);
        }
    }
    if ($v['protocol'] === 'webdav') {
        $v['host'] = (string) input('host_url');
    }
    return $v;
}

/** Map API field names (options.x) to form field names (opt_x). */
function target_field_errors(ApiResponse $response): array
{
    $errors = [];
    foreach (field_errors($response) as $field => $message) {
        $errors[str_starts_with($field, 'options.') ? 'opt_' . substr($field, 8) : $field] = $message;
    }
    return $errors;
}

function smtp_form_body(): array
{
    $body = [
        'host' => input('smtp_host'),
        'port' => (int) input('smtp_port', '587'),
        'security' => input('smtp_security', 'starttls'),
        'username' => input('smtp_username'),
        'sender' => input('smtp_sender'),
        'sender_name' => input('smtp_sender_name', 'NetUSBFlash'),
        'verify_tls' => checkbox('smtp_verify_tls'),
    ];
    $password = (string) ($_POST['smtp_password'] ?? '');
    if ($password !== '') {
        $body['password'] = $password;
    }
    if (checkbox('smtp_clear_password')) {
        $body['clear_password'] = true;
    }
    return $body;
}

function smtp_form_values(array $smtp): array
{
    return [
        'smtp_host' => $smtp['host'] ?? '',
        'smtp_port' => $smtp['port'] ?? 587,
        'smtp_security' => $smtp['security'] ?? 'starttls',
        'smtp_username' => $smtp['username'] ?? '',
        'smtp_sender' => $smtp['sender'] ?? '',
        'smtp_sender_name' => $smtp['sender_name'] ?? 'NetUSBFlash',
        'smtp_verify_tls' => $smtp['verify_tls'] ?? true,
        'smtp_has_password' => !empty($smtp['has_password']),
    ];
}

function smtp_field_errors(ApiResponse $response): array
{
    $errors = [];
    foreach (field_errors($response) as $field => $message) {
        $errors['smtp_' . $field] = $message;
    }
    return $errors;
}

function posted_smtp_values(): array
{
    $v = smtp_form_values([]);
    foreach (array_keys($v) as $key) {
        if ($key === 'smtp_verify_tls') {
            $v[$key] = checkbox($key);
        } elseif ($key !== 'smtp_has_password') {
            $v[$key] = (string) input($key, (string) $v[$key]);
        }
    }
    return $v;
}

/** Render a <select>. */
function select_options(array $options, string|int|null $selected): string
{
    $html = '';
    foreach ($options as $value => $label) {
        $sel = (string) $value === (string) $selected ? ' selected' : '';
        $html .= '<option value="' . e($value) . '"' . $sel . '>' . e($label) . '</option>';
    }
    return $html;
}

function checked(mixed $value): string
{
    return $value ? ' checked' : '';
}
