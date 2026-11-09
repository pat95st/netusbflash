<?php

declare(strict_types=1);

$user = require_role('manager');
render('notifications', [
    'title' => t('nav.notifications'),
    'userEmail' => $user['email'] ?? '',
    // Quill (HTML mail editor) writes inline styles, e.g. for text alignment.
    'inline_styles' => true,
    'styles' => ['/assets/vendor/quill/quill.snow.css'],
    'scripts' => ['/assets/vendor/quill/quill.min.js', '/assets/js/pages/notifications.js'],
]);
