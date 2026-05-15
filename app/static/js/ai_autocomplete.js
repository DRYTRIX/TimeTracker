/*
 * AI ghost-text autocomplete for time-entry notes fields.
 *
 * Binds to any <input> or <textarea> with `data-ai-autocomplete="notes"`. While the user
 * types, this debounced helper queries /api/ai/suggest?q=<value> and shows the rest of the
 * best-matching suggestion as a soft gray "ghost" overlay aligned with the field's caret.
 * Tab/ArrowRight accept the ghost; Escape (or any other change) dismisses it.
 *
 * No build step or framework required — exposes a single global `initAIAutocomplete()` that
 * scans the document (or an optional root) for matching elements and binds them once.
 */
(function (global) {
    'use strict';

    var ENDPOINT = '/api/ai/suggest';
    var DEBOUNCE_MS = 400;
    var MIN_LENGTH = 3;
    var GHOST_COLOR = 'rgba(107, 114, 128, 0.65)'; // gray-500 @ 65%

    function buildOverlay(input) {
        var parent = input.parentNode;
        if (!parent) return null;

        var wrap = document.createElement('span');
        wrap.className = 'ai-autocomplete-wrap';
        var inline = input.tagName === 'TEXTAREA' ? 'block' : 'inline-block';
        wrap.style.cssText = 'position:relative;display:' + inline + ';width:100%;';

        var overlay = document.createElement('div');
        overlay.className = 'ai-autocomplete-ghost';
        overlay.setAttribute('aria-hidden', 'true');
        overlay.style.cssText = [
            'position:absolute',
            'top:0', 'left:0', 'right:0', 'bottom:0',
            'pointer-events:none',
            'overflow:hidden',
            'white-space:pre-wrap',
            'word-wrap:break-word',
            'color:transparent',
            'background:transparent',
            'z-index:0',
            'margin:0'
        ].join(';');

        parent.insertBefore(wrap, input);
        wrap.appendChild(input);
        wrap.appendChild(overlay);

        if (!input.style.backgroundColor) {
            input.style.backgroundColor = 'transparent';
        }
        input.style.position = 'relative';
        input.style.zIndex = '1';

        return overlay;
    }

    function syncOverlayStyles(input, overlay) {
        var cs = window.getComputedStyle(input);
        var props = [
            'fontFamily', 'fontSize', 'fontWeight', 'fontStyle', 'fontVariant',
            'lineHeight', 'letterSpacing', 'wordSpacing', 'textIndent',
            'paddingTop', 'paddingRight', 'paddingBottom', 'paddingLeft',
            'boxSizing', 'textAlign', 'textTransform'
        ];
        for (var i = 0; i < props.length; i++) {
            overlay.style[props[i]] = cs[props[i]];
        }
        overlay.style.borderTopWidth = cs.borderTopWidth;
        overlay.style.borderRightWidth = cs.borderRightWidth;
        overlay.style.borderBottomWidth = cs.borderBottomWidth;
        overlay.style.borderLeftWidth = cs.borderLeftWidth;
        overlay.style.borderColor = 'transparent';
        overlay.style.borderStyle = 'solid';
    }

    function setGhost(input, overlay, suffix) {
        if (!overlay) return;
        overlay.textContent = '';
        if (!suffix) {
            input.removeAttribute('data-ai-ghost');
            return;
        }
        syncOverlayStyles(input, overlay);
        overlay.appendChild(document.createTextNode(input.value || ''));
        var ghost = document.createElement('span');
        ghost.style.color = GHOST_COLOR;
        ghost.textContent = suffix;
        overlay.appendChild(ghost);
        try {
            overlay.scrollTop = input.scrollTop;
            overlay.scrollLeft = input.scrollLeft;
        } catch (_) {}
        input.setAttribute('data-ai-ghost', suffix);
    }

    function clearGhost(input, overlay) {
        setGhost(input, overlay, '');
    }

    function acceptGhost(input, overlay) {
        var suffix = input.getAttribute('data-ai-ghost');
        if (!suffix) return false;
        var current = input.value || '';
        input.value = current + suffix;
        clearGhost(input, overlay);
        try {
            var end = input.value.length;
            input.setSelectionRange(end, end);
        } catch (_) {}
        try { input.dispatchEvent(new Event('input', { bubbles: true })); } catch (_) {}
        try { input.dispatchEvent(new Event('change', { bubbles: true })); } catch (_) {}
        return true;
    }

    function findGhostSuffix(value, suggestions) {
        if (!value || !Array.isArray(suggestions) || !suggestions.length) return '';
        var lower = value.toLowerCase();
        for (var i = 0; i < suggestions.length; i++) {
            var s = suggestions[i];
            var notes = (s && s.notes) ? String(s.notes) : '';
            if (!notes) continue;
            if (notes.length <= value.length) continue;
            if (notes.toLowerCase().indexOf(lower) === 0) {
                return notes.slice(value.length);
            }
        }
        return '';
    }

    var inflightController = null;
    function fetchSuggestions(query) {
        if (inflightController) {
            try { inflightController.abort(); } catch (_) {}
            inflightController = null;
        }
        var controller = (typeof AbortController !== 'undefined') ? new AbortController() : null;
        inflightController = controller;
        var url = ENDPOINT + '?q=' + encodeURIComponent(query);
        return fetch(url, {
            credentials: 'same-origin',
            headers: { 'Accept': 'application/json' },
            cache: 'no-store',
            signal: controller ? controller.signal : undefined
        }).then(function (resp) {
            if (!resp.ok) return [];
            return resp.json();
        }).then(function (data) {
            if (!data || !Array.isArray(data.suggestions)) return [];
            return data.suggestions;
        }).catch(function () {
            return [];
        }).then(function (result) {
            if (inflightController === controller) inflightController = null;
            return result;
        });
    }

    function bindInput(input) {
        if (input.__aiAutocompleteBound) return;
        input.__aiAutocompleteBound = true;
        var overlay = buildOverlay(input);
        if (!overlay) return;

        var debounceTimer = null;

        function onInput() {
            clearGhost(input, overlay);
            if (debounceTimer) { clearTimeout(debounceTimer); debounceTimer = null; }
            var value = input.value || '';
            if (value.length < MIN_LENGTH) return;
            debounceTimer = setTimeout(function () {
                debounceTimer = null;
                var current = input.value || '';
                if (current.length < MIN_LENGTH) return;
                fetchSuggestions(current).then(function (suggestions) {
                    if ((input.value || '') !== current) return;
                    var suffix = findGhostSuffix(current, suggestions);
                    if (suffix) setGhost(input, overlay, suffix);
                });
            }, DEBOUNCE_MS);
        }

        function onKeyDown(e) {
            var hasGhost = !!input.getAttribute('data-ai-ghost');
            if (!hasGhost) return;
            if (e.key === 'Tab' || e.key === 'ArrowRight') {
                if (e.key === 'ArrowRight') {
                    var len = (input.value || '').length;
                    var start = input.selectionStart;
                    var end = input.selectionEnd;
                    if (start !== len || end !== len) return;
                }
                e.preventDefault();
                acceptGhost(input, overlay);
            } else if (e.key === 'Escape') {
                e.stopPropagation();
                clearGhost(input, overlay);
            }
        }

        function onScroll() {
            try {
                overlay.scrollTop = input.scrollTop;
                overlay.scrollLeft = input.scrollLeft;
            } catch (_) {}
        }

        input.addEventListener('input', onInput);
        input.addEventListener('keydown', onKeyDown);
        input.addEventListener('blur', function () { clearGhost(input, overlay); });
        input.addEventListener('scroll', onScroll);
    }

    function initAIAutocomplete(root) {
        var scope = root && root.querySelectorAll ? root : document;
        var nodes = scope.querySelectorAll(
            'input[data-ai-autocomplete="notes"], textarea[data-ai-autocomplete="notes"]'
        );
        for (var i = 0; i < nodes.length; i++) bindInput(nodes[i]);
    }

    global.initAIAutocomplete = initAIAutocomplete;

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', function () { initAIAutocomplete(); });
    } else {
        initAIAutocomplete();
    }
})(window);
