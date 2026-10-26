<?php
/**
 * Target form fields. Expects $v (values) and $errors.
 * Elements with data-protocols are shown only for the listed protocols (app.js).
 */
$protocolLabels = [];
foreach (PROTOCOLS as $p) {
    $protocolLabels[$p] = t('protocol.' . $p);
}
?>
<div class="row g-3" data-target-form>
    <div class="col-md-6">
        <label class="form-label" for="name"><?= e(t('target.name')) ?></label>
        <input class="form-control<?= invalid($errors, 'name') ?>" id="name" name="name" value="<?= e($v['name']) ?>" maxlength="64" required>
        <?= feedback($errors, 'name') ?>
    </div>
    <div class="col-md-6">
        <label class="form-label" for="protocol"><?= e(t('target.protocol')) ?></label>
        <select class="form-select<?= invalid($errors, 'protocol') ?>" id="protocol" name="protocol" data-protocol-select>
            <?= select_options($protocolLabels, $v['protocol']) ?>
        </select>
        <?= feedback($errors, 'protocol') ?>
    </div>

    <div class="col-md-8" data-protocols="smb ftp ftps sftp sshfs scp">
        <label class="form-label" for="host"><?= e(t('target.host')) ?></label>
        <input class="form-control<?= invalid($errors, 'host') ?>" id="host" name="host" value="<?= e($v['host']) ?>"
               placeholder="nas.local" autocapitalize="none" data-host-input>
        <?= feedback($errors, 'host') ?>
    </div>
    <div class="col-md-4" data-protocols="smb ftp ftps sftp sshfs scp">
        <label class="form-label" for="port"><?= e(t('target.port')) ?></label>
        <input class="form-control<?= invalid($errors, 'port') ?>" id="port" name="port" value="<?= e($v['port']) ?>"
               inputmode="numeric" placeholder="<?= e(t('target.port_default')) ?>">
        <?= feedback($errors, 'port') ?>
    </div>
    <div class="col-12" data-protocols="webdav">
        <label class="form-label" for="host_url"><?= e(t('target.url')) ?></label>
        <input class="form-control<?= invalid($errors, 'host') ?>" id="host_url" name="host_url" value="<?= e($v['host']) ?>"
               placeholder="https://cloud.example.com/remote.php/dav/files/USER/" autocapitalize="none" data-url-input>
        <div class="form-text"><?= e(t('target.url_help')) ?></div>
        <?= feedback($errors, 'host') ?>
    </div>

    <div class="col-12">
        <label class="form-label" for="path"><?= e(t('target.path')) ?></label>
        <input class="form-control<?= invalid($errors, 'path') ?>" id="path" name="path" value="<?= e($v['path']) ?>" autocapitalize="none">
        <div class="form-text" data-protocols="smb"><?= e(t('target.path_help_smb')) ?></div>
        <div class="form-text" data-protocols="webdav ftp ftps sftp sshfs scp"><?= e(t('target.path_help_remote')) ?></div>
        <div class="form-text" data-protocols="local"><?= e(t('target.path_help_local')) ?></div>
        <?= feedback($errors, 'path') ?>
    </div>

    <div class="col-md-6" data-protocols="smb webdav ftp ftps sftp sshfs scp">
        <label class="form-label" for="username"><?= e(t('field.username')) ?></label>
        <input class="form-control<?= invalid($errors, 'username') ?>" id="username" name="username" value="<?= e($v['username']) ?>"
               autocomplete="off" autocapitalize="none">
        <?= feedback($errors, 'username') ?>
    </div>
    <div class="col-md-6" data-protocols="sftp sshfs scp">
        <label class="form-label" for="opt_auth"><?= e(t('target.auth')) ?></label>
        <select class="form-select" id="opt_auth" name="opt_auth" data-auth-select>
            <?= select_options(['password' => t('target.auth_password'), 'key' => t('target.auth_key')], $v['opt_auth']) ?>
        </select>
        <div class="form-text" data-auth="key"><?= e(t('target.auth_key_help')) ?></div>
    </div>
    <div class="col-md-6" data-protocols="smb webdav ftp ftps sftp sshfs scp" data-auth="password">
        <label class="form-label" for="password"><?= e(t('field.password')) ?></label>
        <input class="form-control<?= invalid($errors, 'password') ?>" id="password" name="password" type="password"
               autocomplete="new-password" placeholder="<?= !empty($v['has_password']) ? e(t('target.password_keep')) : '' ?>">
        <?php if (!empty($v['has_password'])): ?>
            <div class="form-check mt-1">
                <input class="form-check-input" type="checkbox" id="clear_password" name="clear_password" value="1">
                <label class="form-check-label small" for="clear_password"><?= e(t('target.password_clear')) ?></label>
            </div>
        <?php endif; ?>
        <div class="form-text" data-protocols="webdav"><?= e(t('target.nextcloud_app_password')) ?></div>
        <?= feedback($errors, 'password') ?>
    </div>

    <div class="col-md-6" data-protocols="smb">
        <label class="form-label" for="opt_domain"><?= e(t('target.domain')) ?></label>
        <input class="form-control<?= invalid($errors, 'opt_domain') ?>" id="opt_domain" name="opt_domain" value="<?= e($v['opt_domain']) ?>">
        <div class="form-text"><?= e(t('target.domain_help')) ?></div>
    </div>
    <div class="col-md-6" data-protocols="webdav">
        <label class="form-label" for="opt_vendor"><?= e(t('target.vendor')) ?></label>
        <select class="form-select" id="opt_vendor" name="opt_vendor">
            <?= select_options(['other' => t('target.vendor_other'), 'nextcloud' => 'Nextcloud', 'owncloud' => 'ownCloud'], $v['opt_vendor']) ?>
        </select>
    </div>
    <div class="col-md-6" data-protocols="ftps">
        <label class="form-label" for="opt_tls_mode"><?= e(t('target.tls_mode')) ?></label>
        <select class="form-select" id="opt_tls_mode" name="opt_tls_mode">
            <?= select_options(['explicit' => t('target.tls_explicit'), 'implicit' => t('target.tls_implicit')], $v['opt_tls_mode']) ?>
        </select>
    </div>
    <div class="col-12" data-protocols="webdav ftps">
        <div class="form-check">
            <input class="form-check-input" type="checkbox" id="opt_insecure_tls" name="opt_insecure_tls" value="1"<?= checked($v['opt_insecure_tls']) ?>>
            <label class="form-check-label" for="opt_insecure_tls"><?= e(t('target.insecure_tls')) ?></label>
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
        <label class="form-label" for="opt_subfolder"><?= e(t('target.subfolder')) ?></label>
        <input class="form-control<?= invalid($errors, 'opt_subfolder') ?>" id="opt_subfolder" name="opt_subfolder" value="<?= e($v['opt_subfolder']) ?>">
        <div class="form-text"><?= e(t('target.subfolder_help')) ?></div>
        <?= feedback($errors, 'opt_subfolder') ?>
    </div>
    <div class="col-md-6" data-protocols="smb webdav ftp ftps sftp sshfs">
        <label class="form-label" for="opt_bwlimit"><?= e(t('target.bwlimit')) ?></label>
        <input class="form-control<?= invalid($errors, 'opt_bwlimit') ?>" id="opt_bwlimit" name="opt_bwlimit" value="<?= e($v['opt_bwlimit']) ?>" placeholder="5M">
        <div class="form-text"><?= e(t('target.bwlimit_help')) ?></div>
        <?= feedback($errors, 'opt_bwlimit') ?>
    </div>
    <div class="col-12">
        <div class="form-check">
            <input class="form-check-input" type="checkbox" id="opt_keep_structure" name="opt_keep_structure" value="1"<?= checked($v['opt_keep_structure']) ?>>
            <label class="form-check-label" for="opt_keep_structure"><?= e(t('target.keep_structure')) ?></label>
        </div>
        <input type="hidden" name="enabled_present" value="1">
        <div class="form-check">
            <input class="form-check-input" type="checkbox" id="enabled" name="enabled" value="1"<?= checked($v['enabled']) ?>>
            <label class="form-check-label" for="enabled"><?= e(t('target.enabled')) ?></label>
        </div>
    </div>
</div>
