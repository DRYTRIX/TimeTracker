/**
 * Shared confirm / alert dialogs (replaces native confirm() and alert()).
 *
 * Exports: window.ttConfirm, window.ttAlert
 * Back-compat: window.showConfirm, window.showAlert
 *
 * Remaining native alert()/confirm() call sites should migrate to ttAlert/ttConfirm.
 */
(function (global) {
  'use strict';

  var ROOT_ID = 'tt-dialog-root';
  var previousFocus = null;
  var activeCleanup = null;

  var VARIANTS = {
    primary: {
      iconWrap: 'bg-sky-100 dark:bg-sky-900/30',
      icon: 'text-sky-600 dark:text-sky-400',
      btn: 'bg-primary hover:bg-primary/90',
    },
    danger: {
      iconWrap: 'bg-rose-100 dark:bg-rose-900/30',
      icon: 'text-rose-600 dark:text-rose-400',
      btn: 'bg-rose-600 hover:bg-rose-700',
    },
    warning: {
      iconWrap: 'bg-amber-100 dark:bg-amber-900/30',
      icon: 'text-amber-600 dark:text-amber-400',
      btn: 'bg-amber-500 hover:bg-amber-600',
    },
    info: {
      iconWrap: 'bg-blue-100 dark:bg-blue-900/30',
      icon: 'text-blue-600 dark:text-blue-400',
      btn: 'bg-primary hover:bg-primary/90',
    },
  };

  function normalizeOptions(opts) {
    var options = opts || {};
    return {
      title: options.title != null ? String(options.title) : '',
      confirmText: options.confirmText || options.okText || 'OK',
      cancelText: options.cancelText || 'Cancel',
      variant: options.variant || 'primary',
      mode: options.mode || 'confirm',
    };
  }

  function getRoot() {
    var root = document.getElementById(ROOT_ID);
    if (!root) {
      root = document.createElement('div');
      root.id = ROOT_ID;
      document.body.appendChild(root);
    }
    return root;
  }

  function getFocusable(container) {
    var sel =
      'button:not([disabled]), [href], input:not([disabled]), select:not([disabled]), textarea:not([disabled]), [tabindex]:not([tabindex="-1"])';
    return Array.prototype.filter.call(container.querySelectorAll(sel), function (el) {
      return el.offsetParent !== null || el === document.activeElement;
    });
  }

  function closeDialog(result) {
    if (typeof activeCleanup === 'function') {
      var fn = activeCleanup;
      activeCleanup = null;
      fn(result);
    }
  }

  function openDialog(message, opts) {
    var options = normalizeOptions(opts);
    var isAlert = options.mode === 'alert';
    var variant = VARIANTS[options.variant] || VARIANTS.primary;

    if (activeCleanup) {
      try {
        activeCleanup(isAlert ? undefined : false);
      } catch (_) {}
    }

    return new Promise(function (resolve) {
      previousFocus = document.activeElement;

      var overlay = document.createElement('div');
      overlay.className =
        'fixed inset-0 z-[2000] flex items-center justify-center px-4';
      overlay.setAttribute('role', 'presentation');

      var backdrop = document.createElement('button');
      backdrop.type = 'button';
      backdrop.className = 'absolute inset-0 bg-black/50 dark:bg-black/60 cursor-default';
      backdrop.setAttribute('aria-label', 'Close dialog');
      backdrop.tabIndex = -1;

      var panel = document.createElement('div');
      panel.className =
        'relative bg-card-light dark:bg-card-dark text-text-light dark:text-text-dark rounded-lg shadow-xl w-full max-w-md mx-4 outline-none';
      panel.setAttribute('role', 'dialog');
      panel.setAttribute('aria-modal', 'true');
      panel.tabIndex = -1;

      var body = document.createElement('div');
      body.className = 'p-6';

      var row = document.createElement('div');
      row.className = 'flex items-start gap-3';

      var iconWrap = document.createElement('div');
      iconWrap.className =
        'w-12 h-12 rounded-full flex items-center justify-center flex-shrink-0 ' +
        variant.iconWrap;
      iconWrap.innerHTML =
        '<i class="fas fa-exclamation-triangle ' +
        variant.icon +
        '" aria-hidden="true"></i>';

      var textCol = document.createElement('div');
      textCol.className = 'flex-1 min-w-0';

      var titleId = 'tt-dialog-title';
      var descId = 'tt-dialog-desc';

      if (options.title) {
        var titleEl = document.createElement('h3');
        titleEl.id = titleId;
        titleEl.className = 'text-lg font-semibold mb-1 text-text-light dark:text-text-dark';
        titleEl.textContent = options.title;
        panel.setAttribute('aria-labelledby', titleId);
        textCol.appendChild(titleEl);
      } else {
        panel.setAttribute('aria-labelledby', descId);
      }

      var msgEl = document.createElement('p');
      msgEl.id = descId;
      msgEl.className = 'text-sm text-text-muted-light dark:text-text-muted-dark whitespace-pre-wrap';
      msgEl.textContent = message != null ? String(message) : '';
      textCol.appendChild(msgEl);

      row.appendChild(iconWrap);
      row.appendChild(textCol);
      body.appendChild(row);

      var actions = document.createElement('div');
      actions.className = 'mt-6 flex justify-end gap-3';

      var cancelBtn = null;
      var confirmBtn = document.createElement('button');
      confirmBtn.type = 'button';
      confirmBtn.className =
        'px-4 py-2 text-white rounded-lg transition-colors ' + variant.btn;
      confirmBtn.textContent = options.confirmText;

      if (!isAlert) {
        cancelBtn = document.createElement('button');
        cancelBtn.type = 'button';
        cancelBtn.className =
          'px-4 py-2 bg-gray-200 dark:bg-gray-700 text-gray-800 dark:text-gray-200 rounded-lg hover:bg-gray-300 dark:hover:bg-gray-600 transition-colors';
        cancelBtn.textContent = options.cancelText;
        actions.appendChild(cancelBtn);
      }

      actions.appendChild(confirmBtn);
      body.appendChild(actions);
      panel.appendChild(body);
      overlay.appendChild(backdrop);
      overlay.appendChild(panel);

      function finish(result) {
        document.removeEventListener('keydown', onKeyDown, true);
        try {
          getRoot().removeChild(overlay);
        } catch (_) {}
        activeCleanup = null;
        var restore = previousFocus;
        previousFocus = null;
        if (restore && typeof restore.focus === 'function') {
          try {
            restore.focus();
          } catch (_) {}
        }
        resolve(result);
      }

      activeCleanup = finish;

      function onKeyDown(e) {
        if (e.key === 'Escape') {
          e.preventDefault();
          finish(isAlert ? undefined : false);
          return;
        }
        if (e.key === 'Tab') {
          var nodes = getFocusable(panel);
          if (!nodes.length) {
            e.preventDefault();
            return;
          }
          var first = nodes[0];
          var last = nodes[nodes.length - 1];
          if (e.shiftKey && document.activeElement === first) {
            e.preventDefault();
            last.focus();
          } else if (!e.shiftKey && document.activeElement === last) {
            e.preventDefault();
            first.focus();
          }
        }
      }

      backdrop.addEventListener('click', function () {
        finish(isAlert ? undefined : false);
      });
      if (cancelBtn) {
        cancelBtn.addEventListener('click', function () {
          finish(false);
        });
      }
      confirmBtn.addEventListener('click', function () {
        finish(isAlert ? undefined : true);
      });

      document.addEventListener('keydown', onKeyDown, true);
      getRoot().appendChild(overlay);
      confirmBtn.focus();
    });
  }

  function ttConfirm(message, options) {
    try {
      return openDialog(message, Object.assign({}, options || {}, { mode: 'confirm' }));
    } catch (_) {
      try {
        return Promise.resolve(global.confirm(message));
      } catch (__) {
        return Promise.resolve(false);
      }
    }
  }

  function ttAlert(message, options) {
    try {
      var opts = Object.assign({ confirmText: 'OK', mode: 'alert' }, options || {}, { mode: 'alert' });
      return openDialog(message, opts).then(function () {});
    } catch (_) {
      try {
        global.alert(message);
      } catch (__) {}
      return Promise.resolve();
    }
  }

  global.ttConfirm = ttConfirm;
  global.ttAlert = ttAlert;
  global.showConfirm = ttConfirm;
  global.showAlert = ttAlert;
})(typeof window !== 'undefined' ? window : globalThis);
