<?php

declare(strict_types=1);

$locale = $params[0];
$_SESSION['locale'] = $locale;
if (current_user() !== null) {
    $response = call('PUT', '/me', ['email' => current_user()['email'], 'locale' => $locale]);
    if ($response->ok()) {
        $_SESSION['user'] = $response->data['user'];
    }
}
$back = (string) ($_SERVER['HTTP_REFERER'] ?? '/');
$path = (string) parse_url($back, PHP_URL_PATH);
$query = (string) parse_url($back, PHP_URL_QUERY);
redirect(($path !== '' && str_starts_with($path, '/') && !str_starts_with($path, '/lang/') ? $path : '/') . ($query !== '' ? '?' . $query : ''));
