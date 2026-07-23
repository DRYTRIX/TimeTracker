/**
 * Service worker: poll timer status, update toolbar badge and icon.
 */

import {
  ApiClient,
  elapsedSecondsFromTimer,
  formatBadgeText,
} from './lib/api.js';

const ALARM_NAME = 'tt-timer-poll';
const POLL_MINUTES = 0.25; // ~15s

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

async function refreshTimerStatus({ force = false } = {}) {
  const { server_url, api_token, logged_out } = await getCredentials();
  if (!server_url || !api_token || logged_out) {
    setIdleUi();
    await setTimerCache({ active: false, timer: null, error: logged_out ? 'logged_out' : 'not_configured' });
    return { active: false, timer: null };
  }

  const client = new ApiClient(server_url, api_token);
  try {
    const status = await client.getTimerStatus();
    const active = Boolean(status?.active && status?.timer);
    if (active) {
      setRunningUi(status.timer);
    } else {
      setIdleUi();
    }
    await setTimerCache({
      active,
      timer: status?.timer || null,
      error: null,
      force,
    });
    return { active, timer: status?.timer || null };
  } catch (error) {
    if (error.status === 401 || error.code === 'UNAUTHORIZED') {
      await chrome.storage.local.set({ logged_out: true });
      setIdleUi();
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

ensureAlarm();
refreshTimerStatus({ force: true });
