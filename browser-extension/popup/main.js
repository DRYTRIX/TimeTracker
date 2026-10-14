/**
 * Popup controller: bootstrap, tab switching, data loading and shared state.
 * Tabs are small modules that receive a `ctx` with everything they need.
 */

import { ApiClient, elapsedSecondsFromTimer } from '../lib/api.js';
import {
  addDays,
  entryDurationSeconds,
  localDateKey,
} from '../lib/format.js';
import { icons } from '../lib/icons.js';
import { initTimerTab } from './timer-tab.js';
import { initInsightsTab } from './insights-tab.js';
import { initRecentsTab } from './recents-tab.js';

const el = (id) => document.getElementById(id);

const els = {
  conn: el('conn'),
  connText: el('conn-text'),
  settings: el('btn-settings'),
  glyph: el('glyph'),
  setupGlyph: el('setup-glyph'),
  setup: el('setup'),
  setupText: el('setup-text'),
  main: el('main'),
  message: el('message'),
  tabs: {
    timer: el('tab-timer'),
    insights: el('tab-insights'),
    recents: el('tab-recents'),
  },
  panels: {
    timer: el('panel-timer'),
    insights: el('panel-insights'),
    recents: el('panel-recents'),
  },
};

els.glyph.innerHTML = icons.timer;
els.setupGlyph.innerHTML = icons.timer;
els.settings.innerHTML = icons.settings;
els.settings.addEventListener('click', () => chrome.runtime.openOptionsPage());
el('btn-open-settings').addEventListener('click', () => chrome.runtime.openOptionsPage());
el('search-icon').innerHTML = icons.search;

/** Shared mutable state handed to the tab modules. */
const state = {
  serverUrl: null,
  timer: null,
  projects: [],
  recentEntries: [],
  weeklyGoal: null,
  weekByProject: [],
  weekEntries: [],
  todaySeconds: 0,
  billableSecondsToday: 0,
  todayEntries: 0,
  selected: { projectId: null, taskId: null },
};

let client = null;
let keepAlivePort = null;
let timerApi = null;
let insightsApi = null;
let recentsApi = null;

// ── messaging + UI helpers ───────────────────────────────

let messageTimer = null;
function showMessage(text, kind = 'error') {
  els.message.textContent = text;
  els.message.className = `toast ${kind}`;
  els.message.classList.remove('hidden');
  clearTimeout(messageTimer);
  messageTimer = setTimeout(() => {
    els.message.classList.add('hidden');
  }, 3000);
}

function clearMessage() {
  clearTimeout(messageTimer);
  els.message.classList.add('hidden');
}

function notifyBackground() {
  try {
    chrome.runtime.sendMessage({ type: 'refresh_timer' }).catch(() => {});
  } catch {
    /* extension context gone */
  }
}

function setConn({ offline = false } = {}) {
  els.conn.hidden = false;
  els.conn.classList.toggle('is-offline', offline);
  els.connText.textContent = offline ? 'Offline' : 'Connected';
}

function activeElapsedSeconds() {
  return state.timer ? elapsedSecondsFromTimer(state.timer) : 0;
}

function switchTab(name) {
  for (const key of Object.keys(els.tabs)) {
    const active = key === name;
    els.tabs[key].classList.toggle('is-active', active);
    els.tabs[key].setAttribute('aria-selected', String(active));
    els.panels[key].hidden = !active;
  }
}

for (const [name, button] of Object.entries(els.tabs)) {
  button.addEventListener('click', () => switchTab(name));
}

// '/' focuses search from anywhere (when not typing)
document.addEventListener('keydown', (event) => {
  if (event.key !== '/' || event.defaultPrevented) return;
  const target = event.target;
  if (target instanceof HTMLElement && target.matches('input, textarea, select')) return;
  if (els.panels.timer.hidden || state.timer) return;
  event.preventDefault();
  el('search-input').focus();
});

// ── data loading ─────────────────────────────────────────

function sortProjects(a, b) {
  if (a.favorite !== b.favorite) return a.favorite ? -1 : 1;
  const aUsed = a.last_used_at ? Date.parse(a.last_used_at) : 0;
  const bUsed = b.last_used_at ? Date.parse(b.last_used_at) : 0;
  if (aUsed !== bUsed) return bUsed - aUsed;
  return String(a.name).localeCompare(String(b.name));
}

async function loadDirectory() {
  try {
    const [projectsResp, favResp, clientsResp] = await Promise.all([
      client.getAllProjects({ status: 'active', per_page: 100 }),
      client.getFavoriteProjects().catch(() => ({ favorites: [] })),
      client.getClients({ per_page: 100 }).catch(() => ({ clients: [] })),
    ]);
    const favIds = new Set((favResp?.favorites || []).map((f) => f.project_id));
    const clientNames = new Map((clientsResp?.clients || []).map((c) => [c.id, c.name]));
    const raw = projectsResp?.projects || [];
    state.projects = raw
      .map((p) => ({
        id: p.id,
        name: p.name,
        client_id: p.client_id ?? null,
        clientName: clientNames.get(p.client_id) || null,
        favorite: favIds.has(p.id),
        last_used_at: p.last_used_at ?? null,
      }))
      .sort(sortProjects);

    if (!state.selected.projectId) {
      const { last_project } = await chrome.storage.local.get('last_project');
      const last = state.projects.find((p) => p.id === last_project?.project_id);
      if (last) state.selected.projectId = last.id;
    }
    timerApi?.renderIdle();
  } catch (error) {
    console.warn('Failed to load projects', error);
  }
}

async function loadWeekData() {
  const now = new Date();
  const today = localDateKey(now);
  const weekAgo = localDateKey(addDays(now, -6));

  try {
    const [todaySum, weekSum, weekEntriesResp, goalsResp] = await Promise.all([
      client.getSummary({ startDate: today, endDate: today }).catch(() => null),
      client.getSummary({ startDate: weekAgo, endDate: today }).catch(() => null),
      client
        .getTimeEntries({ startDate: weekAgo, endDate: today, perPage: 200, includeActive: true })
        .catch(() => ({ time_entries: [] })),
      client.getWeeklyGoals().catch(() => ({ weekly_goals: [] })),
    ]);

    const summary = todaySum?.summary;
    state.todaySeconds = Math.round((Number(summary?.total_hours) || 0) * 3600);
    state.billableSecondsToday = Math.round((Number(summary?.billable_hours) || 0) * 3600);
    state.todayEntries = Number(summary?.total_entries) || 0;
    state.weekByProject = weekSum?.summary?.by_project || [];

    const entries = weekEntriesResp?.time_entries || [];
    state.weekEntries = entries;
    state.recentEntries = entries;

    const goals = goalsResp?.weekly_goals || [];
    state.weeklyGoal =
      goals.find((g) => {
        const start = localDateKey(new Date(g.week_start_date || ''));
        const end = localDateKey(new Date(g.week_end_date || ''));
        return start <= today && today <= end;
      }) || goals[0] || null;

    insightsApi?.renderAll();
    recentsApi?.render();
    timerApi?.renderNoteSuggestions();
  } catch (error) {
    console.warn('Failed to load insights', error);
    insightsApi?.renderAll();
    recentsApi?.render();
  }
}

// ── timer status sync ────────────────────────────────────

function applyStatus(status) {
  const active = Boolean(status?.active && status?.timer);
  state.timer = active ? status.timer : null;
  timerApi?.render();
}

chrome.storage.onChanged.addListener((changes, area) => {
  if (area !== 'local') return;
  if (changes.last_timer_status) {
    const value = changes.last_timer_status.newValue;
    if (value && !value.error) setConn({});
    else if (value?.error && value.error !== 'not_configured') setConn({ offline: true });
    if (value && 'active' in value) applyStatus(value);
  }
});

function connectKeepAlive() {
  try {
    keepAlivePort = chrome.runtime.connect({ name: 'popup-keepalive' });
  } catch {
    keepAlivePort = null;
  }
}

// ── bootstrap ────────────────────────────────────────────

function showSetup(message = null) {
  els.main.classList.add('hidden');
  els.setup.classList.remove('hidden');
  els.conn.hidden = true;
  if (message) els.setupText.textContent = message;
}

async function bootstrap() {
  const cfg = await chrome.storage.local.get([
    'server_url',
    'api_token',
    'logged_out',
    'last_timer_status',
  ]);

  if (!cfg.server_url || !cfg.api_token || cfg.logged_out) {
    const expired = Boolean(cfg.server_url && cfg.logged_out);
    showSetup(
      expired
        ? 'Session expired. Sign in again in Settings.'
        : 'Sign in to your TimeTracker server to start and stop timers from the toolbar.'
    );
    return;
  }

  state.serverUrl = cfg.server_url;
  client = new ApiClient(cfg.server_url, cfg.api_token);

  timerApi = initTimerTab(ctx);
  insightsApi = initInsightsTab(ctx);
  recentsApi = initRecentsTab(ctx);

  try {
    const status = await client.getTimerStatus();
    setConn({});
    applyStatus(status);
  } catch (error) {
    if (error.status === 401 || error.code === 'UNAUTHORIZED') {
      await chrome.storage.local.set({ logged_out: true });
      showSetup('Session expired. Sign in again in Settings.');
      return;
    }
    setConn({ offline: true });
    const cached = cfg.last_timer_status;
    if (cached?.active && cached?.timer) {
      state.timer = cached.timer;
      showMessage(error.message || 'Could not refresh timer; showing last known state.');
    } else {
      showMessage(error.message || 'Could not reach TimeTracker.');
    }
  }

  els.main.classList.remove('hidden');
  els.setup.classList.add('hidden');
  timerApi.render();
  connectKeepAlive();
  await Promise.all([loadDirectory(), loadWeekData()]);
}

const ctx = {
  get client() {
    return client;
  },
  state,
  showMessage,
  clearMessage,
  notifyBackground,
  setConn,
  switchTab,
  activeElapsedSeconds,
  loadDirectory,
  loadWeekData,
  refreshInsights: () => void loadWeekData(),
  refreshRecents: () => void loadWeekData(),
  refreshAll: () => {
    void loadDirectory();
    void loadWeekData();
  },
  startTracking: (args) => timerApi?.startTracking(args),
  /** Recents "track again" needs entry duration helpers too. */
  entryDurationFor: (entry) => entryDurationSeconds(entry),
};

void bootstrap();
