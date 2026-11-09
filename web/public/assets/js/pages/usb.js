// USB stick page: state, settings, image recreation and the file list.
(function () {
    'use strict';
    var root = document.getElementById('usb');
    if (!root) {
        return;
    }
    var t = NUF.t;
    var q = function (sel) { return root.querySelector(sel); };
    var settingsForm = q('[data-settings-form]');
    var imageForm = q('[data-image-form]');

    function renderUsb(u) {
        var card = q('[data-usb-state]').closest('.card');
        NUF.bind(card, u);
        var state = NUF.usbState({ enabled: u.settings.enabled, image: u.image, state: u.state });
        NUF.badge(q('[data-usb-state]'), state[0], state[1]);

        var warning = q('[data-usb-unavailable]');
        warning.hidden = u.available;
        warning.textContent = t('usb.unavailable', { reason: u.unavailable_reason || '' });

        var image = u.image || {};
        q('[data-image-summary]').textContent = image.exists
            ? [NUF.fmtBytes(image.size), u.settings.filesystem === 'vfat' ? 'FAT32' : 'exFAT', u.settings.label].join(' · ')
            : t('usb.state_no_image');
        q('[data-image-allocated]').textContent = image.exists ? t('usb.allocated', { size: NUF.fmtBytes(image.allocated) }) : '';

        var attach = q('[data-action="attach"]');
        var detach = q('[data-action="detach"]');
        if (attach && detach) {
            attach.hidden = Boolean(u.state.attached);
            detach.hidden = !u.state.attached;
        }

        NUF.fillForm(settingsForm, u.settings);
        settingsForm.querySelector('[name="size_mb"]').max = u.max_size_mb;
        var help = q('[data-size-help]');
        help.textContent = help.dataset.template.replace('{value}', u.max_size_mb);
    }

    function renderFiles(files) {
        NUF.list(q('[data-files]'), files, function (row, file) {
            row.querySelector('[data-uploaded]').textContent = file.uploaded ? '✓ ' + t('common.yes') : t('common.no');
        });
        q('[data-file-count]').textContent = files.length;
        var uploaded = files.filter(function (f) { return f.uploaded; }).length;
        q('[data-file-uploaded]').textContent = t('usb.files_uploaded', { n: uploaded });
    }

    function load() {
        return Promise.all([NUF.api('GET', '/usb'), NUF.api('GET', '/files?limit=500')]).then(function (r) {
            if (r[0].ok) {
                renderUsb(r[0].data);
            } else {
                NUF.notify('danger', r[0].message);
            }
            if (r[1].ok) {
                renderFiles(r[1].data.files);
            }
        });
    }

    // Toolbar actions: sync, attach, detach.
    root.querySelectorAll('[data-action]').forEach(function (button) {
        button.addEventListener('click', function () {
            var action = button.dataset.action;
            NUF.clearNotices();
            NUF.api('POST', '/usb/' + action, {}).then(function (r) {
                if (!r.ok) {
                    NUF.showFailure(r);
                    return;
                }
                NUF.notify('success', t('usb.done_' + action));
                window.setTimeout(load, action === 'sync' ? 1500 : 0);
            });
        });
    });

    NUF.onSubmit(settingsForm, function (data) {
        NUF.clearNotices();
        data.label = (data.label || '').toUpperCase();
        return NUF.api('PUT', '/usb', data).then(function (r) {
            if (!r.ok) {
                NUF.showFailure(r, settingsForm);
                return;
            }
            NUF.notify('success', t('common.saved'));
            if (r.data.gadget_error) {
                NUF.notify('warning', t('usb.gadget_error', { error: r.data.gadget_error }));
            }
            if (r.data.image_rebuild_needed) {
                NUF.notify('info', t('usb.rebuild_needed'));
            }
            return load();
        });
    });

    if (imageForm) {
        NUF.onSubmit(imageForm, function (data) {
            NUF.clearNotices();
            if ((data.confirm_text || '').trim().toUpperCase() !== imageForm.dataset.word) {
                NUF.showErrors(imageForm, { confirm_text: t('usb.image_confirm_wrong') });
                return null;
            }
            return NUF.api('POST', '/usb/image', { confirm: true }).then(function (r) {
                if (!r.ok) {
                    NUF.showFailure(r);
                    return;
                }
                imageForm.reset();
                NUF.notify('success', t('usb.image_created'));
                if (r.data.gadget_error) {
                    NUF.notify('warning', t('usb.gadget_error', { error: r.data.gadget_error }));
                }
                return load();
            });
        });
    }

    load();
})();
