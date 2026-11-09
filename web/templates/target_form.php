<div id="target-form" data-target-id="<?= e($id ?? '') ?>">
    <nav aria-label="breadcrumb">
        <ol class="breadcrumb">
            <li class="breadcrumb-item"><a href="/targets"><?= e(t('nav.targets')) ?></a></li>
            <li class="breadcrumb-item active" aria-current="page" data-title><?= e($isNew ? t('target.add') : t('target.edit')) ?></li>
        </ol>
    </nav>
    <h1 class="h3 mb-4"><?= e($isNew ? t('target.add') : t('target.edit')) ?></h1>

    <div data-test-result></div>

    <form class="card" novalidate>
        <fieldset class="card-body"<?= readonly_unless('manager') ?>>
            <?php require __DIR__ . '/partials/target_fields.php'; ?>
            <?php if (has_role('manager')): ?>
                <div class="mt-4" data-protocols="sftp sshfs scp" data-auth="key">
                    <span class="form-label d-block"><?= e(t('target.public_key')) ?></span>
                    <div data-key-present hidden>
                        <textarea class="form-control font-monospace small" rows="2" readonly data-public-key data-ignore
                                  aria-label="<?= e(t('target.public_key')) ?>"></textarea>
                        <div class="form-text"><?= e(t('target.public_key_help')) ?></div>
                    </div>
                    <button class="btn btn-outline-secondary btn-sm" type="button" data-generate-key hidden><?= e(t('target.generate_key')) ?></button>
                </div>
            <?php endif; ?>
        </fieldset>
        <?php if (has_role('manager')): ?>
            <div class="card-footer bg-body d-flex flex-wrap gap-2">
                <button class="btn btn-primary" type="submit" value="save"><?= e(t('common.save')) ?></button>
                <button class="btn btn-outline-secondary" type="submit" value="test"><?= e(t('target.test')) ?></button>
                <a class="btn btn-link ms-auto" href="/targets"><?= e(t('common.cancel')) ?></a>
            </div>
        <?php endif; ?>
    </form>
</div>
