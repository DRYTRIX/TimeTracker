// Command Palette and Keyboard Shortcuts
// Provides Ctrl/Cmd+K palette, quick nav (g d, g p, g r, g t), and timer controls

(function(){
  if (window.__ttCommandsLoaded) return; // prevent double load
  window.__ttCommandsLoaded = true;

  const isMac = navigator.platform.toUpperCase().indexOf('MAC') >= 0;

  // Lightweight DOM helpers
  function $(sel, root){ return (root||document).querySelector(sel); }
  function $all(sel, root){ return Array.from((root||document).querySelectorAll(sel)); }

  function openModal(){
    const el = $('#commandPaletteModal');
    if (!el) return;
    // If already open, just refocus the input instead of reopening
    if (!el.classList.contains('hidden')) {
      setTimeout(() => $('#commandPaletteInput')?.focus(), 10);
      return;
    }
    el.classList.remove('hidden');
    setTimeout(() => $('#commandPaletteInput')?.focus(), 50);
    refreshCommands();
    renderList();
  }

  function closeModal(){
    const el = $('#commandPaletteModal');
    if (!el) return;
    el.classList.add('hidden');
    clearFilter();
  }

  // Timer helpers
  async function getActiveTimer(){
    try {
      const res = await fetch('/timer/status', { credentials: 'same-origin' });
      if (!res.ok) return null;
      const json = await res.json();
      return json && json.active ? json.timer : null;
    } catch(e) { return null; }
  }

  async function startTimerQuick(){
    // Navigate to log time if no quick context; palette is for quick access, not forms
    window.location.href = '/timer/manual';
  }

  async function stopTimerQuick(){
    try {
      const active = await getActiveTimer();
      if (!active) { showToast('No active timer', 'warning'); return; }
      const token = document.querySelector('meta[name="csrf-token"]')?.getAttribute('content') || '';
      const res = await fetch('/timer/stop', { method: 'POST', headers: { 'X-CSRF-Token': token }, credentials: 'same-origin' });
      if (res.ok) {
        showToast('Timer stopped', 'info');
      } else {
        showToast('Failed to stop timer', 'danger');
      }
    } catch(e) {
      showToast('Failed to stop timer', 'danger');
    }
  }

  // Commands registry
  const registry = [];
  function addCommand(cmd){ registry.push(cmd); }
  function nav(href){ window.location.href = href; }

  addCommand({ id: 'goto-dashboard', title: 'Go to Dashboard', hint: 'g d', keywords: 'home main', action: () => nav('/') });
  addCommand({ id: 'goto-projects', title: 'Go to Projects', hint: 'g p', keywords: 'work clients', action: () => nav('/projects') });
  addCommand({ id: 'goto-clients', title: 'Go to Clients', hint: '', keywords: 'work companies', action: () => nav('/clients') });
  addCommand({ id: 'goto-tasks', title: 'Go to Tasks', hint: 'g t', keywords: 'work', action: () => nav('/tasks') });
  addCommand({ id: 'goto-reports', title: 'Go to Reports', hint: 'g r', keywords: 'insights analytics', action: () => nav('/reports') });
  addCommand({ id: 'goto-invoices', title: 'Go to Invoices', hint: '', keywords: 'billing finance', action: () => nav('/invoices') });
  addCommand({ id: 'goto-analytics', title: 'Go to Analytics', hint: '', keywords: 'charts insights', action: () => nav('/analytics') });
  addCommand({ id: 'open-calendar', title: 'Open Calendar', hint: '', keywords: 'day week month schedule', action: () => nav('/timer/calendar') });
  addCommand({ id: 'log-time', title: 'Log Time (Manual Entry)', hint: '', keywords: 'add create', action: () => nav('/timer/manual') });
  addCommand({ id: 'bulk-entry', title: 'Bulk Time Entry', hint: '', keywords: 'multi add', action: () => nav('/timer/bulk') });
  addCommand({ id: 'start-timer', title: 'Start New Timer (Quick → Manual)', hint: '', keywords: 'play run', action: startTimerQuick });
  addCommand({ id: 'stop-timer', title: 'Stop Timer', hint: '', keywords: 'pause end', action: stopTimerQuick });
  addCommand({ id: 'goto-admin', title: 'Open Admin', hint: '', keywords: 'settings system', action: () => nav('/admin') });
  addCommand({ id: 'open-profile', title: 'Open Profile', hint: '', keywords: 'account user', action: () => nav('/profile') });
  addCommand({ id: 'open-help', title: 'Open Help', hint: '', keywords: 'support docs', action: () => nav('/help') });
  addCommand({ id: 'open-about', title: 'Open About', hint: '', keywords: 'info version', action: () => nav('/about') });
  addCommand({ id: 'toggle-theme', title: 'Toggle Theme', hint: isMac ? '⌘⇧L' : 'Ctrl+Shift+L', keywords: 'light dark', action: () => { try { document.getElementById('theme-toggle')?.click(); } catch(e) {} } });
  
  // New Quick Wins Features
  addCommand({ id: 'time-templates', title: 'Time Entry Templates', hint: '', keywords: 'quick templates saved', action: () => nav('/templates') });
  addCommand({ id: 'saved-filters', title: 'Saved Filters', hint: '', keywords: 'search quick filters', action: () => nav('/filters') });
  addCommand({ id: 'user-settings', title: 'User Settings', hint: '', keywords: 'preferences config options', action: () => nav('/settings') });
  addCommand({ id: 'create-project', title: 'Create New Project', hint: '', keywords: 'add new', action: () => nav('/projects/create') });
  addCommand({ id: 'create-task', title: 'Create New Task', hint: '', keywords: 'add new', action: () => nav('/tasks/create') });
  addCommand({ id: 'create-client', title: 'Create New Client', hint: '', keywords: 'add new', action: () => nav('/clients/create') });
  addCommand({ id: 'create-invoice', title: 'Create New Invoice', hint: '', keywords: 'add new billing', action: () => nav('/invoices/create') });
  addCommand({ id: 'export-excel', title: 'Export Reports to Excel', hint: '', keywords: 'download export xlsx', action: () => nav('/reports/export/excel') });
  addCommand({ id: 'my-tasks', title: 'My Tasks', hint: '', keywords: 'assigned work todo', action: () => nav('/tasks/my-tasks') });

  // Filtering and rendering
  let filtered = registry.slice();
  let selectedIdx = 0;

  function clearFilter(){
    const input = $('#commandPaletteInput');
    if (input) input.value = '';
    filtered = registry.slice();
    selectedIdx = 0;
  }

  function normalize(s){ return (s||'').toLowerCase(); }
  function isMatch(cmd, q){
    if (!q) return true;
    const t = normalize(cmd.title);
    const k = normalize(cmd.keywords);
    q = normalize(q);
    return t.indexOf(q) !== -1 || k.indexOf(q) !== -1;
  }

  async function refreshCommands(){
    // Update titles that depend on state (e.g., timer)
    const active = await getActiveTimer();
    const stop = registry.find(c => c.id === 'stop-timer');
    if (stop) stop.title = active ? `Stop Timer (${active.project_name || 'Current'})` : 'Stop Timer';
  }

  function renderList(){
    const list = $('#commandPaletteList');
    if (!list) return;
    list.innerHTML = '';
    // Ensure container has modern styling
    list.className = 'flex flex-col max-h-96 overflow-y-auto divide-y divide-border-light dark:divide-border-dark';
    filtered.forEach((cmd, idx) => {
      const li = document.createElement('button');
      li.type = 'button';
      li.className = 'px-3 py-2 text-left flex justify-between items-center hover:bg-background-light dark:hover:bg-background-dark focus:outline-none focus:ring-2 focus:ring-primary';
      li.setAttribute('data-idx', String(idx));
      li.innerHTML = `<span class="truncate">${cmd.title}</span>${cmd.hint ? `<span class="ml-3 text-xs text-text-muted-light dark:text-text-muted-dark">${cmd.hint}</span>` : ''}`;
      li.addEventListener('click', () => { closeModal(); setTimeout(() => cmd.action(), 50); });
      list.appendChild(li);
    });
    highlightSelected();
  }

  function highlightSelected(){
    $all('#commandPaletteList > button').forEach((el, idx) => {
      const isActive = idx === selectedIdx;
      el.classList.toggle('bg-background-light', isActive);
      el.classList.toggle('dark:bg-background-dark', isActive);
    });
  }

  function onInput(){
    const q = $('#commandPaletteInput')?.value || '';
    filtered = registry.filter(c => isMatch(c, q));
    selectedIdx = 0;
    renderList();
  }

  function onKeyDown(ev){
    // Check if typing in input field or editor
    if (isTypingInField(ev)) return;
    
    // Note: ? key (Shift+/) is now handled by keyboard-shortcuts-advanced.js for shortcuts panel
    // Command palette is opened with Ctrl+K
    
    // Sequence shortcuts: g d / g p / g r / g t
    sequenceHandler(ev);
  }

  // Key sequence handling
  let seq = [];
  let seqTimer = null;
  function resetSeq(){ seq = []; if (seqTimer) { clearTimeout(seqTimer); seqTimer = null; } }
  
  // Check if user is typing in input field or rich text editor
  function isTypingInField(ev){
    const target = ev.target;
    const tag = (target.tagName || '').toLowerCase();
    
    // Check standard inputs
    if (['input','textarea','select'].includes(tag) || target.isContentEditable) {
      return true;
    }
    
    // Check for rich text editors (Toast UI Editor, etc.)
    const editorSelectors = [
      '.toastui-editor', '.toastui-editor-contents', '.ProseMirror', 
      '.CodeMirror', '.ql-editor', '.tox-edit-area', '.note-editable',
      '[contenteditable="true"]', '.toastui-editor-ww-container', 
      '.toastui-editor-md-container'
    ];
    
    for (let i = 0; i < editorSelectors.length; i++) {
      if (target.closest && target.closest(editorSelectors[i])) {
        console.log('[Commands.js] Blocked - inside editor:', editorSelectors[i]);
        return true;
      }
    }
    
    return false;
  }
  
  function sequenceHandler(ev){
    if (ev.repeat) return;
    const key = ev.key.toLowerCase();
    
    // Check if typing in any input field or editor
    if (isTypingInField(ev)) {
      console.log('[Commands.js] Blocked - user is typing');
      resetSeq(); // Clear any partial sequence
      return;
    }
    
    if (ev.ctrlKey || ev.metaKey || ev.altKey) return; // only plain keys
    
    console.log('[Commands.js] Processing key in sequence:', key, 'current seq:', seq);
    seq.push(key);
    if (seq.length > 2) seq.shift();
    if (seq.length === 1 && seq[0] === 'g'){
      seqTimer = setTimeout(resetSeq, 1000);
      return;
    }
    if (seq.length === 2 && seq[0] === 'g'){
      const second = seq[1];
      console.log('[Commands.js] Executing navigation for g +', second);
      resetSeq();
      if (second === 'd') return nav('/');
      if (second === 'p') return nav('/projects');
      if (second === 'r') return nav('/reports');
      if (second === 't') return nav('/tasks');
    }
  }

  // Modal-specific keyboard handling
  document.addEventListener('keydown', (ev) => {
    const modal = $('#commandPaletteModal');
    if (!modal || modal.classList.contains('hidden')) return;
    // If palette is already open, prevent re-opening via hotkeys and simply refocus input
    if ((ev.ctrlKey || ev.metaKey) && (ev.key === '?' || ev.key === '/')) {
      ev.preventDefault();
      setTimeout(() => $('#commandPaletteInput')?.focus(), 10);
      return;
    }
    if (ev.key === '?') {
      ev.preventDefault();
      setTimeout(() => $('#commandPaletteInput')?.focus(), 10);
      return;
    }
    if (ev.key === 'Escape'){ ev.preventDefault(); closeModal(); return; }
    if (ev.key === 'ArrowDown'){ ev.preventDefault(); selectedIdx = Math.min(selectedIdx + 1, filtered.length - 1); highlightSelected(); return; }
    if (ev.key === 'ArrowUp'){ ev.preventDefault(); selectedIdx = Math.max(selectedIdx - 1, 0); highlightSelected(); return; }
    if (ev.key === 'Enter'){
      ev.preventDefault();
      const cmd = filtered[selectedIdx];
      if (cmd){ closeModal(); setTimeout(() => cmd.action(), 50); }
      return;
    }
  });

  // Global keydown to open palette and handle sequences
  document.addEventListener('keydown', onKeyDown);

  // Wire input events when DOM is ready
  document.addEventListener('DOMContentLoaded', function(){
    const input = $('#commandPaletteInput');
    if (input){ input.addEventListener('input', onInput); }
    const closeBtn = $('#commandPaletteClose');
    if (closeBtn){ closeBtn.addEventListener('click', closeModal); }
    const help = $('#commandPaletteHelp');
    if (help){
      help.textContent = `Shortcuts: ${isMac ? '⌘' : 'Ctrl'}+K (Command Palette) · ${isMac ? '⌘' : 'Ctrl'}+/ (Search) · Shift+? (All Shortcuts) · g d (Dashboard) · g p (Projects) · g r (Reports) · g t (Tasks)`;
    }
  });

  // Expose for programmatic access
  window.openCommandPalette = openModal;
})();


