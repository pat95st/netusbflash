<?php

declare(strict_types=1);

require dirname(__DIR__) . '/src/bootstrap.php';

$path = rtrim((string) parse_url($_SERVER['REQUEST_URI'] ?? '/', PHP_URL_PATH), '/') ?: '/';

// Every request that changes something must carry the CSRF token
// (form field _csrf or header X-CSRF-Token).
if (($_SERVER['REQUEST_METHOD'] ?? 'GET') !== 'GET') {
    csrf_check();
}

$routes = [
    '#^/ajax/api(/[a-z0-9/_-]+)$#' => 'ajax_api',
    '#^/setup/api/(state|verify|submit|goto)$#' => 'setup_api',
    '#^/$#' => 'dashboard',
    '#^/login$#' => 'login',
    '#^/logout$#' => 'logout',
    '#^/setup$#' => 'setup',
    '#^/lang/(en|de)$#' => 'lang',
    '#^/usb$#' => 'usb',
    '#^/targets$#' => 'targets',
    '#^/targets/(new|\d+)$#' => 'target_form',
    '#^/uploads$#' => 'uploads',
    '#^/notifications$#' => 'notifications',
    '#^/users$#' => 'users',
    '#^/profile$#' => 'profile',
    '#^/logs$#' => 'logs',
    '#^/system$#' => 'system',
    '#^/files$#' => 'files',
    '#^/updates$#' => 'updates',
    '#^/backup$#' => 'backup',
];

foreach ($routes as $pattern => $page) {
    if (preg_match($pattern, $path, $matches)) {
        $params = array_slice($matches, 1);
        require APP_ROOT . '/pages/' . $page . '.php';
        exit;
    }
}

if (is_ajax_request()) {
    json_out(['ok' => false, 'message' => t('error.not_found')], 404);
}
http_response_code(404);
render('error', ['code' => 404, 'message' => t('error.not_found')]);
