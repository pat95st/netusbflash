// Event log and audit log with level filter and manual refresh.
(function () {
    'use strict';
    var root = document.getElementById('logs');
    if (!root) {
        return;
    }
    var params = new URLSearchParams(window.location.search);
    var tab = params.get('tab') === 'audit' && root.querySelector('[data-tab="audit"]') ? 'audit' : 'events';
    var level = params.get('level') || '';
    if (['info', 'warning', 'error'].indexOf(level) === -1) {
        level = '';
    }
    var LEVEL_CLASS = { info: 'secondary', warning: 'warning', error: 'danger' };

    root.querySelectorAll('[data-tab]').forEach(function (a) {
        a.classList.toggle('active', a.dataset.tab === tab);
    });
    root.querySelectorAll('[data-level]').forEach(function (a) {
        a.classList.toggle('active', a.dataset.level === level);
    });
    root.querySelector('[data-levels]').hidden = tab !== 'events';
    root.querySelector('[data-download]').href = '/logs?download=1&tab=' + tab + (level ? '&level=' + level : '');

    var events = root.querySelector('[data-events]');
    var audit = root.querySelector('[data-audit]');
    events.hidden = tab !== 'events';
    audit.hidden = tab !== 'audit';

    function load() {
        if (tab === 'audit') {
            return NUF.api('GET', '/audit?limit=500').then(function (r) {
                if (!r.ok) {
                    NUF.notify('danger', r.message);
                    return;
                }
                NUF.list(audit, r.data.audit, function (row, entry) {
                    row.querySelector('[data-details]').textContent =
                        [entry.object, entry.details].filter(Boolean).join(' ') || '–';
                    if (!entry.username) {
                        row.querySelector('[data-bind="username"]').textContent = '–';
                    }
                });
            });
        }
        return NUF.api('GET', '/events?limit=500' + (level ? '&level=' + level : '')).then(function (r) {
            if (!r.ok) {
                NUF.notify('danger', r.message);
                return;
            }
            NUF.list(events, r.data.events, function (row, entry) {
                NUF.badge(row.querySelector('[data-level-badge]'), LEVEL_CLASS[entry.level] || 'secondary', entry.level);
            });
        });
    }

    root.querySelector('[data-action="refresh"]').addEventListener('click', function () {
        NUF.clearNotices();
        load();
    });

    load();
})();
