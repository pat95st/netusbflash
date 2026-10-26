<div class="card mx-auto narrow-card">
    <div class="card-body text-center py-5">
        <p class="display-6 mb-2"><?= e($code) ?></p>
        <p class="mb-4"><?= e($message ?? t('error.generic', ['message' => ''])) ?></p>
        <a href="/" class="btn btn-primary"><?= e(t('common.back_home')) ?></a>
    </div>
</div>
