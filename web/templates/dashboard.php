<?php
/** @var array $s status from the API */
$usb = $s['usb'];
$disk = $s['disk'];
$diskPct = $disk['total'] > 0 ? (int) round($disk['used'] / $disk['total'] * 100) : 0;
?>
<div class="d-flex flex-wrap justify-content-between align-items-center gap-2 mb-4">
    <h1 class="h3 mb-0"><?= e(t('nav.dashboard')) ?></h1>
    <?php if (has_role('operator')): ?>
        <form method="post" action="/usb">
            <?= csrf_field() ?>
            <button class="btn btn-primary" name="action" value="sync" type="submit">
                <i class="bi bi-arrow-repeat" aria-hidden="true"></i> <?= e(t('usb.sync_now')) ?>
            </button>
        </form>
    <?php endif; ?>
</div>

<?php if (!empty($s['simulated'])): ?>
    <div class="alert alert-info small"><?= e(t('common.simulation_notice')) ?></div>
<?php endif; ?>
<?php if (!$usb['available'] && empty($s['simulated'])): ?>
    <div class="alert alert-warning"><?= e(t('usb.unavailable', ['reason' => $usb['unavailable_reason']])) ?></div>
<?php endif; ?>
<?php if ((int) $s['targets'] === 0): ?>
    <div class="alert alert-warning d-flex justify-content-between align-items-center flex-wrap gap-2">
        <span><?= e(t('dashboard.no_targets')) ?></span>
        <?php if (has_role('manager')): ?><a class="btn btn-sm btn-warning" href="/targets/new"><?= e(t('target.add')) ?></a><?php endif; ?>
    </div>
<?php endif; ?>

<div class="row g-3 mb-4" data-status-poll="/ajax/status">
    <div class="col-md-6 col-xl-3">
        <div class="card h-100">
            <div class="card-body">
                <div class="text-body-secondary small mb-1"><?= e(t('dashboard.usb_stick')) ?></div>
                <div class="fs-5 fw-semibold">
                    <span class="badge text-bg-<?= e(usb_state_class($usb)) ?>" data-field="usb_state" data-class-field="usb_state_class"><?= e(usb_state_label($usb)) ?></span>
                </div>
                <div class="small text-body-secondary mt-2" data-field="monitor"><?= e(t('monitor.' . ($usb['monitor']['phase'] ?? 'idle'))) ?></div>
            </div>
        </div>
    </div>
    <div class="col-md-6 col-xl-3">
        <div class="card h-100">
            <div class="card-body">
                <div class="text-body-secondary small mb-1"><?= e(t('dashboard.uploads')) ?></div>
                <div class="d-flex gap-4">
                    <div><div class="fs-5 fw-semibold text-info" data-field="pending"><?= e($s['uploads']['pending']) ?></div><div class="small text-body-secondary"><?= e(t('upload.status_pending')) ?></div></div>
                    <div><div class="fs-5 fw-semibold text-danger" data-field="failed"><?= e($s['uploads']['failed']) ?></div><div class="small text-body-secondary"><?= e(t('upload.status_failed')) ?></div></div>
                    <div><div class="fs-5 fw-semibold text-success" data-field="done"><?= e($s['uploads']['done']) ?></div><div class="small text-body-secondary"><?= e(t('upload.status_done')) ?></div></div>
                </div>
                <div class="small text-body-secondary mt-2 text-truncate" data-field="current">
                    <?= e($s['uploads']['current'] ? t('dashboard.uploading', ['file' => $s['uploads']['current']['path'], 'target' => $s['uploads']['current']['target']]) : t('dashboard.no_upload')) ?>
                </div>
            </div>
        </div>
    </div>
    <div class="col-md-6 col-xl-3">
        <div class="card h-100">
            <div class="card-body">
                <div class="text-body-secondary small mb-1"><?= e(t('dashboard.last_sync')) ?></div>
                <div class="fs-6 fw-semibold" data-field="last_sync"><?= e(fmt_time($usb['last_sync']['time'] ?? null)) ?></div>
                <?php if (!empty($usb['last_sync'])): ?>
                    <div class="small text-body-secondary mt-2">
                        <?= e(t('dashboard.sync_counts', [
                            'created' => $usb['last_sync']['created'] ?? 0,
                            'modified' => $usb['last_sync']['modified'] ?? 0,
                            'deleted' => $usb['last_sync']['deleted'] ?? 0,
                        ])) ?>
                    </div>
                <?php endif; ?>
            </div>
        </div>
    </div>
    <div class="col-md-6 col-xl-3">
        <div class="card h-100">
            <div class="card-body">
                <div class="text-body-secondary small mb-1"><?= e(t('dashboard.system')) ?></div>
                <div class="small">
                    <?= e($s['hostname']) ?> · <span data-field="cpu_temp"><?= $s['cpu_temp'] !== null ? e(number_format((float) $s['cpu_temp'], 1)) . ' °C' : '–' ?></span><br>
                    <?= e(t('dashboard.disk', ['free' => fmt_bytes($disk['free']), 'total' => fmt_bytes($disk['total'])])) ?>
                </div>
                <div class="progress mt-2" role="progressbar" aria-valuenow="<?= e($diskPct) ?>" aria-valuemin="0" aria-valuemax="100">
                    <div class="progress-bar<?= $diskPct > 85 ? ' bg-danger' : '' ?>" data-width="<?= e($diskPct) ?>"></div>
                </div>
            </div>
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
                    <tbody>
                    <?php foreach ($events as $ev): ?>
                        <tr>
                            <td class="text-nowrap small text-body-secondary"><?= e(fmt_time($ev['time'])) ?></td>
                            <td><span class="badge text-bg-light border"><?= e(t('event.' . $ev['event'])) ?></span></td>
                            <td class="text-break"><?= e($ev['path']) ?></td>
                            <td class="text-end small text-nowrap"><?= e($ev['size'] !== null ? fmt_bytes($ev['size']) : '') ?></td>
                        </tr>
                    <?php endforeach; ?>
                    <?php if (!$events): ?>
                        <tr><td class="text-body-secondary p-3"><?= e(t('dashboard.no_files')) ?></td></tr>
                    <?php endif; ?>
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
            <ul class="list-group list-group-flush">
                <?php foreach ($failed as $u): ?>
                    <li class="list-group-item small">
                        <div class="fw-semibold text-break"><?= e($u['path']) ?> → <?= e($u['target']) ?></div>
                        <div class="text-danger text-break"><?= e($u['last_error']) ?></div>
                    </li>
                <?php endforeach; ?>
                <?php if (!$failed): ?>
                    <li class="list-group-item text-body-secondary small"><?= e(t('dashboard.no_failed')) ?></li>
                <?php endif; ?>
            </ul>
        </div>
    </div>
</div>
