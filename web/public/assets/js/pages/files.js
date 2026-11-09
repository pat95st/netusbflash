// File manager: switches the stick's file view (off / read-only / edit) and
// shows FileGator (/fm/) in a frame.
(function () {
    'use strict';
    var root = document.getElementById('files');
    if (!root) {
        return;
    }
    var t = NUF.t;
    var frame = root.querySelector('[data-frame]');
    var frameWrap = root.querySelector('[data-frame-wrap]');
    var frameLoading = root.querySelector('[data-frame-loading]');
    var countdown = root.querySelector('[data-countdown]');
    var state = null;
    var shownMode = null;
    var tick = null;
    var autoOpened = false;

    frame.addEventListener('load', function () {
        frameLoading.hidden = true;
    });

    function loadFrame() {
        frameLoading.hidden = false;
        // A new URL makes FileGator fetch the user again, so permissions match the mode.
        frame.src = '/fm/?v=' + Date.now();
    }

    function updateCountdown() {
        if (!state || state.mode !== 'edit' || !state.edit_until) {
            countdown.textContent = '';
            return;
        }
        var left = Math.max(0, Math.round(state.edit_until - Date.now() / 1000));
        var m = Math.floor(left / 60);
        var s = left % 60;
        countdown.textContent = t('files.edit_ends', { time: m + ':' + (s < 10 ? '0' : '') + s });
        if (left === 0) {
            load(true);
        }
    }

    function render(next, forceReload) {
        state = next;
        var mode = state.mode;
        root.querySelectorAll('[data-mode]').forEach(function (button) {
            var active = button.dataset.mode === mode;
            button.classList.toggle('active', active && !button.closest('[data-state-off]'));
            button.disabled = !state.image_exists && button.dataset.mode !== 'off';
        });
        root.querySelector('[data-action="refresh"]').disabled = mode === 'off';
        root.querySelector('[data-no-image]').hidden = state.image_exists;
        root.querySelector('[data-state-off]').hidden = mode !== 'off' || !state.image_exists;
        root.querySelector('[data-state-view]').hidden = mode !== 'view';
        root.querySelector('[data-state-edit]').hidden = mode !== 'edit';
        frameWrap.hidden = mode === 'off';

        if (mode === 'off') {
            frame.src = 'about:blank';
            frameLoading.hidden = true;
        } else if (forceReload || shownMode !== mode) {
            loadFrame();
        }
        shownMode = mode;

        clearInterval(tick);
        tick = null;
        if (mode === 'edit') {
            tick = setInterval(updateCountdown, 1000);
        }
        updateCountdown();
    }

    function load(silent) {
        return NUF.api('GET', '/browser', null, { silent: silent }).then(function (r) {
            if (!r.ok) {
                if (!silent) {
                    NUF.notify('danger', r.message);
                }
                return;
            }
            // Opening the page shows the files right away (read-only).
            if (!autoOpened && r.data.mode === 'off' && r.data.image_exists) {
                autoOpened = true;
                setMode('view');
                return;
            }
            autoOpened = true;
            render(r.data, false);
        });
    }

    function setMode(mode) {
        NUF.clearNotices();
        return NUF.api('POST', '/browser', { mode: mode }).then(function (r) {
            if (!r.ok) {
                NUF.showFailure(r);
                return load(true);
            }
            render(r.data, true);
            if (mode === 'edit') {
                NUF.notify('warning', t('files.edit_started'));
            } else if (mode === 'off' && state && state.image_exists) {
                NUF.notify('success', t('files.closed'));
            }
        });
    }

    root.addEventListener('click', function (event) {
        var button = event.target.closest('[data-mode], [data-action]');
        if (!button || button.disabled) {
            return;
        }
        if (button.dataset.mode) {
            if (state && button.dataset.mode === state.mode) {
                return;
            }
            setMode(button.dataset.mode);
        } else if (button.dataset.action === 'refresh') {
            NUF.clearNotices();
            NUF.api('POST', '/browser/refresh').then(function (r) {
                if (!r.ok) {
                    NUF.showFailure(r);
                    return;
                }
                render(r.data, true);
            });
        }
    });

    // Picks up a timeout or a mode change made elsewhere.
    setInterval(function () {
        if (!document.hidden) {
            load(true);
        }
    }, 30000);

    load(false);
})();
