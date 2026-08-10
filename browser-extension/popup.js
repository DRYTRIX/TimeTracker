/**
 * Popup: running timer view, project/task picker, quick-create.
 */

import {
  ApiClient,
  elapsedSecondsFromTimer,
  formatElapsedHhMm,
} from './lib/api.js';

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
  projectFilter: document.getElementById('project-filter'),
  projectSelect: document.getElementById('project-select'),
  taskSelect: document.getElementById('task-select'),
  notes: document.getElementById('notes'),
  startBtn: document.getElementById('start-btn'),
  tabTask: document.getElementById('tab-task'),
  tabProject: document.getElementById('tab-project'),
  createTask: document.getElementById('create-task'),
  createProject: document.getElementById('create-project'),
  newTaskName: document.getElementById('new-task-name'),
  newTaskProject: document.getElementById('new-task-project'),
  createTaskBtn: document.getElementById('create-task-btn'),
  newProjectName: document.getElementById('new-project-name'),
  newProjectClient: document.getElementById('new-project-client'),
  createProjectBtn: document.getElementById('create-project-btn'),
};

/** Closed statuses — matches Task.is_active (anything else is selectable). */
const CLOSED_TASK_STATUSES = new Set(['done', 'cancelled']);

/** @type {ApiClient|null} */
let client = null;
/** @type {Array<{id:number,name:string,favorite?:boolean}>} */
let projects = [];
/** @type {object|null} */
let activeTimer = null;
let tickHandle = null;
/** Keep service worker alive while the popup is open (MV3). */
let keepAlivePort = null;

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

function setCreateTab(which) {
  const isTask = which === 'task';
  els.tabTask.classList.toggle('active', isTask);
  els.tabProject.classList.toggle('active', !isTask);
  els.createTask.classList.toggle('hidden', !isTask);
  els.createProject.classList.toggle('hidden', isTask);
}

els.tabTask.addEventListener('click', () => setCreateTab('task'));
els.tabProject.addEventListener('click', () => setCreateTab('project'));

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
  els.runningProject.textContent = timer.project || `Project #${timer.project_id}`;
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

function filteredProjects() {
  const q = els.projectFilter.value.trim().toLowerCase();
  if (!q) return projects;
  return projects.filter((p) => p.name.toLowerCase().includes(q));
}

function fillProjectSelects(selectedId = null) {
  const list = filteredProjects();
  const current =
    selectedId != null
      ? String(selectedId)
      : els.projectSelect.value || (list[0] ? String(list[0].id) : '');

  els.projectSelect.innerHTML = '';
  els.newTaskProject.innerHTML = '';

  if (!list.length) {
    const opt = document.createElement('option');
    opt.value = '';
    opt.textContent = 'No projects found';
    els.projectSelect.appendChild(opt);
  } else {
    for (const p of list) {
      const opt = document.createElement('option');
      opt.value = String(p.id);
      opt.textContent = p.favorite ? `★ ${p.name}` : p.name;
      if (String(p.id) === current) opt.selected = true;
      els.projectSelect.appendChild(opt);
    }
  }

  for (const p of projects) {
    const opt = document.createElement('option');
    opt.value = String(p.id);
    opt.textContent = p.name;
    els.newTaskProject.appendChild(opt);
  }

  if (els.newTaskProject.options.length && current) {
    els.newTaskProject.value = current;
  }
}

async function loadTasksForProject(projectId, selectedTaskId = null) {
  els.taskSelect.innerHTML = '<option value="">— No task —</option>';
  if (!client || !projectId) return;
  try {
    const data = await client.getTasks({
      project_id: projectId,
      status: 'open',
      per_page: 200,
    });
    const tasks = (data?.tasks || [])
      .filter((t) => t.status && !CLOSED_TASK_STATUSES.has(t.status))
      .sort((a, b) => a.name.localeCompare(b.name));
    const selectedId = selectedTaskId != null ? String(selectedTaskId) : '';
    for (const t of tasks) {
      const opt = document.createElement('option');
      opt.value = String(t.id);
      opt.textContent = t.status && t.status !== 'todo' ? `${t.name} (${t.status})` : t.name;
      if (selectedId && String(t.id) === selectedId) opt.selected = true;
      els.taskSelect.appendChild(opt);
    }
  } catch (error) {
    // Non-fatal: timer can start without a task list, but surface the failure.
    console.warn('Failed to load tasks', error);
    const opt = document.createElement('option');
    opt.value = '';
    opt.textContent = 'Could not load tasks';
    els.taskSelect.appendChild(opt);
    showMessage(error.message || 'Could not load tasks.');
  }
}

async function loadProjects() {
  if (!client) return;
  const [projectsResp, favResp] = await Promise.all([
    client.getAllProjects({ status: 'active', per_page: 100 }),
    client.getFavoriteProjects().catch(() => ({ favorites: [] })),
  ]);

  const favIds = new Set((favResp?.favorites || []).map((f) => f.project_id));
  const raw = projectsResp?.projects || [];
  projects = raw
    .map((p) => ({ id: p.id, name: p.name, favorite: favIds.has(p.id) }))
    .sort((a, b) => {
      if (a.favorite !== b.favorite) return a.favorite ? -1 : 1;
      return a.name.localeCompare(b.name);
    });

  fillProjectSelects();
  const selected = Number(els.projectSelect.value);
  if (selected) await loadTasksForProject(selected);
}

async function loadClients() {
  if (!client) return;
  els.newProjectClient.innerHTML = '';
  try {
    const data = await client.getClients({ per_page: 100 });
    const clients = data?.clients || [];
    const none = document.createElement('option');
    none.value = '';
    none.textContent = clients.length ? '— No client —' : 'No clients (optional)';
    els.newProjectClient.appendChild(none);
    for (const c of clients) {
      const opt = document.createElement('option');
      opt.value = String(c.id);
      opt.textContent = c.name;
      els.newProjectClient.appendChild(opt);
    }
  } catch (error) {
    const opt = document.createElement('option');
    opt.value = '';
    opt.textContent = '— No client —';
    els.newProjectClient.appendChild(opt);
    console.warn(error);
  }
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

els.projectFilter.addEventListener('input', () => {
  fillProjectSelects(els.projectSelect.value || null);
  const id = Number(els.projectSelect.value);
  loadTasksForProject(id || null);
});

els.projectSelect.addEventListener('change', () => {
  const id = Number(els.projectSelect.value);
  loadTasksForProject(id);
  if (id) els.newTaskProject.value = String(id);
});

els.startBtn.addEventListener('click', async () => {
  clearMessage();
  const projectId = Number(els.projectSelect.value);
  if (!projectId) {
    showMessage('Select a project first.');
    return;
  }
  const taskId = els.taskSelect.value ? Number(els.taskSelect.value) : null;
  const notes = els.notes.value.trim();
  els.startBtn.disabled = true;
  try {
    const result = await client.startTimer({ projectId, taskId, notes });
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
      // Prefer timer from error payload when present; otherwise refetch status.
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
    await Promise.all([loadProjects(), loadClients()]);
    await notifyBackground();
  } catch (error) {
    showMessage(error.message || 'Could not stop timer.');
  } finally {
    els.stopBtn.disabled = false;
  }
});

els.createTaskBtn.addEventListener('click', async () => {
  clearMessage();
  const name = els.newTaskName.value.trim();
  const projectId = Number(els.newTaskProject.value);
  if (!name || !projectId) {
    showMessage('Task name and project are required.');
    return;
  }
  els.createTaskBtn.disabled = true;
  try {
    const result = await client.createTask({ name, projectId });
    els.newTaskName.value = '';
    showMessage('Task created.', 'success');
    fillProjectSelects(projectId);
    await loadTasksForProject(projectId, result?.task?.id);
  } catch (error) {
    showMessage(error.message || 'Could not create task.');
  } finally {
    els.createTaskBtn.disabled = false;
  }
});

els.createProjectBtn.addEventListener('click', async () => {
  clearMessage();
  const name = els.newProjectName.value.trim();
  const clientId = els.newProjectClient.value ? Number(els.newProjectClient.value) : null;
  if (!name) {
    showMessage('Project name is required.');
    return;
  }
  els.createProjectBtn.disabled = true;
  try {
    const result = await client.createProject({ name, clientId });
    els.newProjectName.value = '';
    showMessage('Project created.', 'success');
    await loadProjects();
    if (result?.project?.id) {
      fillProjectSelects(result.project.id);
      await loadTasksForProject(result.project.id);
    }
  } catch (error) {
    showMessage(error.message || 'Could not create project.');
  } finally {
    els.createProjectBtn.disabled = false;
  }
});

async function bootstrap() {
  clearMessage();
  connectKeepAlive();

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
      await Promise.all([loadProjects(), loadClients()]);
    }
    await notifyBackground();
  } catch (error) {
    if (error.status === 401 || error.code === 'UNAUTHORIZED') {
      await chrome.storage.local.set({ logged_out: true });
      showSetup();
      showMessage('Session expired. Sign in again in Settings.');
      return;
    }
    // Fall back to cached status if poll fails
    if (last_timer_status?.active && last_timer_status?.timer) {
      showRunning(last_timer_status.timer);
      showMessage(error.message || 'Could not refresh timer; showing last known state.');
    } else {
      showIdle();
      showMessage(error.message || 'Could not reach TimeTracker.');
      try {
        await Promise.all([loadProjects(), loadClients()]);
      } catch {
        /* ignore */
      }
    }
  }
}

bootstrap();
