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

// Auto-detect the device timezone and keep the server profile in sync.
// Only runs for logged-in pages; users who pinned a timezone manually
// ('manual' source) are ignored server-side.
(function () {
  'use strict';
  if (!document.body || !document.body.dataset.authenticated) return;
  var tz;
  try {
    tz = Intl.DateTimeFormat().resolvedOptions().timeZone;
  } catch (_) {
    return;
  }
  if (!tz) return;
  var KEY = 'tt_device_tz';
  var last = null;
  try { last = localStorage.getItem(KEY); } catch (_) {}
  if (last === tz) return;
  var meta = document.querySelector('meta[name="csrf-token"]');
  var token = (meta && meta.getAttribute('content')) || '';
  fetch('/api/timezone', {
    method: 'POST',
    credentials: 'same-origin',
    headers: { 'Content-Type': 'application/json', 'X-CSRF-Token': token },
    body: JSON.stringify({ timezone: tz })
  })
    .then(function (res) { return res.ok ? res.json() : null; })
    .then(function (data) {
      if (data && data.success && !data.ignored) {
        try { localStorage.setItem(KEY, tz); } catch (_) {}
      }
    })
    .catch(function () {});
})();

// Parse a naive ISO datetime (stored wall time in the app timezone, no zone
// suffix) into a correct epoch. Browsers would otherwise interpret it in the
// DEVICE zone, which is wrong when the user travels. Exposed globally so
// dashboard, floating-timer-bar, and idle.js share one implementation.
(function () {
  'use strict';
  function offsetFor(wallMs, tz) {
    try {
      var f = new Intl.DateTimeFormat('en-US', { timeZone: tz, year: 'numeric', month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit', second: '2-digit', hour12: false });
      var p = {};
      f.formatToParts(wallMs).forEach(function (x) { p[x.type] = x.value; });
      var asUTC = Date.UTC(Number(p.year), Number(p.month) - 1, Number(p.day), Number(p.hour) % 24, Number(p.minute), Number(p.second));
      return asUTC - wallMs;
    } catch (_) {
      return 0;
    }
  }
  window.ttParseStart = function (iso) {
    if (!iso) return NaN;
    var ms = new Date(iso).getTime();
    if (!isNaN(ms) && /Z|[+-]\d{2}:?\d{2}$/.test(String(iso))) return ms; // already zone-aware
    if (isNaN(ms)) return ms;
    var tz = window.__TT_APP_TZ__ ||
      (document.querySelector('meta[name="app-timezone"]') || {}).content || '';
    if (!tz || tz === 'UTC') return ms;
    var m = String(iso).match(/^(\d{4})-(\d{2})-(\d{2})[T ](\d{2}):(\d{2})(?::(\d{2}))?/);
    if (!m) return ms;
    var wall = Date.UTC(Number(m[1]), Number(m[2]) - 1, Number(m[3]), Number(m[4]), Number(m[5]), Number(m[6] || 0));
    var off = offsetFor(wall, tz);
    return wall - off;
  };
})();
