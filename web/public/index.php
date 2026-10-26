<?php

declare(strict_types=1);

require dirname(__DIR__) . '/src/bootstrap.php';

$path = rtrim((string) parse_url($_SERVER['REQUEST_URI'] ?? '/', PHP_URL_PATH), '/') ?: '/';

if (is_post()) {
    csrf_check();
}

$routes = [
    '#^/$#' => 'dashboard',
    '#^/ajax/status$#' => 'ajax_status',
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
];

foreach ($routes as $pattern => $page) {
    if (preg_match($pattern, $path, $matches)) {
        $params = array_slice($matches, 1);
        require APP_ROOT . '/pages/' . $page . '.php';
        exit;
    }
}

http_response_code(404);
render('error', ['code' => 404, 'message' => t('error.not_found')]);
