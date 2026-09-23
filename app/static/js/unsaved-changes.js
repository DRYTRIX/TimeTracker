/**
 * Warn before leaving pages when a guarded form or editor has unsaved edits.
 *
 * Mark scope with `data-unsaved-guard` on a <form> or container element.
 * Custom editors (e.g. Konva PDF layout) can dispatch:
 *   window.dispatchEvent(new CustomEvent('tt:unsaved-dirty'));
 *   window.dispatchEvent(new CustomEvent('tt:unsaved-clean'));
 */
(function () {
    var dirty = false;

    function message() {
        if (window.i18n && window.i18n.messages && window.i18n.messages.unsavedChanges) {
            return window.i18n.messages.unsavedChanges;
        }
        return 'You have unsaved changes. Are you sure you want to leave?';
    }

    function markDirty() {
        dirty = true;
    }

    function markClean() {
        dirty = false;
    }

    function bindGuard(root) {
        if (!root || root.dataset.unsavedGuardBound === '1') return;
        root.dataset.unsavedGuardBound = '1';

        root.addEventListener(
            'input',
            function () {
                markDirty();
            },
            true
        );
        root.addEventListener(
            'change',
            function () {
                markDirty();
            },
            true
        );
        root.addEventListener(
            'submit',
            function () {
                markClean();
            },
            true
        );
    }

    function initGuards() {
        document.querySelectorAll('[data-unsaved-guard]').forEach(bindGuard);
    }

    window.addEventListener('tt:unsaved-dirty', markDirty);
    window.addEventListener('tt:unsaved-clean', markClean);

    window.addEventListener('beforeunload', function (e) {
        if (!dirty) return;
        e.preventDefault();
        e.returnValue = message();
        return e.returnValue;
    });

    document.addEventListener(
        'click',
        function (e) {
            if (!dirty) return;
            var a = e.target.closest && e.target.closest('a[href]');
            if (!a || a.target === '_blank' || a.hasAttribute('download')) return;
            var href = a.getAttribute('href') || '';
            if (!href || href.charAt(0) === '#' || href.indexOf('javascript:') === 0) return;
            if (a.dataset.unsavedGuardBypass === 'true') return;
            // eslint-disable-next-line no-alert
            if (!window.confirm(message())) {
                e.preventDefault();
                e.stopPropagation();
            }
        },
        true
    );

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', initGuards);
    } else {
        initGuards();
    }

    if (typeof MutationObserver !== 'undefined') {
        var observer = new MutationObserver(function () {
            initGuards();
        });
        observer.observe(document.body, { childList: true, subtree: true });
    }
})();
