<?php

// Router for PHP's built-in web server (development only, see scripts/dev-server.sh).
// In production nginx does this: see packaging/nginx-site.conf.
$path = (string) parse_url($_SERVER['REQUEST_URI'] ?? '/', PHP_URL_PATH);

// File manager (FileGator) under /fm/.
if ($path === '/fm' || str_starts_with($path, '/fm/')) {
    $fgDir = rtrim((string) (getenv('NETUSBFLASH_FILEGATOR_DIR') ?: dirname(__DIR__) . '/vendor/filegator'), '/');
    $asset = substr($path, 4);
    if ($asset !== '' && preg_match('#^(css|js|fonts|img)/[A-Za-z0-9._/-]+$#', $asset) && is_file($fgDir . '/dist/' . $asset)) {
        $types = ['css' => 'text/css', 'js' => 'application/javascript', 'woff' => 'font/woff', 'woff2' => 'font/woff2',
                  'ttf' => 'font/ttf', 'svg' => 'image/svg+xml', 'png' => 'image/png', 'ico' => 'image/x-icon'];
        $ext = pathinfo($asset, PATHINFO_EXTENSION);
        header('Content-Type: ' . ($types[$ext] ?? 'application/octet-stream'));
        readfile($fgDir . '/dist/' . $asset);
        return true;
    }
    // Same check nginx makes with auth_request.
    require __DIR__ . '/src/bootstrap.php';
    $user = filemanager_identity();
    session_write_close();
    header_remove('X-Frame-Options');
    header_remove('Content-Security-Policy');
    if ($user === null) {
        http_response_code(401);
        echo 'Not logged in';
        return true;
    }
    $_SERVER['NUF_USER'] = $user['username'];
    $_SERVER['NUF_ROLE'] = $user['role'];
    $_SERVER['NUF_LOCALE'] = $user['locale'];
    $_SERVER['NETUSBFLASH_FILEGATOR_DIR'] = $fgDir;
    require __DIR__ . '/filegator/entry.php';
    return true;
}

if ($path !== '/' && is_file(__DIR__ . '/public' . $path)) {
    return false;
}
require __DIR__ . '/public/index.php';
