// Upload queue with status filter, retry and discard.
(function () {
    'use strict';
    var root = document.getElementById('uploads');
    if (!root) {
        return;
    }
    var t = NUF.t;
    var status = new URLSearchParams(window.location.search).get('status') || '';
    if (['pending', 'failed', 'done'].indexOf(status) === -1) {
        status = '';
    }
    root.querySelectorAll('[data-filter]').forEach(function (link) {
        link.classList.toggle('active', link.dataset.filter === status);
    });

    function load() {
        var path = '/uploads?limit=300' + (status ? '&status=' + status : '');
        return NUF.api('GET', path).then(function (r) {
            if (!r.ok) {
                NUF.notify('danger', r.message);
                return;
            }
            NUF.list(root.querySelector('[data-uploads]'), r.data.uploads, function (row, u) {
                row.querySelector('tr').dataset.id = u.id;
                NUF.uploadBadge(row.querySelector('[data-status]'), u.status);
                row.querySelector('[data-attempts]').textContent =
                    u.attempts > 0 && u.status !== 'done' ? t('upload.attempts', { n: u.attempts }) : '';
                row.querySelector('[data-time]').textContent = NUF.fmtTime(u.finished_at || u.created_at);
                row.querySelectorAll('[data-action]').forEach(function (b) {
                    b.hidden = u.status !== 'failed';
                });
            });
        });
    }

    function run(path, message) {
        NUF.clearNotices();
        return NUF.api('POST', path, {}).then(function (r) {
            if (!r.ok) {
                NUF.showFailure(r);
                return;
            }
            NUF.notify('success', typeof message === 'function' ? message(r.data) : message);
            return load();
        });
    }

    root.addEventListener('click', function (event) {
        var button = event.target.closest('[data-action]');
        if (!button) {
            return;
        }
        var action = button.dataset.action;
        if (action === 'retry_all') {
            run('/uploads/retry-failed', function (d) { return t('upload.retried', { n: d.retried }); });
            return;
        }
        var id = button.closest('tr').dataset.id;
        if (action === 'retry') {
            run('/uploads/' + id + '/retry', t('upload.retried', { n: 1 }));
        } else if (action === 'discard') {
            run('/uploads/' + id + '/discard', t('upload.discarded'));
        }
    });

    load();
})();
