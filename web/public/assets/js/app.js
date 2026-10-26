// NetUSBFlash UI behaviour. No build step, no inline scripts (strict CSP).
(function () {
    'use strict';

    // Confirmation for dangerous buttons: <button data-confirm="Really?">
    document.addEventListener('click', function (event) {
        var button = event.target.closest('[data-confirm]');
        if (button && !window.confirm(button.getAttribute('data-confirm'))) {
            event.preventDefault();
        }
    });

    // Prevent double submits: disable the clicked button while the form is sent.
    document.addEventListener('submit', function (event) {
        var submitter = event.submitter;
        if (!submitter || event.defaultPrevented) {
            return;
        }
        window.setTimeout(function () {
            submitter.disabled = true;
            if (submitter.name) {
                var hidden = document.createElement('input');
                hidden.type = 'hidden';
                hidden.name = submitter.name;
                hidden.value = submitter.value;
                submitter.form.appendChild(hidden);
            }
        }, 0);
    });

    // Progress bars: width from data-width (inline styles are blocked by the CSP).
    document.querySelectorAll('[data-width]').forEach(function (el) {
        el.style.width = Math.max(0, Math.min(100, parseInt(el.getAttribute('data-width'), 10) || 0)) + '%';
    });

    // Target form: show only the fields that belong to the selected protocol and auth method.
    document.querySelectorAll('[data-target-form]').forEach(function (form) {
        var root = form.closest('form') || document;
        var protocol = root.querySelector('[data-protocol-select]');
        var auth = root.querySelector('[data-auth-select]');
        function update() {
            var p = protocol ? protocol.value : '';
            var a = auth ? auth.value : 'password';
            var usesAuthChoice = ['sftp', 'sshfs', 'scp'].indexOf(p) !== -1;
            root.querySelectorAll('[data-protocols]').forEach(function (el) {
                el.hidden = el.getAttribute('data-protocols').split(' ').indexOf(p) === -1;
            });
            root.querySelectorAll('[data-auth]').forEach(function (el) {
                var protocolHidden = el.hasAttribute('data-protocols') &&
                    el.getAttribute('data-protocols').split(' ').indexOf(p) === -1;
                el.hidden = protocolHidden || (usesAuthChoice && el.getAttribute('data-auth') !== a) ||
                    (!usesAuthChoice && el.getAttribute('data-auth') === 'key');
            });
        }
        if (protocol) {
            protocol.addEventListener('change', update);
        }
        if (auth) {
            auth.addEventListener('change', update);
        }
        update();
    });

    // Dashboard: refresh live values every 5 seconds.
    var poll = document.querySelector('[data-status-poll]');
    if (poll) {
        var url = poll.getAttribute('data-status-poll');
        var refresh = function () {
            fetch(url, { credentials: 'same-origin', headers: { Accept: 'application/json' } })
                .then(function (response) {
                    if (response.status === 401) {
                        window.location.href = '/login';
                        return null;
                    }
                    return response.ok ? response.json() : null;
                })
                .then(function (data) {
                    if (!data) {
                        return;
                    }
                    document.querySelectorAll('[data-field]').forEach(function (el) {
                        var key = el.getAttribute('data-field');
                        if (Object.prototype.hasOwnProperty.call(data, key)) {
                            el.textContent = data[key];
                        }
                        var classKey = el.getAttribute('data-class-field');
                        if (classKey && data[classKey]) {
                            el.className = el.className.replace(/text-bg-\w+/, 'text-bg-' + data[classKey]);
                        }
                    });
                })
                .catch(function () { /* offline: try again on the next tick */ });
        };
        window.setInterval(refresh, 5000);
    }
})();
