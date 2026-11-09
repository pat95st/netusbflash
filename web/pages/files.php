<?php

declare(strict_types=1);

require_role('viewer');
render('files', [
    'title' => t('nav.files'),
    'scripts' => ['/assets/js/pages/files.js'],
]);
