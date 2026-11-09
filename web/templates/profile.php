<div id="profile">
    <h1 class="h3 mb-4"><?= e(t('nav.profile')) ?></h1>
    <div class="alert alert-warning" data-forced hidden><?= e(t('profile.must_change')) ?></div>
    <div class="row g-4">
        <div class="col-lg-6">
            <form class="card" data-password-form novalidate>
                <div class="card-header bg-body fw-semibold"><?= e(t('profile.password')) ?></div>
                <div class="card-body">
                    <div class="mb-3">
                        <label class="form-label" for="current"><?= e(t('profile.current_password')) ?></label>
                        <input class="form-control" id="current" name="current" type="password" autocomplete="current-password">
                    </div>
                    <div class="mb-3">
                        <label class="form-label" for="new"><?= e(t('profile.new_password')) ?></label>
                        <input class="form-control" id="new" name="new" type="password" autocomplete="new-password" minlength="12">
                        <div class="form-text"><?= e(t('field.password_help')) ?></div>
                    </div>
                    <div>
                        <label class="form-label" for="new_confirm"><?= e(t('field.password_confirm')) ?></label>
                        <input class="form-control" id="new_confirm" name="new_confirm" type="password" autocomplete="new-password">
                    </div>
                </div>
                <div class="card-footer bg-body">
                    <button class="btn btn-primary" type="submit"><?= e(t('profile.change_password')) ?></button>
                </div>
            </form>
        </div>
        <div class="col-lg-6" data-settings-col hidden>
            <form class="card" data-profile-form novalidate>
                <div class="card-header bg-body fw-semibold"><?= e(t('profile.settings')) ?></div>
                <div class="card-body">
                    <p class="mb-3"><?= e(t('field.username')) ?>: <strong data-bind="username"></strong> · <span data-role></span></p>
                    <div class="mb-3">
                        <label class="form-label" for="email"><?= e(t('field.email')) ?></label>
                        <input class="form-control" id="email" name="email" type="email">
                        <div class="form-text"><?= e(t('profile.email_help')) ?></div>
                    </div>
                    <div>
                        <label class="form-label" for="locale"><?= e(t('user.language')) ?></label>
                        <select class="form-select" id="locale" name="locale"><?= select_options(I18n::LOCALES) ?></select>
                    </div>
                </div>
                <div class="card-footer bg-body">
                    <button class="btn btn-primary" type="submit"><?= e(t('common.save')) ?></button>
                </div>
            </form>
        </div>
    </div>
</div>
