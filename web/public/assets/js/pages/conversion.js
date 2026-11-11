// Audio conversion: rules that convert recordings to FLAC, MP3 or AAC before the upload.
(function () {
    'use strict';
    var root = document.getElementById('conversion');
    if (!root) {
        return;
    }
    var t = NUF.t;
    var canEdit = root.dataset.canEdit === '1';
    var form = root.querySelector('[data-conversion-form]');
    var list = root.querySelector('[data-rules]');
    var template = root.querySelector('[data-rule-template]');
    var choices = null;
    var defaultRule = null;

    function fmtRate(hz) {
        var text = String(parseFloat((hz / 1000).toFixed(3))) + ' kHz';
        return document.documentElement.lang === 'de' ? text.replace('.', ',') : text;
    }

    function field(card, name) {
        return card.querySelector('[data-field="' + name + '"]');
    }

    function fillSelect(select, values, label, keep) {
        var current = select.value;
        select.innerHTML = '';
        values.forEach(function (value) {
            var option = document.createElement('option');
            option.value = value;
            option.textContent = value === 0 && keep ? keep : label(value);
            select.appendChild(option);
        });
        if (values.map(String).indexOf(current) !== -1) {
            select.value = current;
        }
    }

    // Show only the settings of the chosen format and limit the choices to what it supports.
    function updateCard(card) {
        var format = field(card, 'format').value;
        var mode = field(card, 'mp3_mode').value;
        card.querySelectorAll('[data-show-format]').forEach(function (el) {
            var formats = el.dataset.showFormat.split(' ');
            var visible = formats.indexOf(format) !== -1;
            if (visible && el.dataset.showMode && format === 'mp3') {
                visible = el.dataset.showMode === mode;
            }
            el.hidden = !visible;
        });

        var bitrate = field(card, 'bitrate');
        var wanted = bitrate.value || bitrate.dataset.value;
        var rates = format === 'mp3' ? choices.mp3_bitrates : choices.aac_bitrates;
        fillSelect(bitrate, rates, function (v) { return v + ' kbit/s'; });
        if (wanted && rates.map(String).indexOf(String(wanted)) !== -1) {
            bitrate.value = wanted;
        } else if (rates.indexOf(192) !== -1) {
            bitrate.value = '192';
        }

        var sampleRate = field(card, 'sample_rate');
        var max = choices.max_sample_rate[format];
        Array.prototype.forEach.call(sampleRate.options, function (option) {
            option.disabled = Number(option.value) > max;
        });
        if (Number(sampleRate.value) > max) {
            sampleRate.value = '0';
        }

        var ext = choices.extensions[format];
        card.querySelector('[data-format-help]').textContent = t('conversion.format_help_' + format, { ext: '.' + ext });
    }

    // Field names carry the rule position ("rules.0.format"), so error
    // messages from the service land on the right field.
    function renumber() {
        var cards = list.querySelectorAll('[data-rule]');
        cards.forEach(function (card, index) {
            card.querySelector('[data-rule-title]').textContent = t('conversion.rule_title', { n: index + 1 });
            card.querySelectorAll('[data-field]').forEach(function (el) {
                el.name = 'rules.' + index + '.' + el.dataset.field;
                el.id = 'rule_' + index + '_' + el.dataset.field;
            });
            card.querySelectorAll('[data-label-for]').forEach(function (label) {
                label.htmlFor = 'rule_' + index + '_' + label.dataset.labelFor;
            });
            var up = card.querySelector('[data-action="up"]');
            var down = card.querySelector('[data-action="down"]');
            if (up) {
                up.disabled = index === 0;
                down.disabled = index === cards.length - 1;
            }
        });
        list.querySelector('[data-empty]').hidden = cards.length > 0;
        var add = root.querySelector('[data-action="add"]');
        if (add && choices) {
            add.disabled = cards.length >= choices.max_rules;
        }
    }

    function addRule(rule) {
        var fragment = template.content.cloneNode(true);
        var card = fragment.querySelector('[data-rule]');
        fillSelect(field(card, 'sample_rate'), choices.sample_rates, fmtRate, t('conversion.keep_source'));
        list.appendChild(fragment);
        renumber();
        Object.keys(rule).forEach(function (key) {
            var el = field(card, key);
            if (!el) {
                return;
            }
            var value = rule[key];
            if (el.type === 'checkbox') {
                el.checked = Boolean(value);
            } else if (key === 'extensions') {
                el.value = (value || []).join(', ');
            } else if (key === 'bitrate') {
                el.dataset.value = value;
            } else {
                el.value = value;
            }
        });
        updateCard(card);
        return card;
    }

    function render(data) {
        choices = data.choices;
        defaultRule = data.default_rule;
        list.querySelectorAll('[data-rule]').forEach(function (card) { card.remove(); });
        form.querySelector('[name="enabled"]').checked = Boolean(data.settings.enabled);
        (data.settings.rules || []).forEach(addRule);
        renumber();
        root.querySelector('[data-ffmpeg-missing]').hidden = data.available;
        root.querySelector('[data-ffmpeg-version]').textContent = data.available
            ? t('conversion.ffmpeg_version', { version: data.ffmpeg_version || '?' })
            : '';
        var queue = data.queue || {};
        root.querySelector('[data-queue]').textContent = queue.current
            ? t('conversion.converting', { file: queue.current.path, n: queue.pending })
            : t('conversion.queue', { n: queue.pending || 0 });
    }

    function load() {
        return NUF.api('GET', '/conversion').then(function (r) {
            if (!r.ok) {
                NUF.notify('danger', r.message);
                return;
            }
            render(r.data);
        });
    }

    form.addEventListener('change', function (event) {
        var card = event.target.closest('[data-rule]');
        if (card && (event.target.dataset.field === 'format' || event.target.dataset.field === 'mp3_mode')) {
            updateCard(card);
        }
    });

    root.addEventListener('click', function (event) {
        var button = event.target.closest('[data-action]');
        if (!button || button.disabled || !canEdit) {
            return;
        }
        var action = button.dataset.action;
        var card = button.closest('[data-rule]');
        if (action === 'add') {
            var rule = Object.assign({}, defaultRule);
            var used = [];
            list.querySelectorAll('[data-field="extensions"]').forEach(function (el) {
                used = used.concat(el.value.toLowerCase().split(/[\s,;]+/));
            });
            rule.extensions = used.indexOf('wav') === -1 ? ['wav'] : [];
            var added = addRule(rule);
            field(added, 'extensions').focus();
        } else if (action === 'remove') {
            card.remove();
            renumber();
        } else if (action === 'up' && card.previousElementSibling && card.previousElementSibling.matches('[data-rule]')) {
            list.insertBefore(card, card.previousElementSibling);
            renumber();
        } else if (action === 'down' && card.nextElementSibling) {
            list.insertBefore(card.nextElementSibling, card);
            renumber();
        }
    });

    NUF.onSubmit(form, function (data) {
        NUF.clearNotices();
        var rules = [];
        list.querySelectorAll('[data-rule]').forEach(function (card, index) {
            var rule = (data.rules || {})[index] || {};
            rule.extensions = field(card, 'extensions').value;
            rules.push(rule);
        });
        return NUF.api('PUT', '/conversion', { enabled: Boolean(data.enabled), rules: rules }).then(function (r) {
            if (!r.ok) {
                NUF.showFailure(r, form);
                return;
            }
            NUF.notify('success', t('common.saved'));
            render(r.data);
        });
    });

    load();
})();
