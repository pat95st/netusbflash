<?php
/** @var string $content */
/** @var string $title */
require __DIR__ . '/head.php';
?>
<body class="bg-body-tertiary">
<main class="container py-5 plain-container">
    <div class="text-center mb-4">
        <img src="/assets/img/icon.svg" alt="" width="48" height="48" class="mb-2">
        <h1 class="h4 fw-semibold mb-0">NetUSBFlash</h1>
    </div>
    <?php require __DIR__ . '/flashes.php'; ?>
    <?= $content ?>
    <?php if (empty($hideLanguageFooter)): ?>
    <p class="text-center small mt-4 mb-0">
        <?php foreach (I18n::LOCALES as $code => $name): ?>
            <a href="/lang/<?= e($code) ?>" class="<?= I18n::locale() === $code ? 'fw-semibold' : 'link-secondary' ?> mx-1"><?= e($name) ?></a>
        <?php endforeach; ?>
    </p>
    <?php endif; ?>
</main>
<script src="/assets/vendor/bootstrap/js/bootstrap.bundle.min.js"></script>
<script src="/assets/js/app.js"></script>
</body>
</html>
