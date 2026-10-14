/**
 * Dev preview shim: lets popup.html and options.html run in a plain browser
 * (http://localhost) with realistic demo data — no extension runtime needed.
 *
 * It is a no-op inside the real extension (chrome.* already exists) and is
 * safe to ship. To preview: cd browser-extension && python3 -m http.server,
 * then open http://localhost:8000/popup/popup.html
 * Hash options: #idle (idle view), #paused (paused timer).
 */

(() => {
  if (typeof chrome !== 'undefined' && chrome.storage && chrome.runtime) return;

  const pad2 = (n) => String(n).padStart(2, '0');
  const isoLocal = (d) =>
    `${d.getFullYear()}-${pad2(d.getMonth() + 1)}-${pad2(d.getDate())}` +
    `T${pad2(d.getHours())}:${pad2(d.getMinutes())}:00`;
  const dateKey = (d) =>
    `${d.getFullYear()}-${pad2(d.getMonth() + 1)}-${pad2(d.getDate())}`;
  const at = (offsetDays, h, m) => {
    const d = new Date();
    d.setDate(d.getDate() + offsetDays);
    d.setHours(h, m, 0, 0);
    return d;
  };

  const params = new URLSearchParams(window.location.search || '');
  const mode = window.location.hash || (params.get('view') ? `#${params.get('view')}` : '');
  const wantIdle = mode === '#idle';
  const wantPaused = mode === '#paused';

  const runningStart = new Date(Date.now() - 5077 * 1000);
  const activeEntry = {
    id: 501,
    project_id: 1,
    client_id: 11,
    task_id: 101,
    project: 'Homepage redesign',
    client: 'Acme Corp',
    task: 'Design review',
    start_time: isoLocal(runningStart),
    end_time: null,
    paused_at: wantPaused ? isoLocal(new Date(Date.now() - 60 * 1000)) : null,
    break_seconds: 720,
    duration_seconds: null,
    duration_hours: null,
    notes: '',
    billable: true,
    is_active: true,
    idle_notified: false,
    needs_review: false,
  };

  const finishedEntries = [
    { id: 481, project_id: 3, project: 'Q3 invoices', client_id: 11, client: 'Acme Corp', task_id: null, task: null, start: at(0, 8, 30), end: at(0, 9, 2), notes: 'Batch send', billable: true },
    { id: 488, project_id: 2, project: 'Client portal API', client_id: 11, client: 'Acme Corp', task_id: null, task: null, start: at(0, 9, 15), end: at(0, 10, 40), notes: 'Pairing on auth', billable: true },
    { id: 452, project_id: 1, project: 'Homepage redesign', client_id: 11, client: 'Acme Corp', task_id: 102, task: 'Sprint 42 planning', start: at(-1, 10, 0), end: at(-1, 11, 30), notes: '', billable: true },
    { id: 455, project_id: 4, project: 'Internal R&D', client_id: null, client: null, task_id: null, task: null, start: at(-1, 14, 0), end: at(-1, 16, 12), notes: 'Landing page &amp; Pricing Page Design', billable: false },
    { id: 430, project_id: 1, project: 'Homepage redesign', client_id: 11, client: 'Acme Corp', task_id: null, task: null, start: at(-2, 9, 0), end: at(-2, 12, 10), notes: 'Design review call', billable: true },
    { id: 428, project_id: 2, project: 'Client portal API', client_id: 11, client: 'Acme Corp', task_id: null, task: null, start: at(-3, 11, 0), end: at(-3, 12, 30), notes: '', billable: true },
  ];

  const toDict = (e) => {
    const seconds = Math.round((e.end - e.start) / 1000);
    return {
      id: e.id,
      project_id: e.project_id,
      client_id: e.client_id,
      task_id: e.task_id,
      project: e.project,
      client: e.client,
      task: e.task,
      start_time: isoLocal(e.start),
      end_time: isoLocal(e.end),
      duration_seconds: seconds,
      duration_hours: seconds / 3600,
      break_seconds: 0,
      paused_at: null,
      notes: e.notes,
      billable: e.billable,
      is_active: false,
      idle_notified: false,
      needs_review: false,
    };
  };

  const allEntries = () => [
    ...finishedEntries.map(toDict),
    ...(wantIdle ? [] : [{ ...activeEntry }]),
  ];

  const projects = [
    { id: 1, name: 'Homepage redesign', client_id: 11, last_used_at: new Date().toISOString() },
    { id: 2, name: 'Client portal API', client_id: 11, last_used_at: new Date(Date.now() - 86400000).toISOString() },
    { id: 4, name: 'Internal R&D', client_id: null, last_used_at: new Date(Date.now() - 2 * 86400000).toISOString() },
    { id: 3, name: 'Q3 invoices', client_id: 11, last_used_at: new Date(Date.now() - 3 * 86400000).toISOString() },
  ];
  const tasksByProject = {
    1: [
      { id: 101, name: 'Design review', status: 'in_progress' },
      { id: 102, name: 'Sprint 42 planning', status: 'todo' },
      { id: 103, name: 'Handoff to engineering', status: 'todo' },
      { id: 104, name: 'Error Handling &amp; Security Improvements', status: 'todo' },
    ],
    2: [{ id: 201, name: 'Auth endpoints', status: 'in_progress' }],
  };

  const listeners = { changed: [] };
  const store = new Map();
  const put = (key, value) => {
    store.set(key, value);
    for (const fn of listeners.changed) {
      fn({ [key]: { oldValue: undefined, newValue: value } }, 'local');
    }
  };
  put('server_url', 'https://demo.local');
  put('api_token', 'tt_demo');
  put('logged_out', false);
  put('badge_show_elapsed', true);
  put('last_project', { project_id: 1, task_id: null, name: 'Homepage redesign' });
  put('last_timer_status', {
    active: !wantIdle,
    timer: wantIdle ? null : activeEntry,
    error: null,
  });

  const mondayOfThisWeek = () => {
    const d = new Date();
    const day = (d.getDay() + 6) % 7;
    d.setDate(d.getDate() - day);
    return d;
  };
  const weekStart = mondayOfThisWeek();
  const weekEnd = new Date(weekStart);
  weekEnd.setDate(weekEnd.getDate() + 6);

  globalThis.chrome = {
    storage: {
      local: {
        async get(keys) {
          const out = {};
          if (keys == null) {
            for (const [k, v] of store) out[k] = v;
            return out;
          }
          const list = Array.isArray(keys) ? keys : typeof keys === 'string' ? [keys] : Object.keys(keys);
          for (const k of list) {
            out[k] = store.has(k) ? store.get(k) : (Array.isArray(keys) ? undefined : keys[k]);
          }
          return out;
        },
        async set(obj) {
          for (const [k, v] of Object.entries(obj)) put(k, v);
        },
        async remove(keys) {
          for (const k of Array.isArray(keys) ? keys : [keys]) store.delete(k);
        },
      },
      onChanged: {
        addListener(fn) {
          listeners.changed.push(fn);
        },
      },
    },
    runtime: {
      sendMessage: async () => ({}),
      connect: () => ({ onDisconnect: { addListener() {} } }),
      openOptionsPage: () => {
        window.location.href = '../options/options.html';
      },
    },
    commands: {
      getAll: async () => [
        { name: 'toggle-timer', shortcut: 'Ctrl+Shift+S' },
        { name: '_execute_action', shortcut: 'Ctrl+Shift+T' },
      ],
    },
    permissions: {
      contains: async () => true,
      request: async () => true,
    },
  };

  // ── fetch mock ─────────────────────────────────────────
  const json = (body) => ({
    ok: true,
    status: 200,
    text: async () => JSON.stringify(body),
  });

  function summaryFor(startKey, endKey) {
    const entries = finishedEntries.map(toDict).filter((e) => {
      const key = dateKey(new Date(e.start_time));
      return (!startKey || key >= startKey) && (!endKey || key <= endKey);
    });
    const byProject = new Map();
    let total = 0;
    let billable = 0;
    for (const e of entries) {
      total += e.duration_hours;
      if (e.billable) billable += e.duration_hours;
      const key = e.project_id || 0;
      const item = byProject.get(key) || { project_id: e.project_id, project_name: e.project, hours: 0, entries: 0 };
      item.hours += e.duration_hours;
      item.entries += 1;
      byProject.set(key, item);
    }
    return {
      summary: {
        start_date: startKey,
        end_date: endKey,
        total_hours: Math.round(total * 100) / 100,
        billable_hours: Math.round(billable * 100) / 100,
        total_entries: entries.length,
        by_project: Array.from(byProject.values()),
      },
    };
  }

  globalThis.fetch = async (url, init) => {
    const parsed = new URL(url, window.location.origin);
    const path = parsed.pathname.replace(/\/api\/v1$/, '/api/v1');
    const method = (init?.method || 'GET').toUpperCase();

    if (path === '/api/v1/timer/status') {
      return json({
        active: !wantIdle,
        timer: wantIdle ? null : activeEntry,
        idle_timeout_minutes: 30,
        idle_unanswered_action: 'review',
        idle_notified: false,
      });
    }
    if (path === '/api/v1/timer/start') {
      return json({ timer: { ...activeEntry } });
    }
    if (path === '/api/v1/timer/pause') {
      return json({ time_entry: { ...activeEntry, paused_at: isoLocal(new Date()) } });
    }
    if (path === '/api/v1/timer/resume') {
      return json({ time_entry: { ...activeEntry, paused_at: null } });
    }
    if (path === '/api/v1/timer/stop' || path === '/api/v1/timer/heartbeat') {
      return json({ ok: true });
    }
    if (path.startsWith('/api/v1/time-entries/') && method === 'PATCH') {
      return json({ time_entry: { ...activeEntry } });
    }
    if (path === '/api/v1/time-entries') {
      const startKey = parsed.searchParams.get('start_date');
      const endKey = parsed.searchParams.get('end_date');
      const entries = allEntries().filter((e) => {
        const key = dateKey(new Date(e.start_time));
        return (!startKey || key >= startKey) && (!endKey || key <= endKey);
      });
      return json({ time_entries: entries, pagination: { page: 1, pages: 1 } });
    }
    if (path === '/api/v1/reports/summary') {
      return json(
        summaryFor(parsed.searchParams.get('start_date'), parsed.searchParams.get('end_date'))
      );
    }
    if (path === '/api/v1/weekly-goals') {
      return json({
        weekly_goals: [
          {
            id: 1,
            week_start_date: dateKey(weekStart),
            week_end_date: dateKey(weekEnd),
            target_hours: 40,
            actual_hours: 26.4,
            progress_percentage: 66,
            remaining_hours: 13.6,
            status: 'active',
          },
        ],
      });
    }
    if (path === '/api/v1/projects') {
      return json({ projects, pagination: { page: 1, pages: 1 } });
    }
    if (path === '/api/v1/users/me/favorites/projects') {
      return json({ favorites: [{ project_id: 4 }] });
    }
    if (path === '/api/v1/clients') {
      return json({ clients: [{ id: 11, name: 'Acme Corp' }] });
    }
    if (path === '/api/v1/tasks') {
      const projectId = Number(parsed.searchParams.get('project_id'));
      return json({ tasks: tasksByProject[projectId] || [] });
    }
    if (path === '/api/v1/users/me') {
      return json({ user: { username: 'giorgio', email: 'giorgio@example.com' } });
    }
    return json({ error: 'mock: no route' });
  };
})();
