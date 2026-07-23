// Resolved at build time to node_modules/cmdk/dist/command-score.mjs via the `alias`
// map in scripts/build-js.mjs. cmdk's package exports only expose ".", and that entry
// pulls in React, so the deep path is aliased rather than imported directly.
// This was previously a bare `https://cdn.jsdelivr.net/...` import, which meant the
// command palette silently failed without internet access.
import { commandScore } from 'cmdk/command-score';

(() => {
  if (window.__ttCommandPaletteLoaded) return;
  window.__ttCommandPaletteLoaded = true;

  const isMac = (() => {
    try {
      return /Mac|iPhone|iPad|iPod/i.test(navigator.platform) || /Mac OS X/i.test(navigator.userAgent);
    } catch (_) {
      return false;
    }
  })();

  // Swap Ctrl badge to ⌘ on macOS for the sidebar hint.
  try {
    if (isMac) {
      document.querySelectorAll('#sidebar kbd').forEach((kbd) => {
        if (kbd.textContent && kbd.textContent.trim().toLowerCase() === 'ctrl') kbd.textContent = '⌘';
      });
    }
  } catch (_) {}

  const sel = {
    root: '#ttCommandPalette',
    input: '#ttCommandPaletteInput',
    list: '#ttCommandPaletteList',
    close: '#ttCommandPaletteClose',
    subheader: '#ttCommandPaletteSubheader',
  };

  const $ = (s, r = document) => r.querySelector(s);
  const $all = (s, r = document) => Array.from(r.querySelectorAll(s));

  const root = $(sel.root);
  if (!root) return;

  const input = $(sel.input);
  const list = $(sel.list);
  const closeBtn = $(sel.close);
  const subheader = $(sel.subheader);

  const csrfToken = () => document.querySelector('meta[name="csrf-token"]')?.content || '';

  const urls = {
    dashboard: root.dataset.dashboardUrl || '/',
    reports: root.dataset.reportsUrl || '/reports',
    clients: root.dataset.clientsUrl || '/clients',
    newTimeEntry: root.dataset.newTimeEntryUrl || '/timer/manual',
    newProject: root.dataset.newProjectUrl || '/projects/create',
    newInvoice: root.dataset.newInvoiceUrl || '/invoices/create',
  };

  const state = {
    open: false,
    mode: 'commands', // 'commands' | 'projects'
    selected: 0,
    query: '',
    lastFocus: null,
    projects: null,
    commands: [],
    filtered: [],
  };

  function showToast(message, level = 'info') {
    try {
      if (typeof window.showToast === 'function') {
        window.showToast(message, level);
        return;
      }
    } catch (_) {}
    // Fallback: minimal alert-style feedback
    try {
      // eslint-disable-next-line no-alert
      alert(message);
    } catch (_) {}
  }

  function normalize(s) {
    return String(s || '').trim().toLowerCase();
  }

  function fuzzyRank(haystack, query) {
    const q = normalize(query);
    if (!q) return 0;
    const h = normalize(haystack);
    try {
      return commandScore(h, q);
    } catch (_) {
      // Very small fallback if commandScore import fails
      return h.includes(q) ? 1 : 0;
    }
  }

  function isTyping(ev) {
    return window.TimeTracker && window.TimeTracker.isTyping ? window.TimeTracker.isTyping(ev) : false;
  }

  function openPalette() {
    if (!root.classList.contains('hidden')) {
      setTimeout(() => input?.focus(), 10);
      return;
    }
    state.lastFocus = document.activeElement;
    state.open = true;
    state.mode = 'commands';
    state.query = '';
    state.selected = 0;
    if (input) input.value = '';
    if (subheader) subheader.classList.add('hidden');
    root.classList.remove('hidden');
    setTimeout(() => input?.focus(), 30);
    applyFilter();
    render();
  }

  function closePalette() {
    state.open = false;
    root.classList.add('hidden');
    state.query = '';
    state.selected = 0;
    state.mode = 'commands';
    if (input) input.value = '';
    if (subheader) {
      subheader.textContent = '';
      subheader.classList.add('hidden');
    }
    try {
      if (state.lastFocus && typeof state.lastFocus.focus === 'function') state.lastFocus.focus();
    } catch (_) {}
  }

  function nav(href) {
    window.location.href = href;
  }

  async function fetchProjects() {
    if (state.projects) return state.projects;
    const res = await fetch('/api/projects', { credentials: 'same-origin' });
    if (!res.ok) throw new Error('Failed to load projects');
    const json = await res.json();
    const projects = Array.isArray(json.projects) ? json.projects : [];
    state.projects = projects;
    return projects;
  }

  async function startTimerWithProject(projectId) {
    const res = await fetch('/api/timer/start', {
      method: 'POST',
      credentials: 'same-origin',
      headers: {
        'Content-Type': 'application/json',
        'X-CSRFToken': csrfToken(),
      },
      body: JSON.stringify({ project_id: projectId }),
    });

    const json = await res.json().catch(() => ({}));
    if (!res.ok || json.success === false) {
      throw new Error(json.error || json.message || 'Failed to start timer');
    }
    return json;
  }

  function setMode(mode, headerText = '') {
    state.mode = mode;
    state.selected = 0;
    state.query = '';
    if (input) input.value = '';
    if (subheader) {
      if (headerText) {
        subheader.textContent = headerText;
        subheader.classList.remove('hidden');
      } else {
        subheader.textContent = '';
        subheader.classList.add('hidden');
      }
    }
    applyFilter();
    render();
    setTimeout(() => input?.focus(), 10);
  }

  function buildCommands() {
    state.commands = [
      {
        id: 'start-timer',
        title: 'Start Timer',
        keywords: 'timer start track',
        hint: isMac ? '⌘K' : 'Ctrl+K',
        action: async () => {
          try {
            await fetchProjects();
            setMode('projects', 'Start Timer → Select a project');
          } catch (e) {
            showToast(e.message || 'Failed to load projects', 'danger');
          }
        },
      },
      { id: 'new-time-entry', title: 'New Time Entry', keywords: 'manual log add', action: () => nav(urls.newTimeEntry) },
      { id: 'new-project', title: 'New Project', keywords: 'project create add', action: () => nav(urls.newProject) },
      { id: 'new-invoice', title: 'New Invoice', keywords: 'invoice billing create', action: () => nav(urls.newInvoice) },
      { id: 'goto-dashboard', title: 'Go to Dashboard', keywords: 'home overview main', action: () => nav(urls.dashboard) },
      { id: 'goto-reports', title: 'Go to Reports', keywords: 'analytics insights', action: () => nav(urls.reports) },
      { id: 'goto-clients', title: 'Go to Clients', keywords: 'crm customers companies', action: () => nav(urls.clients) },
    ];
  }

  function getActiveItems() {
    if (state.mode === 'projects') {
      const projects = state.projects || [];
      return projects.map((p) => ({
        id: `project:${p.id}`,
        title: p.name || `Project #${p.id}`,
        keywords: `${p.name || ''} ${p.client_name || ''}`.trim(),
        hint: p.client_name ? String(p.client_name) : '',
        action: async () => {
          try {
            await startTimerWithProject(p.id);
            closePalette();
            showToast('Timer started', 'info');
          } catch (e) {
            showToast(e.message || 'Failed to start timer', 'danger');
          }
        },
      }));
    }
    return state.commands;
  }

  function applyFilter() {
    const items = getActiveItems();
    const q = state.query;

    if (!q) {
      state.filtered = items.slice();
      state.selected = Math.min(state.selected, Math.max(0, state.filtered.length - 1));
      return;
    }

    const scored = items
      .map((it) => {
        const haystack = `${it.title} ${it.keywords || ''}`;
        const score = fuzzyRank(haystack, q);
        return { it, score };
      })
      .filter((x) => x.score > 0);

    scored.sort((a, b) => b.score - a.score);
    state.filtered = scored.map((x) => x.it);
    state.selected = 0;
  }

  function highlightSelected() {
    $all('[data-tt-cp-idx]', list).forEach((el) => {
      const idx = Number(el.getAttribute('data-tt-cp-idx') || '0');
      const active = idx === state.selected;
      el.classList.toggle('bg-background-light', active);
      el.classList.toggle('dark:bg-background-dark', active);
    });
  }

  function renderEmpty(message) {
    list.innerHTML = `
      <div class="px-3 py-8 text-center text-sm text-text-muted-light dark:text-text-muted-dark">
        ${message}
      </div>
    `;
  }

  function render() {
    if (!list) return;

    const items = state.filtered || [];
    if (!items.length) {
      if (state.mode === 'projects') renderEmpty('No projects found.');
      else renderEmpty('No commands found.');
      return;
    }

    list.innerHTML = '';
    items.forEach((cmd, idx) => {
      const btn = document.createElement('button');
      btn.type = 'button';
      btn.setAttribute('data-tt-cp-idx', String(idx));
      btn.className =
        'px-3 py-2 text-left flex items-center justify-between gap-3 hover:bg-background-light dark:hover:bg-background-dark focus:outline-none focus:ring-2 focus:ring-primary';

      const left = document.createElement('div');
      left.className = 'min-w-0 flex-1';
      left.innerHTML = `<div class="truncate">${cmd.title}</div>`;

      const right = document.createElement('div');
      right.className = 'shrink-0 text-xs text-text-muted-light dark:text-text-muted-dark flex items-center gap-2';
      if (cmd.hint) {
        right.innerHTML = `<span class="truncate">${cmd.hint}</span>`;
      }

      btn.appendChild(left);
      btn.appendChild(right);
      btn.addEventListener('click', () => {
        closePalette();
        setTimeout(() => cmd.action?.(), 30);
      });

      list.appendChild(btn);
    });
    highlightSelected();
  }

  function onInput() {
    state.query = input?.value || '';
    applyFilter();
    render();
  }

  function onPaletteKeydown(ev) {
    if (!state.open) return;

    if (ev.key === 'Escape') {
      ev.preventDefault();
      closePalette();
      return;
    }

    if (ev.key === 'ArrowDown') {
      ev.preventDefault();
      state.selected = Math.min(state.selected + 1, Math.max(0, (state.filtered?.length || 1) - 1));
      highlightSelected();
      return;
    }

    if (ev.key === 'ArrowUp') {
      ev.preventDefault();
      state.selected = Math.max(state.selected - 1, 0);
      highlightSelected();
      return;
    }

    if (ev.key === 'Enter') {
      ev.preventDefault();
      const cmd = state.filtered?.[state.selected];
      if (cmd) {
        closePalette();
        setTimeout(() => cmd.action?.(), 30);
      }
    }
  }

  function onGlobalKeydown(ev) {
    const combo = (ev.ctrlKey || ev.metaKey) && (ev.key === 'k' || ev.key === 'K');
    if (combo) {
      ev.preventDefault();
      openPalette();
      return;
    }

    if (!state.open) return;

    // When palette is open, keep focus in the input.
    if (ev.key === '/' && (ev.ctrlKey || ev.metaKey)) {
      ev.preventDefault();
      setTimeout(() => input?.focus(), 10);
    }
  }

  function onBackdropClick(e) {
    const shouldClose = e.target?.hasAttribute?.('data-tt-cp-close');
    if (shouldClose) closePalette();
  }

  function onRootClick(e) {
    const btn = e.target.closest?.('#ttCommandPaletteClose');
    if (btn) {
      e.preventDefault();
      closePalette();
    }
  }

  function init() {
    buildCommands();
    state.filtered = state.commands.slice();

    document.addEventListener('keydown', onGlobalKeydown);
    document.addEventListener('keydown', (ev) => {
      if (!state.open) return;
      // Allow navigation even if the input isn't focused.
      if (!isTyping(ev)) onPaletteKeydown(ev);
    });

    root.addEventListener('click', onRootClick);
    root.addEventListener('click', onBackdropClick);
    input?.addEventListener('input', onInput);
    closeBtn?.addEventListener('click', (e) => {
      e.preventDefault();
      closePalette();
    });

    window.openCommandPalette = openPalette;
  }

  init();
})();

