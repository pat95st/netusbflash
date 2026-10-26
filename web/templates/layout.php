<?php
/** @var string $content */
/** @var string $title */
$user = current_user();
require __DIR__ . '/head.php';
?>
<body>
<nav class="navbar navbar-expand-lg border-bottom bg-body-tertiary">
    <div class="container-xl">
        <a class="navbar-brand d-flex align-items-center gap-2" href="/">
            <img src="/assets/img/icon.svg" alt="" width="26" height="26">
            <span class="fw-semibold">NetUSBFlash</span>
        </a>
        <?php if ($user !== null): ?>
        <button class="navbar-toggler" type="button" data-bs-toggle="collapse" data-bs-target="#mainNav"
                aria-controls="mainNav" aria-expanded="false" aria-label="<?= e(t('nav.toggle')) ?>">
            <span class="navbar-toggler-icon"></span>
        </button>
        <div class="collapse navbar-collapse" id="mainNav">
            <ul class="navbar-nav me-auto">
                <li class="nav-item"><a class="nav-link<?= nav_active('/') ?>" href="/"><?= e(t('nav.dashboard')) ?></a></li>
                <li class="nav-item"><a class="nav-link<?= nav_active('/usb') ?>" href="/usb"><?= e(t('nav.usb')) ?></a></li>
                <li class="nav-item"><a class="nav-link<?= nav_active('/targets') ?>" href="/targets"><?= e(t('nav.targets')) ?></a></li>
                <li class="nav-item"><a class="nav-link<?= nav_active('/uploads') ?>" href="/uploads"><?= e(t('nav.uploads')) ?></a></li>
                <?php if (has_role('manager')): ?>
                <li class="nav-item"><a class="nav-link<?= nav_active('/notifications') ?>" href="/notifications"><?= e(t('nav.notifications')) ?></a></li>
                <?php endif; ?>
                <li class="nav-item"><a class="nav-link<?= nav_active('/logs') ?>" href="/logs"><?= e(t('nav.logs')) ?></a></li>
                <?php if (has_role('admin')): ?>
                <li class="nav-item"><a class="nav-link<?= nav_active('/users') ?>" href="/users"><?= e(t('nav.users')) ?></a></li>
                <li class="nav-item"><a class="nav-link<?= nav_active('/system') ?>" href="/system"><?= e(t('nav.system')) ?></a></li>
                <?php endif; ?>
            </ul>
            <ul class="navbar-nav">
                <li class="nav-item dropdown">
                    <a class="nav-link dropdown-toggle" href="#" role="button" data-bs-toggle="dropdown" aria-expanded="false">
                        <i class="bi bi-person-circle" aria-hidden="true"></i> <?= e($user['username']) ?>
                        <span class="badge text-bg-secondary ms-1"><?= e(t('role.' . $user['role'])) ?></span>
                    </a>
                    <ul class="dropdown-menu dropdown-menu-end">
                        <li><a class="dropdown-item" href="/profile"><?= e(t('nav.profile')) ?></a></li>
                        <li><hr class="dropdown-divider"></li>
                        <li>
                            <form method="post" action="/logout" class="px-3">
                                <?= csrf_field() ?>
                                <button type="submit" class="btn btn-link p-0 text-decoration-none"><?= e(t('nav.logout')) ?></button>
                            </form>
                        </li>
                    </ul>
                </li>
            </ul>
        </div>
        <?php endif; ?>
    </div>
</nav>

<main class="container-xl py-4">
    <?php require __DIR__ . '/flashes.php'; ?>
    <?= $content ?>
</main>

<footer class="container-xl pb-4 text-body-secondary small d-flex flex-wrap gap-3 justify-content-between">
    <span>NetUSBFlash <?= e(APP_VERSION) ?></span>
    <span>
        <?php foreach (I18n::LOCALES as $code => $name): ?>
            <a href="/lang/<?= e($code) ?>" class="<?= I18n::locale() === $code ? 'fw-semibold' : 'link-secondary' ?> me-2"><?= e($name) ?></a>
        <?php endforeach; ?>
    </span>
</footer>
<script src="/assets/vendor/bootstrap/js/bootstrap.bundle.min.js"></script>
<script src="/assets/js/app.js"></script>
</body>
</html>
