<div id="updates">
    <h1 class="h3 mb-4"><?= e(t('nav.updates')) ?></h1>

    <div class="alert alert-warning d-flex flex-wrap align-items-center gap-2" data-reboot-required hidden>
        <i class="bi bi-arrow-repeat" aria-hidden="true"></i>
        <span><?= e(t('update.reboot_required')) ?></span>
        <button type="button" class="btn btn-sm btn-warning ms-auto" data-action="reboot"
                data-confirm="<?= e(t('system.reboot_confirm')) ?>"><?= e(t('system.reboot')) ?></button>
    </div>
    <div class="alert alert-info" data-simulated hidden><?= e(t('update.simulated')) ?></div>

    <div class="row g-4">
        <div class="col-lg-6">
            <div class="card mb-4">
                <div class="card-header bg-body fw-semibold d-flex align-items-center gap-2">
                    <i class="bi bi-box-seam" aria-hidden="true"></i> <?= e(t('update.software')) ?>
                </div>
                <div class="card-body">
                    <table class="table table-sm mb-3">
                        <tbody>
                        <tr><th><?= e(t('update.installed')) ?></th><td class="font-monospace" data-bind="current"></td></tr>
                        <tr><th><?= e(t('update.latest')) ?></th>
                            <td>
                                <span class="font-monospace" data-latest-version>–</span>
                                <span class="badge text-bg-warning" data-latest-pre hidden><?= e(t('update.prerelease')) ?></span>
                                <span class="badge text-bg-success" data-up-to-date hidden><?= e(t('update.up_to_date')) ?></span>
                                <span class="badge text-bg-primary" data-available hidden><?= e(t('update.available')) ?></span>
                            </td>
                        </tr>
                        <tr><th><?= e(t('update.published')) ?></th><td data-published>–</td></tr>
                        <tr><th><?= e(t('update.last_check')) ?></th><td data-bind="last_check" data-format="time"></td></tr>
                        </tbody>
                    </table>
                    <div class="alert alert-danger small" data-check-error hidden></div>
                    <div data-notes-box hidden>
                        <div class="d-flex justify-content-between align-items-center mb-1">
                            <span class="small fw-semibold" data-release-name></span>
                            <a class="small" href="#" target="_blank" rel="noopener noreferrer" data-release-url><?= e(t('update.on_github')) ?> <i class="bi bi-box-arrow-up-right" aria-hidden="true"></i></a>
                        </div>
                        <pre class="release-notes border rounded p-2 bg-body-tertiary mb-0" data-release-notes></pre>
                    </div>
                </div>
                <div class="card-footer bg-body d-flex flex-wrap gap-2">
                    <button type="button" class="btn btn-outline-secondary" data-action="check">
                        <i class="bi bi-search" aria-hidden="true"></i> <?= e(t('update.check')) ?>
                    </button>
                    <button type="button" class="btn btn-primary" data-action="software" hidden
                            data-confirm="<?= e(t('update.software_confirm')) ?>">
                        <i class="bi bi-download" aria-hidden="true"></i> <span data-install-label></span>
                    </button>
                </div>
            </div>

            <form class="card" data-settings-form novalidate>
                <div class="card-header bg-body fw-semibold"><?= e(t('update.settings')) ?></div>
                <div class="card-body">
                    <div class="mb-3">
                        <label class="form-label" for="repository"><?= e(t('update.repository')) ?></label>
                        <input class="form-control font-monospace" id="repository" name="repository" autocapitalize="none" spellcheck="false" placeholder="owner/repository">
                        <div class="form-text"><?= e(t('update.repository_help')) ?></div>
                    </div>
                    <div class="form-check form-switch mb-2">
                        <input class="form-check-input" type="checkbox" role="switch" id="prereleases" name="prereleases">
                        <label class="form-check-label" for="prereleases"><?= e(t('update.prereleases')) ?></label>
                    </div>
                    <div class="form-check form-switch">
                        <input class="form-check-input" type="checkbox" role="switch" id="auto_check" name="auto_check">
                        <label class="form-check-label" for="auto_check"><?= e(t('update.auto_check')) ?></label>
                    </div>
                </div>
                <div class="card-footer bg-body">
                    <button class="btn btn-primary" type="submit"><?= e(t('common.save')) ?></button>
                </div>
            </form>
        </div>

        <div class="col-lg-6">
            <div class="card mb-4">
                <div class="card-header bg-body fw-semibold d-flex align-items-center gap-2">
                    <i class="bi bi-cpu" aria-hidden="true"></i> <?= e(t('update.os')) ?>
                </div>
                <div class="card-body">
                    <p class="text-body-secondary small"><?= e(t('update.os_help')) ?></p>
                    <table class="table table-sm mb-2">
                        <tbody>
                        <tr><th><?= e(t('update.last_check')) ?></th><td data-os-checked>–</td></tr>
                        <tr><th><?= e(t('update.os_packages')) ?></th><td data-os-count>–</td></tr>
                        </tbody>
                    </table>
                    <div class="alert alert-danger small" data-os-error hidden></div>
                    <details data-os-list-box hidden>
                        <summary class="small"><?= e(t('update.os_show_packages')) ?></summary>
                        <div class="small font-monospace mt-2" data-os-list></div>
                    </details>
                </div>
                <div class="card-footer bg-body d-flex flex-wrap gap-2">
                    <button type="button" class="btn btn-outline-secondary" data-action="os-check">
                        <span class="spinner-border spinner-border-sm" data-os-checking hidden aria-hidden="true"></span>
                        <i class="bi bi-search" aria-hidden="true"></i> <?= e(t('update.os_check')) ?>
                    </button>
                    <button type="button" class="btn btn-primary" data-action="os"
                            data-confirm="<?= e(t('update.os_confirm')) ?>">
                        <i class="bi bi-download" aria-hidden="true"></i> <?= e(t('update.os_install')) ?>
                    </button>
                </div>
            </div>

            <div class="card">
                <div class="card-header bg-body fw-semibold d-flex align-items-center gap-2">
                    <span><?= e(t('update.log')) ?></span>
                    <span class="badge text-bg-info" data-job-running hidden>
                        <span class="spinner-border spinner-border-sm me-1" aria-hidden="true"></span><span data-job-label></span>
                    </span>
                    <span class="badge text-bg-secondary" data-job-done hidden></span>
                </div>
                <div class="card-body">
                    <p class="text-body-secondary small mb-0" data-no-log><?= e(t('update.no_log')) ?></p>
                    <pre class="update-log border rounded p-2 bg-body-tertiary mb-0" data-log hidden></pre>
                </div>
            </div>
        </div>
    </div>
</div>
