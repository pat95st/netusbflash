<?php
/**
 * @var string $screen 'code' | 'step'
 * @var list<string> $steps
 * @var ?string $step
 * @var array $errors
 * @var array $old
 */
$current = $step === null ? -1 : array_search($step, $steps, true);
?>
<div class="card shadow-sm mx-auto wizard-card">
    <div class="card-header bg-body">
        <div class="d-flex justify-content-between align-items-center">
            <h2 class="h5 mb-0"><?= e(t('setup.title')) ?></h2>
            <?php if ($current >= 0): ?>
                <span class="text-body-secondary small"><?= e(t('setup.step_of', ['n' => $current + 1, 'total' => count($steps)])) ?></span>
            <?php endif; ?>
        </div>
        <?php if ($current >= 0): ?>
        <ol class="wizard-steps list-unstyled d-flex flex-wrap gap-2 mt-3 mb-1">
            <?php foreach ($steps as $i => $s): ?>
                <li>
                    <?php if ($i < $current): ?>
                        <a class="badge rounded-pill text-bg-success text-decoration-none" href="/setup?goto=<?= e($s) ?>"><?= e(t('setup.step.' . $s)) ?></a>
                    <?php elseif ($i === $current): ?>
                        <span class="badge rounded-pill text-bg-primary"><?= e(t('setup.step.' . $s)) ?></span>
                    <?php else: ?>
                        <span class="badge rounded-pill text-bg-light border"><?= e(t('setup.step.' . $s)) ?></span>
                    <?php endif; ?>
                </li>
            <?php endforeach; ?>
        </ol>
        <?php endif; ?>
    </div>
    <div class="card-body p-4">
        <?php if (!empty($simulated)): ?>
            <div class="alert alert-info small"><?= e(t('common.simulation_notice')) ?></div>
        <?php endif; ?>
        <?php if (!empty($notice)): ?>
            <div class="alert alert-<?= e($notice[0]) ?>"><?= e($notice[1]) ?></div>
        <?php endif; ?>

        <?php if ($screen === 'code'): ?>
            <p><?= e(t('setup.welcome')) ?></p>
            <div class="mb-3">
                <span class="form-label d-block"><?= e(t('setup.language')) ?></span>
                <div class="btn-group" role="group">
                    <?php foreach (I18n::LOCALES as $code => $name): ?>
                        <a class="btn btn-outline-primary<?= I18n::locale() === $code ? ' active' : '' ?>" href="/lang/<?= e($code) ?>"><?= e($name) ?></a>
                    <?php endforeach; ?>
                </div>
            </div>
            <form method="post" action="/setup" novalidate>
                <?= csrf_field() ?>
                <label class="form-label" for="code"><?= e(t('setup.code')) ?></label>
                <input class="form-control form-control-lg font-monospace<?= invalid($errors, 'code') ?>" id="code" name="code"
                       placeholder="XXXX-XXXX-XXXX" autocomplete="off" autocapitalize="characters" required autofocus>
                <?= feedback($errors, 'code') ?>
                <div class="form-text"><?= e(t('setup.code_help')) ?></div>
                <button class="btn btn-primary mt-3" type="submit"><?= e(t('common.continue')) ?></button>
            </form>

        <?php elseif ($step === 'admin'): ?>
            <p><?= e(t('setup.admin_intro')) ?></p>
            <form method="post" action="/setup" novalidate>
                <?= csrf_field() ?>
                <div class="row g-3">
                    <div class="col-md-6">
                        <label class="form-label" for="username"><?= e(t('field.username')) ?></label>
                        <input class="form-control<?= invalid($errors, 'username') ?>" id="username" name="username" value="<?= e($old['username'] ?? 'admin') ?>" autocapitalize="none" required>
                        <?= feedback($errors, 'username') ?>
                    </div>
                    <div class="col-md-6">
                        <label class="form-label" for="email"><?= e(t('field.email')) ?></label>
                        <input class="form-control<?= invalid($errors, 'email') ?>" id="email" name="email" type="email" value="<?= e($old['email'] ?? '') ?>">
                        <?= feedback($errors, 'email') ?>
                    </div>
                    <div class="col-md-6">
                        <label class="form-label" for="password"><?= e(t('field.password')) ?></label>
                        <input class="form-control<?= invalid($errors, 'password') ?>" id="password" name="password" type="password" autocomplete="new-password" minlength="12" required>
                        <?= feedback($errors, 'password') ?>
                        <div class="form-text"><?= e(t('field.password_help')) ?></div>
                    </div>
                    <div class="col-md-6">
                        <label class="form-label" for="password_confirm"><?= e(t('field.password_confirm')) ?></label>
                        <input class="form-control<?= invalid($errors, 'password_confirm') ?>" id="password_confirm" name="password_confirm" type="password" autocomplete="new-password" required>
                        <?= feedback($errors, 'password_confirm') ?>
                    </div>
                </div>
                <button class="btn btn-primary mt-4" type="submit"><?= e(t('common.save_continue')) ?></button>
            </form>

        <?php elseif ($step === 'system'): ?>
            <p><?= e(t('setup.system_intro')) ?></p>
            <form method="post" action="/setup" novalidate>
                <?= csrf_field() ?>
                <div class="row g-3">
                    <div class="col-md-6">
                        <label class="form-label" for="hostname"><?= e(t('system.hostname')) ?></label>
                        <input class="form-control<?= invalid($errors, 'hostname') ?>" id="hostname" name="hostname"
                               value="<?= e($old['hostname'] ?? ($data['hostname'] ?? 'netusbflash')) ?>" autocapitalize="none" required>
                        <?= feedback($errors, 'hostname') ?>
                        <div class="form-text"><?= e(t('system.hostname_help')) ?></div>
                    </div>
                    <div class="col-md-6">
                        <label class="form-label" for="timezone"><?= e(t('system.timezone')) ?></label>
                        <select class="form-select<?= invalid($errors, 'timezone') ?>" id="timezone" name="timezone">
                            <?php $tzs = array_combine($data['timezones'] ?? ['UTC'], $data['timezones'] ?? ['UTC']); ?>
                            <?= select_options($tzs, $old['timezone'] ?? ($data['current'] ?? 'Europe/Berlin')) ?>
                        </select>
                        <?= feedback($errors, 'timezone') ?>
                    </div>
                </div>
                <button class="btn btn-primary mt-4" type="submit"><?= e(t('common.save_continue')) ?></button>
            </form>

        <?php elseif ($step === 'usb'): ?>
            <?php $s = $data['settings'] ?? []; ?>
            <p><?= e(t('setup.usb_intro')) ?></p>
            <?php if (isset($data['available']) && !$data['available']): ?>
                <div class="alert alert-warning small"><?= e(t('usb.unavailable', ['reason' => $data['unavailable_reason'] ?? ''])) ?></div>
            <?php endif; ?>
            <form method="post" action="/setup" novalidate>
                <?= csrf_field() ?>
                <div class="row g-3">
                    <div class="col-md-6">
                        <label class="form-label" for="size_mb"><?= e(t('usb.size_mb')) ?></label>
                        <input class="form-control<?= invalid($errors, 'size_mb') ?>" id="size_mb" name="size_mb" type="number" min="64"
                               max="<?= e($data['max_size_mb'] ?? '') ?>" value="<?= e($old['size_mb'] ?? min((int) ($s['size_mb'] ?? 4096), (int) ($data['max_size_mb'] ?? 4096))) ?>">
                        <?= feedback($errors, 'size_mb') ?>
                        <div class="form-text"><?= e(t('usb.size_help', ['max' => $data['max_size_mb'] ?? '?'])) ?></div>
                    </div>
                    <div class="col-md-6">
                        <label class="form-label" for="filesystem"><?= e(t('usb.filesystem')) ?></label>
                        <select class="form-select" id="filesystem" name="filesystem">
                            <?= select_options(['exfat' => 'exFAT', 'vfat' => 'FAT32'], $old['filesystem'] ?? ($s['filesystem'] ?? 'exfat')) ?>
                        </select>
                        <div class="form-text"><?= e(t('usb.filesystem_help')) ?></div>
                    </div>
                    <div class="col-md-6">
                        <label class="form-label" for="label"><?= e(t('usb.label')) ?></label>
                        <input class="form-control text-uppercase<?= invalid($errors, 'label') ?>" id="label" name="label" maxlength="11"
                               value="<?= e($old['label'] ?? ($s['label'] ?? 'RECORDINGS')) ?>">
                        <?= feedback($errors, 'label') ?>
                    </div>
                    <div class="col-md-6">
                        <label class="form-label" for="idle_seconds"><?= e(t('usb.idle_seconds')) ?></label>
                        <input class="form-control<?= invalid($errors, 'idle_seconds') ?>" id="idle_seconds" name="idle_seconds" type="number" min="5" max="3600"
                               value="<?= e($old['idle_seconds'] ?? ($s['idle_seconds'] ?? 30)) ?>">
                        <?= feedback($errors, 'idle_seconds') ?>
                    </div>
                    <div class="col-12">
                        <span class="form-label d-block"><?= e(t('usb.sync_mode')) ?></span>
                        <?php foreach (['detach', 'live'] as $mode): ?>
                            <div class="form-check">
                                <input class="form-check-input" type="radio" name="sync_mode" id="sync_<?= e($mode) ?>" value="<?= e($mode) ?>"
                                    <?= checked(($old['sync_mode'] ?? ($s['sync_mode'] ?? 'detach')) === $mode) ?>>
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

        <?php elseif ($step === 'target'): ?>
            <p><?= e(t('setup.target_intro')) ?></p>
            <?php
            $v = is_post() ? posted_target_values() : target_form_values(['protocol' => 'smb', 'enabled' => true, 'options' => []]);
            ?>
            <?php if ($testResult !== null): ?>
                <?php require __DIR__ . '/partials/test_result.php'; ?>
            <?php endif; ?>
            <form method="post" action="/setup" novalidate>
                <?= csrf_field() ?>
                <?php require __DIR__ . '/partials/target_fields.php'; ?>
                <div class="d-flex flex-wrap gap-2 mt-4">
                    <button class="btn btn-primary" type="submit" name="action" value="save"><?= e(t('common.save_continue')) ?></button>
                    <button class="btn btn-outline-secondary" type="submit" name="action" value="test"><?= e(t('target.test')) ?></button>
                    <button class="btn btn-link ms-auto" type="submit" name="action" value="skip" formnovalidate><?= e(t('common.skip')) ?></button>
                </div>
            </form>

        <?php elseif ($step === 'smtp'): ?>
            <p><?= e(t('setup.smtp_intro')) ?></p>
            <?php $v = is_post() ? posted_smtp_values() : smtp_form_values([]); ?>
            <form method="post" action="/setup" novalidate>
                <?= csrf_field() ?>
                <?php require __DIR__ . '/partials/smtp_fields.php'; ?>
                <div class="row g-2 mt-3 align-items-end">
                    <div class="col-md-8">
                        <label class="form-label" for="test_to"><?= e(t('smtp.test_to')) ?></label>
                        <input class="form-control" id="test_to" name="test_to" type="email" value="<?= e($old['test_to'] ?? '') ?>">
                    </div>
                    <div class="col-md-4">
                        <button class="btn btn-outline-secondary w-100" type="submit" name="action" value="test"><?= e(t('smtp.send_test')) ?></button>
                    </div>
                </div>
                <div class="d-flex flex-wrap gap-2 mt-4">
                    <button class="btn btn-primary" type="submit" name="action" value="save"><?= e(t('common.save_continue')) ?></button>
                    <button class="btn btn-link ms-auto" type="submit" name="action" value="skip" formnovalidate><?= e(t('common.skip')) ?></button>
                </div>
            </form>

        <?php elseif ($step === 'finish'): ?>
            <p><?= e(t('setup.finish_intro')) ?></p>
            <ul>
                <li><?= e(t('setup.finish_point_usb')) ?></li>
                <li><?= e(t('setup.finish_point_targets')) ?></li>
                <li><?= e(t('setup.finish_point_users')) ?></li>
            </ul>
            <form method="post" action="/setup">
                <?= csrf_field() ?>
                <button class="btn btn-success" type="submit"><?= e(t('setup.finish')) ?></button>
            </form>
        <?php endif; ?>
    </div>
</div>
