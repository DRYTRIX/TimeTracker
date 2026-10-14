/**
 * Timer tab: idle selection flow (search/chips/notes) + running clock view.
 * Talks to /api/v1/timer/* directly; badge/background sync via ctx.
 */

import { ApiClient, elapsedSecondsFromTimer } from '../lib/api.js';
import { colorForProject, formatClock, formatTimeOf, noteSuggestions, formatHM } from '../lib/format.js';
import { icons } from '../lib/icons.js';
import { createProjectSearch } from './search.js';
import { decodeEntities, displayHtml } from './text.js';

/** Closed statuses — matches Task.is_active (anything else is selectable). */
const CLOSED_TASK_STATUSES = new Set(['done', 'cancelled']);

const el = (id) => document.getElementById(id);

export function initTimerTab(ctx) {
  const els = {
    viewIdle: el('view-idle'),
    viewRunning: el('view-running'),
    runCard: el('run-card'),
    searchInput: el('search-input'),
    recentChiprow: el('recent-chiprow'),
    recentChips: el('recent-chips'),
    favChiprow: el('fav-chiprow'),
    favChips: el('fav-chips'),
    selection: el('selection'),
    selDot: el('sel-dot'),
    selProject: el('sel-project'),
    selClient: el('sel-client'),
    selClear: el('sel-clear'),
    selTask: el('sel-task'),
    selTaskName: el('sel-task-name'),
    selTaskChevron: el('sel-task-chevron'),
    taskMenu: el('task-menu'),
    notes: el('notes'),
    noteSugg: el('note-sugg'),
    noteSuggChips: el('note-sugg-chips'),
    btnStart: el('btn-start'),
    runDot: el('run-dot'),
    runProject: el('run-project'),
    runSub: el('run-sub'),
    recBadge: el('rec-badge'),
    clock: el('clock'),
    runMeta: el('run-meta'),
    btnPause: el('btn-pause'),
    btnStop: el('btn-stop'),
    btnNote: el('btn-note'),
    noteEditor: el('note-editor'),
    quickNoteInput: el('quick-note-input'),
    quickNoteSave: el('quick-note-save'),
  };

  let searchHandle = null;
  let taskLoadGeneration = 0;
  const taskCache = new Map();
  let noteSaveTimer = null;

  const state = ctx.state;

  function selectedProject() {
    return state.projects.find((p) => p.id === state.selected.projectId) || null;
  }

  function selectedTask() {
    if (state.selected.taskId == null) return null;
    return (taskCache.get(state.selected.projectId) || []).find(
      (t) => t.id === state.selected.taskId
    ) || null;
  }

  // ── rendering: idle ────────────────────────────────────

  function renderChips() {
    const favorites = state.projects.filter((p) => p.favorite).slice(0, 3);
    const favoriteIds = new Set(favorites.map((p) => p.id));
    const recent = state.projects
      .filter((p) => p.last_used_at && !favoriteIds.has(p.id))
      .slice(0, 3);

    els.favChiprow.hidden = favorites.length === 0;
    els.recentChiprow.hidden = recent.length === 0;
    fillChipRow(els.favChips, favorites);
    fillChipRow(els.recentChips, recent);
  }

  function fillChipRow(container, projects) {
    container.innerHTML = '';
    for (const p of projects) {
      const chip = document.createElement('button');
      chip.type = 'button';
      chip.className = 'chip';
      chip.classList.toggle('is-selected', p.id === state.selected.projectId);
      const star = p.favorite ? `<span class="r-star">${icons.star}</span>` : '';
      chip.innerHTML = `<span class="pdot" style="background:${colorForProject(p.id)}"></span>${displayHtml(p.name)}${star}`;
      chip.addEventListener('click', () => {
        selectProject(p);
        searchHandle?.close();
      });
      container.appendChild(chip);
    }
  }

  function renderNoteSuggestions() {
    const suggestions = noteSuggestions(state.recentEntries, 3);
    els.noteSugg.hidden = suggestions.length === 0;
    els.noteSuggChips.innerHTML = '';
    for (const note of suggestions) {
      const chip = document.createElement('button');
      chip.type = 'button';
      chip.className = 'chip sm';
      chip.textContent = decodeEntities(note);
      chip.addEventListener('click', () => {
        els.notes.value = note;
        els.notes.focus();
      });
      els.noteSuggChips.appendChild(chip);
    }
  }

  function renderSelection() {
    const project = selectedProject();
    els.selection.classList.toggle('hidden', !project);
    els.btnStart.disabled = !project;
    els.btnStart.innerHTML = project
      ? `${icons.play}<span>Start timer</span>`
      : `${icons.play}<span>Select a project</span>`;
    if (!project) return;

    els.selDot.style.background = colorForProject(project.id);
    els.selProject.textContent = decodeEntities(project.name);
    els.selClient.textContent = decodeEntities(project.clientName || '');

    const task = selectedTask();
    els.selTaskName.textContent = task ? decodeEntities(task.name) : 'None';

    renderNoteSuggestions();
  }

  function renderIdle() {
    renderChips();
    renderSelection();
  }

  // ── rendering: running ─────────────────────────────────

  function runningName(timer) {
    return (
      timer.project ||
      timer.client ||
      (timer.project_id ? `Project #${timer.project_id}` : 'Timer')
    );
  }

  function renderRunning() {
    const timer = state.timer;
    if (!timer) return;

    const paused = Boolean(timer.paused_at);
    els.runCard.dataset.paused = paused ? '1' : '';
    els.runDot.style.background = colorForProject(timer.project_id);
    els.runProject.textContent = decodeEntities(runningName(timer));
    const parts = [timer.client, timer.task].filter(Boolean);
    els.runSub.textContent = decodeEntities(parts.join(' · '));

    els.recBadge.classList.toggle('is-paused', paused);
    els.recBadge.innerHTML = paused
      ? 'Paused'
      : '<span class="rec-dot"></span>Rec';

    els.btnPause.innerHTML = paused
      ? `${icons.play}<span>Resume</span>`
      : `${icons.pause}<span>Pause</span>`;
    els.btnStop.innerHTML = `${icons.stop}<span>Stop</span>`;

    updateClock();
  }

  function updateClock() {
    const timer = state.timer;
    if (!timer) return;
    els.clock.textContent = formatClock(elapsedSecondsFromTimer(timer));

    const meta = [`Started ${formatTimeOf(timer.start_time)}`];
    const breakSeconds = Number(timer.break_seconds) || 0;
    if (breakSeconds > 0) {
      meta.push(
        breakSeconds < 3600
          ? `Break ${Math.round(breakSeconds / 60)} min`
          : `Break ${formatHM(breakSeconds)} h`
      );
    }
    if (state.todaySeconds > 0) {
      meta.push(`Today ${formatHM(state.todaySeconds + elapsedSecondsFromTimer(timer))}`);
    }
    els.runMeta.textContent = meta.join(' · ');
  }

  function render() {
    const running = Boolean(state.timer);
    els.viewRunning.classList.toggle('hidden', !running);
    els.viewIdle.classList.toggle('hidden', running);
    if (running) {
      resetNoteEditor();
      renderRunning();
    } else {
      renderIdle();
    }
  }

  // ── actions ────────────────────────────────────────────

  function selectProject(project) {
    state.selected.projectId = project.id;
    state.selected.taskId = null;
    renderSelection();
  }

  function clearSelection() {
    state.selected.projectId = null;
    state.selected.taskId = null;
    renderSelection();
  }

  async function startTracking({ projectId, clientId = null, taskId = null, notes = '' } = {}) {
    const project = state.projects.find((p) => p.id === projectId);
    ctx.clearMessage();
    els.btnStart.disabled = true;
    try {
      const result = await ctx.client.startTimer({
        projectId,
        clientId: clientId ?? project?.client_id ?? null,
        taskId,
        notes,
      });
      const timer = result?.timer;
      if (timer) {
        applyTimer(timer);
        ctx.showMessage('Timer started.', 'success');
      }
      const name = timer?.project || project?.name || 'Timer';
      chrome.storage.local.set({
        last_project: { project_id: projectId, task_id: taskId || null, name },
      });
      ctx.refreshInsights();
      ctx.refreshRecents();
    } catch (error) {
      await handleStartConflict(error);
    } finally {
      els.btnStart.disabled = !selectedProject();
    }
  }

  /** When start conflicts with an existing timer, sync to that running timer. */
  async function handleStartConflict(error) {
    const isConflict =
      error.status === 409 ||
      error.code === 'CONFLICT' ||
      error.code === 'timer_already_running';
    if (isConflict) {
      if (error.data?.timer) {
        applyTimer(error.data.timer);
        ctx.showMessage('A timer is already running.', 'success');
        return;
      }
      try {
        const status = await ctx.client.getTimerStatus();
        if (status?.active && status?.timer) {
          applyTimer(status.timer);
          ctx.showMessage('A timer is already running.', 'success');
          return;
        }
      } catch {
        /* fall through */
      }
    }
    ctx.showMessage(error.message || 'Could not start timer.');
  }

  function applyTimer(timer) {
    state.timer = timer || null;
    ctx.notifyBackground();
    render();
  }

  els.btnStart.addEventListener('click', () => {
    const project = selectedProject();
    if (!project) return;
    void startTracking({
      projectId: project.id,
      taskId: state.selected.taskId,
      notes: els.notes.value.trim(),
    });
  });

  els.notes.addEventListener('keydown', (event) => {
    if (event.key === 'Enter') els.btnStart.click();
  });

  els.btnPause.addEventListener('click', async () => {
    const timer = state.timer;
    if (!timer) return;
    const paused = Boolean(timer.paused_at);
    els.btnPause.disabled = true;
    ctx.clearMessage();
    try {
      const result = paused
        ? await ctx.client.resumeTimer()
        : await ctx.client.pauseTimer();
      const updated = result?.time_entry || result?.timer;
      if (updated) applyTimer(updated);
    } catch (error) {
      ctx.showMessage(error.message || 'Could not update timer.');
    } finally {
      els.btnPause.disabled = false;
    }
  });

  els.btnStop.addEventListener('click', async () => {
    if (!state.timer) return;
    els.btnStop.disabled = true;
    ctx.clearMessage();
    try {
      await ctx.client.stopTimer();
      state.timer = null;
      ctx.notifyBackground();
      render();
      ctx.refreshAll();
    } catch (error) {
      ctx.showMessage(error.message || 'Could not stop timer.');
    } finally {
      els.btnStop.disabled = false;
    }
  });

  // ── quick note (updates the running entry) ─────────────

  function resetNoteEditor() {
    els.noteEditor.classList.add('hidden');
    els.btnNote.classList.remove('hidden');
  }

  els.btnNote.innerHTML = `${icons.plus}<span>Quick note</span>`;
  els.btnNote.addEventListener('click', () => {
    els.btnNote.classList.add('hidden');
    els.noteEditor.classList.remove('hidden');
    els.quickNoteInput.value = state.timer?.notes || '';
    els.quickNoteInput.focus();
  });

  els.quickNoteSave.innerHTML = icons['check-circle'];
  els.quickNoteSave.addEventListener('click', saveQuickNote);
  els.quickNoteInput.addEventListener('keydown', (event) => {
    if (event.key === 'Enter') saveQuickNote();
  });

  async function saveQuickNote() {
    const timer = state.timer;
    if (!timer) return;
    const notes = els.quickNoteInput.value.trim();
    els.quickNoteSave.disabled = true;
    try {
      await ctx.client.updateTimeEntry(timer.id, { notes });
      state.timer = { ...timer, notes };
      resetNoteEditor();
      els.btnNote.innerHTML = `${icons.plus}<span>Saved</span>`;
      clearTimeout(noteSaveTimer);
      noteSaveTimer = setTimeout(() => {
        els.btnNote.innerHTML = `${icons.plus}<span>Quick note</span>`;
      }, 1500);
    } catch (error) {
      ctx.showMessage(error.message || 'Could not save note.');
    } finally {
      els.quickNoteSave.disabled = false;
    }
  }

  // ── task menu ──────────────────────────────────────────

  els.selTaskChevron.innerHTML = icons['chevron-right'];
  els.selClear.innerHTML = icons.x;

  els.selClear.addEventListener('click', clearSelection);

  els.selTask.addEventListener('click', async () => {
    const project = selectedProject();
    if (!project) return;
    if (!els.taskMenu.classList.contains('hidden')) {
      els.taskMenu.classList.add('hidden');
      els.selTaskChevron.innerHTML = icons['chevron-right'];
      return;
    }
    els.selTaskChevron.innerHTML = icons['chevron-down'];
    await openTaskMenu(project);
  });

  async function openTaskMenu(project) {
    const tasks = await loadTasks(project.id);
    renderTaskMenu(project, tasks, '');
  }

  async function loadTasks(projectId) {
    if (taskCache.has(projectId)) return taskCache.get(projectId);
    const generation = ++taskLoadGeneration;
    try {
      const data = await ctx.client.getTasks({
        project_id: projectId,
        status: 'open',
        per_page: 200,
      });
      if (generation !== taskLoadGeneration) return taskCache.get(projectId) || [];
      const byId = new Map();
      for (const t of data?.tasks || []) {
        if (!t || t.id == null) continue;
        if (!t.status || CLOSED_TASK_STATUSES.has(t.status)) continue;
        if (!byId.has(t.id)) byId.set(t.id, t);
      }
      const tasks = Array.from(byId.values()).sort((a, b) =>
        String(a.name).localeCompare(String(b.name))
      );
      taskCache.set(projectId, tasks);
      return tasks;
    } catch (error) {
      console.warn('Failed to load tasks', error);
      return [];
    }
  }

  function renderTaskMenu(project, tasks, filter) {
    els.taskMenu.innerHTML = '';
    els.taskMenu.classList.remove('hidden');

    const search = document.createElement('div');
    search.className = 'field task-search';
    search.innerHTML = '<input type="text" placeholder="Filter or create task…" aria-label="Filter or create task">';
    const searchInput = search.querySelector('input');
    searchInput.addEventListener('input', () => {
      renderTaskList(project, tasks, searchInput.value);
    });
    searchInput.addEventListener('keydown', (event) => {
      if (event.key === 'Enter') {
        event.preventDefault();
        createTaskIfMissing(project, tasks, searchInput.value);
      }
      if (event.key === 'Escape') closeTaskMenu();
    });
    els.taskMenu.appendChild(search);

    const list = document.createElement('div');
    list.setAttribute('role', 'listbox');
    els.taskMenu.appendChild(list);
    els.taskMenu._list = list;

    renderTaskList(project, tasks, filter);
    searchInput.focus();
  }

  function renderTaskList(project, tasks, filter) {
    const list = els.taskMenu._list;
    if (!list) return;
    const q = String(filter || '').trim().toLowerCase();
    const visible = q ? tasks.filter((t) => String(t.name).toLowerCase().includes(q)) : tasks;

    list.innerHTML = '';
    const none = document.createElement('button');
    none.type = 'button';
    none.className = 'result';
    none.innerHTML = `<span>No task</span>${state.selected.taskId == null ? '<span class="r-client">✓</span>' : ''}`;
    none.addEventListener('mousedown', (event) => {
      event.preventDefault();
      state.selected.taskId = null;
      closeTaskMenu();
      renderSelection();
    });
    list.appendChild(none);

    for (const t of visible) {
      const row = document.createElement('button');
      row.type = 'button';
      row.className = 'result';
      const selected = state.selected.taskId === t.id;
      const status = t.status && t.status !== 'todo' ? ` (${t.status})` : '';
      row.innerHTML = `<span>${displayHtml(t.name)}${displayHtml(status)}</span>${selected ? '<span class="r-client">✓</span>' : ''}`;
      row.addEventListener('mousedown', (event) => {
        event.preventDefault();
        state.selected.taskId = t.id;
        closeTaskMenu();
        renderSelection();
      });
      list.appendChild(row);
    }

    const exact = tasks.some((t) => String(t.name).toLowerCase() === q);
    if (q.length >= 2 && !exact) {
      const create = document.createElement('button');
      create.type = 'button';
      create.className = 'result result-create';
      create.innerHTML = `${icons.plus}<span>Create task “${displayHtml(q)}”</span>`;
      create.addEventListener('mousedown', (event) => {
        event.preventDefault();
        void createTask(project, q);
      });
      list.appendChild(create);
    }
  }

  async function createTaskIfMissing(project, tasks, value) {
    const q = String(value || '').trim();
    if (q.length < 2) return;
    const exact = tasks.some((t) => String(t.name).toLowerCase() === q.toLowerCase());
    if (!exact) await createTask(project, q);
  }

  async function createTask(project, name) {
    try {
      const result = await ctx.client.createTask({ name, projectId: project.id });
      const created = result?.task || result;
      const task = created?.id
        ? { id: created.id, name: created.name || name, status: created.status || 'todo' }
        : null;
      if (task) {
        taskCache.set(project.id, [...(taskCache.get(project.id) || []), task]);
        state.selected.taskId = task.id;
      }
      closeTaskMenu();
      renderSelection();
      ctx.showMessage('Task created.', 'success');
    } catch (error) {
      ctx.showMessage(error.message || 'Could not create task.');
    }
  }

  function closeTaskMenu() {
    els.taskMenu.classList.add('hidden');
    els.taskMenu.innerHTML = '';
    els.selTaskChevron.innerHTML = icons['chevron-right'];
  }

  // ── search ─────────────────────────────────────────────

  searchHandle = createProjectSearch({
    wrapEl: el('search-wrap'),
    input: els.searchInput,
    listEl: el('search-results'),
    getProjects: () => state.projects,
    onSelect: selectProject,
    onCreate: (name) => void createProjectInline(name),
  });

  async function createProjectInline(name) {
    try {
      const result = await ctx.client.createProject({ name });
      const created = result?.project || result;
      ctx.showMessage('Project created.', 'success');
      await ctx.loadDirectory(created?.id ?? null);
      const project = state.projects.find((p) => p.id === created?.id);
      if (project) selectProject(project);
      else if (created?.id) selectProject({ id: created.id, name: created.name || name });
    } catch (error) {
      ctx.showMessage(error.message || 'Could not create project.');
    }
  }

  // ── tick + external updates ────────────────────────────

  setInterval(() => {
    if (state.timer && !els.viewRunning.classList.contains('hidden')) updateClock();
  }, 1000);

  return {
    render,
    renderIdle,
    applyTimer,
    startTracking,
    renderNoteSuggestions,
  };
}

