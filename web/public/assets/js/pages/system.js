// System page: device info, hostname/time zone, SSH key, power, setup reset.
(function () {
    'use strict';
    var root = document.getElementById('system');
    if (!root) {
        return;
    }
    var t = NUF.t;
    var form = root.querySelector('[data-settings-form]');

    function showInfo(status) {
        NUF.bind(root, status);
        root.querySelector('[data-addresses]').textContent = (status.addresses || []).join(', ') || '–';
        root.querySelector('[data-disk]').textContent = t('dashboard.disk', {
            free: NUF.fmtBytes(status.disk.free),
            total: NUF.fmtBytes(status.disk.total)
        });
        root.querySelector('[data-temp]').textContent =
            status.cpu_temp === null ? '–' : status.cpu_temp.toFixed(1) + ' °C';
    }

    function showSettings(sys) {
        var select = form.querySelector('[name="timezone"]');
        select.innerHTML = '';
        var zones = (sys.timezones || []).slice();
        // Keep the current zone selectable even if the list does not contain it.
        if (sys.timezone && zones.indexOf(sys.timezone) === -1) {
            zones.unshift(sys.timezone);
        }
        zones.forEach(function (tz) {
            var option = document.createElement('option');
            option.value = tz;
            option.textContent = tz;
            select.appendChild(option);
        });
        NUF.fillForm(form, sys);
        if (sys.model) {
            root.querySelector('[data-bind="model"]').textContent = sys.model;
        }
    }

    function showKey(key) {
        root.querySelector('[data-public-key]').value = key || '';
        root.querySelector('[data-key-present]').hidden = !key;
        root.querySelector('[data-key-missing]').hidden = Boolean(key);
    }

    function load() {
        return Promise.all([
            NUF.api('GET', '/status'),
            NUF.api('GET', '/system'),
            NUF.api('GET', '/system/ssh-key')
        ]).then(function (results) {
            var failed = results.filter(function (r) { return !r.ok; });
            if (failed.length) {
                NUF.notify('danger', failed[0].message);
            }
            if (results[0].ok) {
                showInfo(results[0].data);
            }
            if (results[1].ok) {
                showSettings(results[1].data);
            }
            if (results[2].ok) {
                showKey(results[2].data.public_key);
            }
        });
    }

    NUF.onSubmit(form, function (data) {
        NUF.clearNotices();
        return NUF.api('PUT', '/system', data).then(function (r) {
            if (!r.ok) {
                NUF.showFailure(r, form);
                return;
            }
            NUF.notify('success', t('common.saved'));
        });
    });

    root.addEventListener('click', function (event) {
        var button = event.target.closest('[data-action]');
        if (!button) {
            return;
        }
        NUF.clearNotices();
        var action = button.dataset.action;
        if (action === 'generate_key' || action === 'regenerate_key') {
            NUF.api('POST', '/system/ssh-key', { regenerate: action === 'regenerate_key' }).then(function (r) {
                if (!r.ok) {
                    NUF.notify('danger', r.message);
                    return;
                }
                showKey(r.data.public_key);
                NUF.notify('success', t('target.key_generated'));
            });
        } else if (action === 'reboot' || action === 'poweroff') {
            NUF.api('POST', '/system/' + action, {}).then(function (r) {
                if (!r.ok) {
                    NUF.notify('danger', r.message);
                    return;
                }
                NUF.notify('info', t('system.' + action + '_started'));
            });
        } else if (action === 'setup_reset') {
            // On success the gateway answers with a redirect to /setup.
            NUF.api('POST', '/system/setup-reset', {
                wipe_users: root.querySelector('[data-wipe-users]').checked
            }).then(function (r) {
                if (!r.ok) {
                    NUF.notify('danger', r.message);
                }
            });
        }
    });

    load();
})();
