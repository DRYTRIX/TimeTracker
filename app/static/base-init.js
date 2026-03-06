/**
 * Base layout init: global keyboard shortcuts (Ctrl+/, Ctrl+Shift+L, t for timer)
 * and optional sidebar collapse. Expects window.__BASE_INIT__ with URLs when timer shortcut is used.
 */
(function () {
  'use strict';

  function isTyping(e) {
    var t = e.target;
    var tag = (t && t.tagName || '').toLowerCase();
    if (tag === 'input' || tag === 'textarea' || tag === 'select' || (t && t.isContentEditable)) return true;
    var editorSelectors = ['.toastui-editor', '.toastui-editor-contents', '.ProseMirror', '.CodeMirror', '.ql-editor', '.tox-edit-area', '.note-editable', '[contenteditable="true"]', '.toastui-editor-ww-container', '.toastui-editor-md-container'];
    for (var i = 0; i < editorSelectors.length; i++) {
      if (t.closest && t.closest(editorSelectors[i])) return true;
    }
    return false;
  }

  document.addEventListener('keydown', function (e) {
    if ((e.ctrlKey || e.metaKey) && !e.shiftKey && !e.altKey && e.key === '/') {
      e.preventDefault();
      var search = document.getElementById('header-search');
      if (search) {
        search.focus();
        if (search.select) search.select();
      }
    }
  });

  document.addEventListener('keydown', function (e) {
    if ((e.ctrlKey || e.metaKey) && e.shiftKey && (e.key === 'l' || e.key === 'L')) {
      e.preventDefault();
      var themeToggle = document.getElementById('theme-toggle');
      if (themeToggle) themeToggle.click();
    }
  });

  var urls = window.__BASE_INIT__ || {};
  async function toggleTimer() {
    try {
      if (!urls.timerStatus || !urls.stopTimer || !urls.dashboard || !urls.manualEntry) return;
      var statusRes = await fetch(urls.timerStatus, { credentials: 'same-origin' });
      var status = await statusRes.json();
      if (status && status.active) {
        var meta = document.querySelector('meta[name="csrf-token"]');
      var token = (meta && meta.getAttribute('content')) || '';
        var stopRes = await fetch(urls.stopTimer, { method: 'POST', headers: { 'X-CSRF-Token': token }, credentials: 'same-origin' });
        if (stopRes.ok && window.toastManager && window.toastManager.info) window.toastManager.info('Timer stopped');
        window.location.href = urls.dashboard;
      } else {
        window.location.href = urls.manualEntry;
      }
    } catch (_) {
      if (urls.manualEntry) window.location.href = urls.manualEntry;
    }
  }

  document.addEventListener('keydown', function (e) {
    if (isTyping(e)) return;
    if (!e.ctrlKey && !e.metaKey && !e.altKey && (e.key === 't' || e.key === 'T')) {
      e.preventDefault();
      toggleTimer();
    }
  });
})();
