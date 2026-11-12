// Dashboard: status cards, recent file events and failed uploads.
// The first load shows the spinner; the 5-second refresh runs silently.
(function () {
    'use strict';
    var root = document.getElementById('dashboard');
    if (!root) {
        return;
    }
    var t = NUF.t;
    var q = function (sel) { return root.querySelector(sel); };

    function renderStatus(s) {
        NUF.bind(q('[data-status]'), s);
        var usb = s.usb;
        var state = NUF.usbState(usb);
        NUF.badge(q('[data-usb-state]'), state[0], state[1]);
        q('[data-monitor]').textContent = t('monitor.' + ((usb.monitor && usb.monitor.phase) || 'idle'));

        var unavailable = q('[data-usb-unavailable]');
        unavailable.hidden = usb.available || s.simulated;
        unavailable.textContent = t('usb.unavailable', { reason: usb.unavailable_reason || '' });
        q('[data-no-targets]').hidden = s.targets > 0;

        var current = s.uploads.current;
        var converting = s.conversion && s.conversion.current;
        q('[data-current-upload]').textContent = current
            ? t('dashboard.uploading', { file: current.path, target: current.target })
            : (converting ? t('dashboard.converting', { file: converting.path }) : t('dashboard.no_upload'));

        var sync = usb.last_sync;
        q('[data-sync-counts]').textContent = sync
            ? t('dashboard.sync_counts', { created: sync.created || 0, modified: sync.modified || 0, deleted: sync.deleted || 0 })
            : '';

        q('[data-cpu-temp]').textContent = s.cpu_temp === null ? '–' : s.cpu_temp.toFixed(1) + ' °C';
        q('[data-disk]').textContent = t('dashboard.disk', { free: NUF.fmtBytes(s.disk.free), total: NUF.fmtBytes(s.disk.total) });
        var pct = s.disk.total ? Math.round(s.disk.used / s.disk.total * 100) : 0;
        var bar = q('[data-disk-bar]');
        bar.style.width = pct + '%';
        bar.classList.toggle('bg-danger', pct > 85);
        bar.parentElement.setAttribute('aria-valuenow', pct);
    }

    function loadStatus(silent) {
        return NUF.api('GET', '/status', undefined, { silent: silent }).then(function (r) {
            if (r.ok) {
                renderStatus(r.data);
            } else if (!silent) {
                NUF.notify('danger', r.message);
            }
        });
    }

    function loadLists(silent) {
        return Promise.all([
            NUF.api('GET', '/file-events?limit=10', undefined, { silent: silent }),
            NUF.api('GET', '/uploads?status=failed&limit=5', undefined, { silent: silent })
        ]).then(function (results) {
            if (results[0].ok) {
                NUF.list(q('[data-events]'), results[0].data.events, function (row, ev) {
                    row.querySelector('[data-event]').textContent = t('event.' + ev.event);
                });
            }
            if (results[1].ok) {
                NUF.list(q('[data-failed]'), results[1].data.uploads);
            }
        });
    }

    function load(silent) {
        return Promise.all([loadStatus(silent), loadLists(silent)]);
    }

    var syncButton = q('[data-action="sync"]');
    if (syncButton) {
        syncButton.addEventListener('click', function () {
            syncButton.disabled = true;
            NUF.api('POST', '/usb/sync', {}).then(function (r) {
                syncButton.disabled = false;
                NUF.clearNotices();
                if (r.ok) {
                    NUF.notify('success', t('usb.done_sync'));
                    window.setTimeout(function () { load(true); }, 1500);
                } else {
                    NUF.showFailure(r);
                }
            });
        });
    }

    load(false);
    window.setInterval(function () { load(true); }, 5000);
})();
