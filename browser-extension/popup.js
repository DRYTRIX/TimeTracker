/**
 * Popup: running timer view + cascading client → project → task pickers
 * with inline create (Issue #728 follow-up).
 */

import {
  ApiClient,
  elapsedSecondsFromTimer,
  formatElapsedHhMm,
} from './lib/api.js';
import { enhanceSelect } from './lib/picker.js';

const els = {
  message: document.getElementById('message'),
  needSetup: document.getElementById('need-setup'),
  goSettings: document.getElementById('go-settings'),
  openOptions: document.getElementById('open-options'),
  runningView: document.getElementById('running-view'),
  idleView: document.getElementById('idle-view'),
  elapsed: document.getElementById('elapsed'),
  pausedBadge: document.getElementById('paused-badge'),
  runningProject: document.getElementById('running-project'),
  runningTaskWrap: document.getElementById('running-task-wrap'),
  runningTask: document.getElementById('running-task'),
  pauseBtn: document.getElementById('pause-btn'),
  resumeBtn: document.getElementById('resume-btn'),
  stopBtn: document.getElementById('stop-btn'),
  clientSelect: document.getElementById('client-select'),
  projectSelect: document.getElementById('project-select'),
  taskSelect: document.getElementById('task-select'),
  notes: document.getElementById('notes'),
  startBtn: document.getElementById('start-btn'),
};

/** Closed statuses — matches Task.is_active (anything else is selectable). */
const CLOSED_TASK_STATUSES = new Set(['done', 'cancelled']);

/** @type {ApiClient|null} */
let client = null;
/** @type {Array<{id:number,name:string,client_id?:number|null,favorite?:boolean,last_used_at?:string|null}>} */
let projects = [];
/** @type {Array<{id:number,name:string}>} */
let clients = [];
/** @type {object|null} */
let activeTimer = null;
let tickHandle = null;
/** Keep service worker alive while the popup is open (MV3). */
let keepAlivePort = null;
/** Monotonic counter so concurrent loadTasksForProject calls don't duplicate options (#700). */
let loadTasksGeneration = 0;

let clientPicker = null;
let projectPicker = null;
let taskPicker = null;

function showMessage(text, kind = 'error') {
  els.message.textContent = text;
  els.message.className = kind === 'success' ? 'success' : 'error';
  els.message.classList.remove('hidden');
}

function clearMessage() {
  els.message.classList.add('hidden');
  els.message.textContent = '';
}

function openSettings() {
  chrome.runtime.openOptionsPage();
}

els.goSettings.addEventListener('click', openSettings);
els.openOptions.addEventListener('click', (event) => {
  event.preventDefault();
  openSettings();
});

function stopTick() {
  if (tickHandle) {
    clearInterval(tickHandle);
    tickHandle = null;
  }
}

function renderElapsed() {
  if (!activeTimer) return;
  els.elapsed.textContent = formatElapsedHhMm(elapsedSecondsFromTimer(activeTimer));
}

function updatePauseResumeUi(timer) {
  const paused = Boolean(timer?.paused_at);
  els.pausedBadge.classList.toggle('hidden', !paused);
  els.pauseBtn.classList.toggle('hidden', paused);
  els.resumeBtn.classList.toggle('hidden', !paused);
  els.elapsed.classList.toggle('is-paused', paused);
}

function showRunning(timer) {
  activeTimer = timer;
  els.needSetup.classList.add('hidden');
  els.idleView.classList.add('hidden');
  els.runningView.classList.remove('hidden');
  els.runningProject.textContent =
    timer.project ||
    timer.client ||
    (timer.project_id ? `Project #${timer.project_id}` : null) ||
    (timer.client_id ? `Client #${timer.client_id}` : 'Timer');
  if (timer.task) {
    els.runningTask.textContent = timer.task;
    els.runningTaskWrap.classList.remove('hidden');
  } else {
    els.runningTaskWrap.classList.add('hidden');
  }
  updatePauseResumeUi(timer);
  renderElapsed();
  stopTick();
  if (!timer.paused_at) {
    tickHandle = setInterval(renderElapsed, 1000);
  }
}

function showIdle() {
  activeTimer = null;
  stopTick();
  els.needSetup.classList.add('hidden');
  els.runningView.classList.add('hidden');
  els.idleView.classList.remove('hidden');
}

function showSetup() {
  activeTimer = null;
  stopTick();
  els.runningView.classList.add('hidden');
  els.idleView.classList.add('hidden');
  els.needSetup.classList.remove('hidden');
}

function fillClientSelect(selectedId = null) {
  const current =
    selectedId != null
      ? String(selectedId)
      : els.clientSelect.value || '';
  els.clientSelect.innerHTML = '';
  const none = document.createElement('option');
  none.value = '';
  none.textContent = '— All clients —';
  els.clientSelect.appendChild(none);
  for (const c of clients) {
    const opt = document.createElement('option');
    opt.value = String(c.id);
    opt.textContent = c.name;
    if (String(c.id) === current) opt.selected = true;
    els.clientSelect.appendChild(opt);
  }
  if (clientPicker) clientPicker.refresh();
}

function fillProjectSelect(selectedId = null) {
  const clientId = els.clientSelect.value ? Number(els.clientSelect.value) : null;
  let list = projects;
  if (clientId) {
    list = projects.filter((p) => !p.client_id || Number(p.client_id) === clientId);
  }
  const current =
    selectedId != null
      ? String(selectedId)
      : els.projectSelect.value || '';

  els.projectSelect.innerHTML = '';
  if (!list.length) {
    const opt = document.createElement('option');
    opt.value = '';
    opt.textContent = clientId ? 'No projects for this client' : 'No projects found';
    els.projectSelect.appendChild(opt);
  } else {
    const empty = document.createElement('option');
    empty.value = '';
    empty.textContent = '— Select a project —';
    els.projectSelect.appendChild(empty);
    for (const p of list) {
      const opt = document.createElement('option');
      opt.value = String(p.id);
      opt.textContent = p.favorite ? `★ ${p.name}` : p.name;
      if (p.client_id) {
        opt.setAttribute('data-client-id', String(p.client_id));
        opt.setAttribute('data-parent-id', String(p.client_id));
      }
      if (String(p.id) === current) opt.selected = true;
      els.projectSelect.appendChild(opt);
    }
  }
  if (projectPicker) projectPicker.refresh();
}

async function loadTasksForProject(projectId, selectedTaskId = null) {
  const gen = ++loadTasksGeneration;
  if (!client || !projectId) {
    els.taskSelect.innerHTML = '<option value="">— No task —</option>';
    if (taskPicker) taskPicker.refresh();
    return;
  }
  try {
    const data = await client.getTasks({
      project_id: projectId,
      status: 'open',
      per_page: 200,
    });
    if (gen !== loadTasksGeneration) return;
    const byId = new Map();
    for (const t of data?.tasks || []) {
      if (!t || t.id == null) continue;
      if (!t.status || CLOSED_TASK_STATUSES.has(t.status)) continue;
      if (!byId.has(t.id)) byId.set(t.id, t);
    }
    const tasks = Array.from(byId.values()).sort((a, b) => a.name.localeCompare(b.name));
    const selectedId = selectedTaskId != null ? String(selectedTaskId) : '';
    els.taskSelect.innerHTML = '<option value="">— No task —</option>';
    for (const t of tasks) {
      const opt = document.createElement('option');
      opt.value = String(t.id);
      opt.textContent = t.status && t.status !== 'todo' ? `${t.name} (${t.status})` : t.name;
      opt.setAttribute('data-parent-id', String(projectId));
      if (selectedId && String(t.id) === selectedId) opt.selected = true;
      els.taskSelect.appendChild(opt);
    }
    if (taskPicker) taskPicker.refresh();
  } catch (error) {
    if (gen !== loadTasksGeneration) return;
    console.warn('Failed to load tasks', error);
    els.taskSelect.innerHTML = '<option value="">— No task —</option>';
    const opt = document.createElement('option');
    opt.value = '';
    opt.textContent = 'Could not load tasks';
    els.taskSelect.appendChild(opt);
    if (taskPicker) taskPicker.refresh();
    showMessage(error.message || 'Could not load tasks.');
  }
}

async function loadProjects(preferredProjectId = null) {
  if (!client) return;
  const clientId = els.clientSelect.value ? Number(els.clientSelect.value) : null;
  const params = { status: 'active', per_page: 100 };
  // Always load all projects so switching client filter is instant; filter client-side.
  // (API also supports client_id — used as a hint when creating.)
  const [projectsResp, favResp] = await Promise.all([
    client.getAllProjects(params),
    client.getFavoriteProjects().catch(() => ({ favorites: [] })),
  ]);

  const favIds = new Set((favResp?.favorites || []).map((f) => f.project_id));
  const raw = projectsResp?.projects || [];
  projects = raw
    .map((p) => ({
      id: p.id,
      name: p.name,
      client_id: p.client_id ?? null,
      favorite: favIds.has(p.id),
      last_used_at: p.last_used_at ?? null,
    }))
    .sort((a, b) => {
      if (a.favorite !== b.favorite) return a.favorite ? -1 : 1;
      const aUsed = a.last_used_at ? Date.parse(a.last_used_at) : 0;
      const bUsed = b.last_used_at ? Date.parse(b.last_used_at) : 0;
      if (aUsed !== bUsed) return bUsed - aUsed;
      return a.name.localeCompare(b.name);
    });

  fillProjectSelect(preferredProjectId);
  const selected = Number(els.projectSelect.value);
  if (selected) await loadTasksForProject(selected);
  else await loadTasksForProject(null);
  void clientId;
}

async function loadClients(preferredClientId = null) {
  if (!client) return;
  try {
    const data = await client.getClients({ per_page: 100 });
    clients = (data?.clients || []).map((c) => ({ id: c.id, name: c.name }));
  } catch (error) {
    clients = [];
    console.warn(error);
  }
  fillClientSelect(preferredClientId);
}

async function notifyBackground() {
  try {
    await chrome.runtime.sendMessage({ type: 'refresh_timer' });
  } catch {
    /* ignore */
  }
}

function connectKeepAlive() {
  try {
    keepAlivePort = chrome.runtime.connect({ name: 'popup-keepalive' });
  } catch {
    keepAlivePort = null;
  }
}

/** When start conflicts with an existing timer, sync to that running timer. */
async function syncToActiveTimerOnConflict() {
  try {
    const status = await client.getTimerStatus();
    if (status?.active && status?.timer) {
      showRunning(status.timer);
      await notifyBackground();
      showMessage('A timer is already running.', 'success');
      return true;
    }
  } catch {
    /* fall through */
  }
  return false;
}

async function createClientInline(name) {
  clearMessage();
  try {
    const result = await client.createClient({ name });
    const created = result?.client || result;
    showMessage('Client created.', 'success');
    await loadClients(created?.id);
    fillProjectSelect(els.projectSelect.value || null);
  } catch (error) {
    showMessage(error.message || 'Could not create client.');
  }
}

async function createProjectInline(name) {
  clearMessage();
  const clientId = els.clientSelect.value ? Number(els.clientSelect.value) : null;
  if (!clientId) {
    showMessage('Select a client before creating a project.');
    return;
  }
  try {
    const result = await client.createProject({ name, clientId });
    const created = result?.project || result;
    showMessage('Project created.', 'success');
    if (created?.client_id && !els.clientSelect.value) {
      await loadClients(created.client_id);
    }
    await loadProjects(created?.id);
    if (created?.id) await loadTasksForProject(created.id);
  } catch (error) {
    showMessage(error.message || 'Could not create project.');
  }
}

async function createTaskInline(name) {
  clearMessage();
  const projectId = Number(els.projectSelect.value);
  if (!projectId) {
    showMessage('Select a project before creating a task.');
    return;
  }
  try {
    const result = await client.createTask({ name, projectId });
    const taskId = result?.task?.id || result?.id;
    showMessage('Task created.', 'success');
    await loadTasksForProject(projectId, taskId);
  } catch (error) {
    showMessage(error.message || 'Could not create task.');
  }
}

function initPickers() {
  clientPicker = enhanceSelect(els.clientSelect, {
    kind: 'client',
    canCreate: true,
    placeholder: 'Type to search clients…',
    onCreate: createClientInline,
  });
  projectPicker = enhanceSelect(els.projectSelect, {
    kind: 'project',
    canCreate: true,
    placeholder: 'Type to search projects…',
    onCreate: createProjectInline,
    canCreateGuard: () => !!els.clientSelect.value,
    canCreateGuardHint: 'Select a client first',
  });
  taskPicker = enhanceSelect(els.taskSelect, {
    kind: 'task',
    canCreate: true,
    placeholder: 'Type to search tasks…',
    onCreate: createTaskInline,
  });
}

els.clientSelect.addEventListener('change', () => {
  fillProjectSelect(null);
  const id = Number(els.projectSelect.value);
  loadTasksForProject(id || null);
});

els.projectSelect.addEventListener('change', () => {
  const id = Number(els.projectSelect.value);
  if (id) {
    const opt = els.projectSelect.options[els.projectSelect.selectedIndex];
    const cid = opt?.getAttribute('data-client-id') || '';
    if (cid && els.clientSelect.value !== cid) {
      els.clientSelect.value = cid;
      if (clientPicker) clientPicker.refresh();
      // Re-filter project list but keep selection
      fillProjectSelect(id);
    }
  }
  loadTasksForProject(id || null);
});

els.startBtn.addEventListener('click', async () => {
  clearMessage();
  const projectId = els.projectSelect.value ? Number(els.projectSelect.value) : null;
  const clientId = els.clientSelect.value ? Number(els.clientSelect.value) : null;
  if (!projectId && !clientId) {
    showMessage('Select a client or project first.');
    return;
  }
  const taskId = projectId && els.taskSelect.value ? Number(els.taskSelect.value) : null;
  const notes = els.notes.value.trim();
  els.startBtn.disabled = true;
  try {
    const result = await client.startTimer({ projectId, clientId, taskId, notes });
    const timer = result?.timer;
    if (timer) showRunning(timer);
    else await bootstrap();
    await notifyBackground();
  } catch (error) {
    const isConflict =
      error.status === 409 ||
      error.code === 'CONFLICT' ||
      error.code === 'timer_already_running';
    if (isConflict) {
      if (error.data?.timer) {
        showRunning(error.data.timer);
        await notifyBackground();
        showMessage('A timer is already running.', 'success');
      } else if (!(await syncToActiveTimerOnConflict())) {
        showMessage(error.message || 'A timer is already running.');
      }
    } else {
      showMessage(error.message || 'Could not start timer.');
    }
  } finally {
    els.startBtn.disabled = false;
  }
});

els.pauseBtn.addEventListener('click', async () => {
  clearMessage();
  els.pauseBtn.disabled = true;
  try {
    const result = await client.pauseTimer();
    const timer = result?.time_entry || result?.timer;
    if (timer) showRunning(timer);
    else await bootstrap();
    await notifyBackground();
  } catch (error) {
    showMessage(error.message || 'Could not pause timer.');
  } finally {
    els.pauseBtn.disabled = false;
  }
});

els.resumeBtn.addEventListener('click', async () => {
  clearMessage();
  els.resumeBtn.disabled = true;
  try {
    const result = await client.resumeTimer();
    const timer = result?.time_entry || result?.timer;
    if (timer) showRunning(timer);
    else await bootstrap();
    await notifyBackground();
  } catch (error) {
    showMessage(error.message || 'Could not resume timer.');
  } finally {
    els.resumeBtn.disabled = false;
  }
});

els.stopBtn.addEventListener('click', async () => {
  clearMessage();
  els.stopBtn.disabled = true;
  try {
    await client.stopTimer();
    showIdle();
    await Promise.all([loadClients(), loadProjects()]);
    await notifyBackground();
  } catch (error) {
    showMessage(error.message || 'Could not stop timer.');
  } finally {
    els.stopBtn.disabled = false;
  }
});

async function bootstrap() {
  clearMessage();
  connectKeepAlive();
  initPickers();

  const { server_url, api_token, logged_out, last_timer_status } = await chrome.storage.local.get([
    'server_url',
    'api_token',
    'logged_out',
    'last_timer_status',
  ]);

  if (!server_url || !api_token || logged_out) {
    client = null;
    showSetup();
    return;
  }

  client = new ApiClient(server_url, api_token);

  try {
    const status = await client.getTimerStatus();
    if (status?.active && status?.timer) {
      showRunning(status.timer);
    } else {
      showIdle();
      await loadClients();
      await loadProjects();
    }
    await notifyBackground();
  } catch (error) {
    if (error.status === 401 || error.code === 'UNAUTHORIZED') {
      await chrome.storage.local.set({ logged_out: true });
      showSetup();
      showMessage('Session expired. Sign in again in Settings.');
      return;
    }
    if (last_timer_status?.active && last_timer_status?.timer) {
      showRunning(last_timer_status.timer);
      showMessage(error.message || 'Could not refresh timer; showing last known state.');
    } else {
      showIdle();
      showMessage(error.message || 'Could not reach TimeTracker.');
      try {
        await loadClients();
        await loadProjects();
      } catch {
        /* ignore */
      }
    }
  }
}

bootstrap();
