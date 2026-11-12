<?php

declare(strict_types=1);

require_role('viewer');
render('conversion', ['title' => t('nav.conversion'), 'scripts' => ['/assets/js/pages/conversion.js']]);
