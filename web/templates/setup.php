<?php
/**
 * Setup wizard skeleton. All steps are present in the HTML and hidden;
 * assets/js/pages/setup.js loads the state via AJAX, shows the current step,
 * fills in dynamic values and submits each step via AJAX.
 *
 * @var list<string> $steps
 */
?>
<div class="card shadow-sm mx-auto wizard-card position-relative" id="setup">

    <?php require __DIR__ . '/loading.php'; ?>

    <div class="card-header bg-body">
        <div class="d-flex justify-content-between align-items-center">
            <h2 class="h5 mb-0"><?= e(t('setup.title')) ?></h2>
            <span class="text-body-secondary small" data-step-counter hidden
                  data-template="<?= e(t('setup.step_of', ['n' => '{n}', 'total' => '{total}'])) ?>"></span>
        </div>
        <ol class="wizard-steps list-unstyled d-flex flex-wrap gap-2 mt-3 mb-1" data-step-list hidden>
            <?php foreach ($steps as $s): ?>
                <li><a href="#" class="badge rounded-pill text-decoration-none" data-goto="<?= e($s) ?>"><?= e(t('setup.step.' . $s)) ?></a></li>
            <?php endforeach; ?>
        </ol>
    </div>

    <div class="card-body p-4">
        <noscript><div class="alert alert-warning"><?= e(t('setup.noscript')) ?></div></noscript>
        <div class="alert alert-info small" data-simulated hidden><?= e(t('common.simulation_notice')) ?></div>
        <div data-notices></div>

        <!-- Language and setup code -->
        <section data-screen="code" hidden>
            <p><?= e(t('setup.welcome')) ?></p>
            <div class="mb-3">
                <span class="form-label d-block"><?= e(t('setup.language')) ?></span>
                <div class="btn-group" role="group">
                    <?php foreach (I18n::LOCALES as $code => $name): ?>
                        <a class="btn btn-outline-primary<?= I18n::locale() === $code ? ' active' : '' ?>" href="/lang/<?= e($code) ?>"><?= e($name) ?></a>
                    <?php endforeach; ?>
                </div>
            </div>
            <form data-setup-form="code" novalidate>
                <label class="form-label" for="code"><?= e(t('setup.code')) ?></label>
                <input class="form-control form-control-lg font-monospace" id="code" name="code"
                       placeholder="XXXX-XXXX-XXXX" autocomplete="off" autocapitalize="characters" required>
                <div class="form-text"><?= e(t('setup.code_help')) ?> <code>sudo netusbflash-cli setup show-code</code></div>
                <button class="btn btn-primary mt-3" type="submit"><?= e(t('common.continue')) ?></button>
            </form>
        </section>

        <!-- Step: administrator -->
        <section data-screen="admin" hidden>
            <p><?= e(t('setup.admin_intro')) ?></p>
            <form data-setup-form novalidate>
                <input type="hidden" name="step" value="admin">
                <div class="row g-3">
                    <div class="col-md-6">
                        <label class="form-label" for="admin_username"><?= e(t('field.username')) ?></label>
                        <input class="form-control" id="admin_username" name="username" value="admin" autocapitalize="none" required>
                    </div>
                    <div class="col-md-6">
                        <label class="form-label" for="admin_email"><?= e(t('field.email')) ?></label>
                        <input class="form-control" id="admin_email" name="email" type="email">
                    </div>
                    <div class="col-md-6">
                        <label class="form-label" for="admin_password"><?= e(t('field.password')) ?></label>
                        <input class="form-control" id="admin_password" name="password" type="password" autocomplete="new-password" minlength="12" required>
                        <div class="form-text"><?= e(t('field.password_help')) ?></div>
                    </div>
                    <div class="col-md-6">
                        <label class="form-label" for="admin_password_confirm"><?= e(t('field.password_confirm')) ?></label>
                        <input class="form-control" id="admin_password_confirm" name="password_confirm" type="password" autocomplete="new-password" required>
                    </div>
                </div>
                <button class="btn btn-primary mt-4" type="submit"><?= e(t('common.save_continue')) ?></button>
            </form>
        </section>

        <!-- Step: system -->
        <section data-screen="system" hidden>
            <p><?= e(t('setup.system_intro')) ?></p>
            <form data-setup-form novalidate>
                <input type="hidden" name="step" value="system">
                <div class="row g-3">
                    <div class="col-md-6">
                        <label class="form-label" for="hostname"><?= e(t('system.hostname')) ?></label>
                        <input class="form-control" id="hostname" name="hostname" autocapitalize="none" required>
                        <div class="form-text"><?= e(t('system.hostname_help')) ?></div>
                    </div>
                    <div class="col-md-6">
                        <label class="form-label" for="timezone"><?= e(t('system.timezone')) ?></label>
                        <select class="form-select" id="timezone" name="timezone"></select>
                    </div>
                </div>
                <button class="btn btn-primary mt-4" type="submit"><?= e(t('common.save_continue')) ?></button>
            </form>
        </section>

        <!-- Step: USB stick -->
        <section data-screen="usb" hidden>
            <p><?= e(t('setup.usb_intro')) ?></p>
            <div class="alert alert-warning small" data-usb-unavailable hidden></div>
            <form data-setup-form novalidate>
                <input type="hidden" name="step" value="usb">
                <div class="row g-3">
                    <div class="col-md-6">
                        <label class="form-label" for="size_mb"><?= e(t('usb.size_mb')) ?></label>
                        <input class="form-control" id="size_mb" name="size_mb" type="number" min="64" data-type="int">
                        <div class="form-text" data-size-help
                             data-template="<?= e(t('usb.size_help', ['max' => '{value}'])) ?>"></div>
                    </div>
                    <div class="col-md-6">
                        <label class="form-label" for="filesystem"><?= e(t('usb.filesystem')) ?></label>
                        <select class="form-select" id="filesystem" name="filesystem">
                            <option value="exfat">exFAT</option>
                            <option value="vfat">FAT32</option>
                        </select>
                        <div class="form-text"><?= e(t('usb.filesystem_help')) ?></div>
                    </div>
                    <div class="col-md-6">
                        <label class="form-label" for="label"><?= e(t('usb.label')) ?></label>
                        <input class="form-control text-uppercase" id="label" name="label" maxlength="11">
                    </div>
                    <div class="col-md-6">
                        <label class="form-label" for="idle_seconds"><?= e(t('usb.idle_seconds')) ?></label>
                        <input class="form-control" id="idle_seconds" name="idle_seconds" type="number" min="5" max="3600" data-type="int">
                    </div>
                    <div class="col-12">
                        <span class="form-label d-block"><?= e(t('usb.sync_mode')) ?></span>
                        <?php foreach (['detach', 'live'] as $mode): ?>
                            <div class="form-check">
                                <input class="form-check-input" type="radio" name="sync_mode" id="sync_<?= e($mode) ?>" value="<?= e($mode) ?>">
                                <label class="form-check-label" for="sync_<?= e($mode) ?>">
                                    <?= e(t('usb.sync_' . $mode)) ?><br><span class="small text-body-secondary"><?= e(t('usb.sync_' . $mode . '_help')) ?></span>
                                </label>
                            </div>
                        <?php endforeach; ?>
                    </div>
                </div>
                <div class="alert alert-secondary small mt-3 mb-0"><?= e(t('setup.usb_create_note')) ?></div>
                <button class="btn btn-primary mt-4" type="submit"><?= e(t('setup.usb_create')) ?></button>
            </form>
        </section>

        <!-- Step: upload target -->
        <section data-screen="target" hidden>
            <p><?= e(t('setup.target_intro')) ?></p>
            <div data-test-result></div>
            <form data-setup-form novalidate>
                <input type="hidden" name="step" value="target">
                <?php require __DIR__ . '/partials/target_fields.php'; ?>
                <div class="d-flex flex-wrap gap-2 mt-4">
                    <button class="btn btn-primary" type="submit" name="action" value="save"><?= e(t('common.save_continue')) ?></button>
                    <button class="btn btn-outline-secondary" type="submit" name="action" value="test"><?= e(t('target.test')) ?></button>
                    <button class="btn btn-link ms-auto" type="submit" name="action" value="skip"><?= e(t('common.skip')) ?></button>
                </div>
            </form>
        </section>

        <!-- Step: email -->
        <section data-screen="smtp" hidden>
            <p><?= e(t('setup.smtp_intro')) ?></p>
            <form data-setup-form novalidate>
                <input type="hidden" name="step" value="smtp">
                <?php require __DIR__ . '/partials/smtp_fields.php'; ?>
                <div class="row g-2 mt-3 align-items-end">
                    <div class="col-md-8">
                        <label class="form-label" for="test_to"><?= e(t('smtp.test_to')) ?></label>
                        <input class="form-control" id="test_to" name="test_to" type="email">
                    </div>
                    <div class="col-md-4">
                        <button class="btn btn-outline-secondary w-100" type="submit" name="action" value="test"><?= e(t('smtp.send_test')) ?></button>
                    </div>
                </div>
                <div class="d-flex flex-wrap gap-2 mt-4">
                    <button class="btn btn-primary" type="submit" name="action" value="save"><?= e(t('common.save_continue')) ?></button>
                    <button class="btn btn-link ms-auto" type="submit" name="action" value="skip"><?= e(t('common.skip')) ?></button>
                </div>
            </form>
        </section>

        <!-- Step: finish -->
        <section data-screen="finish" hidden>
            <p><?= e(t('setup.finish_intro')) ?></p>
            <ul>
                <li><?= e(t('setup.finish_point_usb')) ?></li>
                <li><?= e(t('setup.finish_point_targets')) ?></li>
                <li><?= e(t('setup.finish_point_users')) ?></li>
            </ul>
            <form data-setup-form novalidate>
                <input type="hidden" name="step" value="finish">
                <button class="btn btn-success" type="submit"><?= e(t('setup.finish')) ?></button>
            </form>
        </section>
    </div>
</div>
