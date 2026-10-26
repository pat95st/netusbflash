<h1 class="h3 mb-4"><?= e(t('nav.notifications')) ?></h1>

<div class="row g-4">
    <div class="col-xl-6">
        <form method="post" action="/notifications" novalidate class="card h-100">
            <?= csrf_field() ?>
            <div class="card-header bg-body fw-semibold"><?= e(t('smtp.title')) ?></div>
            <div class="card-body">
                <?php require __DIR__ . '/partials/smtp_fields.php'; ?>
            </div>
            <div class="card-footer bg-body">
                <button class="btn btn-primary" name="action" value="smtp_save"><?= e(t('common.save')) ?></button>
            </div>
        </form>
    </div>
    <div class="col-xl-6">
        <form method="post" action="/notifications" class="card mb-4">
            <?= csrf_field() ?>
            <div class="card-header bg-body fw-semibold"><?= e(t('smtp.send_test')) ?></div>
            <div class="card-body">
                <div class="input-group">
                    <input class="form-control" name="test_to" type="email" value="<?= e($userEmail) ?>" aria-label="<?= e(t('smtp.test_to')) ?>" placeholder="<?= e(t('smtp.test_to')) ?>">
                    <button class="btn btn-outline-secondary" name="action" value="smtp_test"><?= e(t('smtp.send_test')) ?></button>
                </div>
                <div class="form-text"><?= e(t('smtp.test_help')) ?></div>
            </div>
        </form>

        <div class="card">
            <div class="card-header bg-body fw-semibold"><?= e(t('mail.queue')) ?></div>
            <ul class="list-group list-group-flush small">
                <?php foreach ($queue as $m): ?>
                    <li class="list-group-item">
                        <div class="d-flex justify-content-between gap-2">
                            <span class="text-break"><?= e($m['subject']) ?></span>
                            <?php if ($m['sent_at']): ?>
                                <span class="badge text-bg-success"><?= e(t('mail.sent')) ?></span>
                            <?php else: ?>
                                <span class="badge text-bg-<?= $m['last_error'] ? 'danger' : 'info' ?>"><?= e($m['last_error'] ? t('mail.retrying') : t('mail.queued')) ?></span>
                            <?php endif; ?>
                        </div>
                        <div class="text-body-secondary"><?= e(fmt_time($m['sent_at'] ?? $m['created_at'])) ?> · <?= e($m['recipients']) ?></div>
                        <?php if (!$m['sent_at'] && $m['last_error']): ?><div class="text-danger text-break"><?= e($m['last_error']) ?></div><?php endif; ?>
                    </li>
                <?php endforeach; ?>
                <?php if (!$queue): ?>
                    <li class="list-group-item text-body-secondary"><?= e(t('mail.none')) ?></li>
                <?php endif; ?>
            </ul>
        </div>
    </div>
</div>

<div class="d-flex flex-wrap justify-content-between align-items-center gap-2 mt-5 mb-3">
    <h2 class="h4 mb-0"><?= e(t('rule.title')) ?></h2>
    <a class="btn btn-primary" href="/notifications?rule=0#rule-form"><i class="bi bi-plus-lg" aria-hidden="true"></i> <?= e(t('rule.add')) ?></a>
</div>
<p class="text-body-secondary"><?= e(t('rule.intro')) ?></p>

<div class="card mb-4">
    <div class="table-responsive">
        <table class="table align-middle mb-0">
            <thead><tr>
                <th><?= e(t('rule.name')) ?></th>
                <th><?= e(t('rule.events')) ?></th>
                <th><?= e(t('rule.recipients')) ?></th>
                <th><?= e(t('rule.mode')) ?></th>
                <th></th>
            </tr></thead>
            <tbody>
            <?php foreach ($rules as $rule): ?>
                <tr class="<?= $rule['enabled'] ? '' : 'text-body-secondary' ?>">
                    <td class="fw-semibold"><?= e($rule['name']) ?><?php if (!$rule['enabled']): ?> <span class="badge text-bg-secondary"><?= e(t('common.disabled')) ?></span><?php endif; ?>
                        <div class="small text-body-secondary font-monospace"><?= e($rule['pattern']) ?></div></td>
                    <td class="small"><?= e(implode(', ', array_map(fn($ev) => t('event.' . $ev), $rule['events']))) ?></td>
                    <td class="small text-break"><?= e(implode(', ', $rule['recipients'])) ?></td>
                    <td class="small"><?= e($rule['mode'] === 'digest' ? t('rule.digest_every', ['n' => $rule['digest_minutes']]) : t('rule.instant')) ?></td>
                    <td class="text-end text-nowrap">
                        <a class="btn btn-sm btn-outline-primary" href="/notifications?rule=<?= e($rule['id']) ?>#rule-form"><?= e(t('common.edit')) ?></a>
                        <form method="post" action="/notifications" class="d-inline">
                            <?= csrf_field() ?>
                            <input type="hidden" name="id" value="<?= e($rule['id']) ?>">
                            <button class="btn btn-sm btn-outline-danger" name="action" value="rule_delete" data-confirm="<?= e(t('rule.delete_confirm')) ?>"><?= e(t('common.delete')) ?></button>
                        </form>
                    </td>
                </tr>
            <?php endforeach; ?>
            <?php if (!$rules): ?>
                <tr><td colspan="5" class="text-body-secondary p-3"><?= e(t('rule.none')) ?></td></tr>
            <?php endif; ?>
            </tbody>
        </table>
    </div>
</div>

<?php if ($showRuleForm): ?>
<form method="post" action="/notifications" novalidate class="card" id="rule-form">
    <?= csrf_field() ?>
    <input type="hidden" name="id" value="<?= e($rv['id']) ?>">
    <div class="card-header bg-body fw-semibold"><?= e($rv['id'] ? t('rule.edit') : t('rule.add')) ?></div>
    <div class="card-body">
        <div class="row g-3">
            <div class="col-md-6">
                <label class="form-label" for="rule_name"><?= e(t('rule.name')) ?></label>
                <input class="form-control<?= invalid($ruleErrors, 'name') ?>" id="rule_name" name="name" value="<?= e($rv['name']) ?>" maxlength="64">
                <?= feedback($ruleErrors, 'name') ?>
            </div>
            <div class="col-md-6">
                <label class="form-label" for="rule_pattern"><?= e(t('rule.pattern')) ?></label>
                <input class="form-control" id="rule_pattern" name="pattern" value="<?= e($rv['pattern']) ?>" placeholder="*.wav">
                <div class="form-text"><?= e(t('rule.pattern_help')) ?></div>
            </div>
            <div class="col-12">
                <span class="form-label d-block<?= isset($ruleErrors['events']) ? ' text-danger' : '' ?>"><?= e(t('rule.events')) ?></span>
                <?php foreach ($eventTypes as $ev): ?>
                    <div class="form-check form-check-inline">
                        <input class="form-check-input" type="checkbox" name="events[]" id="ev_<?= e($ev) ?>" value="<?= e($ev) ?>"<?= checked(in_array($ev, (array) $rv['events'], true)) ?>>
                        <label class="form-check-label" for="ev_<?= e($ev) ?>"><?= e(t('event.' . $ev)) ?></label>
                    </div>
                <?php endforeach; ?>
                <?php if (isset($ruleErrors['events'])): ?><div class="small text-danger"><?= e(t('rule.events_required')) ?></div><?php endif; ?>
            </div>
            <div class="col-12">
                <label class="form-label" for="rule_recipients"><?= e(t('rule.recipients')) ?></label>
                <input class="form-control<?= invalid($ruleErrors, 'recipients') ?>" id="rule_recipients" name="recipients" value="<?= e(is_array($rv['recipients']) ? implode(', ', $rv['recipients']) : $rv['recipients']) ?>">
                <div class="form-text"><?= e(t('rule.recipients_help')) ?></div>
                <?= feedback($ruleErrors, 'recipients') ?>
            </div>
            <div class="col-md-6">
                <span class="form-label d-block"><?= e(t('rule.mode')) ?></span>
                <div class="form-check">
                    <input class="form-check-input" type="radio" name="mode" id="mode_instant" value="instant"<?= checked($rv['mode'] === 'instant') ?>>
                    <label class="form-check-label" for="mode_instant"><?= e(t('rule.instant')) ?></label>
                </div>
                <div class="form-check">
                    <input class="form-check-input" type="radio" name="mode" id="mode_digest" value="digest"<?= checked($rv['mode'] === 'digest') ?>>
                    <label class="form-check-label" for="mode_digest"><?= e(t('rule.digest')) ?></label>
                </div>
            </div>
            <div class="col-md-6">
                <label class="form-label" for="digest_minutes"><?= e(t('rule.digest_minutes')) ?></label>
                <input class="form-control<?= invalid($ruleErrors, 'digest_minutes') ?>" id="digest_minutes" name="digest_minutes" type="number" min="5" max="10080" value="<?= e($rv['digest_minutes']) ?>">
                <?= feedback($ruleErrors, 'digest_minutes') ?>
            </div>
            <div class="col-12">
                <div class="form-check form-switch">
                    <input class="form-check-input" type="checkbox" role="switch" id="rule_enabled" name="enabled" value="1"<?= checked($rv['enabled']) ?>>
                    <label class="form-check-label" for="rule_enabled"><?= e(t('rule.enabled')) ?></label>
                </div>
            </div>
        </div>
    </div>
    <div class="card-footer bg-body d-flex gap-2">
        <button class="btn btn-primary" name="action" value="rule_save"><?= e(t('common.save')) ?></button>
        <a class="btn btn-link" href="/notifications"><?= e(t('common.cancel')) ?></a>
    </div>
</form>
<?php endif; ?>
