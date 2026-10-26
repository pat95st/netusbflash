<?php

declare(strict_types=1);

define('APP_ROOT', dirname(__DIR__));
define('APP_VERSION', trim((string) @file_get_contents(dirname(APP_ROOT) . '/VERSION')) ?: 'dev');

require __DIR__ . '/ApiClient.php';
require __DIR__ . '/I18n.php';
require __DIR__ . '/helpers.php';
require __DIR__ . '/forms.php';

$https = !empty($_SERVER['HTTPS']) && $_SERVER['HTTPS'] !== 'off';
ini_set('session.use_strict_mode', '1');
ini_set('session.use_only_cookies', '1');
session_name('nufsid');
session_set_cookie_params([
    'lifetime' => 0,
    'path' => '/',
    'secure' => $https,
    'httponly' => true,
    'samesite' => 'Strict',
]);
session_start();

I18n::setLocale(I18n::detect(current_user()));

header('X-Frame-Options: DENY');
header('X-Content-Type-Options: nosniff');
header('Referrer-Policy: same-origin');
header("Content-Security-Policy: default-src 'self'; img-src 'self' data:; style-src 'self'; script-src 'self'; font-src 'self'; frame-ancestors 'none'; form-action 'self'");
