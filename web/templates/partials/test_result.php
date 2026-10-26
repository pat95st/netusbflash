<?php /** Expects $testResult = ['ok' => bool, 'steps' => [...], 'error' => ?string, 'duration' => float] */ ?>
<?php if (!empty($testResult['ok'])): ?>
    <div class="alert alert-success">
        <strong><?= e(t('target.test_ok', ['seconds' => $testResult['duration'] ?? 0])) ?></strong>
        <ul class="mb-0 mt-1 small">
            <?php foreach ($testResult['steps'] ?? [] as $line): ?>
                <li><?= e($line) ?></li>
            <?php endforeach; ?>
        </ul>
    </div>
<?php else: ?>
    <div class="alert alert-danger">
        <strong><?= e(t('target.test_failed')) ?></strong>
        <div class="small font-monospace mt-1 text-break"><?= e($testResult['error'] ?? '') ?></div>
    </div>
<?php endif; ?>
