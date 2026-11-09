// Setup wizard: loads the state via AJAX, shows the current step and submits it.
(function () {
    'use strict';
    var root = document.getElementById('setup');
    if (!root) {
        return;
    }
    var t = NUF.t;
    var notices = root.querySelector('[data-notices]');
    var counter = root.querySelector('[data-step-counter]');
    var stepList = root.querySelector('[data-step-list]');

    function show(screen) {
        root.querySelectorAll('[data-screen]').forEach(function (el) {
            el.hidden = el.dataset.screen !== screen;
        });
    }

    function renderSteps(steps, current) {
        var index = steps.indexOf(current);
        counter.textContent = counter.dataset.template.replace('{n}', index + 1).replace('{total}', steps.length);
        stepList.querySelectorAll('[data-goto]').forEach(function (link) {
            var i = steps.indexOf(link.dataset.goto);
            var cls = i < index ? 'success' : (i === index ? 'primary' : 'light');
            NUF.badge(link, cls);
            link.classList.toggle('border', i > index);
            link.classList.toggle('pe-none', i >= index);
            link.setAttribute('aria-current', i === index ? 'step' : 'false');
        });
        counter.hidden = false;
        stepList.hidden = false;
    }

    // Fill the dynamic parts of a step from the loaded data.
    function fillStep(step, data) {
        var section = root.querySelector('[data-screen="' + step + '"]');
        var form = section.querySelector('form');
        if (step === 'system') {
            var select = form.querySelector('[name="timezone"]');
            select.innerHTML = '';
            var zones = (data.timezones || []).slice();
            // Keep the current zone selectable even if the list does not contain it.
            if (data.current && zones.indexOf(data.current) === -1) {
                zones.unshift(data.current);
            }
            zones.forEach(function (tz) {
                select.add(new Option(tz, tz));
            });
            NUF.fillForm(form, { hostname: data.hostname || 'netusbflash', timezone: data.current || 'UTC' });
        } else if (step === 'usb') {
            var settings = data.settings || {};
            var max = data.max_size_mb || 0;
            NUF.fillForm(form, {
                size_mb: Math.min(settings.size_mb || 4096, max || 4096),
                filesystem: settings.filesystem,
                label: settings.label,
                idle_seconds: settings.idle_seconds,
                sync_mode: settings.sync_mode
            });
            form.querySelector('[name="size_mb"]').max = max;
            var help = section.querySelector('[data-size-help]');
            help.textContent = help.dataset.template.replace('{value}', max);
            var warning = section.querySelector('[data-usb-unavailable]');
            warning.textContent = data.unavailable_message || '';
            warning.hidden = !data.unavailable_message;
        }
    }

    function load() {
        return NUF.request('/setup/api/state', 'GET').then(function (state) {
            if (!state.ok) {
                NUF.notify('danger', state.message, notices);
                return;
            }
            root.querySelector('[data-simulated]').hidden = !state.simulated;
            if (state.message) {
                NUF.notify('danger', state.message, notices);
            }
            if (!state.verified) {
                counter.hidden = true;
                stepList.hidden = true;
                show('code');
                root.querySelector('#code').focus();
                return;
            }
            renderSteps(state.steps, state.step);
            fillStep(state.step, state.data || {});
            show(state.step);
        });
    }

    function handle(result, form) {
        if (result.reload || (result.ok && !result.stay)) {
            NUF.clearNotices(notices);
            if (result.message) {
                NUF.notify('danger', result.message, notices);
            }
            return load();
        }
        if (result.test) {
            NUF.testResult(root.querySelector('[data-test-result]'), result.test);
        }
        if (result.notice) {
            NUF.notify('success', result.notice, notices);
        }
        if (!result.ok) {
            if (result.fields && Object.keys(result.fields).length) {
                NUF.showErrors(form, result.fields);
            } else {
                NUF.notify('danger', result.message || t('error.network'), notices);
            }
        }
        return null;
    }

    root.querySelectorAll('form[data-setup-form]').forEach(function (form) {
        NUF.onSubmit(form, function (data, action) {
            NUF.clearNotices(notices);
            if (form.dataset.setupForm === 'code') {
                return NUF.request('/setup/api/verify', 'POST', data).then(function (r) { return handle(r, form); });
            }
            data.action = action || 'save';
            return NUF.request('/setup/api/submit', 'POST', data).then(function (r) { return handle(r, form); });
        });
    });

    stepList.addEventListener('click', function (event) {
        var link = event.target.closest('[data-goto]');
        if (!link) {
            return;
        }
        event.preventDefault();
        NUF.request('/setup/api/goto', 'POST', { step: link.dataset.goto }).then(function (r) { return handle(r); });
    });

    load();
})();
