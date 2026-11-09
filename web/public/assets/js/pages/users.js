// User management: list with inline editing, add, reset password, unlock, delete.
(function () {
    'use strict';
    var root = document.getElementById('users');
    if (!root) {
        return;
    }
    var t = NUF.t;
    var me = Number(root.dataset.me);
    var users = {};

    function load() {
        return NUF.api('GET', '/users').then(function (r) {
            if (!r.ok) {
                NUF.notify('danger', r.message);
                return;
            }
            users = {};
            NUF.list(root.querySelector('[data-users]'), r.data.users, function (row, u) {
                users[u.id] = u;
                var tr = row.querySelector('tr');
                tr.dataset.id = u.id;
                tr.querySelector('[name="email"]').value = u.email || '';
                tr.querySelector('[name="role"]').value = u.role;
                tr.querySelector('[name="locale"]').value = u.locale;
                var disabled = tr.querySelector('[name="disabled"]');
                disabled.checked = Boolean(u.disabled);
                disabled.id = 'disabled-' + u.id;
                disabled.nextElementSibling.htmlFor = disabled.id;
                tr.querySelector('[data-you]').hidden = u.id !== me;
                tr.querySelector('[data-action="delete"]').hidden = u.id === me;
            });
        });
    }

    function rowValues(tr) {
        return {
            email: tr.querySelector('[name="email"]').value.trim(),
            role: tr.querySelector('[name="role"]').value,
            locale: tr.querySelector('[name="locale"]').value,
            disabled: tr.querySelector('[name="disabled"]').checked
        };
    }

    function rowFailure(tr, r) {
        if (r.fields && Object.keys(r.fields).length) {
            NUF.notify('danger', Object.keys(r.fields).map(function (k) { return r.fields[k]; }).join(' '));
        } else {
            NUF.notify('danger', r.message);
        }
    }

    root.addEventListener('click', function (event) {
        var button = event.target.closest('[data-action]');
        if (!button) {
            return;
        }
        var tr = button.closest('tr');
        var id = Number(tr.dataset.id);
        var user = users[id];
        NUF.clearNotices();
        var action = button.dataset.action;
        if (action === 'save') {
            NUF.api('PUT', '/users/' + id, rowValues(tr)).then(function (r) {
                if (!r.ok) {
                    rowFailure(tr, r);
                    return;
                }
                NUF.notify('success', t('common.saved'));
                return load();
            });
        } else if (action === 'reset') {
            if (!window.confirm(t('user.reset_confirm', { user: user.username }))) {
                return;
            }
            NUF.api('POST', '/users/' + id + '/reset-password', {}).then(function (r) {
                if (!r.ok) {
                    NUF.notify('danger', r.message);
                    return;
                }
                NUF.notify('success', t('user.reset_password_done', { user: user.username, password: r.data.temporary_password }));
                return load();
            });
        } else if (action === 'unlock') {
            NUF.api('POST', '/users/' + id + '/unlock', {}).then(function (r) {
                if (!r.ok) {
                    NUF.notify('danger', r.message);
                    return;
                }
                NUF.notify('success', t('user.unlocked'));
                return load();
            });
        } else if (action === 'delete') {
            if (!window.confirm(t('user.delete_confirm', { user: user.username }))) {
                return;
            }
            NUF.api('DELETE', '/users/' + id).then(function (r) {
                if (!r.ok) {
                    NUF.notify('danger', r.message);
                    return;
                }
                NUF.notify('success', t('common.deleted'));
                return load();
            });
        }
    });

    var addForm = root.querySelector('[data-add-user]');
    NUF.onSubmit(addForm, function (data) {
        NUF.clearNotices();
        return NUF.api('POST', '/users', data).then(function (r) {
            if (!r.ok) {
                NUF.showFailure(r, addForm);
                return;
            }
            NUF.notify('success', t('user.created_password', {
                user: r.data.user.username,
                password: r.data.temporary_password
            }));
            addForm.reset();
            return load();
        });
    });

    load();
})();
