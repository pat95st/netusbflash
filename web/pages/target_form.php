<?php

declare(strict_types=1);

$isNew = $params[0] === 'new';
require_role($isNew ? 'manager' : 'viewer');

render('target_form', [
    'title' => $isNew ? t('target.add') : t('target.edit'),
    'isNew' => $isNew,
    'id' => $isNew ? null : (int) $params[0],
    'scripts' => ['/assets/js/pages/target_form.js'],
]);
