/**
 * @deprecated Use inline-create.js (Issue #728 follow-up).
 * Kept so any cached template references keep working.
 */
(function () {
  'use strict';
  if (window.ttInlineCreate) return;
  var s = document.createElement('script');
  s.src = (document.currentScript && document.currentScript.src || '').replace(
    /inline-create-client\.js.*$/,
    'inline-create.js'
  );
  if (!s.src || s.src.indexOf('inline-create.js') === -1) {
    s.src = '/static/inline-create.js';
  }
  document.head.appendChild(s);
})();
