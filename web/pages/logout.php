<?php

declare(strict_types=1);

if (is_post() && current_user() !== null) {
    api()->call('POST', '/auth/logout', [], ['X-Session-Token' => $_SESSION['token'] ?? null]);
}
$locale = $_SESSION['locale'] ?? null;
$_SESSION = [];
session_regenerate_id(true);
if ($locale !== null) {
    $_SESSION['locale'] = $locale;
}
flash('success', t('login.logged_out'));
redirect('/login');
