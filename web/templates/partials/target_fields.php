<?php
/**
 * Target form fields. Names match the API (options.* are nested).
 * Values are filled by JavaScript (NUF.fillForm); the defaults below are for new targets.
 * Elements with data-protocols are shown only for the listed protocols.
 */
$protocolLabels = [];
foreach (PROTOCOLS as $p) {
    $protocolLabels[$p] = t('protocol.' . $p);
}
?>
<div class="row g-3" data-target-form>
    <div class="col-md-6">
        <label class="form-label" for="t_name"><?= e(t('target.name')) ?></label>
        <input class="form-control" id="t_name" name="name" maxlength="64" required>
    </div>
    <div class="col-md-6">
        <label class="form-label" for="t_protocol"><?= e(t('target.protocol')) ?></label>
        <select class="form-select" id="t_protocol" name="protocol" data-protocol-select>
            <?= select_options($protocolLabels, 'smb') ?>
        </select>
    </div>

    <div class="col-md-8" data-protocols="smb ftp ftps sftp sshfs scp">
        <label class="form-label" for="t_host"><?= e(t('target.host')) ?></label>
        <input class="form-control" id="t_host" name="host" placeholder="nas.local" autocapitalize="none">
    </div>
    <div class="col-md-4" data-protocols="smb ftp ftps sftp sshfs scp">
        <label class="form-label" for="t_port"><?= e(t('target.port')) ?></label>
        <input class="form-control" id="t_port" name="port" data-type="int" inputmode="numeric" placeholder="<?= e(t('target.port_default')) ?>">
    </div>
    <div class="col-12" data-protocols="webdav">
        <label class="form-label" for="t_url"><?= e(t('target.url')) ?></label>
        <input class="form-control" id="t_url" name="host" placeholder="https://cloud.example.com/remote.php/dav/files/USER/" autocapitalize="none">
        <div class="form-text"><?= e(t('target.url_help')) ?></div>
    </div>

    <div class="col-12">
        <label class="form-label" for="t_path"><?= e(t('target.path')) ?></label>
        <input class="form-control" id="t_path" name="path" autocapitalize="none">
        <div class="form-text" data-protocols="smb"><?= e(t('target.path_help_smb')) ?></div>
        <div class="form-text" data-protocols="webdav ftp ftps sftp sshfs scp"><?= e(t('target.path_help_remote')) ?></div>
        <div class="form-text" data-protocols="local"><?= e(t('target.path_help_local')) ?></div>
    </div>

    <div class="col-md-6" data-protocols="smb webdav ftp ftps sftp sshfs scp">
        <label class="form-label" for="t_username"><?= e(t('field.username')) ?></label>
        <input class="form-control" id="t_username" name="username" autocomplete="off" autocapitalize="none">
    </div>
    <div class="col-md-6" data-protocols="sftp sshfs scp">
        <label class="form-label" for="t_auth"><?= e(t('target.auth')) ?></label>
        <select class="form-select" id="t_auth" name="options.auth" data-auth-select>
            <?= select_options(['password' => t('target.auth_password'), 'key' => t('target.auth_key')], 'password') ?>
        </select>
        <div class="form-text" data-auth="key"><?= e(t('target.auth_key_help')) ?></div>
    </div>
    <div class="col-md-6" data-protocols="smb webdav ftp ftps sftp sshfs scp" data-auth="password">
        <label class="form-label" for="t_password"><?= e(t('field.password')) ?></label>
        <input class="form-control" id="t_password" name="password" type="password" autocomplete="new-password"
               data-placeholder-saved="<?= e(t('target.password_keep')) ?>">
        <div class="form-check mt-1" data-saved-password hidden>
            <input class="form-check-input" type="checkbox" id="t_clear_password" name="clear_password" value="1">
            <label class="form-check-label small" for="t_clear_password"><?= e(t('target.password_clear')) ?></label>
        </div>
        <div class="form-text" data-protocols="webdav"><?= e(t('target.nextcloud_app_password')) ?></div>
    </div>

    <div class="col-md-6" data-protocols="smb">
        <label class="form-label" for="t_domain"><?= e(t('target.domain')) ?></label>
        <input class="form-control" id="t_domain" name="options.domain">
        <div class="form-text"><?= e(t('target.domain_help')) ?></div>
    </div>
    <div class="col-md-6" data-protocols="webdav">
        <label class="form-label" for="t_vendor"><?= e(t('target.vendor')) ?></label>
        <select class="form-select" id="t_vendor" name="options.vendor">
            <?= select_options(['other' => t('target.vendor_other'), 'nextcloud' => 'Nextcloud', 'owncloud' => 'ownCloud'], 'other') ?>
        </select>
    </div>
    <div class="col-md-6" data-protocols="ftps">
        <label class="form-label" for="t_tls_mode"><?= e(t('target.tls_mode')) ?></label>
        <select class="form-select" id="t_tls_mode" name="options.tls_mode">
            <?= select_options(['explicit' => t('target.tls_explicit'), 'implicit' => t('target.tls_implicit')], 'explicit') ?>
        </select>
    </div>
    <div class="col-12" data-protocols="webdav ftps">
        <div class="form-check">
            <input class="form-check-input" type="checkbox" id="t_insecure_tls" name="options.insecure_tls" value="1">
            <label class="form-check-label" for="t_insecure_tls"><?= e(t('target.insecure_tls')) ?></label>
        </div>
    </div>
    <div class="col-12" data-protocols="ftp">
        <div class="alert alert-warning small mb-0"><?= e(t('target.ftp_warning')) ?></div>
    </div>
    <div class="col-12" data-protocols="scp">
        <div class="form-text"><?= e(t('target.scp_help')) ?></div>
    </div>

    <div class="col-12"><hr class="my-1"></div>
    <div class="col-md-6">
        <label class="form-label" for="t_subfolder"><?= e(t('target.subfolder')) ?></label>
        <input class="form-control" id="t_subfolder" name="options.subfolder" value="{date}">
        <div class="form-text"><?= e(t('target.subfolder_help')) ?></div>
    </div>
    <div class="col-md-6" data-protocols="smb webdav ftp ftps sftp sshfs">
        <label class="form-label" for="t_bwlimit"><?= e(t('target.bwlimit')) ?></label>
        <input class="form-control" id="t_bwlimit" name="options.bwlimit" placeholder="5M">
        <div class="form-text"><?= e(t('target.bwlimit_help')) ?></div>
    </div>
    <div class="col-12">
        <div class="form-check">
            <input class="form-check-input" type="checkbox" id="t_keep_structure" name="options.keep_structure" value="1" checked>
            <label class="form-check-label" for="t_keep_structure"><?= e(t('target.keep_structure')) ?></label>
        </div>
        <div class="form-check">
            <input class="form-check-input" type="checkbox" id="t_enabled" name="enabled" value="1" checked>
            <label class="form-check-label" for="t_enabled"><?= e(t('target.enabled')) ?></label>
        </div>
    </div>
</div>
