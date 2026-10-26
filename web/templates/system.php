<h1 class="h3 mb-4"><?= e(t('nav.system')) ?></h1>

<div class="row g-4">
    <div class="col-lg-6">
        <div class="card mb-4">
            <div class="card-header bg-body fw-semibold"><?= e(t('system.info')) ?></div>
            <table class="table table-sm mb-0">
                <tbody>
                <tr><th><?= e(t('system.model')) ?></th><td><?= e($sys['model']) ?></td></tr>
                <tr><th><?= e(t('system.version')) ?></th><td><?= e($s['version']) ?> (UI <?= e(APP_VERSION) ?>)</td></tr>
                <tr><th><?= e(t('system.addresses')) ?></th><td class="font-monospace small"><?= e(implode(', ', $s['addresses'])) ?></td></tr>
                <tr><th><?= e(t('system.uptime')) ?></th><td><?= e(fmt_duration($s['uptime'])) ?></td></tr>
                <tr><th><?= e(t('system.disk')) ?></th><td><?= e(t('dashboard.disk', ['free' => fmt_bytes($s['disk']['free']), 'total' => fmt_bytes($s['disk']['total'])])) ?></td></tr>
                <tr><th><?= e(t('system.cpu_temp')) ?></th><td><?= $s['cpu_temp'] !== null ? e(number_format((float) $s['cpu_temp'], 1)) . ' °C' : '–' ?></td></tr>
                </tbody>
            </table>
        </div>

        <form method="post" action="/system" novalidate class="card">
            <?= csrf_field() ?>
            <div class="card-header bg-body fw-semibold"><?= e(t('system.settings')) ?></div>
            <div class="card-body">
                <div class="mb-3">
                    <label class="form-label" for="hostname"><?= e(t('system.hostname')) ?></label>
                    <input class="form-control<?= invalid($errors, 'hostname') ?>" id="hostname" name="hostname" value="<?= e($v['hostname']) ?>" autocapitalize="none">
                    <?= feedback($errors, 'hostname') ?>
                    <div class="form-text"><?= e(t('system.hostname_help')) ?></div>
                </div>
                <div>
                    <label class="form-label" for="timezone"><?= e(t('system.timezone')) ?></label>
                    <select class="form-select<?= invalid($errors, 'timezone') ?>" id="timezone" name="timezone">
                        <?= select_options(array_combine($sys['timezones'], $sys['timezones']), $v['timezone']) ?>
                    </select>
                    <?= feedback($errors, 'timezone') ?>
                </div>
            </div>
            <div class="card-footer bg-body">
                <button class="btn btn-primary" name="action" value="save"><?= e(t('common.save')) ?></button>
            </div>
        </form>
    </div>

    <div class="col-lg-6">
        <div class="card mb-4">
            <div class="card-header bg-body fw-semibold"><?= e(t('target.public_key')) ?></div>
            <div class="card-body">
                <?php if ($sshKey !== ''): ?>
                    <textarea class="form-control font-monospace small mb-2" rows="3" readonly aria-label="<?= e(t('target.public_key')) ?>"><?= e($sshKey) ?></textarea>
                    <p class="form-text"><?= e(t('target.public_key_help')) ?></p>
                <?php else: ?>
                    <p class="text-body-secondary"><?= e(t('system.no_key')) ?></p>
                <?php endif; ?>
                <form method="post" action="/system">
                    <?= csrf_field() ?>
                    <button class="btn btn-outline-secondary btn-sm" name="action" value="regenerate_key"
                        <?= $sshKey !== '' ? 'data-confirm="' . e(t('system.regenerate_key_confirm')) . '"' : '' ?>>
                        <?= e($sshKey !== '' ? t('system.regenerate_key') : t('target.generate_key')) ?>
                    </button>
                </form>
            </div>
        </div>

        <form method="post" action="/system" class="card mb-4">
            <?= csrf_field() ?>
            <div class="card-header bg-body fw-semibold"><?= e(t('system.power')) ?></div>
            <div class="card-body d-flex flex-wrap gap-2">
                <button class="btn btn-outline-warning" name="action" value="reboot" data-confirm="<?= e(t('system.reboot_confirm')) ?>"><?= e(t('system.reboot')) ?></button>
                <button class="btn btn-outline-danger" name="action" value="poweroff" data-confirm="<?= e(t('system.poweroff_confirm')) ?>"><?= e(t('system.poweroff')) ?></button>
            </div>
        </form>

        <form method="post" action="/system" class="card border-danger">
            <?= csrf_field() ?>
            <div class="card-header bg-body fw-semibold text-danger"><?= e(t('system.setup_reset')) ?></div>
            <div class="card-body">
                <p><?= e(t('system.setup_reset_text')) ?></p>
                <div class="form-check mb-3">
                    <input class="form-check-input" type="checkbox" id="wipe_users" name="wipe_users" value="1">
                    <label class="form-check-label" for="wipe_users"><?= e(t('system.wipe_users')) ?></label>
                </div>
                <button class="btn btn-danger" name="action" value="setup_reset" data-confirm="<?= e(t('system.setup_reset_confirm')) ?>"><?= e(t('system.setup_reset')) ?></button>
            </div>
        </form>
    </div>
</div>
