// NetUSBFlash UI library. No build step, no inline scripts (strict CSP).
//
// Pages are delivered as an HTML skeleton; the page scripts (assets/js/pages/*.js)
// load their data through NUF.api() and fill the skeleton. While any request
// runs, every element with [data-loading] (the spinner overlay) is shown.
(function () {
    'use strict';

    var I18N = {};
    try {
        I18N = JSON.parse(document.getElementById('i18n-data').textContent);
    } catch (e) { /* page without translations */ }
    var LOCALE = document.documentElement.lang || 'en';
    var csrfMeta = document.querySelector('meta[name="csrf-token"]');
    var CSRF = csrfMeta ? csrfMeta.content : '';

    // Translation ---------------------------------------------------------

    function t(key, params) {
        var text = Object.prototype.hasOwnProperty.call(I18N, key) ? I18N[key] : key;
        Object.keys(params || {}).forEach(function (name) {
            text = text.split('{' + name + '}').join(String(params[name]));
        });
        return text;
    }

    // Formatting ----------------------------------------------------------

    function fmtBytes(bytes) {
        if (bytes === null || bytes === undefined || bytes === '') {
            return '–';
        }
        var units = ['B', 'KB', 'MB', 'GB', 'TB'];
        var value = Number(bytes);
        var i = 0;
        while (value >= 1024 && i < units.length - 1) {
            value /= 1024;
            i++;
        }
        var text = i === 0 ? String(Math.round(value)) : value.toFixed(1);
        return (LOCALE === 'de' ? text.replace('.', ',') : text) + ' ' + units[i];
    }

    function pad(n) {
        return n < 10 ? '0' + n : String(n);
    }

    function fmtTime(ts) {
        if (!ts) {
            return '–';
        }
        var d = new Date(ts * 1000);
        var time = pad(d.getHours()) + ':' + pad(d.getMinutes()) + ':' + pad(d.getSeconds());
        if (LOCALE === 'de') {
            return pad(d.getDate()) + '.' + pad(d.getMonth() + 1) + '.' + d.getFullYear() + ' ' + time;
        }
        return d.getFullYear() + '-' + pad(d.getMonth() + 1) + '-' + pad(d.getDate()) + ' ' + time;
    }

    function fmtDuration(seconds) {
        if (seconds === null || seconds === undefined) {
            return '–';
        }
        seconds = Math.floor(seconds);
        var d = Math.floor(seconds / 86400);
        var h = Math.floor((seconds % 86400) / 3600);
        var m = Math.floor((seconds % 3600) / 60);
        return (d ? d + 'd ' : '') + pad(h) + ':' + pad(m);
    }

    var FORMATS = {
        bytes: fmtBytes,
        time: fmtTime,
        duration: fmtDuration,
        text: function (v) { return v === null || v === undefined || v === '' ? '–' : String(v); }
    };

    // Object paths like "usb.state.udc" ---------------------------------

    function get(obj, path) {
        return String(path).split('.').reduce(function (cur, key) {
            return cur === null || cur === undefined ? undefined : cur[key];
        }, obj);
    }

    function set(obj, path, value) {
        var keys = String(path).split('.');
        var cur = obj;
        keys.slice(0, -1).forEach(function (key) {
            if (typeof cur[key] !== 'object' || cur[key] === null) {
                cur[key] = {};
            }
            cur = cur[key];
        });
        cur[keys[keys.length - 1]] = value;
    }

    // Spinner -------------------------------------------------------------

    var pending = 0;

    function syncLoading() {
        document.querySelectorAll('[data-loading]').forEach(function (el) {
            el.hidden = pending === 0;
        });
    }

    function loading(delta) {
        pending = Math.max(0, pending + delta);
        syncLoading();
    }

    // AJAX ----------------------------------------------------------------

    // Calls the JSON gateway. Resolves with {ok, data, message, fields};
    // never rejects. opts.silent: do not show the spinner (background refresh).
    function request(url, method, body, opts) {
        opts = opts || {};
        if (!opts.silent) {
            loading(1);
        }
        var init = {
            method: method,
            credentials: 'same-origin',
            headers: { Accept: 'application/json', 'X-CSRF-Token': CSRF }
        };
        if (body !== undefined && method !== 'GET') {
            init.headers['Content-Type'] = 'application/json';
            init.body = JSON.stringify(body);
        }
        return fetch(url, init)
            .then(function (response) {
                return response.json().catch(function () {
                    return { ok: false, message: t('error.network') };
                });
            })
            .catch(function () {
                return { ok: false, message: t('error.network') };
            })
            .then(function (result) {
                if (result && result.redirect) {
                    window.location.href = result.redirect;
                    return new Promise(function () { /* page changes */ });
                }
                return result || { ok: false, message: t('error.network') };
            })
            .finally(function () {
                if (!opts.silent) {
                    loading(-1);
                }
            });
    }

    function api(method, path, body, opts) {
        return request('/ajax/api' + path, method, body, opts);
    }

    // Notices -------------------------------------------------------------

    function notify(type, message, container) {
        var target = container || document.querySelector('[data-notices]');
        if (!target || !message) {
            return;
        }
        var alert = document.createElement('div');
        alert.className = 'alert alert-' + type + ' alert-dismissible fade show';
        alert.setAttribute('role', 'alert');
        alert.textContent = message;
        var close = document.createElement('button');
        close.type = 'button';
        close.className = 'btn-close';
        close.setAttribute('data-bs-dismiss', 'alert');
        close.setAttribute('aria-label', t('common.close'));
        alert.appendChild(close);
        target.appendChild(alert);
        alert.scrollIntoView({ block: 'nearest', behavior: 'smooth' });
    }

    function clearNotices(container) {
        var target = container || document.querySelector('[data-notices]');
        if (target) {
            target.innerHTML = '';
        }
    }

    // Show the result of a failed call: field errors on the form, else a notice.
    function showFailure(result, form) {
        if (form && result.fields && Object.keys(result.fields).length) {
            showErrors(form, result.fields);
            return;
        }
        notify('danger', result.message || t('error.network'));
    }

    // A notice that survives a page change (e.g. "Saved." after a redirect).
    function flashNext(type, message) {
        try {
            sessionStorage.setItem('nuf-flash', JSON.stringify({ type: type, message: message }));
        } catch (e) { /* storage unavailable: no notice */ }
    }

    function showStoredFlash() {
        try {
            var raw = sessionStorage.getItem('nuf-flash');
            if (raw) {
                sessionStorage.removeItem('nuf-flash');
                var item = JSON.parse(raw);
                notify(item.type, item.message);
            }
        } catch (e) { /* ignore */ }
    }

    // Forms ---------------------------------------------------------------

    // Fields inside a hidden protocol/auth block do not belong to the form.
    function fieldActive(el) {
        return !el.disabled && !el.closest('[data-protocols][hidden], [data-auth][hidden], [data-ignore]');
    }

    // Serialise a form to an object. Names may be paths ("options.domain");
    // "name[]" checkboxes become arrays; data-type="int" converts numbers.
    function formData(form) {
        var data = {};
        form.querySelectorAll('[name]').forEach(function (el) {
            if (!fieldActive(el) || el.type === 'submit' || el.type === 'button') {
                return;
            }
            var name = el.name;
            var value;
            if (el.type === 'checkbox' && name.slice(-2) === '[]') {
                var key = name.slice(0, -2);
                if (!Array.isArray(get(data, key))) {
                    set(data, key, []);
                }
                if (el.checked) {
                    get(data, key).push(el.value);
                }
                return;
            }
            if (el.type === 'checkbox') {
                value = el.checked;
            } else if (el.type === 'radio') {
                if (!el.checked) {
                    return;
                }
                value = el.value;
            } else {
                value = el.value;
            }
            if (el.dataset.type === 'int') {
                value = value === '' ? null : parseInt(value, 10);
            }
            if (el.type === 'password' && value === '') {
                return; // empty password = keep the stored one
            }
            set(data, name, value);
        });
        return data;
    }

    // Fill form fields from an object (by field name / path).
    function fillForm(form, data) {
        form.querySelectorAll('[name]').forEach(function (el) {
            var name = el.name.slice(-2) === '[]' ? el.name.slice(0, -2) : el.name;
            var value = get(data, name);
            if (value === undefined || el.type === 'password') {
                return;
            }
            if (el.type === 'checkbox') {
                el.checked = Array.isArray(value) ? value.indexOf(el.value) !== -1 : Boolean(value);
            } else if (el.type === 'radio') {
                el.checked = String(value) === el.value;
            } else {
                el.value = value === null ? '' : value;
            }
            el.dispatchEvent(new Event('change', { bubbles: true }));
        });
    }

    function clearErrors(form) {
        form.querySelectorAll('.is-invalid').forEach(function (el) {
            el.classList.remove('is-invalid');
        });
        form.querySelectorAll('[data-feedback]').forEach(function (el) {
            el.remove();
        });
    }

    function showErrors(form, fields) {
        clearErrors(form);
        var first = null;
        Object.keys(fields).forEach(function (name) {
            var targets = Array.prototype.filter.call(
                form.querySelectorAll('[name="' + name + '"], [name="' + name + '[]"], [data-error-for="' + name + '"]'),
                fieldActive
            );
            if (!targets.length) {
                notify('danger', fields[name]);
                return;
            }
            targets.forEach(function (el) {
                el.classList.add('is-invalid');
            });
            var last = targets[targets.length - 1];
            var feedback = document.createElement('div');
            feedback.className = 'invalid-feedback d-block';
            feedback.setAttribute('data-feedback', '');
            feedback.textContent = fields[name];
            var anchor = last.closest('.form-check') || last;
            anchor.insertAdjacentElement('afterend', feedback);
            first = first || last;
        });
        if (first && first.focus) {
            first.focus();
        }
    }

    // Wire a form: on submit call handler(data, submitterValue, form).
    // The handler returns a promise of an API result.
    function onSubmit(form, handler) {
        form.addEventListener('submit', function (event) {
            event.preventDefault();
            var submitter = event.submitter;
            var action = submitter && submitter.value ? submitter.value : '';
            clearErrors(form);
            var buttons = form.querySelectorAll('button[type="submit"], button:not([type])');
            buttons.forEach(function (b) { b.disabled = true; });
            Promise.resolve(handler(formData(form), action, form)).finally(function () {
                buttons.forEach(function (b) { b.disabled = false; });
            });
        });
    }

    // Binding data into the skeleton -------------------------------------

    // [data-bind="path"] -> textContent (data-format: bytes|time|duration|text)
    // [data-bind-show="path"] -> shown when truthy; [data-bind-hide="path"] the reverse
    function bind(root, data) {
        root.querySelectorAll('[data-bind]').forEach(function (el) {
            var value = get(data, el.dataset.bind);
            var format = FORMATS[el.dataset.format || 'text'] || FORMATS.text;
            el.textContent = format(value);
        });
        root.querySelectorAll('[data-bind-show]').forEach(function (el) {
            el.hidden = !get(data, el.dataset.bindShow);
        });
        root.querySelectorAll('[data-bind-hide]').forEach(function (el) {
            el.hidden = Boolean(get(data, el.dataset.bindHide));
        });
    }

    // Render rows into a table body / list from its <template data-row>.
    // fill(fragment, row) customises each clone; [data-empty] shows when empty.
    function list(container, rows, fill) {
        var template = container.querySelector('template[data-row]');
        var empty = container.querySelector('[data-empty]');
        container.querySelectorAll('[data-rendered]').forEach(function (el) { el.remove(); });
        (rows || []).forEach(function (row) {
            var fragment = template.content.cloneNode(true);
            Array.prototype.forEach.call(fragment.children, function (child) {
                child.setAttribute('data-rendered', '');
            });
            bind(fragment, row);
            if (fill) {
                fill(fragment, row);
            }
            container.insertBefore(fragment, template);
        });
        if (empty) {
            empty.hidden = Boolean(rows && rows.length);
        }
    }

    function badge(el, cls, text) {
        el.className = el.className.replace(/\btext-bg-\w+/g, '').trim() + ' text-bg-' + cls;
        if (text !== undefined) {
            el.textContent = text;
        }
    }

    // Shared UI pieces -----------------------------------------------------

    function usbState(usb) {
        var state = usb.state || {};
        if (!usb.enabled) {
            return ['secondary', t('usb.state_disabled')];
        }
        if (!usb.image || !usb.image.exists) {
            return ['secondary', t('usb.state_no_image')];
        }
        if (!state.attached) {
            return ['warning', t('usb.state_detached')];
        }
        return state.host_connected ? ['success', t('usb.state_connected')] : ['info', t('usb.state_waiting_host')];
    }

    var STATUS_CLASS = { pending: 'info', done: 'success', failed: 'danger', discarded: 'secondary' };

    function uploadBadge(el, status) {
        badge(el, STATUS_CLASS[status] || 'secondary', t('upload.status_' + status));
    }

    // Result of a connection test as an alert.
    function testResult(container, result, title) {
        container.innerHTML = '';
        if (title) {
            var heading = document.createElement('h2');
            heading.className = 'h6';
            heading.textContent = title;
            container.appendChild(heading);
        }
        var box = document.createElement('div');
        box.className = 'alert ' + (result.ok ? 'alert-success' : 'alert-danger');
        var strong = document.createElement('strong');
        strong.textContent = result.ok ? t('target.test_ok', { seconds: result.duration }) : t('target.test_failed');
        box.appendChild(strong);
        if (result.ok) {
            var ul = document.createElement('ul');
            ul.className = 'mb-0 mt-1 small';
            (result.steps || []).forEach(function (line) {
                var li = document.createElement('li');
                li.textContent = line;
                ul.appendChild(li);
            });
            box.appendChild(ul);
        } else {
            var detail = document.createElement('div');
            detail.className = 'small font-monospace mt-1 text-break';
            detail.textContent = result.error || '';
            box.appendChild(detail);
        }
        container.appendChild(box);
        container.scrollIntoView({ block: 'nearest', behavior: 'smooth' });
    }

    // Generic page behaviour ------------------------------------------------

    // Confirmation for dangerous buttons: <button data-confirm="Really?">
    document.addEventListener('click', function (event) {
        var button = event.target.closest('[data-confirm]');
        if (button && !window.confirm(button.getAttribute('data-confirm'))) {
            event.preventDefault();
            event.stopImmediatePropagation();
        }
    }, true);

    // Target forms: show only the fields of the selected protocol and auth method.
    function initTargetForm(root) {
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
    }
    document.querySelectorAll('[data-target-form]').forEach(initTargetForm);

    showStoredFlash();
    // Page scripts run synchronously after this file; afterwards the spinner
    // reflects their requests (or disappears if a page loads nothing).
    window.setTimeout(syncLoading, 0);

    window.NUF = {
        t: t,
        locale: LOCALE,
        fmtBytes: fmtBytes,
        fmtTime: fmtTime,
        fmtDuration: fmtDuration,
        get: get,
        api: api,
        request: request,
        notify: notify,
        clearNotices: clearNotices,
        showFailure: showFailure,
        flashNext: flashNext,
        formData: formData,
        fillForm: fillForm,
        showErrors: showErrors,
        clearErrors: clearErrors,
        onSubmit: onSubmit,
        bind: bind,
        list: list,
        badge: badge,
        usbState: usbState,
        uploadBadge: uploadBadge,
        testResult: testResult,
        initTargetForm: initTargetForm
    };
})();
