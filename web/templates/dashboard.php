<div id="dashboard">
    <div class="d-flex flex-wrap justify-content-between align-items-center gap-2 mb-4">
        <h1 class="h3 mb-0"><?= e(t('nav.dashboard')) ?></h1>
        <?php if (has_role('operator')): ?>
            <button class="btn btn-primary" type="button" data-action="sync">
                <i class="bi bi-arrow-repeat" aria-hidden="true"></i> <?= e(t('usb.sync_now')) ?>
            </button>
        <?php endif; ?>
    </div>

    <div data-status>
    <div class="alert alert-info small" data-bind-show="simulated" hidden><?= e(t('common.simulation_notice')) ?></div>
    <div class="alert alert-warning" data-usb-unavailable hidden></div>
    <div class="alert alert-warning d-flex justify-content-between align-items-center flex-wrap gap-2" data-no-targets hidden>
        <span><?= e(t('dashboard.no_targets')) ?></span>
        <?php if (has_role('manager')): ?><a class="btn btn-sm btn-warning" href="/targets/new"><?= e(t('target.add')) ?></a><?php endif; ?>
    </div>

    <div class="row g-3 mb-4">
        <div class="col-md-6 col-xl-3">
            <div class="card h-100"><div class="card-body">
                <div class="text-body-secondary small mb-1"><?= e(t('dashboard.usb_stick')) ?></div>
                <div class="fs-5 fw-semibold"><span class="badge text-bg-secondary" data-usb-state>–</span></div>
                <div class="small text-body-secondary mt-2" data-monitor>–</div>
            </div></div>
        </div>
        <div class="col-md-6 col-xl-3">
            <div class="card h-100"><div class="card-body">
                <div class="text-body-secondary small mb-1"><?= e(t('dashboard.uploads')) ?></div>
                <div class="d-flex gap-4">
                    <div><div class="fs-5 fw-semibold text-info" data-bind="uploads.pending">–</div><div class="small text-body-secondary"><?= e(t('upload.status_pending')) ?></div></div>
                    <div><div class="fs-5 fw-semibold text-danger" data-bind="uploads.failed">–</div><div class="small text-body-secondary"><?= e(t('upload.status_failed')) ?></div></div>
                    <div><div class="fs-5 fw-semibold text-success" data-bind="uploads.done">–</div><div class="small text-body-secondary"><?= e(t('upload.status_done')) ?></div></div>
                </div>
                <div class="small text-body-secondary mt-2 text-truncate" data-current-upload>–</div>
            </div></div>
        </div>
        <div class="col-md-6 col-xl-3">
            <div class="card h-100"><div class="card-body">
                <div class="text-body-secondary small mb-1"><?= e(t('dashboard.last_sync')) ?></div>
                <div class="fs-6 fw-semibold" data-bind="usb.last_sync.time" data-format="time">–</div>
                <div class="small text-body-secondary mt-2" data-sync-counts></div>
            </div></div>
        </div>
        <div class="col-md-6 col-xl-3">
            <div class="card h-100"><div class="card-body">
                <div class="text-body-secondary small mb-1"><?= e(t('dashboard.system')) ?></div>
                <div class="small">
                    <span data-bind="hostname">–</span> · <span data-cpu-temp>–</span><br>
                    <span data-disk>–</span>
                </div>
                <div class="progress mt-2" role="progressbar" aria-valuemin="0" aria-valuemax="100">
                    <div class="progress-bar" data-disk-bar></div>
                </div>
            </div></div>
        </div>
    </div>

    </div>

    <div class="row g-3">
        <div class="col-lg-7">
            <div class="card h-100">
                <div class="card-header bg-body d-flex justify-content-between align-items-center">
                    <span class="fw-semibold"><?= e(t('dashboard.recent_files')) ?></span>
                    <a href="/usb#files" class="small"><?= e(t('common.show_all')) ?></a>
                </div>
                <div class="table-responsive">
                    <table class="table table-sm mb-0 align-middle">
                        <tbody data-events>
                            <tr data-empty hidden><td class="text-body-secondary p-3"><?= e(t('dashboard.no_files')) ?></td></tr>
                            <template data-row>
                                <tr>
                                    <td class="text-nowrap small text-body-secondary" data-bind="time" data-format="time"></td>
                                    <td><span class="badge text-bg-light border" data-event></span></td>
                                    <td class="text-break" data-bind="path"></td>
                                    <td class="text-end small text-nowrap" data-bind="size" data-format="bytes"></td>
                                </tr>
                            </template>
                        </tbody>
                    </table>
                </div>
            </div>
        </div>
        <div class="col-lg-5">
            <div class="card h-100">
                <div class="card-header bg-body d-flex justify-content-between align-items-center">
                    <span class="fw-semibold"><?= e(t('dashboard.failed_uploads')) ?></span>
                    <a href="/uploads?status=failed" class="small"><?= e(t('common.show_all')) ?></a>
                </div>
                <ul class="list-group list-group-flush" data-failed>
                    <li class="list-group-item text-body-secondary small" data-empty hidden><?= e(t('dashboard.no_failed')) ?></li>
                    <template data-row>
                        <li class="list-group-item small">
                            <div class="fw-semibold text-break"><span data-bind="path"></span> → <span data-bind="target"></span></div>
                            <div class="text-danger text-break" data-bind="last_error"></div>
                        </li>
                    </template>
                </ul>
            </div>
        </div>
    </div>
</div>
