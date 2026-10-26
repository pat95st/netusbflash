<nav aria-label="breadcrumb">
    <ol class="breadcrumb">
        <li class="breadcrumb-item"><a href="/targets"><?= e(t('nav.targets')) ?></a></li>
        <li class="breadcrumb-item active" aria-current="page"><?= e($isNew ? t('target.add') : $v['name']) ?></li>
    </ol>
</nav>
<h1 class="h3 mb-4"><?= e($isNew ? t('target.add') : t('target.edit')) ?></h1>

<?php if ($testResult !== null): ?>
    <?php require __DIR__ . '/partials/test_result.php'; ?>
<?php endif; ?>

<form method="post" action="/targets/<?= e($isNew ? 'new' : $id) ?>" novalidate class="card">
    <?= csrf_field() ?>
    <div class="card-body">
        <?php require __DIR__ . '/partials/target_fields.php'; ?>
        <?php if ($sshKey !== null): ?>
            <div class="mt-4" data-protocols="sftp sshfs scp" data-auth="key">
                <label class="form-label" for="ssh_public_key"><?= e(t('target.public_key')) ?></label>
                <?php if ($sshKey !== ''): ?>
                    <textarea class="form-control font-monospace small" id="ssh_public_key" rows="2" readonly><?= e($sshKey) ?></textarea>
                    <div class="form-text"><?= e(t('target.public_key_help')) ?></div>
                <?php else: ?>
                    <div class="d-block">
                        <button class="btn btn-outline-secondary btn-sm" name="action" value="generate_key" formnovalidate><?= e(t('target.generate_key')) ?></button>
                    </div>
                <?php endif; ?>
            </div>
        <?php endif; ?>
    </div>
    <?php if (has_role('manager')): ?>
        <div class="card-footer bg-body d-flex flex-wrap gap-2">
            <button class="btn btn-primary" name="action" value="save"><?= e(t('common.save')) ?></button>
            <button class="btn btn-outline-secondary" name="action" value="test"><?= e(t('target.test')) ?></button>
            <a class="btn btn-link ms-auto" href="/targets"><?= e(t('common.cancel')) ?></a>
        </div>
    <?php endif; ?>
</form>
