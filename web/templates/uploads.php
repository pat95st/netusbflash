<div class="d-flex flex-wrap justify-content-between align-items-center gap-2 mb-4">
    <h1 class="h3 mb-0"><?= e(t('nav.uploads')) ?></h1>
    <?php if (has_role('operator')): ?>
        <form method="post" action="/uploads">
            <?= csrf_field() ?>
            <button class="btn btn-outline-primary" name="action" value="retry_all"><?= e(t('upload.retry_all')) ?></button>
        </form>
    <?php endif; ?>
</div>

<ul class="nav nav-pills mb-3">
    <?php foreach (['' => t('upload.filter_all'), 'pending' => t('upload.status_pending'), 'failed' => t('upload.status_failed'), 'done' => t('upload.status_done')] as $key => $label): ?>
        <li class="nav-item"><a class="nav-link<?= $filter === $key ? ' active' : '' ?>" href="/uploads<?= $key !== '' ? '?status=' . e($key) : '' ?>"><?= e($label) ?></a></li>
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
            <tbody>
            <?php foreach ($uploads as $u): ?>
                <tr>
                    <td class="text-break">
                        <?= e($u['path']) ?>
                        <div class="small text-body-secondary font-monospace text-break"><?= e($u['remote_path']) ?></div>
                        <?php if ($u['last_error'] !== ''): ?>
                            <div class="small text-danger text-break"><?= e($u['last_error']) ?></div>
                        <?php endif; ?>
                    </td>
                    <td><?= e($u['target']) ?></td>
                    <td class="text-nowrap">
                        <?= upload_status_badge($u['status']) ?>
                        <?php if ($u['attempts'] > 0 && $u['status'] !== 'done'): ?>
                            <div class="small text-body-secondary"><?= e(t('upload.attempts', ['n' => $u['attempts']])) ?></div>
                        <?php endif; ?>
                    </td>
                    <td class="text-end text-nowrap"><?= e(fmt_bytes($u['size'])) ?></td>
                    <td class="small text-nowrap"><?= e(fmt_time($u['finished_at'] ?? $u['created_at'])) ?></td>
                    <td class="text-end text-nowrap">
                        <?php if ($u['status'] === 'failed'): ?>
                            <form method="post" action="/uploads" class="d-inline">
                                <?= csrf_field() ?>
                                <input type="hidden" name="id" value="<?= e($u['id']) ?>">
                                <?php if (has_role('operator')): ?>
                                    <button class="btn btn-sm btn-outline-primary" name="action" value="retry"><?= e(t('upload.retry')) ?></button>
                                <?php endif; ?>
                                <?php if (has_role('manager')): ?>
                                    <button class="btn btn-sm btn-outline-danger" name="action" value="discard" data-confirm="<?= e(t('upload.discard_confirm')) ?>"><?= e(t('upload.discard')) ?></button>
                                <?php endif; ?>
                            </form>
                        <?php endif; ?>
                    </td>
                </tr>
            <?php endforeach; ?>
            <?php if (!$uploads): ?>
                <tr><td colspan="6" class="text-body-secondary p-3"><?= e(t('upload.none')) ?></td></tr>
            <?php endif; ?>
            </tbody>
        </table>
    </div>
</div>
