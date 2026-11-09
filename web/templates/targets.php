<div id="targets">
    <div class="d-flex flex-wrap justify-content-between align-items-center gap-2 mb-4">
        <h1 class="h3 mb-0"><?= e(t('nav.targets')) ?></h1>
        <?php if (has_role('manager')): ?>
            <a class="btn btn-primary" href="/targets/new"><i class="bi bi-plus-lg" aria-hidden="true"></i> <?= e(t('target.add')) ?></a>
        <?php endif; ?>
    </div>
    <p class="text-body-secondary"><?= e(t('target.intro')) ?></p>

    <div data-test-result></div>

    <div class="card">
        <div class="table-responsive">
            <table class="table table-hover align-middle mb-0">
                <thead><tr>
                    <th><?= e(t('target.name')) ?></th>
                    <th><?= e(t('target.protocol')) ?></th>
                    <th><?= e(t('target.destination')) ?></th>
                    <th class="text-center"><?= e(t('dashboard.uploads')) ?></th>
                    <th></th>
                </tr></thead>
                <tbody data-targets>
                    <tr data-empty hidden><td colspan="5" class="text-body-secondary p-3"><?= e(t('target.none')) ?></td></tr>
                    <template data-row>
                        <tr>
                            <td class="fw-semibold">
                                <span data-bind="name"></span>
                                <span class="badge text-bg-secondary ms-1" data-bind-hide="enabled"><?= e(t('common.disabled')) ?></span>
                            </td>
                            <td data-protocol></td>
                            <td class="small text-break font-monospace" data-destination></td>
                            <td class="text-center text-nowrap small">
                                <span class="text-info" data-bind="uploads.pending"></span> /
                                <span class="text-danger" data-bind="uploads.failed"></span> /
                                <span class="text-success" data-bind="uploads.done"></span>
                            </td>
                            <td class="text-end text-nowrap" data-row-actions>
                                <?php if (has_role('manager')): ?>
                                    <button type="button" class="btn btn-sm btn-outline-secondary" data-action="test"><?= e(t('target.test')) ?></button>
                                    <a class="btn btn-sm btn-outline-primary" data-edit><?= e(t('common.edit')) ?></a>
                                    <button type="button" class="btn btn-sm btn-outline-danger" data-action="delete"><?= e(t('common.delete')) ?></button>
                                <?php else: ?>
                                    <a class="btn btn-sm btn-outline-secondary" data-edit><?= e(t('common.show')) ?></a>
                                <?php endif; ?>
                            </td>
                        </tr>
                    </template>
                </tbody>
            </table>
        </div>
    </div>
    <p class="small text-body-secondary mt-2"><?= e(t('target.counts_legend')) ?></p>
</div>
