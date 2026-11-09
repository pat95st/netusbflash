// Notifications: SMTP settings, test email, rules (with subject and HTML body
// templates edited in Quill) and the recent mail queue.
(function () {
    'use strict';
    var root = document.getElementById('notifications');
    if (!root) {
        return;
    }
    var t = NUF.t;
    var smtpForm = root.querySelector('[data-smtp-form]');
    var testForm = root.querySelector('[data-test-form]');
    var ruleForm = root.querySelector('[data-rule-form]');
    var rules = [];
    var placeholders = [];
    var defaults = { subject: '', body: '' };
    var subjectInput = ruleForm.querySelector('[data-subject]');
    var bodyInput = ruleForm.querySelector('[name="body_template"]');
    var previewModalEl = root.querySelector('[data-preview-modal]');
    var previewNotices = root.querySelector('[data-preview-notices]');
    var previewModal = null;
    var lastField = 'body';
    var bodyRange = null;

    // HTML editor ---------------------------------------------------------

    // Alignment as inline style instead of Quill's CSS classes: mail clients
    // do not have Quill's stylesheet.
    Quill.register(Quill.import('attributors/style/align'), true);
    var editor = new Quill(ruleForm.querySelector('[data-editor]'), {
        theme: 'snow',
        placeholder: t('rule.body_placeholder'),
        modules: {
            toolbar: [
                [{ header: [1, 2, 3, false] }],
                ['bold', 'italic', 'underline', 'strike'],
                [{ color: [] }, { background: [] }],
                [{ list: 'ordered' }, { list: 'bullet' }, { align: [] }],
                ['link', 'blockquote'],
                ['clean']
            ]
        }
    });

    function editorEmpty() {
        return editor.getText().trim() === '';
    }

    function syncBody() {
        bodyInput.value = editorEmpty() ? '' : editor.root.innerHTML;
    }

    function setBody(html) {
        if (html) {
            editor.clipboard.dangerouslyPasteHTML(html, 'silent');
        } else {
            editor.setContents([], 'silent');
        }
        editor.history.clear();
        syncBody();
    }

    editor.on('text-change', function () {
        syncBody();
        var range = editor.getSelection();
        if (range) {
            bodyRange = range;
        }
    });
    editor.on('selection-change', function (range) {
        if (range) {
            lastField = 'body';
            bodyRange = range;
        }
    });
    subjectInput.addEventListener('focus', function () {
        lastField = 'subject';
    });

    function insertPlaceholder(name) {
        var token = '{{' + name + '}}';
        if (lastField === 'subject') {
            var start = subjectInput.selectionStart === null ? subjectInput.value.length : subjectInput.selectionStart;
            var end = subjectInput.selectionEnd === null ? start : subjectInput.selectionEnd;
            subjectInput.value = subjectInput.value.slice(0, start) + token + subjectInput.value.slice(end);
            subjectInput.focus();
            subjectInput.setSelectionRange(start + token.length, start + token.length);
            return;
        }
        var index = bodyRange ? bodyRange.index : Math.max(0, editor.getLength() - 1);
        editor.insertText(index, token, 'user');
        editor.setSelection(index + token.length, 0, 'user');
    }

    function renderPlaceholders() {
        var box = root.querySelector('[data-placeholders]');
        var tpl = box.querySelector('template[data-chip]');
        box.querySelectorAll('[data-insert-placeholder]').forEach(function (el) { el.remove(); });
        placeholders.forEach(function (name) {
            var button = tpl.content.firstElementChild.cloneNode(true);
            button.textContent = '{{' + name + '}}';
            button.dataset.insertPlaceholder = name;
            button.title = t('placeholder.' + name);
            box.appendChild(button);
        });
    }

    // Preview ---------------------------------------------------------------

    function previewDocument(html) {
        return '<!DOCTYPE html><html><head><meta charset="utf-8"></head>' +
            '<body style="margin:0;padding:16px;font-family:Arial,Helvetica,sans-serif;font-size:14px;' +
            'line-height:1.5;color:#212529;background:#fff">' + html + '</body></html>';
    }

    function previewPayload() {
        syncBody();
        var data = NUF.formData(ruleForm);
        delete data.id;
        return data;
    }

    function showPreview() {
        NUF.clearNotices();
        NUF.api('POST', '/rules/preview', previewPayload()).then(function (r) {
            if (!r.ok) {
                NUF.showFailure(r, ruleForm);
                return;
            }
            root.querySelector('[data-preview-subject]').textContent = r.data.subject;
            root.querySelector('[data-preview-text]').textContent = r.data.text;
            // sandbox="" (no scripts); the content is sanitised by the service.
            root.querySelector('[data-preview-frame]').srcdoc = previewDocument(r.data.html);
            NUF.clearNotices(previewNotices);
            previewModal = previewModal || new bootstrap.Modal(previewModalEl);
            previewModal.show();
        });
    }

    NUF.onSubmit(root.querySelector('[data-preview-send]'), function (data) {
        NUF.clearNotices(previewNotices);
        var payload = previewPayload();
        payload.send_to = data.send_to;
        return NUF.api('POST', '/rules/preview', payload).then(function (r) {
            var box = previewNotices;
            if (!r.ok) {
                NUF.notify('danger', r.fields && r.fields.send_to ? r.fields.send_to : r.message, box);
            } else if (!r.data.sent) {
                NUF.notify('danger', t('smtp.test_failed', { error: r.data.error || '' }), box);
            } else {
                NUF.notify('success', t('rule.preview_sent', { to: data.send_to }), box);
            }
        });
    });

    function savedPassword(has) {
        smtpForm.querySelectorAll('[data-placeholder-saved]').forEach(function (el) {
            el.placeholder = has ? el.dataset.placeholderSaved : '';
            el.value = '';
        });
        smtpForm.querySelectorAll('[data-saved-password]').forEach(function (el) {
            el.hidden = !has;
            el.querySelector('input').checked = false;
        });
    }

    function renderRules() {
        NUF.list(root.querySelector('[data-rules]'), rules, function (row, rule) {
            var tr = row.querySelector('tr');
            tr.dataset.id = rule.id;
            tr.classList.toggle('text-body-secondary', !rule.enabled);
            row.querySelector('[data-events]').textContent = rule.events.map(function (ev) { return t('event.' + ev); }).join(', ');
            row.querySelector('[data-recipients]').textContent = rule.recipients.join(', ');
            row.querySelector('[data-mode]').textContent = rule.mode === 'digest'
                ? t('rule.digest_every', { n: rule.digest_minutes })
                : t('rule.instant');
        });
    }

    function renderMails(mails) {
        NUF.list(root.querySelector('[data-mails]'), mails, function (row, mail) {
            var state = row.querySelector('[data-mail-state]');
            if (mail.sent_at) {
                NUF.badge(state, 'success', t('mail.sent'));
            } else {
                NUF.badge(state, mail.last_error ? 'danger' : 'info', mail.last_error ? t('mail.retrying') : t('mail.queued'));
            }
            row.querySelector('[data-mail-time]').textContent = NUF.fmtTime(mail.sent_at || mail.created_at);
            row.querySelector('[data-mail-error]').textContent = mail.sent_at ? '' : (mail.last_error || '');
        });
    }

    function load() {
        return Promise.all([
            NUF.api('GET', '/smtp'),
            NUF.api('GET', '/rules'),
            NUF.api('GET', '/mail-queue?limit=20')
        ]).then(function (r) {
            if (r[0].ok) {
                NUF.fillForm(smtpForm, r[0].data.smtp);
                savedPassword(r[0].data.smtp.has_password);
            } else {
                NUF.notify('danger', r[0].message);
            }
            if (r[1].ok) {
                rules = r[1].data.rules;
                placeholders = r[1].data.placeholders || [];
                defaults = r[1].data.defaults || defaults;
                subjectInput.placeholder = defaults.subject;
                renderPlaceholders();
                renderRules();
            }
            if (r[2].ok) {
                renderMails(r[2].data.mails);
            }
        });
    }

    function openRuleForm(rule) {
        NUF.clearErrors(ruleForm);
        var title = ruleForm.querySelector('[data-rule-title]');
        title.textContent = rule ? title.dataset.titleEdit : title.dataset.titleAdd;
        var values = rule ? Object.assign({}, rule, { recipients: rule.recipients.join(', ') }) : {
            id: '', name: '', events: ['uploaded', 'upload_failed'], pattern: '*',
            recipients: root.dataset.userEmail, mode: 'instant', digest_minutes: 60, enabled: true,
            subject_template: '', body_template: ''
        };
        NUF.fillForm(ruleForm, values);
        setBody(values.body_template || '');
        bodyRange = null;
        lastField = 'body';
        ruleForm.hidden = false;
        ruleForm.scrollIntoView({ behavior: 'smooth' });
        ruleForm.querySelector('[name="name"]').focus();
    }

    NUF.onSubmit(smtpForm, function (data) {
        NUF.clearNotices();
        return NUF.api('PUT', '/smtp', data).then(function (r) {
            if (!r.ok) {
                NUF.showFailure(r, smtpForm);
                return;
            }
            NUF.notify('success', t('common.saved'));
            savedPassword(r.data.smtp.has_password);
        });
    });

    NUF.onSubmit(testForm, function (data) {
        NUF.clearNotices();
        return NUF.api('POST', '/smtp/test', data).then(function (r) {
            if (!r.ok) {
                NUF.showFailure(r, testForm);
            } else if (!r.data.ok) {
                NUF.notify('danger', t('smtp.test_failed', { error: r.data.error || '' }));
            } else {
                NUF.notify('success', t('smtp.test_sent'));
            }
        });
    });

    NUF.onSubmit(ruleForm, function (data) {
        NUF.clearNotices();
        data.body_template = editorEmpty() ? '' : editor.root.innerHTML;
        var id = ruleForm.querySelector('[name="id"]').value;
        var call = id ? NUF.api('PUT', '/rules/' + id, data) : NUF.api('POST', '/rules', data);
        return call.then(function (r) {
            if (!r.ok) {
                NUF.showFailure(r, ruleForm);
                return;
            }
            ruleForm.hidden = true;
            NUF.notify('success', t('common.saved'));
            return load();
        });
    });

    root.addEventListener('click', function (event) {
        var chip = event.target.closest('[data-insert-placeholder]');
        if (chip) {
            insertPlaceholder(chip.dataset.insertPlaceholder);
            return;
        }
        var button = event.target.closest('[data-action]');
        if (!button) {
            return;
        }
        var action = button.dataset.action;
        var tr = button.closest('tr');
        var rule = tr ? rules.filter(function (x) { return String(x.id) === tr.dataset.id; })[0] : null;
        if (action === 'add-rule') {
            openRuleForm(null);
        } else if (action === 'edit-rule') {
            openRuleForm(rule);
        } else if (action === 'cancel-rule') {
            ruleForm.hidden = true;
        } else if (action === 'default-template') {
            if (editorEmpty() || window.confirm(t('rule.replace_confirm'))) {
                setBody(defaults.body);
                if (!subjectInput.value) {
                    subjectInput.value = defaults.subject;
                }
            }
        } else if (action === 'clear-template') {
            setBody('');
            subjectInput.value = '';
        } else if (action === 'preview') {
            showPreview();
        } else if (action === 'delete-rule') {
            NUF.clearNotices();
            NUF.api('DELETE', '/rules/' + rule.id).then(function (r) {
                if (!r.ok) {
                    NUF.showFailure(r);
                    return;
                }
                NUF.notify('success', t('common.deleted'));
                ruleForm.hidden = true;
                load();
            });
        }
    });

    load();
})();
