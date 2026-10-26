<div class="card shadow-sm mx-auto narrow-card">
    <div class="card-body p-4">
        <h2 class="h5 mb-3"><?= e(t('login.title')) ?></h2>
        <?php if ($error): ?>
            <div class="alert alert-danger"><?= e($error) ?></div>
        <?php endif; ?>
        <form method="post" action="/login" novalidate>
            <?= csrf_field() ?>
            <div class="mb-3">
                <label class="form-label" for="username"><?= e(t('field.username')) ?></label>
                <input class="form-control" id="username" name="username" value="<?= e($username) ?>"
                       autocomplete="username" autocapitalize="none" required autofocus>
            </div>
            <div class="mb-3">
                <label class="form-label" for="password"><?= e(t('field.password')) ?></label>
                <input class="form-control" id="password" name="password" type="password"
                       autocomplete="current-password" required>
            </div>
            <button class="btn btn-primary w-100" type="submit"><?= e(t('login.submit')) ?></button>
        </form>
    </div>
</div>
