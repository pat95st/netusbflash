<?php foreach (take_flashes() as $flash): ?>
    <div class="alert alert-<?= e($flash['type']) ?> alert-dismissible fade show" role="alert">
        <?= nl2br(e($flash['message'])) ?>
        <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="<?= e(t('common.close')) ?>"></button>
    </div>
<?php endforeach; ?>
