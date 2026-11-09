<?php

declare(strict_types=1);

require_role('viewer');
render('uploads', ['title' => t('nav.uploads'), 'scripts' => ['/assets/js/pages/uploads.js']]);
