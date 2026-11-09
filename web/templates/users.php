<?php
$roleOptions = [];
foreach (array_keys(ROLE_LEVELS) as $role) {
    $roleOptions[$role] = t('role.' . $role);
}
?>
<div id="users" data-me="<?= e(current_user()['id']) ?>">
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
                <tbody data-users>
                    <tr data-empty hidden><td colspan="6" class="text-body-secondary p-3"><?= e(t('logs.none')) ?></td></tr>
                    <template data-row>
                        <tr>
                            <td class="fw-semibold">
                                <span data-bind="username"></span>
                                <span class="badge text-bg-light border" data-you hidden><?= e(t('user.you')) ?></span>
                                <span class="badge text-bg-warning" data-bind-show="locked"><?= e(t('user.locked')) ?></span>
                                <span class="badge text-bg-info" data-bind-show="must_change_pw"><?= e(t('user.must_change')) ?></span>
                            </td>
                            <td><input class="form-control form-control-sm" name="email" type="email" aria-label="<?= e(t('field.email')) ?>"></td>
                            <td><select class="form-select form-select-sm" name="role" aria-label="<?= e(t('user.role')) ?>"><?= select_options($roleOptions) ?></select></td>
                            <td><select class="form-select form-select-sm" name="locale" aria-label="<?= e(t('user.language')) ?>"><?= select_options(I18n::LOCALES) ?></select></td>
                            <td class="small text-nowrap" data-bind="last_login" data-format="time"></td>
                            <td class="text-end text-nowrap" data-row-actions>
                                <div class="form-check form-check-inline small me-1">
                                    <input class="form-check-input" type="checkbox" name="disabled" value="1">
                                    <label class="form-check-label"><?= e(t('common.disabled')) ?></label>
                                </div>
                                <button type="button" class="btn btn-sm btn-primary" data-action="save"><?= e(t('common.save')) ?></button>
                                <button type="button" class="btn btn-sm btn-outline-secondary" data-action="reset"><?= e(t('user.reset_password')) ?></button>
                                <button type="button" class="btn btn-sm btn-outline-warning" data-action="unlock" data-bind-show="locked"><?= e(t('user.unlock')) ?></button>
                                <button type="button" class="btn btn-sm btn-outline-danger" data-action="delete"><?= e(t('common.delete')) ?></button>
                            </td>
                        </tr>
                    </template>
                </tbody>
            </table>
        </div>
    </div>

    <div class="row g-4">
        <div class="col-lg-6">
            <form class="card" data-add-user novalidate>
                <div class="card-header bg-body fw-semibold"><?= e(t('user.add')) ?></div>
                <div class="card-body">
                    <div class="row g-3">
                        <div class="col-md-6">
                            <label class="form-label" for="new_username"><?= e(t('field.username')) ?></label>
                            <input class="form-control" id="new_username" name="username" autocapitalize="none">
                        </div>
                        <div class="col-md-6">
                            <label class="form-label" for="new_email"><?= e(t('field.email')) ?></label>
                            <input class="form-control" id="new_email" name="email" type="email">
                        </div>
                        <div class="col-md-6">
                            <label class="form-label" for="new_role"><?= e(t('user.role')) ?></label>
                            <select class="form-select" id="new_role" name="role"><?= select_options($roleOptions, 'operator') ?></select>
                        </div>
                        <div class="col-md-6">
                            <label class="form-label" for="new_locale"><?= e(t('user.language')) ?></label>
                            <select class="form-select" id="new_locale" name="locale"><?= select_options(I18n::LOCALES, I18n::locale()) ?></select>
                        </div>
                    </div>
                    <p class="form-text mt-3 mb-0"><?= e(t('user.add_help')) ?></p>
                </div>
                <div class="card-footer bg-body">
                    <button class="btn btn-primary" type="submit"><?= e(t('user.add')) ?></button>
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
</div>
