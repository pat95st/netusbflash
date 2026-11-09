<?php

declare(strict_types=1);

require_role('admin');
render('updates', ['title' => t('nav.updates'), 'scripts' => ['/assets/js/pages/updates.js']]);
