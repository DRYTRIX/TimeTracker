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
  runningProject: document.getElementById('running-project'),
  runningTaskWrap: document.getElementById('running-task-wrap'),
  runningTask: document.getElementById('running-task'),
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

/** @type {ApiClient|null} */
let client = null;
/** @type {Array<{id:number,name:string,favorite?:boolean}>} */
let projects = [];
/** @type {object|null} */
let activeTimer = null;
let tickHandle = null;

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

async function loadTasksForProject(projectId) {
  els.taskSelect.innerHTML = '<option value="">— No task —</option>';
  if (!client || !projectId) return;
  try {
    const data = await client.getTasks({
      project_id: projectId,
      status: 'active',
      per_page: 100,
    });
    const tasks = data?.tasks || [];
    for (const t of tasks) {
      const opt = document.createElement('option');
      opt.value = String(t.id);
      opt.textContent = t.name;
      els.taskSelect.appendChild(opt);
    }
  } catch (error) {
    // Non-fatal: timer can start without a task list.
    console.warn('Failed to load tasks', error);
  }
}

async function loadProjects() {
  if (!client) return;
  const [projectsResp, favResp] = await Promise.all([
    client.getProjects({ status: 'active', per_page: 100 }),
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
    if (!clients.length) {
      const opt = document.createElement('option');
      opt.value = '';
      opt.textContent = 'No clients — create one in the web app';
      els.newProjectClient.appendChild(opt);
      return;
    }
    for (const c of clients) {
      const opt = document.createElement('option');
      opt.value = String(c.id);
      opt.textContent = c.name;
      els.newProjectClient.appendChild(opt);
    }
  } catch (error) {
    const opt = document.createElement('option');
    opt.value = '';
    opt.textContent = 'Could not load clients';
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

els.projectFilter.addEventListener('input', () => {
  fillProjectSelects(els.projectSelect.value || null);
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
    showMessage(error.message || 'Could not start timer.');
  } finally {
    els.startBtn.disabled = false;
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
    els.projectSelect.value = String(projectId);
    await loadTasksForProject(projectId);
    if (result?.task?.id) {
      els.taskSelect.value = String(result.task.id);
    }
  } catch (error) {
    showMessage(error.message || 'Could not create task.');
  } finally {
    els.createTaskBtn.disabled = false;
  }
});

els.createProjectBtn.addEventListener('click', async () => {
  clearMessage();
  const name = els.newProjectName.value.trim();
  const clientId = Number(els.newProjectClient.value);
  if (!name || !clientId) {
    showMessage('Project name and client are required.');
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
