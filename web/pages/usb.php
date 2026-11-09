<?php

declare(strict_types=1);

require_role('viewer');
render('usb', ['title' => t('nav.usb'), 'scripts' => ['/assets/js/pages/usb.js']]);
