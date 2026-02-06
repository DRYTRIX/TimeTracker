/**
 * Shared typing detection utility.
 *
 * Determines whether the user is currently focused on an input element
 * (input, textarea, select, contenteditable, or rich text editor) so that
 * keyboard shortcuts can be suppressed while the user is typing.
 *
 * Usage:
 *   if (window.TimeTracker.isTyping(event)) return;
 */
(function () {
    'use strict';

    var EDITOR_SELECTORS = [
        '.toastui-editor',
        '.toastui-editor-contents',
        '.ProseMirror',
        '.CodeMirror',
        '.ql-editor',
        '.tox-edit-area',
        '.note-editable',
        '[contenteditable="true"]',
        '.toastui-editor-ww-container',
        '.toastui-editor-md-container',
        '.gjs-frame' // GrapesJS editor
    ];

    /**
     * Check whether the event target is an input-like element.
     *
     * @param {Event|KeyboardEvent} ev - The DOM event to inspect.
     * @returns {boolean} true if the user is typing in a form field or editor.
     */
    function isTyping(ev) {
        var target = ev && ev.target;
        if (!target) return false;

        var tag = (target.tagName || '').toLowerCase();

        // Standard form fields
        if (tag === 'input' || tag === 'textarea' || tag === 'select' || target.isContentEditable) {
            return true;
        }

        // Rich text / code editors
        if (target.closest) {
            for (var i = 0; i < EDITOR_SELECTORS.length; i++) {
                if (target.closest(EDITOR_SELECTORS[i])) {
                    return true;
                }
            }
        }

        return false;
    }

    // Expose on a shared namespace
    window.TimeTracker = window.TimeTracker || {};
    window.TimeTracker.isTyping = isTyping;
})();
