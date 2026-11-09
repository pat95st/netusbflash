<div id="uploads">
    <div class="d-flex flex-wrap justify-content-between align-items-center gap-2 mb-4">
        <h1 class="h3 mb-0"><?= e(t('nav.uploads')) ?></h1>
        <?php if (has_role('operator')): ?>
            <button class="btn btn-outline-primary" type="button" data-action="retry_all"><?= e(t('upload.retry_all')) ?></button>
        <?php endif; ?>
    </div>

    <ul class="nav nav-pills mb-3" data-filters>
        <?php foreach (['' => t('upload.filter_all'), 'pending' => t('upload.status_pending'), 'failed' => t('upload.status_failed'), 'done' => t('upload.status_done')] as $key => $label): ?>
            <li class="nav-item"><a class="nav-link" href="/uploads<?= $key !== '' ? '?status=' . e($key) : '' ?>" data-filter="<?= e($key) ?>"><?= e($label) ?></a></li>
        <?php endforeach; ?>
    </ul>

    <div class="card">
        <div class="table-responsive">
            <table class="table table-sm table-hover align-middle mb-0">
                <thead><tr>
                    <th><?= e(t('usb.file')) ?></th>
                    <th><?= e(t('upload.target')) ?></th>
                    <th><?= e(t('upload.status')) ?></th>
                    <th class="text-end"><?= e(t('usb.size')) ?></th>
                    <th><?= e(t('upload.time')) ?></th>
                    <th></th>
                </tr></thead>
                <tbody data-uploads>
                    <tr data-empty hidden><td colspan="6" class="text-body-secondary p-3"><?= e(t('upload.none')) ?></td></tr>
                    <template data-row>
                        <tr>
                            <td class="text-break">
                                <span data-bind="path"></span>
                                <div class="small text-body-secondary font-monospace text-break" data-bind="remote_path"></div>
                                <div class="small text-danger text-break" data-bind="last_error" data-bind-show="last_error"></div>
                            </td>
                            <td data-bind="target"></td>
                            <td class="text-nowrap">
                                <span class="badge" data-status></span>
                                <div class="small text-body-secondary" data-attempts></div>
                            </td>
                            <td class="text-end text-nowrap" data-bind="size" data-format="bytes"></td>
                            <td class="small text-nowrap" data-time></td>
                            <td class="text-end text-nowrap" data-row-actions>
                                <?php if (has_role('operator')): ?>
                                    <button type="button" class="btn btn-sm btn-outline-primary" data-action="retry" hidden><?= e(t('upload.retry')) ?></button>
                                <?php endif; ?>
                                <?php if (has_role('manager')): ?>
                                    <button type="button" class="btn btn-sm btn-outline-danger" data-action="discard" data-confirm="<?= e(t('upload.discard_confirm')) ?>" hidden><?= e(t('upload.discard')) ?></button>
                                <?php endif; ?>
                            </td>
                        </tr>
                    </template>
                </tbody>
            </table>
        </div>
    </div>
</div>
