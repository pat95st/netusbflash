<?php $ro = readonly_unless('manager'); ?>
<div id="conversion" data-can-edit="<?= has_role('manager') ? '1' : '0' ?>">
    <h1 class="h3 mb-2"><?= e(t('nav.conversion')) ?></h1>
    <p class="text-body-secondary mb-4"><?= e(t('conversion.intro')) ?></p>

    <div class="alert alert-warning" data-ffmpeg-missing hidden>
        <i class="bi bi-exclamation-triangle" aria-hidden="true"></i> <?= e(t('conversion.ffmpeg_missing')) ?>
        <code class="ms-1">sudo apt install ffmpeg</code>
    </div>

    <form data-conversion-form novalidate>
        <div class="card mb-4">
            <div class="card-body d-flex flex-wrap justify-content-between align-items-center gap-3">
                <div class="form-check form-switch mb-0">
                    <input class="form-check-input" type="checkbox" role="switch" id="conversion_enabled" name="enabled"<?= $ro ?>>
                    <label class="form-check-label fw-semibold" for="conversion_enabled"><?= e(t('conversion.enabled')) ?></label>
                    <div class="form-text mt-0"><?= e(t('conversion.enabled_help')) ?></div>
                </div>
                <div class="small text-body-secondary text-md-end">
                    <div data-ffmpeg-version></div>
                    <div data-queue></div>
                </div>
            </div>
        </div>

        <div class="d-flex flex-wrap justify-content-between align-items-center gap-2 mb-2">
            <h2 class="h5 mb-0"><?= e(t('conversion.rules')) ?></h2>
            <?php if (has_role('manager')): ?>
                <button class="btn btn-outline-primary btn-sm" type="button" data-action="add"><i class="bi bi-plus-lg" aria-hidden="true"></i> <?= e(t('conversion.add_rule')) ?></button>
            <?php endif; ?>
        </div>
        <p class="small text-body-secondary"><?= e(t('conversion.rules_help')) ?></p>
        <div data-error-for="rules"></div>

        <div data-rules>
            <div class="card card-body text-body-secondary mb-3" data-empty hidden><?= e(t('conversion.no_rules')) ?></div>
        </div>

        <?php if (has_role('manager')): ?>
            <div class="mt-3">
                <button class="btn btn-primary" type="submit"><?= e(t('common.save')) ?></button>
            </div>
        <?php endif; ?>
    </form>

    <template data-rule-template>
        <div class="card mb-3" data-rule>
            <div class="card-header bg-body d-flex flex-wrap align-items-center gap-2">
                <span class="fw-semibold me-auto" data-rule-title></span>
                <div class="form-check form-switch mb-0">
                    <input class="form-check-input" type="checkbox" role="switch" data-field="enabled"<?= $ro ?>>
                    <label class="form-check-label small" data-label-for="enabled"><?= e(t('conversion.rule_enabled')) ?></label>
                </div>
                <?php if (has_role('manager')): ?>
                    <div class="btn-group btn-group-sm" role="group">
                        <button class="btn btn-outline-secondary" type="button" data-action="up" aria-label="<?= e(t('conversion.move_up')) ?>" title="<?= e(t('conversion.move_up')) ?>"><i class="bi bi-arrow-up" aria-hidden="true"></i></button>
                        <button class="btn btn-outline-secondary" type="button" data-action="down" aria-label="<?= e(t('conversion.move_down')) ?>" title="<?= e(t('conversion.move_down')) ?>"><i class="bi bi-arrow-down" aria-hidden="true"></i></button>
                        <button class="btn btn-outline-danger" type="button" data-action="remove" aria-label="<?= e(t('common.delete')) ?>" title="<?= e(t('common.delete')) ?>"><i class="bi bi-trash" aria-hidden="true"></i></button>
                    </div>
                <?php endif; ?>
            </div>
            <div class="card-body">
                <div class="row g-3">
                    <div class="col-md-6">
                        <label class="form-label" data-label-for="extensions"><?= e(t('conversion.extensions')) ?></label>
                        <input class="form-control font-monospace" data-field="extensions" placeholder="wav, aif, aiff" autocapitalize="none" spellcheck="false"<?= $ro ?>>
                        <div class="form-text"><?= e(t('conversion.extensions_help')) ?></div>
                    </div>
                    <div class="col-md-6">
                        <label class="form-label" data-label-for="format"><?= e(t('conversion.format')) ?></label>
                        <select class="form-select" data-field="format"<?= $ro ?>>
                            <option value="flac"><?= e(t('conversion.format_flac')) ?></option>
                            <option value="mp3"><?= e(t('conversion.format_mp3')) ?></option>
                            <option value="aac"><?= e(t('conversion.format_aac')) ?></option>
                        </select>
                        <div class="form-text" data-format-help></div>
                    </div>

                    <div class="col-md-4" data-show-format="mp3">
                        <label class="form-label" data-label-for="mp3_mode"><?= e(t('conversion.mp3_mode')) ?></label>
                        <select class="form-select" data-field="mp3_mode"<?= $ro ?>>
                            <option value="cbr"><?= e(t('conversion.mp3_cbr')) ?></option>
                            <option value="vbr"><?= e(t('conversion.mp3_vbr')) ?></option>
                        </select>
                    </div>
                    <div class="col-md-4" data-show-format="mp3 aac" data-show-mode="cbr">
                        <label class="form-label" data-label-for="bitrate"><?= e(t('conversion.bitrate')) ?></label>
                        <select class="form-select" data-field="bitrate" data-type="int"<?= $ro ?>></select>
                    </div>
                    <div class="col-md-4" data-show-format="mp3" data-show-mode="vbr">
                        <label class="form-label" data-label-for="vbr_quality"><?= e(t('conversion.vbr_quality')) ?></label>
                        <select class="form-select" data-field="vbr_quality" data-type="int"<?= $ro ?>>
                            <?php for ($q = 0; $q <= 9; $q++): ?>
                                <option value="<?= $q ?>"><?= e(t('conversion.vbr_option', ['q' => (string) $q, 'kbps' => ['245', '225', '190', '175', '165', '130', '115', '100', '85', '65'][$q]])) ?></option>
                            <?php endfor; ?>
                        </select>
                    </div>
                    <div class="col-md-4" data-show-format="flac">
                        <label class="form-label" data-label-for="flac_level"><?= e(t('conversion.flac_level')) ?></label>
                        <select class="form-select" data-field="flac_level" data-type="int"<?= $ro ?>>
                            <?php for ($l = 0; $l <= 8; $l++): ?>
                                <option value="<?= $l ?>"><?= $l ?><?= $l === 0 ? ' – ' . e(t('conversion.flac_fastest')) : ($l === 5 ? ' – ' . e(t('conversion.flac_default')) : ($l === 8 ? ' – ' . e(t('conversion.flac_smallest')) : '')) ?></option>
                            <?php endfor; ?>
                        </select>
                    </div>
                    <div class="col-md-4" data-show-format="flac">
                        <label class="form-label" data-label-for="bit_depth"><?= e(t('conversion.bit_depth')) ?></label>
                        <select class="form-select" data-field="bit_depth" data-type="int"<?= $ro ?>>
                            <option value="0"><?= e(t('conversion.keep_source')) ?></option>
                            <option value="16">16 bit</option>
                            <option value="24">24 bit</option>
                        </select>
                    </div>

                    <div class="col-md-4">
                        <label class="form-label" data-label-for="sample_rate"><?= e(t('conversion.sample_rate')) ?></label>
                        <select class="form-select" data-field="sample_rate" data-type="int"<?= $ro ?>></select>
                    </div>
                    <div class="col-md-4">
                        <label class="form-label" data-label-for="channels"><?= e(t('conversion.channels')) ?></label>
                        <select class="form-select" data-field="channels" data-type="int"<?= $ro ?>>
                            <option value="0"><?= e(t('conversion.keep_source')) ?></option>
                            <option value="1"><?= e(t('conversion.mono')) ?></option>
                            <option value="2"><?= e(t('conversion.stereo')) ?></option>
                        </select>
                    </div>
                    <div class="col-12">
                        <div class="form-check">
                            <input class="form-check-input" type="checkbox" data-field="keep_original"<?= $ro ?>>
                            <label class="form-check-label" data-label-for="keep_original"><?= e(t('conversion.keep_original')) ?></label>
                            <div class="form-text"><?= e(t('conversion.keep_original_help')) ?></div>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    </template>
</div>
