<div id="system">
    <h1 class="h3 mb-4"><?= e(t('nav.system')) ?></h1>

    <div class="row g-4">
        <div class="col-lg-6">
            <div class="card mb-4">
                <div class="card-header bg-body fw-semibold"><?= e(t('system.info')) ?></div>
                <table class="table table-sm mb-0">
                    <tbody>
                    <tr><th><?= e(t('system.model')) ?></th><td data-bind="model"></td></tr>
                    <tr><th><?= e(t('system.version')) ?></th><td><span data-bind="version"></span> (UI <?= e(APP_VERSION) ?>)</td></tr>
                    <tr><th><?= e(t('system.addresses')) ?></th><td class="font-monospace small" data-addresses></td></tr>
                    <tr><th><?= e(t('system.uptime')) ?></th><td data-bind="uptime" data-format="duration"></td></tr>
                    <tr><th><?= e(t('system.disk')) ?></th><td data-disk></td></tr>
                    <tr><th><?= e(t('system.cpu_temp')) ?></th><td data-temp></td></tr>
                    </tbody>
                </table>
            </div>

            <form class="card" data-settings-form novalidate>
                <div class="card-header bg-body fw-semibold"><?= e(t('system.settings')) ?></div>
                <div class="card-body">
                    <div class="mb-3">
                        <label class="form-label" for="hostname"><?= e(t('system.hostname')) ?></label>
                        <input class="form-control" id="hostname" name="hostname" autocapitalize="none">
                        <div class="form-text"><?= e(t('system.hostname_help')) ?></div>
                    </div>
                    <div>
                        <label class="form-label" for="timezone"><?= e(t('system.timezone')) ?></label>
                        <select class="form-select" id="timezone" name="timezone"></select>
                    </div>
                </div>
                <div class="card-footer bg-body">
                    <button class="btn btn-primary" type="submit"><?= e(t('common.save')) ?></button>
                </div>
            </form>
        </div>

        <div class="col-lg-6">
            <div class="card mb-4">
                <div class="card-header bg-body fw-semibold"><?= e(t('target.public_key')) ?></div>
                <div class="card-body">
                    <div data-key-present hidden>
                        <textarea class="form-control font-monospace small mb-2" rows="3" readonly data-public-key
                                  aria-label="<?= e(t('target.public_key')) ?>"></textarea>
                        <p class="form-text"><?= e(t('target.public_key_help')) ?></p>
                        <button type="button" class="btn btn-outline-secondary btn-sm" data-action="regenerate_key"
                                data-confirm="<?= e(t('system.regenerate_key_confirm')) ?>"><?= e(t('system.regenerate_key')) ?></button>
                    </div>
                    <div data-key-missing hidden>
                        <p class="text-body-secondary"><?= e(t('system.no_key')) ?></p>
                        <button type="button" class="btn btn-outline-secondary btn-sm" data-action="generate_key"><?= e(t('target.generate_key')) ?></button>
                    </div>
                </div>
            </div>

            <div class="card mb-4">
                <div class="card-header bg-body fw-semibold"><?= e(t('system.power')) ?></div>
                <div class="card-body d-flex flex-wrap gap-2">
                    <button type="button" class="btn btn-outline-warning" data-action="reboot" data-confirm="<?= e(t('system.reboot_confirm')) ?>"><?= e(t('system.reboot')) ?></button>
                    <button type="button" class="btn btn-outline-danger" data-action="poweroff" data-confirm="<?= e(t('system.poweroff_confirm')) ?>"><?= e(t('system.poweroff')) ?></button>
                </div>
            </div>

            <div class="card border-danger">
                <div class="card-header bg-body fw-semibold text-danger"><?= e(t('system.setup_reset')) ?></div>
                <div class="card-body">
                    <p><?= e(t('system.setup_reset_text')) ?></p>
                    <div class="form-check mb-3">
                        <input class="form-check-input" type="checkbox" id="wipe_users" data-wipe-users>
                        <label class="form-check-label" for="wipe_users"><?= e(t('system.wipe_users')) ?></label>
                    </div>
                    <button type="button" class="btn btn-danger" data-action="setup_reset" data-confirm="<?= e(t('system.setup_reset_confirm')) ?>"><?= e(t('system.setup_reset')) ?></button>
                </div>
            </div>
        </div>
    </div>
</div>
