<?php
/** @var array $u usb data from the API, $v form values, $files, $errors */
$state = $u['state'];
$image = $u['image'];
$canEdit = has_role('manager');
$disabled = $canEdit ? '' : ' disabled';
$usbForState = ['enabled' => $u['settings']['enabled'], 'image' => $image, 'state' => $state];
?>
<div class="d-flex flex-wrap justify-content-between align-items-center gap-2 mb-4">
    <h1 class="h3 mb-0"><?= e(t('nav.usb')) ?></h1>
    <?php if (has_role('operator')): ?>
        <form method="post" action="/usb" class="d-flex flex-wrap gap-2">
            <?= csrf_field() ?>
            <button class="btn btn-primary" name="action" value="sync"><i class="bi bi-arrow-repeat" aria-hidden="true"></i> <?= e(t('usb.sync_now')) ?></button>
            <?php if (!empty($state['attached'])): ?>
                <button class="btn btn-outline-secondary" name="action" value="detach" data-confirm="<?= e(t('usb.detach_confirm')) ?>"><?= e(t('usb.detach')) ?></button>
            <?php else: ?>
                <button class="btn btn-outline-secondary" name="action" value="attach"><?= e(t('usb.attach')) ?></button>
            <?php endif; ?>
        </form>
    <?php endif; ?>
</div>

<?php if (!$u['available']): ?>
    <div class="alert alert-warning"><?= e(t('usb.unavailable', ['reason' => $u['unavailable_reason']])) ?></div>
<?php endif; ?>

<div class="row g-3 mb-4">
    <div class="col-md-4">
        <div class="card h-100"><div class="card-body">
            <div class="text-body-secondary small"><?= e(t('usb.state')) ?></div>
            <span class="badge fs-6 text-bg-<?= e(usb_state_class($usbForState)) ?>"><?= e(usb_state_label($usbForState)) ?></span>
            <div class="small text-body-secondary mt-2"><?= e(t('usb.udc')) ?>: <?= e($state['udc'] ?: '–') ?></div>
        </div></div>
    </div>
    <div class="col-md-4">
        <div class="card h-100"><div class="card-body">
            <div class="text-body-secondary small"><?= e(t('usb.image')) ?></div>
            <?php if (!empty($image['exists'])): ?>
                <div class="fw-semibold"><?= e(fmt_bytes($image['size'])) ?> · <?= e($u['settings']['filesystem'] === 'vfat' ? 'FAT32' : 'exFAT') ?> · <?= e($u['settings']['label']) ?></div>
                <div class="small text-body-secondary mt-2"><?= e(t('usb.allocated', ['size' => fmt_bytes($image['allocated'])])) ?></div>
            <?php else: ?>
                <div class="fw-semibold"><?= e(t('usb.state_no_image')) ?></div>
            <?php endif; ?>
        </div></div>
    </div>
    <div class="col-md-4">
        <div class="card h-100"><div class="card-body">
            <div class="text-body-secondary small"><?= e(t('usb.files_on_stick')) ?></div>
            <div class="fw-semibold"><?= e(count($files)) ?></div>
            <div class="small text-body-secondary mt-2"><?= e(t('usb.files_uploaded', ['n' => count(array_filter($files, fn($f) => $f['uploaded']))])) ?></div>
        </div></div>
    </div>
</div>

<form method="post" action="/usb" novalidate class="card mb-4">
    <?= csrf_field() ?>
    <div class="card-header bg-body fw-semibold"><?= e(t('usb.settings')) ?></div>
    <div class="card-body">
        <h2 class="h6 text-body-secondary"><?= e(t('usb.section_sync')) ?></h2>
        <div class="row g-3 mb-4">
            <div class="col-md-6">
                <span class="form-label d-block"><?= e(t('usb.sync_mode')) ?></span>
                <?php foreach (['detach', 'live'] as $mode): ?>
                    <div class="form-check">
                        <input class="form-check-input" type="radio" name="sync_mode" id="sync_<?= e($mode) ?>" value="<?= e($mode) ?>"<?= checked($v['sync_mode'] === $mode) ?><?= $disabled ?>>
                        <label class="form-check-label" for="sync_<?= e($mode) ?>"><?= e(t('usb.sync_' . $mode)) ?>
                            <br><span class="small text-body-secondary"><?= e(t('usb.sync_' . $mode . '_help')) ?></span></label>
                    </div>
                <?php endforeach; ?>
            </div>
            <div class="col-md-6">
                <label class="form-label" for="idle_seconds"><?= e(t('usb.idle_seconds')) ?></label>
                <input class="form-control<?= invalid($errors, 'idle_seconds') ?>" id="idle_seconds" name="idle_seconds" type="number" min="5" max="3600" value="<?= e($v['idle_seconds']) ?>"<?= $disabled ?>>
                <div class="form-text"><?= e(t('usb.idle_help')) ?></div>
                <?= feedback($errors, 'idle_seconds') ?>
                <div class="form-check mt-3">
                    <input class="form-check-input<?= invalid($errors, 'delete_after_upload') ?>" type="checkbox" id="delete_after_upload" name="delete_after_upload" value="1"<?= checked($v['delete_after_upload']) ?><?= $disabled ?>>
                    <label class="form-check-label" for="delete_after_upload"><?= e(t('usb.delete_after_upload')) ?></label>
                    <?= feedback($errors, 'delete_after_upload') ?>
                    <div class="form-text"><?= e(t('usb.delete_after_upload_help')) ?></div>
                </div>
            </div>
            <div class="col-md-6">
                <label class="form-label" for="include"><?= e(t('usb.include')) ?></label>
                <input class="form-control" id="include" name="include" value="<?= e($v['include']) ?>" placeholder="*.wav, *.mp3"<?= $disabled ?>>
            </div>
            <div class="col-md-6">
                <label class="form-label" for="exclude"><?= e(t('usb.exclude')) ?></label>
                <input class="form-control" id="exclude" name="exclude" value="<?= e($v['exclude']) ?>" placeholder="*.tmp"<?= $disabled ?>>
            </div>
        </div>

        <h2 class="h6 text-body-secondary"><?= e(t('usb.section_host')) ?></h2>
        <div class="row g-3 mb-4">
            <div class="col-12">
                <div class="form-check form-switch">
                    <input class="form-check-input" type="checkbox" role="switch" id="enabled" name="enabled" value="1"<?= checked($v['enabled']) ?><?= $disabled ?>>
                    <label class="form-check-label" for="enabled"><?= e(t('usb.enabled')) ?></label>
                </div>
                <div class="form-check">
                    <input class="form-check-input" type="checkbox" id="removable" name="removable" value="1"<?= checked($v['removable']) ?><?= $disabled ?>>
                    <label class="form-check-label" for="removable"><?= e(t('usb.removable')) ?></label>
                </div>
                <div class="form-check">
                    <input class="form-check-input" type="checkbox" id="read_only" name="read_only" value="1"<?= checked($v['read_only']) ?><?= $disabled ?>>
                    <label class="form-check-label" for="read_only"><?= e(t('usb.read_only')) ?></label>
                </div>
            </div>
            <div class="col-md-6">
                <label class="form-label" for="manufacturer"><?= e(t('usb.manufacturer')) ?></label>
                <input class="form-control<?= invalid($errors, 'manufacturer') ?>" id="manufacturer" name="manufacturer" value="<?= e($v['manufacturer']) ?>" maxlength="32"<?= $disabled ?>>
                <?= feedback($errors, 'manufacturer') ?>
            </div>
            <div class="col-md-6">
                <label class="form-label" for="product"><?= e(t('usb.product')) ?></label>
                <input class="form-control<?= invalid($errors, 'product') ?>" id="product" name="product" value="<?= e($v['product']) ?>" maxlength="32"<?= $disabled ?>>
                <?= feedback($errors, 'product') ?>
            </div>
            <div class="col-md-3">
                <label class="form-label" for="vendor_id"><?= e(t('usb.vendor_id')) ?></label>
                <input class="form-control font-monospace<?= invalid($errors, 'vendor_id') ?>" id="vendor_id" name="vendor_id" value="<?= e($v['vendor_id']) ?>"<?= $disabled ?>>
                <?= feedback($errors, 'vendor_id') ?>
            </div>
            <div class="col-md-3">
                <label class="form-label" for="product_id"><?= e(t('usb.product_id')) ?></label>
                <input class="form-control font-monospace<?= invalid($errors, 'product_id') ?>" id="product_id" name="product_id" value="<?= e($v['product_id']) ?>"<?= $disabled ?>>
                <?= feedback($errors, 'product_id') ?>
            </div>
            <div class="col-md-3">
                <label class="form-label" for="serial"><?= e(t('usb.serial')) ?></label>
                <input class="form-control font-monospace<?= invalid($errors, 'serial') ?>" id="serial" name="serial" value="<?= e($v['serial']) ?>" placeholder="<?= e(t('usb.serial_auto')) ?>"<?= $disabled ?>>
                <?= feedback($errors, 'serial') ?>
            </div>
            <div class="col-md-3">
                <label class="form-label" for="max_power_ma"><?= e(t('usb.max_power')) ?></label>
                <input class="form-control<?= invalid($errors, 'max_power_ma') ?>" id="max_power_ma" name="max_power_ma" type="number" min="2" max="500" value="<?= e($v['max_power_ma']) ?>"<?= $disabled ?>>
                <?= feedback($errors, 'max_power_ma') ?>
            </div>
        </div>

        <h2 class="h6 text-body-secondary"><?= e(t('usb.section_image')) ?></h2>
        <div class="row g-3">
            <div class="col-md-4">
                <label class="form-label" for="size_mb"><?= e(t('usb.size_mb')) ?></label>
                <input class="form-control<?= invalid($errors, 'size_mb') ?>" id="size_mb" name="size_mb" type="number" min="64" max="<?= e($u['max_size_mb']) ?>" value="<?= e($v['size_mb']) ?>"<?= $disabled ?>>
                <div class="form-text"><?= e(t('usb.size_help', ['max' => $u['max_size_mb']])) ?></div>
                <?= feedback($errors, 'size_mb') ?>
            </div>
            <div class="col-md-4">
                <label class="form-label" for="filesystem"><?= e(t('usb.filesystem')) ?></label>
                <select class="form-select" id="filesystem" name="filesystem"<?= $disabled ?>>
                    <?= select_options(['exfat' => 'exFAT', 'vfat' => 'FAT32'], $v['filesystem']) ?>
                </select>
            </div>
            <div class="col-md-4">
                <label class="form-label" for="label"><?= e(t('usb.label')) ?></label>
                <input class="form-control text-uppercase<?= invalid($errors, 'label') ?>" id="label" name="label" maxlength="11" value="<?= e($v['label']) ?>"<?= $disabled ?>>
                <?= feedback($errors, 'label') ?>
            </div>
            <div class="col-12 form-text mt-1"><?= e(t('usb.image_settings_help')) ?></div>
        </div>
    </div>
    <?php if ($canEdit): ?>
        <div class="card-footer bg-body">
            <button class="btn btn-primary" name="action" value="save"><?= e(t('common.save')) ?></button>
        </div>
    <?php endif; ?>
</form>

<?php if (has_role('admin')): ?>
    <form method="post" action="/usb" class="card border-danger mb-4">
        <?= csrf_field() ?>
        <div class="card-header bg-body fw-semibold text-danger"><?= e(t('usb.recreate_title')) ?></div>
        <div class="card-body">
            <p class="mb-2"><?= e(t('usb.recreate_text')) ?></p>
            <div class="row g-2 align-items-end">
                <div class="col-sm-6 col-md-4">
                    <label class="form-label" for="confirm_text"><?= e(t('usb.recreate_confirm')) ?></label>
                    <input class="form-control" id="confirm_text" name="confirm_text" autocomplete="off">
                </div>
                <div class="col-auto">
                    <button class="btn btn-danger" name="action" value="image"><?= e(t('usb.recreate_button')) ?></button>
                </div>
            </div>
        </div>
    </form>
<?php endif; ?>

<div class="card" id="files">
    <div class="card-header bg-body fw-semibold"><?= e(t('usb.files_on_stick')) ?></div>
    <div class="table-responsive">
        <table class="table table-sm table-hover mb-0 align-middle">
            <thead><tr>
                <th><?= e(t('usb.file')) ?></th>
                <th class="text-end"><?= e(t('usb.size')) ?></th>
                <th><?= e(t('usb.modified')) ?></th>
                <th><?= e(t('usb.uploaded')) ?></th>
            </tr></thead>
            <tbody>
            <?php foreach ($files as $f): ?>
                <tr>
                    <td class="text-break"><?= e($f['path']) ?></td>
                    <td class="text-end text-nowrap"><?= e(fmt_bytes($f['size'])) ?></td>
                    <td class="text-nowrap small"><?= e(fmt_time($f['mtime'])) ?></td>
                    <td><?= $f['uploaded'] ? '<i class="bi bi-check2-circle text-success" aria-hidden="true"></i> ' . e(t('common.yes')) : e(t('common.no')) ?></td>
                </tr>
            <?php endforeach; ?>
            <?php if (!$files): ?>
                <tr><td colspan="4" class="text-body-secondary p-3"><?= e(t('usb.no_files')) ?></td></tr>
            <?php endif; ?>
            </tbody>
        </table>
    </div>
</div>
