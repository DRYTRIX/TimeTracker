/**
 * System idle detection for the Electron desktop app.
 *
 * Polls powerMonitor.getSystemIdleTime() every 60s. When an active timer is
 * running and the OS idle time exceeds idle_timeout_minutes, shows a
 * "Still working?" notification and notifies the renderer. If the 5-minute
 * grace window expires unanswered:
 * - review (default): the timer KEEPS RUNNING and is flagged for review
 * - auto_stop: stop credited to last_active + idle_timeout (Issue #722)
 */

const { powerMonitor, Notification, net } = require('electron');

const CHECK_INTERVAL_MS = 60 * 1000;
const GRACE_MS = 5 * 60 * 1000;
const DEFAULT_IDLE_TIMEOUT_MINUTES = 30;

function clampIdleTimeoutMinutes(value) {
  const n = Number(value);
  if (!Number.isFinite(n) || n < 1) return DEFAULT_IDLE_TIMEOUT_MINUTES;
  return Math.min(480, Math.floor(n));
}

function normalizeUnansweredAction(value) {
  const v = String(value || 'review').trim().toLowerCase();
  return v === 'auto_stop' ? 'auto_stop' : 'review';
}

function createIdleMonitor({ store, sendToMainWindow, focusMainWindow }) {
  let checkInterval = null;
  let graceTimer = null;
  let promptShown = false;
  let timerActive = false;
  let idleTimeoutMinutes = DEFAULT_IDLE_TIMEOUT_MINUTES;
  let unansweredAction = 'review';
  let stopAtMs = null;
  let needsReviewNotifiedFor = null;

  function clearGrace() {
    if (graceTimer) {
      clearTimeout(graceTimer);
      graceTimer = null;
    }
    promptShown = false;
    stopAtMs = null;
  }

  async function apiRequest(method, path, body) {
    if (!store) return null;
    const serverUrl = store.get('server_url');
    const apiToken = store.get('api_token');
    if (!serverUrl || !apiToken) return null;

    let base = String(serverUrl).replace(/\/+$/, '');
    const url = `${base}${path}`;

    return new Promise((resolve) => {
      try {
        const request = net.request({ method, url });
        request.setHeader('Authorization', `Bearer ${apiToken}`);
        request.setHeader('Content-Type', 'application/json');
        request.setHeader('Accept', 'application/json');
        let raw = '';
        request.on('response', (response) => {
          response.on('data', (chunk) => {
            raw += chunk.toString();
          });
          response.on('end', () => {
            resolve({ status: response.statusCode, body: raw });
          });
        });
        request.on('error', (err) => {
          console.debug('[IdleMonitor] request failed:', err.message);
          resolve(null);
        });
        if (body !== undefined) {
          request.write(JSON.stringify(body));
        }
        request.end();
      } catch (e) {
        console.debug('[IdleMonitor] request error:', e.message);
        resolve(null);
      }
    });
  }

  async function sendHeartbeat() {
    await apiRequest('POST', '/api/v1/timer/heartbeat');
  }

  async function stopTimerAt(ms) {
    const stopTime = new Date(ms || Date.now()).toISOString();
    await apiRequest('POST', '/api/v1/timer/stop', { stop_time: stopTime });
    sendToMainWindow('idle:timer-stopped', { reason: 'idle_timeout' });
  }

  function showStillWorkingNotification() {
    try {
      if (!Notification.isSupported()) return;
      const autoStop = unansweredAction === 'auto_stop';
      const body = autoStop
        ? 'Answer within 5 minutes or the timer will be stopped and the idle time kept.'
        : 'Answer within 5 minutes or the timer will be flagged for review (it keeps running).';
      const notification = new Notification({
        title: 'Still working?',
        body,
        urgency: 'critical',
      });
      notification.on('click', () => {
        focusMainWindow();
        confirmStillWorking();
      });
      notification.show();
    } catch (e) {
      console.debug('[IdleMonitor] notification failed:', e.message);
    }
  }

  /** Grace expired unanswered: keep the timer running, flag for review. */
  function flagNeedsReview() {
    clearGrace();
    if (!timerActive) return;
    showNeedsReviewNotification();
    sendToMainWindow('idle:needs-review', {
      idleTimeoutMinutes,
    });
  }

  function showNeedsReviewNotification() {
    try {
      if (!Notification.isSupported()) return;
      const notification = new Notification({
        title: 'Timer needs review',
        body: 'You were idle and did not answer. Your timer kept running — trim the idle time or stop it.',
        urgency: 'critical',
      });
      notification.on('click', () => {
        focusMainWindow();
      });
      notification.show();
    } catch (e) {
      console.debug('[IdleMonitor] notification failed:', e.message);
    }
  }

  function beginGrace() {
    if (promptShown || !timerActive) return;
    promptShown = true;
    // OS idle already equals the threshold; credit that window (≈ now).
    stopAtMs = Date.now();
    showStillWorkingNotification();
    sendToMainWindow('idle:prompt', {
      stopAtMs,
      graceMs: GRACE_MS,
      idleTimeoutMinutes,
      idleUnansweredAction: unansweredAction,
    });
    focusMainWindow();
    graceTimer = setTimeout(() => {
      if (unansweredAction === 'auto_stop') {
        const at = stopAtMs || Date.now();
        clearGrace();
        timerActive = false;
        stopTimerAt(at).catch(() => {});
      } else {
        flagNeedsReview();
      }
    }, GRACE_MS);
  }

  async function confirmStillWorking() {
    clearGrace();
    await sendHeartbeat();
    sendToMainWindow('idle:dismissed', {});
  }

  async function confirmStop() {
    const at = stopAtMs || Date.now();
    clearGrace();
    timerActive = false;
    await stopTimerAt(at);
  }

  function onTimerStatusUpdate(data) {
    const active = Boolean(data && data.active && !data.paused);
    timerActive = active;
    if (data && data.idle_timeout_minutes != null) {
      idleTimeoutMinutes = clampIdleTimeoutMinutes(data.idle_timeout_minutes);
    }
    if (data && data.idle_unanswered_action != null) {
      unansweredAction = normalizeUnansweredAction(data.idle_unanswered_action);
    }
    if (!active) {
      clearGrace();
      needsReviewNotifiedFor = null;
      return;
    }
    // Server already marked this timer idle (#722) — show prompt even if OS idle
    // time has not crossed the threshold yet (e.g. after reconnect).
    const timer = (data && data.timer) || {};
    const idleNotified = Boolean(data.idle_notified || timer.idle_notified);
    const needsReview = Boolean(data.needs_review || timer.needs_review);
    if (idleNotified && !promptShown && !needsReview) {
      beginGrace();
    }
    // Server flagged the timer for review (grace expired elsewhere) — surface it.
    if (needsReview && needsReviewNotifiedFor !== timer.id) {
      needsReviewNotifiedFor = timer.id || 'unknown';
      showNeedsReviewNotification();
      sendToMainWindow('idle:needs-review', { idleTimeoutMinutes });
    } else if (!needsReview) {
      needsReviewNotifiedFor = null;
    }
  }

  function tick() {
    if (!timerActive || promptShown) return;
    let idleSeconds = 0;
    try {
      idleSeconds = powerMonitor.getSystemIdleTime();
    } catch (e) {
      console.debug('[IdleMonitor] getSystemIdleTime failed:', e.message);
      return;
    }
    const thresholdSeconds = idleTimeoutMinutes * 60;
    if (idleSeconds >= thresholdSeconds) {
      beginGrace();
      return;
    }
    // User is active — keep server heartbeat fresh (throttled by check interval).
    if (idleSeconds < 60) {
      sendHeartbeat().catch(() => {});
    }
  }

  function start() {
    if (checkInterval) return;
    checkInterval = setInterval(tick, CHECK_INTERVAL_MS);
    // First check shortly after start
    setTimeout(tick, 5000);
  }

  function stop() {
    if (checkInterval) {
      clearInterval(checkInterval);
      checkInterval = null;
    }
    clearGrace();
  }

  return {
    start,
    stop,
    onTimerStatusUpdate,
    confirmStillWorking,
    confirmStop,
    sendHeartbeat,
  };
}

module.exports = { createIdleMonitor };
