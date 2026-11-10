/**
 * Desktop activity autotracker stub (privacy-first).
 *
 * Disabled by default. Window title/app capture is intentionally not
 * implemented here — see docs/design/DESKTOP_ACTIVITY_AUTOTRACKER.md.
 * When enabled later, samples stay local and feed the ActivityWatch /
 * PendingActivity pipeline rather than a new server path.
 */

'use strict';

let enabled = false;
let intervalHandle = null;

/**
 * @param {object} [options]
 * @param {object} [options.store] electron-store-like instance
 * @param {number} [options.intervalMs]
 * @returns {{ started: boolean, reason?: string }}
 */
function start(options = {}) {
  const store = options.store;
  const flagOn = store ? Boolean(store.get('activity_tracker_enabled', false)) : false;
  if (!flagOn) {
    enabled = false;
    return { started: false, reason: 'feature_flag_off' };
  }

  // Capture is a follow-up; keep API stable without sampling yet.
  enabled = true;
  if (intervalHandle) {
    clearInterval(intervalHandle);
    intervalHandle = null;
  }
  // Placeholder interval so stop() has something to clear once capture lands.
  const intervalMs = Number(options.intervalMs) > 0 ? Number(options.intervalMs) : 60000;
  intervalHandle = setInterval(() => {
    // No-op: active window capture not implemented in Phase 6 stub.
  }, intervalMs);

  return { started: true };
}

function stop() {
  enabled = false;
  if (intervalHandle) {
    clearInterval(intervalHandle);
    intervalHandle = null;
  }
  return { stopped: true };
}

function isEnabled() {
  return Boolean(enabled);
}

module.exports = {
  start,
  stop,
  isEnabled,
};
