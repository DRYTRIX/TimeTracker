/**
 * System idle detection for the Electron desktop app.
 *
 * Polls powerMonitor.getSystemIdleTime() every 60s to gate heartbeats: only
 * send heartbeats while the OS reports the user as active. The "Still
 * working?" prompt is shown ONLY when the server arms idle_notified (via
 * timer status), never from local OS idle alone — otherwise the answer would
 * race without a check token (Issue #722).
 *
 * The desktop app NEVER stops the timer itself: answers go through
 * POST /api/v1/timer/idle-response (first answer on any device wins),
 * and an unanswered grace window is resolved by the server sweep.
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
  let idleNotifiedAt = null;
  let needsReviewNotifiedFor = null;

  function clearGrace() {
    if (graceTimer) {
      clearTimeout(graceTimer);
      graceTimer = null;
    }
    promptShown = false;
    stopAtMs = null;
    idleNotifiedAt = null;
  }

  /** End the local grace countdown without re-arming the prompt. */
  function endGraceCountdown() {
    if (graceTimer) {
      clearTimeout(graceTimer);
      graceTimer = null;
    }
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
        request.on('error', () => {
          console.debug('[IdleMonitor] request failed');
          resolve(null);
        });
        if (body !== undefined) {
          request.write(JSON.stringify(body));
        }
        request.end();
      } catch (e) {
        console.debug('[IdleMonitor] request error');
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

  /** Grace expired unanswered: the server sweep will resolve it — inform only. */
  function showUnansweredNotification() {
    try {
      if (!Notification.isSupported()) return;
      const autoStop = unansweredAction === 'auto_stop';
      const body = autoStop
        ? 'No answer received — the server will stop this timer (credited to your last activity) at its next check.'
        : 'No answer received — the server will flag this timer for review at its next check.';
      const notification = new Notification({
        title: 'Timer idle — awaiting server',
        body,
      });
      notification.on('click', () => {
        focusMainWindow();
      });
      notification.show();
    } catch (e) {
      console.debug('[IdleMonitor] notification failed:', e.message);
    }
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

  function beginGrace(notifiedAt) {
    if (promptShown || !timerActive) return;
    // Require the server check token so answers participate in first-wins.
    if (!notifiedAt) return;
    promptShown = true;
    idleNotifiedAt = notifiedAt;
    // OS idle already equals the threshold; credit that window (≈ now).
    stopAtMs = Date.now();
    showStillWorkingNotification();
    sendToMainWindow('idle:prompt', {
      stopAtMs,
      graceMs: GRACE_MS,
      idleTimeoutMinutes,
      idleUnansweredAction: unansweredAction,
      idleNotifiedAt: notifiedAt,
    });
    focusMainWindow();
    graceTimer = setTimeout(() => {
      // Never stop or flag locally: the SERVER sweep is the only actor that
      // resolves an unanswered check (Issue #722). Keep promptShown set so
      // the next status tick does not re-arm until the server state changes.
      endGraceCountdown();
      showUnansweredNotification();
    }, GRACE_MS);
  }

  async function confirmStillWorking() {
    clearGrace();
    await sendHeartbeat();
    sendToMainWindow('idle:dismissed', {});
  }

  /** Clear local prompt/grace without heartbeating (used after stop/trim). */
  function dismissPrompt() {
    clearGrace();
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
    // Server already marked this timer idle (#722) — show prompt with its token.
    const timer = (data && data.timer) || {};
    const idleNotified = Boolean(data.idle_notified || timer.idle_notified);
    const needsReview = Boolean(data.needs_review || timer.needs_review);
    const notifiedAt =
      data.idle_notified_at || timer.idle_notified_at || null;
    if (needsReview && promptShown) {
      clearGrace();
    } else if (!idleNotified && promptShown) {
      // Resolved elsewhere or by the server sweep.
      clearGrace();
    } else if (idleNotified && !promptShown && !needsReview) {
      beginGrace(notifiedAt);
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
    // Local OS idle only gates heartbeats — never shows the prompt. The
    // server sweep arms idle_notified; onTimerStatusUpdate shows the UI.
    if (idleSeconds >= thresholdSeconds) {
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
    dismissPrompt,
    confirmStop,
    sendHeartbeat,
  };
}

module.exports = { createIdleMonitor };
