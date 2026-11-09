<?php

declare(strict_types=1);

require_role('viewer');
render('targets', ['title' => t('nav.targets'), 'scripts' => ['/assets/js/pages/targets.js']]);
