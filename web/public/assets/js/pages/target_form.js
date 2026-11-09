// Add or edit a target; test the connection; manage the device's SSH key.
(function () {
    'use strict';
    var root = document.getElementById('target-form');
    if (!root) {
        return;
    }
    var t = NUF.t;
    var id = root.dataset.targetId;
    var form = root.querySelector('form');
    var testBox = root.querySelector('[data-test-result]');
    var keyBox = root.querySelector('[data-key-present]');
    var keyButton = root.querySelector('[data-generate-key]');

    function savedPassword(has) {
        form.querySelectorAll('[data-placeholder-saved]').forEach(function (el) {
            el.placeholder = has ? el.dataset.placeholderSaved : '';
        });
        form.querySelectorAll('[data-saved-password]').forEach(function (el) {
            el.hidden = !has;
        });
    }

    function showKey(key) {
        if (!keyBox) {
            return;
        }
        keyBox.hidden = !key;
        keyButton.hidden = Boolean(key);
        keyBox.querySelector('[data-public-key]').value = key || '';
    }

    function load() {
        var calls = [];
        if (id) {
            calls.push(NUF.api('GET', '/targets/' + id).then(function (r) {
                if (!r.ok) {
                    NUF.notify('danger', r.message);
                    return;
                }
                NUF.fillForm(form, r.data.target);
                savedPassword(r.data.target.has_password);
                root.querySelector('[data-title]').textContent = r.data.target.name;
            }));
        }
        if (keyBox) {
            calls.push(NUF.api('GET', '/system/ssh-key').then(function (r) {
                if (r.ok) {
                    showKey(r.data.public_key);
                }
            }));
        }
        return Promise.all(calls);
    }

    NUF.onSubmit(form, function (data, action) {
        NUF.clearNotices();
        if (action === 'test') {
            if (id) {
                data.id = Number(id);
            }
            return NUF.api('POST', '/targets/test', data).then(function (r) {
                if (r.ok) {
                    NUF.testResult(testBox, r.data);
                } else {
                    NUF.showFailure(r, form);
                }
            });
        }
        var call = id ? NUF.api('PUT', '/targets/' + id, data) : NUF.api('POST', '/targets', data);
        return call.then(function (r) {
            if (!r.ok) {
                NUF.showFailure(r, form);
                return;
            }
            NUF.flashNext('success', t('common.saved'));
            window.location.href = '/targets';
        });
    });

    if (keyButton) {
        keyButton.addEventListener('click', function () {
            NUF.api('POST', '/system/ssh-key', {}).then(function (r) {
                if (r.ok) {
                    showKey(r.data.public_key);
                    NUF.notify('success', t('target.key_generated'));
                } else {
                    NUF.showFailure(r);
                }
            });
        });
    }

    load();
})();
