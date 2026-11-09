<?php $eventTypes = ['created', 'modified', 'deleted', 'uploaded', 'upload_failed']; ?>
<div id="notifications" data-user-email="<?= e($userEmail) ?>">
    <h1 class="h3 mb-4"><?= e(t('nav.notifications')) ?></h1>

    <div class="row g-4">
        <div class="col-xl-6">
            <form class="card h-100" data-smtp-form novalidate>
                <div class="card-header bg-body fw-semibold"><?= e(t('smtp.title')) ?></div>
                <div class="card-body">
                    <?php require __DIR__ . '/partials/smtp_fields.php'; ?>
                </div>
                <div class="card-footer bg-body">
                    <button class="btn btn-primary" type="submit"><?= e(t('common.save')) ?></button>
                </div>
            </form>
        </div>
        <div class="col-xl-6">
            <form class="card mb-4" data-test-form novalidate>
                <div class="card-header bg-body fw-semibold"><?= e(t('smtp.send_test')) ?></div>
                <div class="card-body">
                    <div class="input-group">
                        <input class="form-control" name="to" type="email" value="<?= e($userEmail) ?>"
                               aria-label="<?= e(t('smtp.test_to')) ?>" placeholder="<?= e(t('smtp.test_to')) ?>">
                        <button class="btn btn-outline-secondary" type="submit"><?= e(t('smtp.send_test')) ?></button>
                    </div>
                    <div class="form-text"><?= e(t('smtp.test_help')) ?></div>
                </div>
            </form>

            <div class="card">
                <div class="card-header bg-body fw-semibold"><?= e(t('mail.queue')) ?></div>
                <ul class="list-group list-group-flush small" data-mails>
                    <li class="list-group-item text-body-secondary" data-empty hidden><?= e(t('mail.none')) ?></li>
                    <template data-row>
                        <li class="list-group-item">
                            <div class="d-flex justify-content-between gap-2">
                                <span class="text-break" data-bind="subject"></span>
                                <span class="badge" data-mail-state></span>
                            </div>
                            <div class="text-body-secondary"><span data-mail-time></span> · <span data-bind="recipients"></span></div>
                            <div class="text-danger text-break" data-mail-error></div>
                        </li>
                    </template>
                </ul>
            </div>
        </div>
    </div>

    <div class="d-flex flex-wrap justify-content-between align-items-center gap-2 mt-5 mb-3">
        <h2 class="h4 mb-0"><?= e(t('rule.title')) ?></h2>
        <button class="btn btn-primary" type="button" data-action="add-rule"><i class="bi bi-plus-lg" aria-hidden="true"></i> <?= e(t('rule.add')) ?></button>
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
                <tbody data-rules>
                    <tr data-empty hidden><td colspan="5" class="text-body-secondary p-3"><?= e(t('rule.none')) ?></td></tr>
                    <template data-row>
                        <tr>
                            <td class="fw-semibold">
                                <span data-bind="name"></span>
                                <span class="badge text-bg-secondary" data-bind-hide="enabled"><?= e(t('common.disabled')) ?></span>
                                <div class="small text-body-secondary font-monospace" data-bind="pattern"></div>
                            </td>
                            <td class="small" data-events></td>
                            <td class="small text-break" data-recipients></td>
                            <td class="small" data-mode></td>
                            <td class="text-end text-nowrap" data-row-actions>
                                <button type="button" class="btn btn-sm btn-outline-primary" data-action="edit-rule"><?= e(t('common.edit')) ?></button>
                                <button type="button" class="btn btn-sm btn-outline-danger" data-action="delete-rule" data-confirm="<?= e(t('rule.delete_confirm')) ?>"><?= e(t('common.delete')) ?></button>
                            </td>
                        </tr>
                    </template>
                </tbody>
            </table>
        </div>
    </div>

    <form class="card" data-rule-form novalidate hidden>
        <input type="hidden" name="id" data-ignore>
        <div class="card-header bg-body fw-semibold" data-rule-title
             data-title-add="<?= e(t('rule.add')) ?>" data-title-edit="<?= e(t('rule.edit')) ?>"></div>
        <div class="card-body">
            <div class="row g-3">
                <div class="col-md-6">
                    <label class="form-label" for="rule_name"><?= e(t('rule.name')) ?></label>
                    <input class="form-control" id="rule_name" name="name" maxlength="64">
                </div>
                <div class="col-md-6">
                    <label class="form-label" for="rule_pattern"><?= e(t('rule.pattern')) ?></label>
                    <input class="form-control" id="rule_pattern" name="pattern" placeholder="*.wav">
                    <div class="form-text"><?= e(t('rule.pattern_help')) ?></div>
                </div>
                <div class="col-12">
                    <span class="form-label d-block"><?= e(t('rule.events')) ?></span>
                    <?php foreach ($eventTypes as $ev): ?>
                        <div class="form-check form-check-inline">
                            <input class="form-check-input" type="checkbox" name="events[]" id="ev_<?= e($ev) ?>" value="<?= e($ev) ?>">
                            <label class="form-check-label" for="ev_<?= e($ev) ?>"><?= e(t('event.' . $ev)) ?></label>
                        </div>
                    <?php endforeach; ?>
                </div>
                <div class="col-12">
                    <label class="form-label" for="rule_recipients"><?= e(t('rule.recipients')) ?></label>
                    <input class="form-control" id="rule_recipients" name="recipients">
                    <div class="form-text"><?= e(t('rule.recipients_help')) ?></div>
                </div>
                <div class="col-md-6">
                    <span class="form-label d-block"><?= e(t('rule.mode')) ?></span>
                    <div class="form-check">
                        <input class="form-check-input" type="radio" name="mode" id="mode_instant" value="instant">
                        <label class="form-check-label" for="mode_instant"><?= e(t('rule.instant')) ?></label>
                    </div>
                    <div class="form-check">
                        <input class="form-check-input" type="radio" name="mode" id="mode_digest" value="digest">
                        <label class="form-check-label" for="mode_digest"><?= e(t('rule.digest')) ?></label>
                    </div>
                </div>
                <div class="col-md-6">
                    <label class="form-label" for="digest_minutes"><?= e(t('rule.digest_minutes')) ?></label>
                    <input class="form-control" id="digest_minutes" name="digest_minutes" type="number" min="5" max="10080" data-type="int">
                </div>
                <div class="col-12">
                    <hr class="mt-1 mb-0">
                    <h3 class="h6 mt-3 mb-1"><?= e(t('rule.message')) ?></h3>
                    <p class="form-text mt-0 mb-0"><?= e(t('rule.message_help')) ?></p>
                </div>
                <div class="col-12">
                    <label class="form-label" for="rule_subject"><?= e(t('rule.subject')) ?></label>
                    <input class="form-control" id="rule_subject" name="subject_template" maxlength="250" data-subject>
                </div>
                <div class="col-12">
                    <label class="form-label" id="rule_body_label"><?= e(t('rule.body')) ?></label>
                    <div class="template-editor" data-editor-wrap data-error-for="body_template">
                        <div data-editor aria-labelledby="rule_body_label"></div>
                    </div>
                    <input type="hidden" name="body_template">
                    <div class="d-flex flex-wrap align-items-center gap-1 mt-2 placeholder-chips" data-placeholders>
                        <span class="small text-body-secondary me-1"><?= e(t('rule.placeholders')) ?>:</span>
                        <template data-chip>
                            <button type="button" class="btn btn-sm btn-outline-secondary py-0" data-insert-placeholder></button>
                        </template>
                    </div>
                    <div class="form-text"><?= e(t('rule.placeholders_help')) ?></div>
                    <div class="d-flex flex-wrap gap-2 mt-2">
                        <button type="button" class="btn btn-sm btn-outline-secondary" data-action="default-template">
                            <i class="bi bi-file-earmark-text" aria-hidden="true"></i> <?= e(t('rule.use_default')) ?>
                        </button>
                        <button type="button" class="btn btn-sm btn-outline-secondary" data-action="clear-template">
                            <i class="bi bi-eraser" aria-hidden="true"></i> <?= e(t('rule.clear_template')) ?>
                        </button>
                        <button type="button" class="btn btn-sm btn-outline-primary" data-action="preview">
                            <i class="bi bi-eye" aria-hidden="true"></i> <?= e(t('rule.preview')) ?>
                        </button>
                    </div>
                </div>
                <div class="col-12">
                    <div class="form-check form-switch">
                        <input class="form-check-input" type="checkbox" role="switch" id="rule_enabled" name="enabled" value="1">
                        <label class="form-check-label" for="rule_enabled"><?= e(t('rule.enabled')) ?></label>
                    </div>
                </div>
            </div>
        </div>
        <div class="card-footer bg-body d-flex gap-2">
            <button class="btn btn-primary" type="submit"><?= e(t('common.save')) ?></button>
            <button class="btn btn-link" type="button" data-action="cancel-rule"><?= e(t('common.cancel')) ?></button>
        </div>
    </form>

    <div class="modal fade" tabindex="-1" data-preview-modal aria-labelledby="preview_title" aria-hidden="true">
        <div class="modal-dialog modal-lg modal-dialog-scrollable">
            <div class="modal-content">
                <div class="modal-header">
                    <h2 class="modal-title h5" id="preview_title"><?= e(t('rule.preview')) ?></h2>
                    <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="<?= e(t('common.close')) ?>"></button>
                </div>
                <div class="modal-body">
                    <div data-preview-notices></div>
                    <p class="small text-body-secondary"><?= e(t('rule.preview_help')) ?></p>
                    <div class="mb-2"><span class="text-body-secondary"><?= e(t('rule.subject')) ?>:</span> <strong data-preview-subject></strong></div>
                    <iframe class="mail-preview-frame" sandbox="" title="<?= e(t('rule.preview')) ?>" data-preview-frame></iframe>
                    <details class="mt-3">
                        <summary class="small"><?= e(t('rule.preview_text')) ?></summary>
                        <pre class="small border rounded p-2 mt-2 mb-0" data-preview-text></pre>
                    </details>
                </div>
                <div class="modal-footer">
                    <form class="input-group" data-preview-send novalidate>
                        <input class="form-control" name="send_to" type="email" value="<?= e($userEmail) ?>"
                               aria-label="<?= e(t('smtp.test_to')) ?>" placeholder="<?= e(t('smtp.test_to')) ?>">
                        <button class="btn btn-outline-primary" type="submit"><?= e(t('rule.send_preview')) ?></button>
                    </form>
                </div>
            </div>
        </div>
    </div>
</div>
