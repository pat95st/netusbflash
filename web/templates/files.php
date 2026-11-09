<div id="files" data-can-edit="<?= has_role('manager') ? '1' : '0' ?>">
    <div class="d-flex flex-wrap justify-content-between align-items-center gap-2 mb-3">
        <h1 class="h3 mb-0"><?= e(t('nav.files')) ?></h1>
        <div class="d-flex flex-wrap gap-2" data-controls>
            <div class="btn-group" role="group" aria-label="<?= e(t('files.mode')) ?>">
                <button type="button" class="btn btn-outline-primary" data-mode="view">
                    <i class="bi bi-eye" aria-hidden="true"></i> <?= e(t('files.mode_view')) ?>
                </button>
                <?php if (has_role('manager')): ?>
                <button type="button" class="btn btn-outline-warning" data-mode="edit"
                        data-confirm="<?= e(t('files.edit_confirm')) ?>">
                    <i class="bi bi-pencil" aria-hidden="true"></i> <?= e(t('files.mode_edit')) ?>
                </button>
                <?php endif; ?>
                <button type="button" class="btn btn-outline-secondary" data-mode="off">
                    <i class="bi bi-x-lg" aria-hidden="true"></i> <?= e(t('files.mode_off')) ?>
                </button>
            </div>
            <button type="button" class="btn btn-outline-secondary" data-action="refresh" title="<?= e(t('files.refresh_help')) ?>">
                <i class="bi bi-arrow-clockwise" aria-hidden="true"></i> <?= e(t('files.refresh')) ?>
            </button>
        </div>
    </div>

    <div class="alert alert-info d-flex flex-wrap align-items-center gap-2" data-state-view hidden>
        <i class="bi bi-eye" aria-hidden="true"></i>
        <span><?= e(t('files.view_info')) ?></span>
    </div>
    <div class="alert alert-warning d-flex flex-wrap align-items-center gap-2" data-state-edit hidden>
        <i class="bi bi-pencil" aria-hidden="true"></i>
        <span><?= e(t('files.edit_info')) ?></span>
        <span class="ms-auto fw-semibold" data-countdown></span>
    </div>
    <div class="alert alert-secondary" data-no-image hidden><?= e(t('files.no_image')) ?></div>

    <div class="card" data-state-off hidden>
        <div class="card-body text-center py-5">
            <i class="bi bi-folder2-open display-5 text-body-secondary" aria-hidden="true"></i>
            <p class="mt-3 mb-4 text-body-secondary"><?= e(t('files.off_info')) ?></p>
            <button type="button" class="btn btn-primary" data-mode="view"><?= e(t('files.open')) ?></button>
        </div>
    </div>

    <div class="fm-frame-wrap card" data-frame-wrap hidden>
        <iframe class="fm-frame" data-frame title="<?= e(t('nav.files')) ?>" src="about:blank"></iframe>
        <div class="loading-overlay" data-frame-loading hidden>
            <div class="d-flex flex-column align-items-center gap-2">
                <div class="spinner-border text-primary" aria-hidden="true"></div>
                <span class="small text-body-secondary"><?= e(t('common.loading')) ?></span>
            </div>
        </div>
    </div>
</div>
