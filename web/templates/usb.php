<?php $ro = readonly_unless('manager'); ?>
<div id="usb">
    <div class="d-flex flex-wrap justify-content-between align-items-center gap-2 mb-4">
        <h1 class="h3 mb-0"><?= e(t('nav.usb')) ?></h1>
        <?php if (has_role('operator')): ?>
            <div class="d-flex flex-wrap gap-2">
                <button class="btn btn-primary" type="button" data-action="sync"><i class="bi bi-arrow-repeat" aria-hidden="true"></i> <?= e(t('usb.sync_now')) ?></button>
                <button class="btn btn-outline-secondary" type="button" data-action="detach" data-confirm="<?= e(t('usb.detach_confirm')) ?>" hidden><?= e(t('usb.detach')) ?></button>
                <button class="btn btn-outline-secondary" type="button" data-action="attach" hidden><?= e(t('usb.attach')) ?></button>
            </div>
        <?php endif; ?>
    </div>

    <div class="alert alert-warning" data-usb-unavailable hidden></div>

    <div class="row g-3 mb-4">
        <div class="col-md-4">
            <div class="card h-100"><div class="card-body">
                <div class="text-body-secondary small"><?= e(t('usb.state')) ?></div>
                <span class="badge fs-6 text-bg-secondary" data-usb-state>–</span>
                <div class="small text-body-secondary mt-2"><?= e(t('usb.udc')) ?>: <span data-bind="state.udc">–</span></div>
            </div></div>
        </div>
        <div class="col-md-4">
            <div class="card h-100"><div class="card-body">
                <div class="text-body-secondary small"><?= e(t('usb.image')) ?></div>
                <div class="fw-semibold" data-image-summary>–</div>
                <div class="small text-body-secondary mt-2" data-image-allocated></div>
            </div></div>
        </div>
        <div class="col-md-4">
            <div class="card h-100"><div class="card-body">
                <div class="text-body-secondary small"><?= e(t('usb.files_on_stick')) ?></div>
                <div class="fw-semibold" data-file-count>–</div>
                <div class="small text-body-secondary mt-2" data-file-uploaded></div>
            </div></div>
        </div>
    </div>

    <form class="card mb-4" data-settings-form novalidate>
        <div class="card-header bg-body fw-semibold"><?= e(t('usb.settings')) ?></div>
        <div class="card-body">
            <h2 class="h6 text-body-secondary"><?= e(t('usb.section_sync')) ?></h2>
            <div class="row g-3 mb-4">
                <div class="col-md-6">
                    <span class="form-label d-block"><?= e(t('usb.sync_mode')) ?></span>
                    <?php foreach (['detach', 'live'] as $mode): ?>
                        <div class="form-check">
                            <input class="form-check-input" type="radio" name="sync_mode" id="sync_<?= e($mode) ?>" value="<?= e($mode) ?>"<?= $ro ?>>
                            <label class="form-check-label" for="sync_<?= e($mode) ?>"><?= e(t('usb.sync_' . $mode)) ?>
                                <br><span class="small text-body-secondary"><?= e(t('usb.sync_' . $mode . '_help')) ?></span></label>
                        </div>
                    <?php endforeach; ?>
                </div>
                <div class="col-md-6">
                    <label class="form-label" for="idle_seconds"><?= e(t('usb.idle_seconds')) ?></label>
                    <input class="form-control" id="idle_seconds" name="idle_seconds" type="number" min="5" max="3600" data-type="int"<?= $ro ?>>
                    <div class="form-text"><?= e(t('usb.idle_help')) ?></div>
                    <div class="form-check mt-3">
                        <input class="form-check-input" type="checkbox" id="delete_after_upload" name="delete_after_upload" value="1"<?= $ro ?>>
                        <label class="form-check-label" for="delete_after_upload"><?= e(t('usb.delete_after_upload')) ?></label>
                        <div class="form-text"><?= e(t('usb.delete_after_upload_help')) ?></div>
                    </div>
                </div>
                <div class="col-md-6">
                    <label class="form-label" for="include"><?= e(t('usb.include')) ?></label>
                    <input class="form-control" id="include" name="include" placeholder="*.wav, *.mp3"<?= $ro ?>>
                </div>
                <div class="col-md-6">
                    <label class="form-label" for="exclude"><?= e(t('usb.exclude')) ?></label>
                    <input class="form-control" id="exclude" name="exclude" placeholder="*.tmp"<?= $ro ?>>
                </div>
            </div>

            <h2 class="h6 text-body-secondary"><?= e(t('usb.section_host')) ?></h2>
            <div class="row g-3 mb-4">
                <div class="col-12">
                    <div class="form-check form-switch">
                        <input class="form-check-input" type="checkbox" role="switch" id="enabled" name="enabled" value="1"<?= $ro ?>>
                        <label class="form-check-label" for="enabled"><?= e(t('usb.enabled')) ?></label>
                    </div>
                    <div class="form-check">
                        <input class="form-check-input" type="checkbox" id="removable" name="removable" value="1"<?= $ro ?>>
                        <label class="form-check-label" for="removable"><?= e(t('usb.removable')) ?></label>
                    </div>
                    <div class="form-check">
                        <input class="form-check-input" type="checkbox" id="read_only" name="read_only" value="1"<?= $ro ?>>
                        <label class="form-check-label" for="read_only"><?= e(t('usb.read_only')) ?></label>
                    </div>
                </div>
                <div class="col-md-6">
                    <label class="form-label" for="manufacturer"><?= e(t('usb.manufacturer')) ?></label>
                    <input class="form-control" id="manufacturer" name="manufacturer" maxlength="32"<?= $ro ?>>
                </div>
                <div class="col-md-6">
                    <label class="form-label" for="product"><?= e(t('usb.product')) ?></label>
                    <input class="form-control" id="product" name="product" maxlength="32"<?= $ro ?>>
                </div>
                <div class="col-md-3">
                    <label class="form-label" for="vendor_id"><?= e(t('usb.vendor_id')) ?></label>
                    <input class="form-control font-monospace" id="vendor_id" name="vendor_id"<?= $ro ?>>
                </div>
                <div class="col-md-3">
                    <label class="form-label" for="product_id"><?= e(t('usb.product_id')) ?></label>
                    <input class="form-control font-monospace" id="product_id" name="product_id"<?= $ro ?>>
                </div>
                <div class="col-md-3">
                    <label class="form-label" for="serial"><?= e(t('usb.serial')) ?></label>
                    <input class="form-control font-monospace" id="serial" name="serial" placeholder="<?= e(t('usb.serial_auto')) ?>"<?= $ro ?>>
                </div>
                <div class="col-md-3">
                    <label class="form-label" for="max_power_ma"><?= e(t('usb.max_power')) ?></label>
                    <input class="form-control" id="max_power_ma" name="max_power_ma" type="number" min="2" max="500" data-type="int"<?= $ro ?>>
                </div>
            </div>

            <h2 class="h6 text-body-secondary"><?= e(t('usb.section_image')) ?></h2>
            <div class="row g-3">
                <div class="col-md-4">
                    <label class="form-label" for="size_mb"><?= e(t('usb.size_mb')) ?></label>
                    <input class="form-control" id="size_mb" name="size_mb" type="number" min="64" data-type="int"<?= $ro ?>>
                    <div class="form-text" data-size-help data-template="<?= e(t('usb.size_help', ['max' => '{value}'])) ?>"></div>
                </div>
                <div class="col-md-4">
                    <label class="form-label" for="filesystem"><?= e(t('usb.filesystem')) ?></label>
                    <select class="form-select" id="filesystem" name="filesystem"<?= $ro ?>>
                        <option value="exfat">exFAT</option>
                        <option value="vfat">FAT32</option>
                    </select>
                </div>
                <div class="col-md-4">
                    <label class="form-label" for="label"><?= e(t('usb.label')) ?></label>
                    <input class="form-control text-uppercase" id="label" name="label" maxlength="11"<?= $ro ?>>
                </div>
                <div class="col-12 form-text mt-1"><?= e(t('usb.image_settings_help')) ?></div>
            </div>
        </div>
        <?php if (has_role('manager')): ?>
            <div class="card-footer bg-body">
                <button class="btn btn-primary" type="submit"><?= e(t('common.save')) ?></button>
            </div>
        <?php endif; ?>
    </form>

    <?php if (has_role('admin')): ?>
        <form class="card border-danger mb-4" data-image-form data-word="<?= e(t('usb.recreate_word')) ?>" novalidate>
            <div class="card-header bg-body fw-semibold text-danger"><?= e(t('usb.recreate_title')) ?></div>
            <div class="card-body">
                <p class="mb-2"><?= e(t('usb.recreate_text')) ?></p>
                <div class="row g-2 align-items-end">
                    <div class="col-sm-6 col-md-4">
                        <label class="form-label" for="confirm_text"><?= e(t('usb.recreate_confirm')) ?></label>
                        <input class="form-control" id="confirm_text" name="confirm_text" autocomplete="off">
                    </div>
                    <div class="col-auto">
                        <button class="btn btn-danger" type="submit"><?= e(t('usb.recreate_button')) ?></button>
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
                <tbody data-files>
                    <tr data-empty hidden><td colspan="4" class="text-body-secondary p-3"><?= e(t('usb.no_files')) ?></td></tr>
                    <template data-row>
                        <tr>
                            <td class="text-break" data-bind="path"></td>
                            <td class="text-end text-nowrap" data-bind="size" data-format="bytes"></td>
                            <td class="text-nowrap small" data-bind="mtime" data-format="time"></td>
                            <td data-uploaded></td>
                        </tr>
                    </template>
                </tbody>
            </table>
        </div>
    </div>
</div>
