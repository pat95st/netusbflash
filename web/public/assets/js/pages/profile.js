// Own profile: password change (also the forced one after a reset) and personal settings.
(function () {
    'use strict';
    var root = document.getElementById('profile');
    if (!root) {
        return;
    }
    var t = NUF.t;
    var profileForm = root.querySelector('[data-profile-form]');
    var passwordForm = root.querySelector('[data-password-form]');
    var user = null;

    function load() {
        return NUF.api('GET', '/me').then(function (r) {
            if (!r.ok) {
                NUF.notify('danger', r.message);
                return;
            }
            user = r.data.user;
            NUF.bind(root, user);
            root.querySelector('[data-role]').textContent = t('role.' + user.role);
            root.querySelector('[data-forced]').hidden = !user.must_change_pw;
            root.querySelector('[data-settings-col]').hidden = Boolean(user.must_change_pw);
            NUF.fillForm(profileForm, user);
        });
    }

    NUF.onSubmit(passwordForm, function (data) {
        NUF.clearNotices();
        if (data['new'] !== data.new_confirm) {
            NUF.showErrors(passwordForm, { new_confirm: t('field.mismatch') });
            return;
        }
        var forced = user && user.must_change_pw;
        return NUF.api('POST', '/me/password', { current: data.current || '', 'new': data['new'] || '' }).then(function (r) {
            if (!r.ok) {
                NUF.showFailure(r, passwordForm);
                return;
            }
            passwordForm.reset();
            if (forced) {
                NUF.flashNext('success', t('profile.password_changed'));
                window.location.href = '/';
                return;
            }
            NUF.notify('success', t('profile.password_changed'));
        });
    });

    NUF.onSubmit(profileForm, function (data) {
        NUF.clearNotices();
        var oldLocale = user.locale;
        return NUF.api('PUT', '/me', { email: data.email || '', locale: data.locale }).then(function (r) {
            if (!r.ok) {
                NUF.showFailure(r, profileForm);
                return;
            }
            if (r.data.user.locale !== oldLocale) {
                // The page texts come from the server: reload in the new language.
                NUF.flashNext('success', t('common.saved'));
                window.location.reload();
                return;
            }
            user = r.data.user;
            NUF.notify('success', t('common.saved'));
        });
    });

    load();
})();
