// Settings backup: download, restore and scheduled upload to a storage target.
(function () {
    'use strict';
    var root = document.getElementById('backup');
    if (!root) {
        return;
    }
    var t = NUF.t;
    var downloadForm = root.querySelector('[data-download-form]');
    var restoreForm = root.querySelector('[data-restore-form]');
    var scheduleForm = root.querySelector('[data-schedule-form]');

    function text(selector, value) {
        root.querySelector(selector).textContent = value;
    }

    function render(s) {
        var select = scheduleForm.querySelector('[name="target_id"]');
        select.innerHTML = '';
        var none = document.createElement('option');
        none.value = '';
        none.textContent = t('backup.choose_target');
        select.appendChild(none);
        (s.targets || []).forEach(function (target) {
            var option = document.createElement('option');
            option.value = target.id;
            option.textContent = target.name + ' (' + t('protocol.' + target.protocol) + ')';
            select.appendChild(option);
        });
        root.querySelector('[data-no-targets]').hidden = (s.targets || []).length > 0;
        NUF.fillForm(scheduleForm, s.settings);

        var input = scheduleForm.querySelector('[name="passphrase"]');
        input.value = '';
        input.placeholder = s.settings.has_passphrase ? input.dataset.placeholderSaved : '';
        var clear = scheduleForm.querySelector('[data-saved-passphrase]');
        clear.hidden = !s.settings.has_passphrase;
        clear.querySelector('input').checked = false;

        var last = s.last || {};
        var lastCell = root.querySelector('[data-last-run]');
        lastCell.textContent = '';
        if (last.time) {
            var badge = document.createElement('span');
            NUF.badge(badge, last.ok ? 'success' : 'danger', last.ok ? t('backup.ok') : t('backup.failed'));
            lastCell.appendChild(badge);
            lastCell.appendChild(document.createTextNode(' ' + NUF.fmtTime(last.time)));
            var detail = document.createElement('div');
            detail.className = 'small text-break ' + (last.ok ? 'text-body-secondary' : 'text-danger');
            detail.textContent = last.ok
                ? (last.target ? last.target + ': ' : '') + (last.file || '')
                : (last.error === 'no_target' ? t('backup.no_target_error') : last.error || '');
            lastCell.appendChild(detail);
        } else {
            lastCell.textContent = t('backup.never');
        }
        text('[data-last-success]', last.success_time ? NUF.fmtTime(last.success_time) : '–');
        text('[data-next-run]', s.next_run ? NUF.fmtTime(s.next_run) : t('backup.not_scheduled'));
        root.querySelector('[data-action="run"]').disabled = !s.settings.target_id;
    }

    function load() {
        return NUF.api('GET', '/backup').then(function (r) {
            if (!r.ok) {
                NUF.notify('danger', r.message);
                return;
            }
            render(r.data);
        });
    }

    function saveFile(filename, data) {
        var blob = new Blob([JSON.stringify(data, null, 2) + '\n'], { type: 'application/json' });
        var url = URL.createObjectURL(blob);
        var link = document.createElement('a');
        link.href = url;
        link.download = filename;
        document.body.appendChild(link);
        link.click();
        link.remove();
        setTimeout(function () { URL.revokeObjectURL(url); }, 1000);
    }

    NUF.onSubmit(downloadForm, function (data) {
        NUF.clearNotices();
        return NUF.api('POST', '/backup/export', { passphrase: data.passphrase || '' }).then(function (r) {
            if (!r.ok) {
                NUF.showFailure(r, downloadForm);
                return;
            }
            saveFile(r.data.filename, r.data.backup);
            downloadForm.querySelector('[name="passphrase"]').value = '';
            NUF.notify('success', data.passphrase ? t('backup.downloaded_secrets') : t('backup.downloaded'));
        });
    });

    function readFile(file) {
        return new Promise(function (resolve, reject) {
            var reader = new FileReader();
            reader.onload = function () { resolve(reader.result); };
            reader.onerror = function () { reject(reader.error); };
            reader.readAsText(file);
        });
    }

    NUF.onSubmit(restoreForm, function (data) {
        NUF.clearNotices();
        var file = restoreForm.querySelector('[data-restore-file]').files[0];
        if (!file) {
            NUF.showErrors(restoreForm, { backup: t('backup.choose_file') });
            return null;
        }
        return readFile(file).then(function (content) {
            var backup;
            try {
                backup = JSON.parse(content);
            } catch (e) {
                NUF.showErrors(restoreForm, { backup: t('error.invalid_backup') });
                return null;
            }
            return NUF.api('POST', '/backup/restore', { backup: backup, passphrase: data.passphrase || '' }).then(function (r) {
                if (!r.ok) {
                    if (r.error === 'passphrase_required' || r.error === 'wrong_passphrase') {
                        NUF.showErrors(restoreForm, { passphrase: r.message });
                    } else {
                        NUF.showFailure(r, restoreForm);
                    }
                }
                // On success the gateway answers with a redirect to the login page
                // (a restore ends all sessions); request() follows it.
            });
        }, function () {
            NUF.showErrors(restoreForm, { backup: t('error.invalid_backup') });
        });
    });

    NUF.onSubmit(scheduleForm, function (data) {
        NUF.clearNotices();
        if (!data.target_id) {
            data.target_id = null;
        }
        return NUF.api('PUT', '/backup', data).then(function (r) {
            if (!r.ok) {
                NUF.showFailure(r, scheduleForm);
                return;
            }
            NUF.notify('success', t('common.saved'));
            render(r.data);
        });
    });

    root.addEventListener('click', function (event) {
        var button = event.target.closest('[data-action="run"]');
        if (!button || button.disabled) {
            return;
        }
        NUF.clearNotices();
        NUF.api('POST', '/backup/run').then(function (r) {
            if (!r.ok) {
                NUF.showFailure(r);
                return;
            }
            render(r.data);
            var last = r.data.last || {};
            NUF.notify(last.ok ? 'success' : 'danger', last.ok ? t('backup.run_ok', { file: last.file })
                : t('backup.run_failed', { error: last.error === 'no_target' ? t('backup.no_target_error') : last.error }));
        });
    });

    load();
})();
