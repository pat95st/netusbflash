// Updates: software releases from GitHub and operating system packages.
(function () {
    'use strict';
    var root = document.getElementById('updates');
    if (!root) {
        return;
    }
    var t = NUF.t;
    var form = root.querySelector('[data-settings-form]');
    var initialVersion = null;
    var poll = null;
    var wasActive = false;

    function show(selector, visible) {
        root.querySelectorAll(selector).forEach(function (el) { el.hidden = !visible; });
    }

    function text(selector, value) {
        root.querySelector(selector).textContent = value;
    }

    function render(s) {
        if (initialVersion === null) {
            initialVersion = s.current;
        }
        NUF.bind(root, s);
        show('[data-simulated]', s.simulated);
        show('[data-reboot-required]', s.reboot_required);

        var latest = s.latest;
        text('[data-latest-version]', latest ? latest.version : '–');
        show('[data-latest-pre]', latest && latest.prerelease);
        show('[data-up-to-date]', latest && !s.update_available);
        show('[data-available]', s.update_available);
        text('[data-published]', latest && latest.published_at ? NUF.fmtTime(Date.parse(latest.published_at) / 1000) : '–');
        text('[data-check-error]', s.check_error || '');
        show('[data-check-error]', Boolean(s.check_error));
        show('[data-notes-box]', Boolean(latest));
        if (latest) {
            text('[data-release-name]', latest.name || latest.version);
            text('[data-release-notes]', latest.notes || t('update.no_notes'));
            var link = root.querySelector('[data-release-url]');
            link.hidden = !latest.url;
            link.href = latest.url || '#';
        }
        var job = s.job;
        var busy = Boolean(job && job.active);
        var install = root.querySelector('[data-action="software"]');
        install.hidden = !s.update_available;
        install.disabled = busy;
        text('[data-install-label]', latest ? t('update.install', { version: latest.version }) : '');

        var os = s.os || {};
        text('[data-os-checked]', NUF.fmtTime(os.checked));
        text('[data-os-count]', os.count === undefined || os.count === null ? '–' : String(os.count));
        text('[data-os-error]', os.error || '');
        show('[data-os-error]', Boolean(os.error));
        var packages = os.packages || [];
        show('[data-os-list-box]', packages.length > 0);
        text('[data-os-list]', packages.join(', '));
        show('[data-os-checking]', s.os_check_running);
        root.querySelector('[data-action="os-check"]').disabled = s.os_check_running || busy;
        root.querySelector('[data-action="os"]').disabled = busy;
        root.querySelector('[data-action="check"]').disabled = busy;

        show('[data-job-running]', busy);
        show('[data-job-done]', Boolean(job && !job.active));
        if (job) {
            var kind = t(job.kind === 'os' ? 'update.os' : 'update.software');
            text('[data-job-label]', t('update.running', { kind: kind }));
            text('[data-job-done]', t('update.finished', { kind: kind, time: NUF.fmtTime(job.started) }));
        }
        var log = root.querySelector('[data-log]');
        log.hidden = !s.log;
        show('[data-no-log]', !s.log);
        var atBottom = log.scrollTop + log.clientHeight >= log.scrollHeight - 8;
        log.textContent = s.log || '';
        if (atBottom) {
            log.scrollTop = log.scrollHeight;
        }

        if (wasActive && !busy && job && job.kind === 'os') {
            NUF.notify('success', t('update.os_done'));
        }
        wasActive = busy;
        schedule(busy || s.os_check_running);
    }

    function schedule(active) {
        clearTimeout(poll);
        poll = setTimeout(function () { load(true); }, active ? 2000 : 30000);
    }

    function load(silent) {
        return NUF.api('GET', '/update', null, { silent: silent }).then(function (r) {
            if (!r.ok) {
                // The service restarts during a software update: keep waiting.
                if (wasActive || silent) {
                    schedule(true);
                    return;
                }
                NUF.notify('danger', r.message);
                return;
            }
            if (initialVersion !== null && r.data.current !== initialVersion) {
                NUF.flashNext('success', t('update.software_done', { version: r.data.current }));
                window.location.reload();
                return;
            }
            render(r.data);
        });
    }

    function loadSettings() {
        return NUF.api('GET', '/update').then(function (r) {
            if (!r.ok) {
                NUF.notify('danger', r.message);
                return;
            }
            NUF.fillForm(form, r.data.settings);
            render(r.data);
        });
    }

    NUF.onSubmit(form, function (data) {
        NUF.clearNotices();
        return NUF.api('PUT', '/update', data).then(function (r) {
            if (!r.ok) {
                NUF.showFailure(r, form);
                return;
            }
            NUF.notify('success', t('common.saved'));
            render(r.data);
        });
    });

    root.addEventListener('click', function (event) {
        var button = event.target.closest('[data-action]');
        if (!button || button.disabled) {
            return;
        }
        var action = button.dataset.action;
        NUF.clearNotices();
        if (action === 'reboot') {
            NUF.api('POST', '/system/reboot').then(function (r) {
                if (!r.ok) {
                    NUF.showFailure(r);
                    return;
                }
                NUF.notify('info', t('system.reboot_started'));
            });
            return;
        }
        NUF.api('POST', '/update/' + action).then(function (r) {
            if (!r.ok) {
                NUF.showFailure(r);
                return;
            }
            if (action === 'check') {
                NUF.notify(r.data.update_available ? 'info' : 'success',
                    r.data.update_available ? t('update.available_text', { version: r.data.latest.version })
                        : t('update.none_available'));
            } else if (action === 'software' || action === 'os') {
                NUF.notify('info', t('update.started'));
            }
            render(r.data);
        });
    });

    loadSettings();
})();
