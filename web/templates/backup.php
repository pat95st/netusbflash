<div id="backup">
    <h1 class="h3 mb-2"><?= e(t('nav.backup')) ?></h1>
    <p class="text-body-secondary mb-4"><?= e(t('backup.intro')) ?></p>

    <div class="row g-4">
        <div class="col-lg-6">
            <form class="card mb-4" data-download-form novalidate>
                <div class="card-header bg-body fw-semibold d-flex align-items-center gap-2">
                    <i class="bi bi-download" aria-hidden="true"></i> <?= e(t('backup.download')) ?>
                </div>
                <div class="card-body">
                    <label class="form-label" for="download_passphrase"><?= e(t('backup.passphrase')) ?></label>
                    <input class="form-control" id="download_passphrase" name="passphrase" type="password" autocomplete="new-password" minlength="8">
                    <div class="form-text"><?= e(t('backup.passphrase_help')) ?></div>
                </div>
                <div class="card-footer bg-body">
                    <button class="btn btn-primary" type="submit"><?= e(t('backup.download_button')) ?></button>
                </div>
            </form>

            <form class="card border-danger-subtle" data-restore-form novalidate>
                <div class="card-header bg-body fw-semibold d-flex align-items-center gap-2">
                    <i class="bi bi-upload" aria-hidden="true"></i> <?= e(t('backup.restore')) ?>
                </div>
                <div class="card-body">
                    <p class="small text-body-secondary"><?= e(t('backup.restore_help')) ?></p>
                    <div class="mb-3">
                        <label class="form-label" for="restore_file"><?= e(t('backup.file')) ?></label>
                        <input class="form-control" id="restore_file" type="file" accept=".json,application/json" data-restore-file data-error-for="backup">
                    </div>
                    <div>
                        <label class="form-label" for="restore_passphrase"><?= e(t('backup.passphrase')) ?></label>
                        <input class="form-control" id="restore_passphrase" name="passphrase" type="password" autocomplete="off">
                        <div class="form-text"><?= e(t('backup.restore_passphrase_help')) ?></div>
                    </div>
                </div>
                <div class="card-footer bg-body">
                    <button class="btn btn-danger" type="submit" data-confirm="<?= e(t('backup.restore_confirm')) ?>"><?= e(t('backup.restore_button')) ?></button>
                </div>
            </form>
        </div>

        <div class="col-lg-6">
            <form class="card" data-schedule-form novalidate>
                <div class="card-header bg-body fw-semibold d-flex align-items-center gap-2">
                    <i class="bi bi-clock-history" aria-hidden="true"></i> <?= e(t('backup.scheduled')) ?>
                </div>
                <div class="card-body">
                    <div class="form-check form-switch mb-3">
                        <input class="form-check-input" type="checkbox" role="switch" id="backup_enabled" name="enabled">
                        <label class="form-check-label" for="backup_enabled"><?= e(t('backup.enabled')) ?></label>
                    </div>
                    <div class="alert alert-secondary small" data-no-targets hidden>
                        <?= e(t('backup.no_targets')) ?> <a href="/targets"><?= e(t('nav.targets')) ?></a>
                    </div>
                    <div class="row g-3">
                        <div class="col-md-6">
                            <label class="form-label" for="backup_target"><?= e(t('backup.target')) ?></label>
                            <select class="form-select" id="backup_target" name="target_id" data-type="int"></select>
                        </div>
                        <div class="col-md-6">
                            <label class="form-label" for="backup_directory"><?= e(t('backup.directory')) ?></label>
                            <input class="form-control font-monospace" id="backup_directory" name="directory" autocapitalize="none" spellcheck="false">
                            <div class="form-text"><?= e(t('backup.directory_help')) ?></div>
                        </div>
                        <div class="col-md-6">
                            <label class="form-label" for="backup_interval"><?= e(t('backup.interval')) ?></label>
                            <select class="form-select" id="backup_interval" name="interval">
                                <option value="daily"><?= e(t('backup.daily')) ?></option>
                                <option value="weekly"><?= e(t('backup.weekly')) ?></option>
                                <option value="monthly"><?= e(t('backup.monthly')) ?></option>
                            </select>
                        </div>
                        <div class="col-md-6">
                            <label class="form-label" for="backup_hour"><?= e(t('backup.hour')) ?></label>
                            <select class="form-select" id="backup_hour" name="hour" data-type="int">
                                <?php for ($h = 0; $h < 24; $h++): ?>
                                    <option value="<?= $h ?>"><?= sprintf('%02d:00', $h) ?></option>
                                <?php endfor; ?>
                            </select>
                        </div>
                        <div class="col-12">
                            <label class="form-label" for="backup_passphrase"><?= e(t('backup.passphrase')) ?></label>
                            <input class="form-control" id="backup_passphrase" name="passphrase" type="password" autocomplete="new-password"
                                   data-placeholder-saved="<?= e(t('backup.passphrase_keep')) ?>">
                            <div class="form-text"><?= e(t('backup.schedule_passphrase_help')) ?></div>
                            <div class="form-check mt-1" data-saved-passphrase hidden>
                                <input class="form-check-input" type="checkbox" id="clear_passphrase" name="clear_passphrase">
                                <label class="form-check-label small" for="clear_passphrase"><?= e(t('backup.clear_passphrase')) ?></label>
                            </div>
                        </div>
                    </div>

                    <table class="table table-sm mt-4 mb-0">
                        <tbody>
                        <tr><th><?= e(t('backup.last_run')) ?></th><td data-last-run>–</td></tr>
                        <tr><th><?= e(t('backup.last_success')) ?></th><td data-last-success>–</td></tr>
                        <tr><th><?= e(t('backup.next_run')) ?></th><td data-next-run>–</td></tr>
                        </tbody>
                    </table>
                </div>
                <div class="card-footer bg-body d-flex flex-wrap gap-2">
                    <button class="btn btn-primary" type="submit"><?= e(t('common.save')) ?></button>
                    <button class="btn btn-outline-secondary" type="button" data-action="run"><?= e(t('backup.run_now')) ?></button>
                </div>
            </form>
        </div>
    </div>
</div>
