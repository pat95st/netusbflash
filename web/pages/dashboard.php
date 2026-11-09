<?php

declare(strict_types=1);

require_role('viewer');
render('dashboard', ['title' => t('nav.dashboard'), 'scripts' => ['/assets/js/pages/dashboard.js']]);
