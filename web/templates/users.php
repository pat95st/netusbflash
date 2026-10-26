<?php
$roleOptions = [];
foreach (array_keys(ROLE_LEVELS) as $role) {
    $roleOptions[$role] = t('role.' . $role);
}
?>
<h1 class="h3 mb-4"><?= e(t('nav.users')) ?></h1>

<div class="card mb-4">
    <div class="table-responsive">
        <table class="table align-middle mb-0">
            <thead><tr>
                <th><?= e(t('field.username')) ?></th>
                <th><?= e(t('field.email')) ?></th>
                <th><?= e(t('user.role')) ?></th>
                <th><?= e(t('user.language')) ?></th>
                <th><?= e(t('user.last_login')) ?></th>
                <th></th>
            </tr></thead>
            <tbody>
            <?php foreach ($users as $u): ?>
                <?php $formId = 'user-' . $u['id']; ?>
                <tr>
                    <td class="fw-semibold">
                        <?= e($u['username']) ?>
                        <?php if ($u['id'] === $me['id']): ?><span class="badge text-bg-light border"><?= e(t('user.you')) ?></span><?php endif; ?>
                        <?php if ($u['locked']): ?><span class="badge text-bg-warning"><?= e(t('user.locked')) ?></span><?php endif; ?>
                        <?php if ($u['must_change_pw']): ?><span class="badge text-bg-info"><?= e(t('user.must_change')) ?></span><?php endif; ?>
                    </td>
                    <td><input form="<?= e($formId) ?>" class="form-control form-control-sm" name="email" type="email" value="<?= e($u['email']) ?>" aria-label="<?= e(t('field.email')) ?>"></td>
                    <td><select form="<?= e($formId) ?>" class="form-select form-select-sm" name="role" aria-label="<?= e(t('user.role')) ?>"><?= select_options($roleOptions, $u['role']) ?></select></td>
                    <td><select form="<?= e($formId) ?>" class="form-select form-select-sm" name="locale" aria-label="<?= e(t('user.language')) ?>"><?= select_options(I18n::LOCALES, $u['locale']) ?></select></td>
                    <td class="small text-nowrap"><?= e(fmt_time($u['last_login'])) ?></td>
                    <td class="text-end text-nowrap">
                        <form method="post" action="/users" id="<?= e($formId) ?>" class="d-inline-flex flex-wrap gap-1 justify-content-end align-items-center">
                            <?= csrf_field() ?>
                            <input type="hidden" name="id" value="<?= e($u['id']) ?>">
                            <input type="hidden" name="username" value="<?= e($u['username']) ?>">
                            <div class="form-check form-check-inline small me-1">
                                <input class="form-check-input" type="checkbox" name="disabled" value="1" id="dis-<?= e($u['id']) ?>"<?= checked($u['disabled']) ?>>
                                <label class="form-check-label" for="dis-<?= e($u['id']) ?>"><?= e(t('common.disabled')) ?></label>
                            </div>
                            <button class="btn btn-sm btn-primary" name="action" value="update"><?= e(t('common.save')) ?></button>
                            <button class="btn btn-sm btn-outline-secondary" name="action" value="reset" data-confirm="<?= e(t('user.reset_confirm', ['user' => $u['username']])) ?>"><?= e(t('user.reset_password')) ?></button>
                            <?php if ($u['locked']): ?>
                                <button class="btn btn-sm btn-outline-warning" name="action" value="unlock"><?= e(t('user.unlock')) ?></button>
                            <?php endif; ?>
                            <?php if ($u['id'] !== $me['id']): ?>
                                <button class="btn btn-sm btn-outline-danger" name="action" value="delete" data-confirm="<?= e(t('user.delete_confirm', ['user' => $u['username']])) ?>"><?= e(t('common.delete')) ?></button>
                            <?php endif; ?>
                        </form>
                    </td>
                </tr>
            <?php endforeach; ?>
            </tbody>
        </table>
    </div>
</div>

<div class="row g-4">
    <div class="col-lg-6">
        <form method="post" action="/users" novalidate class="card">
            <?= csrf_field() ?>
            <div class="card-header bg-body fw-semibold"><?= e(t('user.add')) ?></div>
            <div class="card-body">
                <div class="row g-3">
                    <div class="col-md-6">
                        <label class="form-label" for="new_username"><?= e(t('field.username')) ?></label>
                        <input class="form-control<?= invalid($errors, 'username') ?>" id="new_username" name="username" value="<?= e($nv['username']) ?>" autocapitalize="none">
                        <?= feedback($errors, 'username') ?>
                    </div>
                    <div class="col-md-6">
                        <label class="form-label" for="new_email"><?= e(t('field.email')) ?></label>
                        <input class="form-control<?= invalid($errors, 'email') ?>" id="new_email" name="email" type="email" value="<?= e($nv['email']) ?>">
                        <?= feedback($errors, 'email') ?>
                    </div>
                    <div class="col-md-6">
                        <label class="form-label" for="new_role"><?= e(t('user.role')) ?></label>
                        <select class="form-select" id="new_role" name="role"><?= select_options($roleOptions, $nv['role']) ?></select>
                    </div>
                    <div class="col-md-6">
                        <label class="form-label" for="new_locale"><?= e(t('user.language')) ?></label>
                        <select class="form-select" id="new_locale" name="locale"><?= select_options(I18n::LOCALES, $nv['locale']) ?></select>
                    </div>
                </div>
                <p class="form-text mt-3 mb-0"><?= e(t('user.add_help')) ?></p>
            </div>
            <div class="card-footer bg-body">
                <button class="btn btn-primary" name="action" value="create"><?= e(t('user.add')) ?></button>
            </div>
        </form>
    </div>
    <div class="col-lg-6">
        <div class="card">
            <div class="card-header bg-body fw-semibold"><?= e(t('user.roles_title')) ?></div>
            <table class="table table-sm mb-0 small">
                <tbody>
                <?php foreach (array_keys(ROLE_LEVELS) as $role): ?>
                    <tr><th class="text-nowrap"><?= e(t('role.' . $role)) ?></th><td><?= e(t('role.' . $role . '_help')) ?></td></tr>
                <?php endforeach; ?>
                </tbody>
            </table>
        </div>
    </div>
</div>
