<?php

declare(strict_types=1);

require_role('admin');
render('backup', ['title' => t('nav.backup'), 'scripts' => ['/assets/js/pages/backup.js']]);
