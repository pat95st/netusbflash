<?php

declare(strict_types=1);

if (current_user() === null) {
    redirect('/login');
}
render('profile', ['title' => t('nav.profile'), 'scripts' => ['/assets/js/pages/profile.js']]);
