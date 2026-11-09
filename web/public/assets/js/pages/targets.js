// Targets list: load, test and delete targets.
(function () {
    'use strict';
    var root = document.getElementById('targets');
    if (!root) {
        return;
    }
    var t = NUF.t;
    var testBox = root.querySelector('[data-test-result]');

    function destination(target) {
        var host = target.host ? target.host + (target.port ? ':' + target.port : '') : '';
        return (host + ' ' + (target.path || '')).trim();
    }

    function load() {
        return NUF.api('GET', '/targets').then(function (r) {
            if (!r.ok) {
                NUF.notify('danger', r.message);
                return;
            }
            NUF.list(root.querySelector('[data-targets]'), r.data.targets, function (row, target) {
                var tr = row.querySelector('tr');
                tr.dataset.id = target.id;
                tr.dataset.name = target.name;
                tr.classList.toggle('text-body-secondary', !target.enabled);
                row.querySelector('[data-protocol]').textContent = t('protocol.' + target.protocol);
                row.querySelector('[data-destination]').textContent = destination(target);
                row.querySelector('[data-edit]').href = '/targets/' + target.id;
                var del = row.querySelector('[data-action="delete"]');
                if (del) {
                    del.setAttribute('data-confirm', t('target.delete_confirm', { name: target.name }));
                }
            });
        });
    }

    root.addEventListener('click', function (event) {
        var button = event.target.closest('[data-action]');
        if (!button) {
            return;
        }
        var tr = button.closest('tr');
        var id = tr.dataset.id;
        NUF.clearNotices();
        if (button.dataset.action === 'test') {
            NUF.api('POST', '/targets/' + id + '/test', {}).then(function (r) {
                if (r.ok) {
                    NUF.testResult(testBox, r.data, t('target.test_result_for', { name: tr.dataset.name }));
                } else {
                    NUF.showFailure(r);
                }
            });
        } else if (button.dataset.action === 'delete') {
            NUF.api('DELETE', '/targets/' + id).then(function (r) {
                if (!r.ok) {
                    NUF.showFailure(r);
                    return;
                }
                testBox.innerHTML = '';
                NUF.notify('success', t('target.deleted'));
                load();
            });
        }
    });

    load();
})();
