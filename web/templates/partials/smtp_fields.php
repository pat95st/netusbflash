<?php /** SMTP form fields. Names match the API; values are filled by JavaScript. */ ?>
<div class="row g-3">
    <div class="col-md-8">
        <label class="form-label" for="smtp_host"><?= e(t('smtp.host')) ?></label>
        <input class="form-control" id="smtp_host" name="host" placeholder="smtp.example.com" autocapitalize="none">
    </div>
    <div class="col-md-4">
        <label class="form-label" for="smtp_port"><?= e(t('target.port')) ?></label>
        <input class="form-control" id="smtp_port" name="port" data-type="int" value="587" inputmode="numeric">
    </div>
    <div class="col-md-6">
        <label class="form-label" for="smtp_security"><?= e(t('smtp.security')) ?></label>
        <select class="form-select" id="smtp_security" name="security">
            <?= select_options(['starttls' => t('smtp.starttls'), 'ssl' => t('smtp.ssl'), 'none' => t('smtp.none')], 'starttls') ?>
        </select>
    </div>
    <div class="col-md-6 d-flex align-items-end">
        <div class="form-check mb-2">
            <input class="form-check-input" type="checkbox" id="smtp_verify_tls" name="verify_tls" value="1" checked>
            <label class="form-check-label" for="smtp_verify_tls"><?= e(t('smtp.verify_tls')) ?></label>
        </div>
    </div>
    <div class="col-md-6">
        <label class="form-label" for="smtp_username"><?= e(t('field.username')) ?></label>
        <input class="form-control" id="smtp_username" name="username" autocomplete="off" autocapitalize="none">
    </div>
    <div class="col-md-6">
        <label class="form-label" for="smtp_password"><?= e(t('field.password')) ?></label>
        <input class="form-control" id="smtp_password" name="password" type="password" autocomplete="new-password"
               data-placeholder-saved="<?= e(t('target.password_keep')) ?>">
        <div class="form-check mt-1" data-saved-password hidden>
            <input class="form-check-input" type="checkbox" id="smtp_clear_password" name="clear_password" value="1">
            <label class="form-check-label small" for="smtp_clear_password"><?= e(t('target.password_clear')) ?></label>
        </div>
        <div class="form-text"><?= e(t('smtp.app_password_help')) ?></div>
    </div>
    <div class="col-md-6">
        <label class="form-label" for="smtp_sender"><?= e(t('smtp.sender')) ?></label>
        <input class="form-control" id="smtp_sender" name="sender" type="email" placeholder="netusbflash@example.com">
    </div>
    <div class="col-md-6">
        <label class="form-label" for="smtp_sender_name"><?= e(t('smtp.sender_name')) ?></label>
        <input class="form-control" id="smtp_sender_name" name="sender_name" value="NetUSBFlash">
    </div>
</div>
