<h1 class="h3 mb-4"><?= e(t('nav.profile')) ?></h1>
<?php if ($forced): ?>
    <div class="alert alert-warning"><?= e(t('profile.must_change')) ?></div>
<?php endif; ?>
<div class="row g-4">
    <div class="col-lg-6">
        <form method="post" action="/profile" novalidate class="card">
            <?= csrf_field() ?>
            <div class="card-header bg-body fw-semibold"><?= e(t('profile.password')) ?></div>
            <div class="card-body">
                <div class="mb-3">
                    <label class="form-label" for="current"><?= e(t('profile.current_password')) ?></label>
                    <input class="form-control<?= invalid($errors, 'current') ?>" id="current" name="current" type="password" autocomplete="current-password">
                    <?= feedback($errors, 'current') ?>
                </div>
                <div class="mb-3">
                    <label class="form-label" for="new"><?= e(t('profile.new_password')) ?></label>
                    <input class="form-control<?= invalid($errors, 'new') ?>" id="new" name="new" type="password" autocomplete="new-password" minlength="12">
                    <?= feedback($errors, 'new') ?>
                    <div class="form-text"><?= e(t('field.password_help')) ?></div>
                </div>
                <div>
                    <label class="form-label" for="new_confirm"><?= e(t('field.password_confirm')) ?></label>
                    <input class="form-control<?= invalid($errors, 'new_confirm') ?>" id="new_confirm" name="new_confirm" type="password" autocomplete="new-password">
                    <?= feedback($errors, 'new_confirm') ?>
                </div>
            </div>
            <div class="card-footer bg-body">
                <button class="btn btn-primary" name="action" value="password"><?= e(t('profile.change_password')) ?></button>
            </div>
        </form>
    </div>
    <?php if (!$forced): ?>
    <div class="col-lg-6">
        <form method="post" action="/profile" novalidate class="card">
            <?= csrf_field() ?>
            <div class="card-header bg-body fw-semibold"><?= e(t('profile.settings')) ?></div>
            <div class="card-body">
                <p class="mb-3"><?= e(t('field.username')) ?>: <strong><?= e($user['username']) ?></strong> · <?= e(t('role.' . $user['role'])) ?></p>
                <div class="mb-3">
                    <label class="form-label" for="email"><?= e(t('field.email')) ?></label>
                    <input class="form-control<?= invalid($errors, 'email') ?>" id="email" name="email" type="email" value="<?= e($user['email']) ?>">
                    <?= feedback($errors, 'email') ?>
                    <div class="form-text"><?= e(t('profile.email_help')) ?></div>
                </div>
                <div>
                    <label class="form-label" for="locale"><?= e(t('user.language')) ?></label>
                    <select class="form-select" id="locale" name="locale"><?= select_options(I18n::LOCALES, $user['locale']) ?></select>
                </div>
            </div>
            <div class="card-footer bg-body">
                <button class="btn btn-primary" name="action" value="profile"><?= e(t('common.save')) ?></button>
            </div>
        </form>
    </div>
    <?php endif; ?>
</div>
