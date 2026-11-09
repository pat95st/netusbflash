<div id="logs">
    <div class="d-flex flex-wrap justify-content-between align-items-center gap-2 mb-4">
        <h1 class="h3 mb-0"><?= e(t('nav.logs')) ?></h1>
        <div class="d-flex gap-2">
            <button type="button" class="btn btn-outline-secondary" data-action="refresh"><i class="bi bi-arrow-clockwise" aria-hidden="true"></i> <?= e(t('logs.refresh')) ?></button>
            <a class="btn btn-outline-secondary" href="/logs?download=1" data-download><i class="bi bi-download" aria-hidden="true"></i> <?= e(t('logs.download')) ?></a>
        </div>
    </div>

    <ul class="nav nav-tabs mb-3">
        <li class="nav-item"><a class="nav-link" href="/logs" data-tab="events"><?= e(t('logs.events')) ?></a></li>
        <?php if (has_role('admin')): ?>
            <li class="nav-item"><a class="nav-link" href="/logs?tab=audit" data-tab="audit"><?= e(t('logs.audit')) ?></a></li>
        <?php endif; ?>
    </ul>

    <div class="btn-group btn-group-sm mb-3" role="group" data-levels>
        <?php foreach (['' => t('logs.all'), 'info' => t('logs.info'), 'warning' => t('logs.warning'), 'error' => t('logs.error')] as $key => $label): ?>
            <a class="btn btn-outline-secondary" href="/logs<?= $key !== '' ? '?level=' . e($key) : '' ?>" data-level="<?= e($key) ?>"><?= e($label) ?></a>
        <?php endforeach; ?>
    </div>

    <div class="card">
        <div class="table-responsive">
            <table class="table table-sm mb-0 align-middle">
                <tbody data-events hidden>
                    <tr data-empty hidden><td class="text-body-secondary p-3"><?= e(t('logs.none')) ?></td></tr>
                    <template data-row>
                        <tr>
                            <td class="text-nowrap small text-body-secondary" data-bind="time" data-format="time"></td>
                            <td><span class="badge" data-level-badge></span></td>
                            <td class="small text-body-secondary" data-bind="source"></td>
                            <td class="small text-break" data-bind="message"></td>
                        </tr>
                    </template>
                </tbody>
                <tbody data-audit hidden>
                    <tr data-empty hidden><td class="text-body-secondary p-3"><?= e(t('logs.none')) ?></td></tr>
                    <template data-row>
                        <tr>
                            <td class="text-nowrap small text-body-secondary" data-bind="time" data-format="time"></td>
                            <td class="small fw-semibold" data-bind="username"></td>
                            <td class="small font-monospace" data-bind="action"></td>
                            <td class="small text-break" data-details></td>
                        </tr>
                    </template>
                </tbody>
            </table>
        </div>
    </div>
    <p class="small text-body-secondary mt-2"><?= e(t('logs.note')) ?></p>
</div>
