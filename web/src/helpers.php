<?php

declare(strict_types=1);

const ROLE_LEVELS = ['viewer' => 1, 'operator' => 2, 'manager' => 3, 'admin' => 4];
const PROTOCOLS = ['smb', 'webdav', 'ftp', 'ftps', 'sftp', 'sshfs', 'scp', 'local'];

function api(): ApiClient
{
    static $client = null;
    if ($client === null) {
        $socket = getenv('NETUSBFLASH_SOCKET') ?: ($_SERVER['NETUSBFLASH_SOCKET'] ?? '/run/netusbflash/api.sock');
        $client = new ApiClient((string) $socket);
    }
    return $client;
}

/** Headers that identify the logged-in user towards the service. */
function session_headers(): array
{
    return [
        'X-Session-Token' => $_SESSION['token'] ?? null,
        'X-Client-IP' => $_SERVER['REMOTE_ADDR'] ?? '',
    ];
}

/**
 * Call the API as the current user from a page request and handle
 * session-level errors with a redirect.
 */
function call(string $method, string $path, ?array $body = null): ApiResponse
{
    $response = api()->call($method, $path, $body, session_headers());
    switch ($response->error()) {
        case 'session_expired':
            unset($_SESSION['token'], $_SESSION['user']);
            flash('warning', t('error.session_expired'));
            redirect('/login');
        case 'setup_required':
            redirect('/setup');
        case 'password_change_required':
            if (!str_starts_with((string) ($_SERVER['REQUEST_URI'] ?? ''), '/profile')) {
                redirect('/profile');
            }
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

/** True for the JSON endpoints used by the page scripts. */
function is_ajax_request(): bool
{
    $path = (string) parse_url($_SERVER['REQUEST_URI'] ?? '/', PHP_URL_PATH);
    return str_starts_with($path, '/ajax/') || str_starts_with($path, '/setup/api/');
}

function csrf_check(): void
{
    $sent = (string) ($_POST['_csrf'] ?? $_SERVER['HTTP_X_CSRF_TOKEN'] ?? '');
    if ($sent !== '' && hash_equals(csrf_token(), $sent)) {
        return;
    }
    if (is_ajax_request()) {
        json_out(['ok' => false, 'message' => t('error.csrf')], 400);
    }
    http_response_code(400);
    render('error', ['code' => 400, 'message' => t('error.csrf')], 'layout_plain');
    exit;
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

/**
 * The logged-in user for the file manager, or null.
 *
 * Used by nginx's auth subrequest (web/auth/filemanager.php) and the
 * development router. Checks the session with the service at most every 30
 * seconds, so a logout, lock or role change takes effect quickly.
 */
function filemanager_identity(): ?array
{
    $user = current_user();
    if ($user === null) {
        return null;
    }
    if (time() - (int) ($_SESSION['user_checked'] ?? 0) > 30) {
        $response = api()->call('GET', '/me', null, session_headers());
        if (!$response->ok()) {
            if ($response->error() === 'session_expired') {
                unset($_SESSION['token'], $_SESSION['user']);
            }
            return null;
        }
        $_SESSION['user'] = $response->data['user'];
        $_SESSION['user_checked'] = time();
        $user = $_SESSION['user'];
    }
    if (!empty($user['must_change_pw'])) {
        return null;
    }
    return $user;
}

/** Form value from a classic POST (login form). */
function input(string $key, mixed $default = ''): mixed
{
    $value = $_POST[$key] ?? $default;
    return is_string($value) ? trim($value) : $value;
}

/** Decoded JSON request body of an AJAX call. */
function json_input(): array
{
    static $data = null;
    if ($data === null) {
        $decoded = json_decode((string) file_get_contents('php://input'), true);
        $data = is_array($decoded) ? $decoded : [];
    }
    return $data;
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

/**
 * Content Security Policy. Inline styles are only allowed where a page needs
 * them (the HTML mail editor and its preview); scripts are never inline.
 */
function send_csp(bool $inlineStyles = false): void
{
    $style = $inlineStyles ? "'self' 'unsafe-inline'" : "'self'";
    header("Content-Security-Policy: default-src 'self'; img-src 'self' data:; style-src {$style}; "
        . "script-src 'self'; font-src 'self'; frame-src 'self'; frame-ancestors 'none'; form-action 'self'", true);
}

function render(string $template, array $vars = [], string $layout = 'layout'): void
{
    if (!empty($vars['inline_styles'])) {
        send_csp(true);
    }
    extract($vars, EXTR_SKIP);
    ob_start();
    require APP_ROOT . '/templates/' . $template . '.php';
    $content = ob_get_clean();
    $title = $vars['title'] ?? 'NetUSBFlash';
    $scripts = $vars['scripts'] ?? [];
    $styles = $vars['styles'] ?? [];
    require APP_ROOT . '/templates/' . $layout . '.php';
}

function json_out(array $data, int $status = 200): never
{
    http_response_code($status);
    header('Content-Type: application/json; charset=utf-8');
    header('Cache-Control: no-store');
    echo json_encode($data, JSON_UNESCAPED_UNICODE);
    exit;
}

function is_post(): bool
{
    return ($_SERVER['REQUEST_METHOD'] ?? 'GET') === 'POST';
}

function nav_active(string $path): string
{
    $current = rtrim((string) parse_url($_SERVER['REQUEST_URI'] ?? '/', PHP_URL_PATH), '/') ?: '/';
    $active = $path === '/' ? $current === '/' : str_starts_with($current, $path);
    return $active ? ' active" aria-current="page' : '';
}

/** Render a <select>'s options. */
function select_options(array $options, string|int|null $selected = null): string
{
    $html = '';
    foreach ($options as $value => $label) {
        $sel = $selected !== null && (string) $value === (string) $selected ? ' selected' : '';
        $html .= '<option value="' . e($value) . '"' . $sel . '>' . e($label) . '</option>';
    }
    return $html;
}

function checked(mixed $value): string
{
    return $value ? ' checked' : '';
}

/** Disabled attribute for form fields the current user may not change. */
function readonly_unless(string $role): string
{
    return has_role($role) ? '' : ' disabled';
}

/** Translations as JSON for assets/js/app.js (English fallback included). */
function i18n_json(): string
{
    $strings = array_merge(I18n::load('en'), I18n::load(I18n::locale()));
    return (string) json_encode($strings, JSON_UNESCAPED_UNICODE | JSON_HEX_TAG | JSON_HEX_AMP);
}
