<?php

declare(strict_types=1);

/*
 * Entry point of the file manager (FileGator) under /fm/.
 *
 * Replaces FileGator's own dist/index.php so the program directory can stay
 * read-only: logs, temporary files and the CSRF key live in a separate data
 * directory, and the files shown are the USB stick's mount point.
 *
 * Environment (fastcgi_param in nginx, or set by scripts/dev-server.sh):
 *   NETUSBFLASH_FILEGATOR_DIR   FileGator installation (default /opt/netusbflash/filegator)
 *   NETUSBFLASH_FILEGATOR_DATA  writable data directory (default /var/cache/netusbflash/filegator)
 *   NETUSBFLASH_BROWSE_DIR      folder to show (default /srv/netusbflash/usb-stick)
 *   NUF_USER, NUF_ROLE, NUF_LOCALE  the logged-in NetUSBFlash user (see NetUsbFlashAuth)
 */

error_reporting(E_ALL & ~E_DEPRECATED & ~E_STRICT);
ini_set('display_errors', '0');

$env = static function (string $name, string $default): string {
    $value = getenv($name);
    if ($value === false || $value === '') {
        $value = $_SERVER[$name] ?? $default;
    }
    return rtrim((string) $value, '/');
};

$fgDir = $env('NETUSBFLASH_FILEGATOR_DIR', '/opt/netusbflash/filegator');
$dataDir = $env('NETUSBFLASH_FILEGATOR_DATA', '/var/cache/netusbflash/filegator');
$root = $env('NETUSBFLASH_BROWSE_DIR', '/srv/netusbflash/usb-stick');

if (!is_file($fgDir . '/vendor/autoload.php')) {
    http_response_code(503);
    header('Content-Type: text/plain; charset=utf-8');
    echo "The file manager (FileGator) is not installed. Run packaging/fetch-filegator.sh.\n";
    exit;
}

foreach (['logs', 'tmp', 'sessions'] as $sub) {
    if (!is_dir($dataDir . '/' . $sub)) {
        @mkdir($dataDir . '/' . $sub, 0700, true);
    }
}
$keyFile = $dataDir . '/csrf.key';
if (!is_file($keyFile)) {
    @file_put_contents($keyFile, bin2hex(random_bytes(32)));
    @chmod($keyFile, 0600);
}
$csrfKey = (string) @file_get_contents($keyFile) ?: bin2hex(random_bytes(32));

require $fgDir . '/vendor/autoload.php';
require __DIR__ . '/NetUsbFlashAuth.php';

define('APP_ENV', 'production');
define('APP_PUBLIC_PATH', '/fm/');
define('APP_PUBLIC_DIR', $fgDir . '/dist');
if (!defined('APP_VERSION')) { // the development router has already loaded the NetUSBFlash UI
    define('APP_VERSION', trim((string) @file_get_contents($fgDir . '/VERSION')) ?: '7');
}

$locale = (string) ($_SERVER['NUF_LOCALE'] ?? 'en');
$hidden = ['System Volume Information', '$RECYCLE.BIN', '.Trashes', '.Spotlight-V100', '.fseventsd', '.TemporaryItems'];

$config = [
    'public_path' => APP_PUBLIC_PATH,
    'public_dir' => APP_PUBLIC_DIR,
    'overwrite_on_upload' => false,
    'timezone' => date_default_timezone_get(),
    'download_inline' => ['pdf', 'txt', 'mp3', 'wav', 'ogg', 'flac', 'm4a'],

    'frontend_config' => [
        'app_name' => 'NetUSBFlash',
        'app_version' => APP_VERSION,
        'language' => $locale === 'de' ? 'german' : 'english',
        'logo' => '/assets/img/icon.svg',
        'upload_max_size' => 8 * 1024 * 1024 * 1024,
        'upload_chunk_size' => 1 * 1024 * 1024,
        'upload_simultaneous' => 2,
        'default_archive_name' => 'recordings.zip',
        'editable' => ['.txt', '.md', '.csv', '.json', '.log'],
        'date_format' => $locale === 'de' ? 'DD.MM.YYYY HH:mm:ss' : 'YYYY-MM-DD HH:mm:ss',
        'guest_redirection' => '/login',
        'search_simultaneous' => 5,
        'filter_entries' => $hidden,
    ],

    'services' => [
        'Filegator\Services\Logger\LoggerInterface' => [
            'handler' => '\Filegator\Services\Logger\Adapters\MonoLogger',
            'config' => [
                'monolog_handlers' => [
                    function () use ($dataDir) {
                        return new \Monolog\Handler\StreamHandler($dataDir . '/logs/app.log', \Monolog\Logger::WARNING);
                    },
                ],
            ],
        ],
        'Filegator\Services\Session\SessionStorageInterface' => [
            'handler' => '\Filegator\Services\Session\Adapters\SessionStorage',
            'config' => [
                'handler' => function () use ($dataDir) {
                    $handler = new \Symfony\Component\HttpFoundation\Session\Storage\Handler\NativeFileSessionHandler($dataDir . '/sessions');
                    return new \Symfony\Component\HttpFoundation\Session\Storage\NativeSessionStorage([
                        'name' => 'nuffm',
                        'cookie_path' => '/fm/',
                        'cookie_samesite' => 'Strict',
                        'cookie_secure' => !empty($_SERVER['HTTPS']) && $_SERVER['HTTPS'] !== 'off',
                        'cookie_httponly' => true,
                    ], $handler);
                },
            ],
        ],
        'Filegator\Services\Cors\Cors' => [
            'handler' => '\Filegator\Services\Cors\Cors',
            'config' => ['enabled' => false],
        ],
        'Filegator\Services\Tmpfs\TmpfsInterface' => [
            'handler' => '\Filegator\Services\Tmpfs\Adapters\Tmpfs',
            'config' => [
                'path' => $dataDir . '/tmp/',
                'gc_probability_perc' => 10,
                'gc_older_than' => 60 * 60 * 24,
            ],
        ],
        'Filegator\Services\Security\Security' => [
            'handler' => '\Filegator\Services\Security\Security',
            'config' => [
                'csrf_protection' => true,
                'csrf_key' => $csrfKey,
                'ip_allowlist' => [],
                'ip_denylist' => [],
                'allow_insecure_overlays' => false,
            ],
        ],
        'Filegator\Services\View\ViewInterface' => [
            'handler' => '\Filegator\Services\View\Adapters\Vuejs',
            'config' => [
                // Hide FileGator's own login/logout and profile controls: NetUSBFlash handles the login.
                'add_to_head' => '<link rel="icon" href="/assets/img/icon.svg"><link rel="stylesheet" href="/assets/css/filegator.css">',
                'add_to_body' => '',
            ],
        ],
        'Filegator\Services\Storage\Filesystem' => [
            'handler' => '\Filegator\Services\Storage\Filesystem',
            'config' => [
                'separator' => '/',
                'config' => [],
                'adapter' => function () use ($root) {
                    return new \League\Flysystem\Adapter\Local($root, LOCK_EX, \League\Flysystem\Adapter\Local::SKIP_LINKS);
                },
            ],
        ],
        'Filegator\Services\Archiver\ArchiverInterface' => [
            'handler' => '\Filegator\Services\Archiver\Adapters\ZipArchiver',
            'config' => [],
        ],
        'Filegator\Services\Auth\AuthInterface' => [
            'handler' => '\NetUsbFlash\FileGator\NetUsbFlashAuth',
            'config' => ['root' => $root],
        ],
        'Filegator\Services\Router\Router' => [
            'handler' => '\Filegator\Services\Router\Router',
            'config' => [
                'query_param' => 'r',
                'routes_file' => $fgDir . '/backend/Controllers/routes.php',
            ],
        ],
    ],
];

if (!is_dir($root)) {
    @mkdir($root, 0750, true);
}

new \Filegator\App(
    new \Filegator\Config\Config($config),
    \Filegator\Kernel\Request::createFromGlobals(),
    new \Filegator\Kernel\Response(),
    new \Filegator\Kernel\StreamedResponse(),
    new \Filegator\Container\Container()
);
