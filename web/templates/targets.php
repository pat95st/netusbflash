<div class="d-flex flex-wrap justify-content-between align-items-center gap-2 mb-4">
    <h1 class="h3 mb-0"><?= e(t('nav.targets')) ?></h1>
    <?php if (has_role('manager')): ?>
        <a class="btn btn-primary" href="/targets/new"><i class="bi bi-plus-lg" aria-hidden="true"></i> <?= e(t('target.add')) ?></a>
    <?php endif; ?>
</div>
<p class="text-body-secondary"><?= e(t('target.intro')) ?></p>

<?php if ($testResult !== null): ?>
    <h2 class="h6"><?= e(t('target.test_result_for', ['name' => $testedName])) ?></h2>
    <?php require __DIR__ . '/partials/test_result.php'; ?>
<?php endif; ?>

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
            <tbody>
            <?php foreach ($targets as $tg): ?>
                <tr class="<?= $tg['enabled'] ? '' : 'text-body-secondary' ?>">
                    <td class="fw-semibold">
                        <?= e($tg['name']) ?>
                        <?php if (!$tg['enabled']): ?><span class="badge text-bg-secondary ms-1"><?= e(t('common.disabled')) ?></span><?php endif; ?>
                    </td>
                    <td><?= e(t('protocol.' . $tg['protocol'])) ?></td>
                    <td class="small text-break font-monospace"><?= e(trim(($tg['host'] ? $tg['host'] . ($tg['port'] ? ':' . $tg['port'] : '') : '') . ' ' . $tg['path'])) ?></td>
                    <td class="text-center text-nowrap small">
                        <span class="text-info"><?= e($tg['uploads']['pending']) ?></span> /
                        <span class="text-danger"><?= e($tg['uploads']['failed']) ?></span> /
                        <span class="text-success"><?= e($tg['uploads']['done']) ?></span>
                    </td>
                    <td class="text-end text-nowrap">
                        <?php if (has_role('manager')): ?>
                            <form method="post" action="/targets" class="d-inline">
                                <?= csrf_field() ?>
                                <input type="hidden" name="id" value="<?= e($tg['id']) ?>">
                                <input type="hidden" name="name" value="<?= e($tg['name']) ?>">
                                <button class="btn btn-sm btn-outline-secondary" name="action" value="test"><?= e(t('target.test')) ?></button>
                            </form>
                            <a class="btn btn-sm btn-outline-primary" href="/targets/<?= e($tg['id']) ?>"><?= e(t('common.edit')) ?></a>
                            <form method="post" action="/targets" class="d-inline">
                                <?= csrf_field() ?>
                                <input type="hidden" name="id" value="<?= e($tg['id']) ?>">
                                <button class="btn btn-sm btn-outline-danger" name="action" value="delete"
                                        data-confirm="<?= e(t('target.delete_confirm', ['name' => $tg['name']])) ?>"><?= e(t('common.delete')) ?></button>
                            </form>
                        <?php endif; ?>
                    </td>
                </tr>
            <?php endforeach; ?>
            <?php if (!$targets): ?>
                <tr><td colspan="5" class="text-body-secondary p-3"><?= e(t('target.none')) ?></td></tr>
            <?php endif; ?>
            </tbody>
        </table>
    </div>
</div>
<p class="small text-body-secondary mt-2"><?= e(t('target.counts_legend')) ?></p>
