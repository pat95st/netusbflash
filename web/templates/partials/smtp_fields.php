<?php /** Expects $v (smtp_* values) and $errors. */ ?>
<div class="row g-3">
    <div class="col-md-8">
        <label class="form-label" for="smtp_host"><?= e(t('smtp.host')) ?></label>
        <input class="form-control<?= invalid($errors, 'smtp_host') ?>" id="smtp_host" name="smtp_host" value="<?= e($v['smtp_host']) ?>" placeholder="smtp.example.com" autocapitalize="none">
        <?= feedback($errors, 'smtp_host') ?>
    </div>
    <div class="col-md-4">
        <label class="form-label" for="smtp_port"><?= e(t('target.port')) ?></label>
        <input class="form-control<?= invalid($errors, 'smtp_port') ?>" id="smtp_port" name="smtp_port" value="<?= e($v['smtp_port']) ?>" inputmode="numeric">
        <?= feedback($errors, 'smtp_port') ?>
    </div>
    <div class="col-md-6">
        <label class="form-label" for="smtp_security"><?= e(t('smtp.security')) ?></label>
        <select class="form-select" id="smtp_security" name="smtp_security">
            <?= select_options(['starttls' => t('smtp.starttls'), 'ssl' => t('smtp.ssl'), 'none' => t('smtp.none')], $v['smtp_security']) ?>
        </select>
    </div>
    <div class="col-md-6 d-flex align-items-end">
        <div class="form-check mb-2">
            <input class="form-check-input" type="checkbox" id="smtp_verify_tls" name="smtp_verify_tls" value="1"<?= checked($v['smtp_verify_tls']) ?>>
            <label class="form-check-label" for="smtp_verify_tls"><?= e(t('smtp.verify_tls')) ?></label>
        </div>
    </div>
    <div class="col-md-6">
        <label class="form-label" for="smtp_username"><?= e(t('field.username')) ?></label>
        <input class="form-control<?= invalid($errors, 'smtp_username') ?>" id="smtp_username" name="smtp_username" value="<?= e($v['smtp_username']) ?>" autocomplete="off" autocapitalize="none">
        <?= feedback($errors, 'smtp_username') ?>
    </div>
    <div class="col-md-6">
        <label class="form-label" for="smtp_password"><?= e(t('field.password')) ?></label>
        <input class="form-control" id="smtp_password" name="smtp_password" type="password" autocomplete="new-password"
               placeholder="<?= !empty($v['smtp_has_password']) ? e(t('target.password_keep')) : '' ?>">
        <?php if (!empty($v['smtp_has_password'])): ?>
            <div class="form-check mt-1">
                <input class="form-check-input" type="checkbox" id="smtp_clear_password" name="smtp_clear_password" value="1">
                <label class="form-check-label small" for="smtp_clear_password"><?= e(t('target.password_clear')) ?></label>
            </div>
        <?php endif; ?>
        <div class="form-text"><?= e(t('smtp.app_password_help')) ?></div>
    </div>
    <div class="col-md-6">
        <label class="form-label" for="smtp_sender"><?= e(t('smtp.sender')) ?></label>
        <input class="form-control<?= invalid($errors, 'smtp_sender') ?>" id="smtp_sender" name="smtp_sender" value="<?= e($v['smtp_sender']) ?>" type="email" placeholder="netusbflash@example.com">
        <?= feedback($errors, 'smtp_sender') ?>
    </div>
    <div class="col-md-6">
        <label class="form-label" for="smtp_sender_name"><?= e(t('smtp.sender_name')) ?></label>
        <input class="form-control<?= invalid($errors, 'smtp_sender_name') ?>" id="smtp_sender_name" name="smtp_sender_name" value="<?= e($v['smtp_sender_name']) ?>">
    </div>
</div>
