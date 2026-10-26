<?php

declare(strict_types=1);

const ROLE_LEVELS = ['viewer' => 1, 'operator' => 2, 'manager' => 3, 'admin' => 4];

function api(): ApiClient
{
    static $client = null;
    if ($client === null) {
        $socket = getenv('NETUSBFLASH_SOCKET') ?: ($_SERVER['NETUSBFLASH_SOCKET'] ?? '/run/netusbflash/api.sock');
        $client = new ApiClient((string) $socket);
    }
    return $client;
}

/**
 * Call the API as the current user and handle session-level errors centrally.
 */
function call(string $method, string $path, ?array $body = null): ApiResponse
{
    $response = api()->call($method, $path, $body, [
        'X-Session-Token' => $_SESSION['token'] ?? null,
        'X-Client-IP' => $_SERVER['REMOTE_ADDR'] ?? '',
    ]);
    switch ($response->error()) {
        case 'session_expired':
            unset($_SESSION['token'], $_SESSION['user']);
            flash('warning', t('error.session_expired'));
            redirect('/login');
        case 'setup_required':
            redirect('/setup');
        case 'password_change_required':
            redirect('/profile');
    }
    return $response;
}

/** Call a setup endpoint with the one-time code from the session. */
function setup_call(string $method, string $path, ?array $body = null): ApiResponse
{
    return api()->call($method, $path, $body, ['X-Setup-Code' => $_SESSION['setup_code'] ?? null]);
}

function t(string $key, array $params = []): string
{
    return I18n::t($key, $params);
}

function e(mixed $value): string
{
    return htmlspecialchars((string) $value, ENT_QUOTES | ENT_SUBSTITUTE, 'UTF-8');
}

function redirect(string $path): never
{
    header('Location: ' . $path, true, 303);
    exit;
}

function flash(string $type, string $message): void
{
    $_SESSION['flash'][] = ['type' => $type, 'message' => $message];
}

/** @return list<array{type: string, message: string}> */
function take_flashes(): array
{
    $items = $_SESSION['flash'] ?? [];
    unset($_SESSION['flash']);
    return $items;
}

function csrf_token(): string
{
    if (empty($_SESSION['csrf'])) {
        $_SESSION['csrf'] = bin2hex(random_bytes(32));
    }
    return $_SESSION['csrf'];
}

function csrf_field(): string
{
    return '<input type="hidden" name="_csrf" value="' . e(csrf_token()) . '">';
}

function csrf_check(): void
{
    $sent = (string) ($_POST['_csrf'] ?? $_SERVER['HTTP_X_CSRF_TOKEN'] ?? '');
    if ($sent === '' || !hash_equals(csrf_token(), $sent)) {
        http_response_code(400);
        render('error', ['code' => 400, 'message' => t('error.csrf')], 'layout_plain');
        exit;
    }
}

function current_user(): ?array
{
    return $_SESSION['user'] ?? null;
}

function has_role(string $role): bool
{
    $user = current_user();
    return $user !== null && (ROLE_LEVELS[$user['role']] ?? 0) >= ROLE_LEVELS[$role];
}

function require_role(string $role): array
{
    $user = current_user();
    if ($user === null) {
        $_SESSION['after_login'] = $_SERVER['REQUEST_URI'] ?? '/';
        redirect('/login');
    }
    // Refresh the cached user regularly so role changes by an admin take effect.
    if (time() - (int) ($_SESSION['user_checked'] ?? 0) > 30) {
        $response = call('GET', '/me');
        if ($response->ok()) {
            $_SESSION['user'] = $response->data['user'];
            $_SESSION['user_checked'] = time();
            $user = $_SESSION['user'];
        }
    }
    if (!has_role($role)) {
        http_response_code(403);
        render('error', ['code' => 403, 'message' => t('error.forbidden')]);
        exit;
    }
    return $user;
}

function input(string $key, mixed $default = ''): mixed
{
    $value = $_POST[$key] ?? $default;
    return is_string($value) ? trim($value) : $value;
}

function checkbox(string $key): bool
{
    return isset($_POST[$key]) && $_POST[$key] !== '0';
}

function error_message(ApiResponse $response): string
{
    $code = $response->error() ?? 'unknown';
    if (I18n::has('error.' . $code)) {
        return t('error.' . $code);
    }
    $message = (string) ($response->data['message'] ?? $code);
    return t('error.generic', ['message' => $message]);
}

/** @return array<string, string> field => translated message */
function field_errors(ApiResponse $response): array
{
    $out = [];
    foreach ($response->fields() as $field => $code) {
        $out[$field] = I18n::has('field.' . $code) ? t('field.' . $code) : (string) $code;
    }
    return $out;
}

/** Bootstrap validation helpers for templates. */
function invalid(array $errors, string $field): string
{
    return isset($errors[$field]) ? ' is-invalid' : '';
}

function feedback(array $errors, string $field): string
{
    return isset($errors[$field]) ? '<div class="invalid-feedback">' . e($errors[$field]) . '</div>' : '';
}

function fmt_bytes(int|float|null $bytes): string
{
    if ($bytes === null) {
        return '–';
    }
    $units = ['B', 'KB', 'MB', 'GB', 'TB'];
    $i = 0;
    while ($bytes >= 1024 && $i < count($units) - 1) {
        $bytes /= 1024;
        $i++;
    }
    return ($i === 0 ? (string) (int) $bytes : number_format($bytes, 1, I18n::locale() === 'de' ? ',' : '.', '')) . ' ' . $units[$i];
}

function fmt_time(int|float|null $timestamp): string
{
    if (!$timestamp) {
        return '–';
    }
    return date(I18n::locale() === 'de' ? 'd.m.Y H:i:s' : 'Y-m-d H:i:s', (int) $timestamp);
}

function fmt_duration(int|float|null $seconds): string
{
    if ($seconds === null) {
        return '–';
    }
    $seconds = (int) $seconds;
    $d = intdiv($seconds, 86400);
    $h = intdiv($seconds % 86400, 3600);
    $m = intdiv($seconds % 3600, 60);
    return ($d ? $d . 'd ' : '') . sprintf('%02d:%02d', $h, $m);
}

function render(string $template, array $vars = [], string $layout = 'layout'): void
{
    extract($vars, EXTR_SKIP);
    ob_start();
    require APP_ROOT . '/templates/' . $template . '.php';
    $content = ob_get_clean();
    $title = $vars['title'] ?? 'NetUSBFlash';
    require APP_ROOT . '/templates/' . $layout . '.php';
}

function json_out(array $data, int $status = 200): never
{
    http_response_code($status);
    header('Content-Type: application/json; charset=utf-8');
    echo json_encode($data, JSON_UNESCAPED_UNICODE);
    exit;
}

function is_post(): bool
{
    return ($_SERVER['REQUEST_METHOD'] ?? 'GET') === 'POST';
}

function usb_state_label(array $usb): string
{
    $state = $usb['state'] ?? [];
    if (empty($usb['enabled'])) {
        return t('usb.state_disabled');
    }
    if (empty($usb['image']['exists'])) {
        return t('usb.state_no_image');
    }
    if (empty($state['attached'])) {
        return t('usb.state_detached');
    }
    return !empty($state['host_connected']) ? t('usb.state_connected') : t('usb.state_waiting_host');
}

function usb_state_class(array $usb): string
{
    $state = $usb['state'] ?? [];
    if (empty($usb['enabled']) || empty($usb['image']['exists'])) {
        return 'secondary';
    }
    if (empty($state['attached'])) {
        return 'warning';
    }
    return !empty($state['host_connected']) ? 'success' : 'info';
}

function upload_status_badge(string $status): string
{
    $class = ['pending' => 'info', 'done' => 'success', 'failed' => 'danger', 'discarded' => 'secondary'][$status] ?? 'secondary';
    return '<span class="badge text-bg-' . $class . '">' . e(t('upload.status_' . $status)) . '</span>';
}

function nav_active(string $path): string
{
    $current = rtrim((string) parse_url($_SERVER['REQUEST_URI'] ?? '/', PHP_URL_PATH), '/') ?: '/';
    $active = $path === '/' ? $current === '/' : str_starts_with($current, $path);
    return $active ? ' active" aria-current="page' : '';
}
