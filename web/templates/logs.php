<?php
$levelClass = ['info' => 'secondary', 'warning' => 'warning', 'error' => 'danger'];
$query = '?tab=' . $tab . ($level !== '' ? '&level=' . $level : '');
?>
<div class="d-flex flex-wrap justify-content-between align-items-center gap-2 mb-4">
    <h1 class="h3 mb-0"><?= e(t('nav.logs')) ?></h1>
    <a class="btn btn-outline-secondary" href="/logs<?= e($query) ?>&amp;download=1"><i class="bi bi-download" aria-hidden="true"></i> <?= e(t('logs.download')) ?></a>
</div>

<ul class="nav nav-tabs mb-3">
    <li class="nav-item"><a class="nav-link<?= $tab === 'events' ? ' active' : '' ?>" href="/logs"><?= e(t('logs.events')) ?></a></li>
    <?php if (has_role('admin')): ?>
        <li class="nav-item"><a class="nav-link<?= $tab === 'audit' ? ' active' : '' ?>" href="/logs?tab=audit"><?= e(t('logs.audit')) ?></a></li>
    <?php endif; ?>
</ul>

<?php if ($tab === 'events'): ?>
    <div class="btn-group btn-group-sm mb-3" role="group">
        <?php foreach (['' => t('logs.all'), 'info' => t('logs.info'), 'warning' => t('logs.warning'), 'error' => t('logs.error')] as $key => $label): ?>
            <a class="btn btn-outline-secondary<?= $level === $key ? ' active' : '' ?>" href="/logs<?= $key !== '' ? '?level=' . e($key) : '' ?>"><?= e($label) ?></a>
        <?php endforeach; ?>
    </div>
<?php endif; ?>

<div class="card">
    <div class="table-responsive">
        <table class="table table-sm mb-0 align-middle">
            <tbody>
            <?php foreach ($rows as $row): ?>
                <tr>
                    <td class="text-nowrap small text-body-secondary"><?= e(fmt_time($row['time'])) ?></td>
                    <?php if ($tab === 'events'): ?>
                        <td><span class="badge text-bg-<?= e($levelClass[$row['level']] ?? 'secondary') ?>"><?= e($row['level']) ?></span></td>
                        <td class="small text-body-secondary"><?= e($row['source']) ?></td>
                        <td class="small text-break"><?= e($row['message']) ?></td>
                    <?php else: ?>
                        <td class="small fw-semibold"><?= e($row['username'] ?: '–') ?></td>
                        <td class="small font-monospace"><?= e($row['action']) ?></td>
                        <td class="small text-break"><?= e(trim($row['object'] . ' ' . $row['details'])) ?></td>
                    <?php endif; ?>
                </tr>
            <?php endforeach; ?>
            <?php if (!$rows): ?>
                <tr><td class="text-body-secondary p-3"><?= e(t('logs.none')) ?></td></tr>
            <?php endif; ?>
            </tbody>
        </table>
    </div>
</div>
<p class="small text-body-secondary mt-2"><?= e(t('logs.note')) ?></p>
