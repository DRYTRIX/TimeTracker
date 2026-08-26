/**
 * Service worker: poll timer status, update toolbar badge/icon,
 * and enforce idle timeout with a "Still working?" grace window.
 */

import {
  ApiClient,
  elapsedSecondsFromTimer,
  formatBadgeText,
} from './lib/api.js';

const ALARM_NAME = 'tt-timer-poll';
const IDLE_STOP_ALARM = 'tt-idle-stop';
const IDLE_NOTIFICATION_ID = 'tt-still-working';
const POLL_MINUTES = 0.25; // ~15s
const GRACE_MINUTES = 5;
const DEFAULT_IDLE_TIMEOUT_MINUTES = 30;
/** chrome.idle.setDetectionInterval minimum is 15 seconds */
const MIN_IDLE_DETECTION_SECONDS = 15;

const IDLE_ICONS = {
  16: 'icons/idle-16.png',
  32: 'icons/idle-32.png',
  48: 'icons/idle-48.png',
  128: 'icons/idle-128.png',
};

const RUNNING_ICONS = {
  16: 'icons/running-16.png',
  32: 'icons/running-32.png',
  48: 'icons/running-48.png',
  128: 'icons/running-128.png',
};

async function getCredentials() {
  const data = await chrome.storage.local.get(['server_url', 'api_token', 'logged_out']);
  return data;
}

async function setTimerCache(payload) {
  await chrome.storage.local.set({
    last_timer_status: payload,
    last_timer_poll_at: Date.now(),
  });
}

function setIdleUi() {
  chrome.action.setBadgeText({ text: '' });
  chrome.action.setIcon({ path: IDLE_ICONS });
  chrome.action.setTitle({ title: 'TimeTracker — idle' });
}

function setRunningUi(timer) {
  const seconds = elapsedSecondsFromTimer(timer);
  const badge = formatBadgeText(seconds);
  chrome.action.setBadgeBackgroundColor({ color: '#DC2626' });
  chrome.action.setBadgeText({ text: badge });
  chrome.action.setIcon({ path: RUNNING_ICONS });
  const project = timer.project || 'Timer';
  const task = timer.task ? ` / ${timer.task}` : '';
  chrome.action.setTitle({ title: `TimeTracker — ${project}${task}` });
}

function clampIdleTimeoutMinutes(value) {
  const n = Number(value);
  if (!Number.isFinite(n) || n < 1) return DEFAULT_IDLE_TIMEOUT_MINUTES;
  return Math.min(480, Math.floor(n));
}

async function applyIdleDetectionInterval(idleTimeoutMinutes) {
  const minutes = clampIdleTimeoutMinutes(idleTimeoutMinutes);
  const seconds = Math.max(MIN_IDLE_DETECTION_SECONDS, minutes * 60);
  try {
    chrome.idle.setDetectionInterval(seconds);
    await chrome.storage.local.set({ idle_timeout_minutes: minutes });
  } catch (error) {
    console.debug('[TimeTracker] idle.setDetectionInterval failed:', error);
  }
}

async function clearIdleGraceState() {
  try {
    await chrome.alarms.clear(IDLE_STOP_ALARM);
  } catch (_) {
    /* ignore */
  }
  try {
    await chrome.notifications.clear(IDLE_NOTIFICATION_ID);
  } catch (_) {
    /* ignore */
  }
  await chrome.storage.local.remove(['idle_grace_stop_at', 'idle_grace_active']);
}

async function beginIdleGrace(stopAtMs) {
  const { last_timer_status } = await chrome.storage.local.get('last_timer_status');
  if (!last_timer_status?.active || !last_timer_status?.timer) {
    return;
  }

  const existing = await chrome.storage.local.get(['idle_grace_active']);
  if (existing.idle_grace_active) {
    return;
  }

  await chrome.storage.local.set({
    idle_grace_active: true,
    idle_grace_stop_at: stopAtMs,
  });

  chrome.alarms.create(IDLE_STOP_ALARM, { delayInMinutes: GRACE_MINUTES });

  try {
    await chrome.notifications.create(IDLE_NOTIFICATION_ID, {
      type: 'basic',
      iconUrl: 'icons/running-128.png',
      title: 'Still working?',
      message: `Your timer will stop in ${GRACE_MINUTES} minutes if you do not answer.`,
      priority: 2,
      requireInteraction: true,
      buttons: [
        { title: 'Yes, still working' },
        { title: 'No, stop timer' },
      ],
    });
  } catch (error) {
    console.debug('[TimeTracker] idle notification failed:', error);
  }
}

async function sendServerHeartbeat() {
  const { server_url, api_token, logged_out, last_timer_status } = await chrome.storage.local.get([
    'server_url',
    'api_token',
    'logged_out',
    'last_timer_status',
  ]);
  if (!server_url || !api_token || logged_out) return;
  if (!last_timer_status?.active) return;
  const client = new ApiClient(server_url, api_token);
  try {
    await client.sendHeartbeat();
  } catch (error) {
    console.debug('[TimeTracker] heartbeat failed:', error);
  }
}

async function confirmStillWorking() {
  await clearIdleGraceState();
  await sendServerHeartbeat();
}

async function stopTimerForIdle({ stopAtMs = null } = {}) {
  const { server_url, api_token, logged_out, idle_grace_stop_at } = await chrome.storage.local.get([
    'server_url',
    'api_token',
    'logged_out',
    'idle_grace_stop_at',
  ]);
  await clearIdleGraceState();

  if (!server_url || !api_token || logged_out) {
    return;
  }

  const stopTime = new Date(stopAtMs || idle_grace_stop_at || Date.now()).toISOString();
  const client = new ApiClient(server_url, api_token);
  try {
    await client.stopTimer({ stopTime });
  } catch (error) {
    console.debug('[TimeTracker] idle stop failed:', error);
  }
  await refreshTimerStatus({ force: true });
}

async function refreshTimerStatus({ force = false } = {}) {
  const { server_url, api_token, logged_out } = await getCredentials();
  if (!server_url || !api_token || logged_out) {
    setIdleUi();
    await clearIdleGraceState();
    await setTimerCache({ active: false, timer: null, error: logged_out ? 'logged_out' : 'not_configured' });
    return { active: false, timer: null };
  }

  const client = new ApiClient(server_url, api_token);
  try {
    const status = await client.getTimerStatus();
    const active = Boolean(status?.active && status?.timer);
    const idleTimeoutMinutes = clampIdleTimeoutMinutes(status?.idle_timeout_minutes);
    await applyIdleDetectionInterval(idleTimeoutMinutes);

    if (active) {
      setRunningUi(status.timer);
      // Server already marked this timer idle (#722) — enter the same grace
      // window the local chrome.idle path uses, even if OS idle has not fired.
      const idleNotified = Boolean(
        status?.idle_notified || status?.timer?.idle_notified
      );
      if (idleNotified) {
        // Credit the idle window (Issue #722): stop at last_active + threshold ≈ now
        // when the server just notified, not at last_active alone (0 min).
        await beginIdleGrace(Date.now());
      }
      // Only refresh server heartbeat while the OS reports the user as active.
      // Heartbeating during idle/locked would defeat the server-side safety net.
      const { idle_grace_active } = await chrome.storage.local.get('idle_grace_active');
      if (!idle_grace_active) {
        try {
          const idleState = await new Promise((resolve) => {
            try {
              chrome.idle.queryState(MIN_IDLE_DETECTION_SECONDS, resolve);
            } catch (_) {
              resolve('active');
            }
          });
          if (idleState === 'active') {
            await client.sendHeartbeat();
          }
        } catch (hbErr) {
          console.debug('[TimeTracker] poll heartbeat failed:', hbErr);
        }
      }
    } else {
      setIdleUi();
      await clearIdleGraceState();
    }
    await setTimerCache({
      active,
      timer: status?.timer || null,
      idle_timeout_minutes: idleTimeoutMinutes,
      error: null,
      force,
    });
    return { active, timer: status?.timer || null };
  } catch (error) {
    if (error.status === 401 || error.code === 'UNAUTHORIZED') {
      await chrome.storage.local.set({ logged_out: true });
      setIdleUi();
      await clearIdleGraceState();
      await setTimerCache({ active: false, timer: null, error: 'unauthorized' });
      return { active: false, timer: null, error: 'unauthorized' };
    }
    // Keep last known UI on transient errors; still record error for popup.
    await chrome.storage.local.set({
      last_timer_status: {
        ...(await chrome.storage.local.get('last_timer_status')).last_timer_status,
        error: error.message || 'poll_failed',
      },
      last_timer_poll_at: Date.now(),
    });
    return { active: false, timer: null, error: error.message };
  }
}

async function ensureAlarm() {
  const existing = await chrome.alarms.get(ALARM_NAME);
  if (!existing) {
    chrome.alarms.create(ALARM_NAME, { periodInMinutes: POLL_MINUTES });
  }
}

chrome.runtime.onInstalled.addListener(() => {
  ensureAlarm();
  refreshTimerStatus({ force: true });
});

chrome.runtime.onStartup.addListener(() => {
  ensureAlarm();
  refreshTimerStatus({ force: true });
});

chrome.alarms.onAlarm.addListener((alarm) => {
  if (alarm.name === ALARM_NAME) {
    refreshTimerStatus();
    return;
  }
  if (alarm.name === IDLE_STOP_ALARM) {
    stopTimerForIdle();
  }
});

chrome.storage.onChanged.addListener((changes, area) => {
  if (area !== 'local') return;
  if (changes.server_url || changes.api_token || changes.logged_out) {
    refreshTimerStatus({ force: true });
  }
});

chrome.runtime.onMessage.addListener((message, _sender, sendResponse) => {
  if (message?.type === 'refresh_timer') {
    refreshTimerStatus({ force: true })
      .then((result) => sendResponse({ ok: true, ...result }))
      .catch((error) => sendResponse({ ok: false, error: error.message }));
    return true;
  }
  if (message?.type === 'ensure_alarm') {
    ensureAlarm().then(() => sendResponse({ ok: true }));
    return true;
  }
  return false;
});

/** While the popup is open, keep the service worker alive and refresh the badge every 15s.
 *  Packaged MV3 extensions clamp chrome.alarms to ≥1 minute; this port holds the SW
 *  and provides a faster badge tick for the duration of the popup session.
 */
chrome.runtime.onConnect.addListener((port) => {
  if (port.name !== 'popup-keepalive') return;
  const intervalId = setInterval(() => {
    refreshTimerStatus().catch(() => {});
  }, 15_000);
  port.onDisconnect.addListener(() => {
    clearInterval(intervalId);
  });
});

chrome.idle.onStateChanged.addListener(async (newState) => {
  if (newState === 'active') {
    // User returned before grace expired — cancel pending auto-stop and
    // tell the server so the server-side grace window also resets.
    await clearIdleGraceState();
    await sendServerHeartbeat();
    return;
  }
  if (newState !== 'idle' && newState !== 'locked') {
    return;
  }

  const { last_timer_status } = await chrome.storage.local.get([
    'last_timer_status',
  ]);
  if (!last_timer_status?.active || !last_timer_status?.timer) {
    return;
  }

  // chrome.idle already waited the detection interval; credit that window
  // so auto-stop records idle_timeout minutes of work (Issue #722), not 0.
  await beginIdleGrace(Date.now());
});

chrome.notifications.onButtonClicked.addListener(async (notificationId, buttonIndex) => {
  if (notificationId !== IDLE_NOTIFICATION_ID) return;
  if (buttonIndex === 0) {
    await confirmStillWorking();
  } else if (buttonIndex === 1) {
    // "No" stops immediately (like web stopNow), not backdated to last activity.
    await stopTimerForIdle({ stopAtMs: Date.now() });
  }
});

chrome.notifications.onClicked.addListener(async (notificationId) => {
  if (notificationId !== IDLE_NOTIFICATION_ID) return;
  // Clicking the notification body counts as "still working".
  await confirmStillWorking();
});

ensureAlarm();
refreshTimerStatus({ force: true });
