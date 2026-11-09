<?php

declare(strict_types=1);

require_role('admin');
render('users', ['title' => t('nav.users'), 'scripts' => ['/assets/js/pages/users.js']]);
