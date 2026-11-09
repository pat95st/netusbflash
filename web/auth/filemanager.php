<?php

declare(strict_types=1);

/*
 * nginx auth_request target for the file manager (/fm/).
 *
 * 204 + X-NUF-User/X-NUF-Role/X-NUF-Locale when a NetUSBFlash user is logged
 * in, 401 otherwise. nginx passes these headers on to FileGator, whose auth
 * adapter (web/filegator/NetUsbFlashAuth.php) uses them.
 */

require dirname(__DIR__) . '/src/bootstrap.php';

$user = filemanager_identity();
session_write_close();
if ($user === null) {
    http_response_code(401);
    exit;
}
header('X-NUF-User: ' . preg_replace('/[^A-Za-z0-9._-]/', '', (string) $user['username']));
header('X-NUF-Role: ' . preg_replace('/[^a-z]/', '', (string) $user['role']));
header('X-NUF-Locale: ' . preg_replace('/[^a-z]/', '', (string) $user['locale']));
http_response_code(204);
