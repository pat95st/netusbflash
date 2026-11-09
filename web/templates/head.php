<!doctype html>
<html lang="<?= e(I18n::locale()) ?>" data-bs-theme="light">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <meta name="csrf-token" content="<?= e(csrf_token()) ?>">
    <title><?= e($title) ?> · NetUSBFlash</title>
    <link rel="icon" href="/assets/img/icon.svg" type="image/svg+xml">
    <link rel="stylesheet" href="/assets/vendor/bootstrap/css/bootstrap.min.css">
    <link rel="stylesheet" href="/assets/vendor/bootstrap-icons/font/bootstrap-icons.min.css">
<?php foreach (($styles ?? []) as $style): ?>
    <link rel="stylesheet" href="<?= e($style) ?>">
<?php endforeach; ?>
    <link rel="stylesheet" href="/assets/css/app.css">
    <script src="/assets/js/theme.js"></script>
    <script type="application/json" id="i18n-data"><?= i18n_json() ?></script>
</head>
