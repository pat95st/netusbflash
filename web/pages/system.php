<?php

declare(strict_types=1);

require_role('admin');
render('system', ['title' => t('nav.system'), 'scripts' => ['/assets/js/pages/system.js']]);
