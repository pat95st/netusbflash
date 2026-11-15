// Add or edit a target; test the connection; manage the device's SSH key;
// sign in to iCloud with a two-factor code.
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
    var protocolSelect = form.querySelector('[data-protocol-select]');
    var icloudPanel = root.querySelector('[data-icloud-panel]');
    var target = null;

    // Placeholders and "remove" checkboxes for stored passwords, tokens and secrets.
    function savedSecrets(data) {
        form.querySelectorAll('[data-placeholder-saved]').forEach(function (el) {
            var flag = el.dataset.savedFlag || 'has_password';
            el.placeholder = data && data[flag] ? el.dataset.placeholderSaved : '';
        });
        form.querySelectorAll('[data-saved-password]').forEach(function (el) {
            var flag = el.dataset.savedFlag || 'has_password';
            el.hidden = !(data && data[flag]);
        });
    }

    // The iCloud sign-in needs a saved target.
    function updateIcloud() {
        if (!icloudPanel) {
            return;
        }
        icloudPanel.hidden = !id || !protocolSelect || protocolSelect.value !== 'icloud';
        var state = icloudPanel.querySelector('[data-icloud-state]');
        var signedIn = Boolean(target && target.protocol === 'icloud' && target.icloud_signed_in);
        state.textContent = signedIn ? state.dataset.textIn : state.dataset.textOut;
        state.className = 'small mb-2 ' + (signedIn ? 'text-success' : 'text-body-secondary');
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
                target = r.data.target;
                NUF.fillForm(form, target);
                savedSecrets(target);
                updateIcloud();
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
            var saved = r.data.target;
            if (saved.protocol === 'icloud' && !saved.icloud_signed_in) {
                // Stay on the form so the user can sign in with the 2FA code.
                NUF.flashNext('success', t('target.icloud_saved'));
                window.location.href = '/targets/' + saved.id;
                return;
            }
            NUF.flashNext('success', t('common.saved'));
            window.location.href = '/targets';
        });
    });

    if (icloudPanel) {
        var codeBox = icloudPanel.querySelector('[data-icloud-code-box]');
        var codeInput = icloudPanel.querySelector('#t_icloud_code');
        var loginButton = icloudPanel.querySelector('[data-icloud-login]');
        var submitButton = icloudPanel.querySelector('[data-icloud-submit]');

        var signedIn = function (r) {
            if (!r.ok) {
                NUF.showFailure(r);
                return;
            }
            if (r.data.status === 'code_required') {
                codeBox.hidden = false;
                codeInput.value = '';
                codeInput.focus();
                return;
            }
            codeBox.hidden = true;
            target.icloud_signed_in = true;
            updateIcloud();
            NUF.notify('success', t('target.icloud_done'));
        };

        if (protocolSelect) {
            protocolSelect.addEventListener('change', updateIcloud);
        }

        // Save the form first, so the sign-in uses the Apple ID and password shown.
        loginButton.addEventListener('click', function () {
            NUF.clearNotices();
            loginButton.disabled = true;
            NUF.api('PUT', '/targets/' + id, NUF.formData(form)).then(function (r) {
                if (!r.ok) {
                    NUF.showFailure(r, form);
                    return null;
                }
                target = r.data.target;
                savedSecrets(target);
                return NUF.api('POST', '/targets/' + id + '/icloud/login', {}).then(signedIn);
            }).finally(function () {
                loginButton.disabled = false;
            });
        });

        var submitCode = function () {
            var code = codeInput.value.replace(/\s+/g, '');
            if (!/^[0-9]{6}$/.test(code)) {
                codeInput.classList.add('is-invalid');
                codeInput.focus();
                return;
            }
            codeInput.classList.remove('is-invalid');
            submitButton.disabled = true;
            NUF.api('POST', '/targets/' + id + '/icloud/code', { code: code }).then(signedIn).finally(function () {
                submitButton.disabled = false;
            });
        };
        submitButton.addEventListener('click', submitCode);
        codeInput.addEventListener('keydown', function (event) {
            if (event.key === 'Enter') {
                event.preventDefault();
                submitCode();
            }
        });
        updateIcloud();
    }

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
