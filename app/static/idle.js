// Idle detection: when user is inactive, offer to stop timer at last active time
(function(){
  if (window.__ttIdleLoaded) return; window.__ttIdleLoaded = true;

  function getIdleThresholdMs(){
    const meta = document.querySelector('meta[name="idle-timeout-minutes"]');
    const mins = meta ? parseInt(meta.getAttribute('content'), 10) : 30;
    return (isNaN(mins) || mins < 1 ? 30 : Math.min(480, mins)) * 60 * 1000;
  }

  const CHECK_INTERVAL_MS = 60 * 1000; // 1 minute
  const SNOOZE_MS = 5 * 60 * 1000; // 5 minutes

  let lastActivity = Date.now();
  let promptShown = false;

  function markActive(){
    lastActivity = Date.now();
    promptShown = false;
  }

  ['mousemove','keydown','scroll','click','touchstart','visibilitychange'].forEach(evt =>
    document.addEventListener(evt, markActive, { passive: true })
  );

  async function getTimer(){
    try {
      const r = await fetch('/api/timer/status');
      if (!r.ok) return null; const j = await r.json();
      return j && j.active ? j.timer : null;
    } catch(e){ return null; }
  }

  function formatTime(d){
    return window.formatUserTime ? window.formatUserTime(d) : d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
  }

  async function stopAt(ts){
    try {
      const r = await fetch('/api/timer/stop_at', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ stop_time: new Date(ts).toISOString() }) });
      if (r.ok){
        const msg = window.i18n?.messages?.timerStoppedInactivity || 'Timer stopped due to inactivity';
        if (window.toastManager && window.toastManager.warning) {
          window.toastManager.warning(msg, '', 5000);
        } else if (window.toastManager && window.toastManager.show) {
          window.toastManager.show({ message: msg, type: 'warning', duration: 5000 });
        } else {
          alert(msg);
        }
        location.reload();
      }
    } catch(e) {}
  }

  function showIdlePrompt(stopTs){
    if (promptShown) return; promptShown = true;
    const msg = 'You seem inactive since ' + formatTime(new Date(stopTs)) + '. Stop the timer at that time?';
    const stopLabel = window.i18n?.messages?.stop || 'Stop';
    const snoozeLabel = window.i18n?.messages?.snooze || 'Snooze 5 min';
    const dismissLabel = window.i18n?.messages?.dismiss || 'Dismiss';

    if (window.toastManager) {
      const toastEl = document.createElement('div');
      toastEl.className = 'flex items-center gap-3 p-4 bg-amber-100 dark:bg-amber-900/30 border border-amber-300 dark:border-amber-700 rounded-lg shadow-lg pointer-events-auto';
      toastEl.innerHTML = '<div class="flex-1 text-sm text-amber-900 dark:text-amber-100">' + msg + '</div>' +
        '<div class="flex gap-2"><button class="px-3 py-1.5 bg-amber-600 hover:bg-amber-700 text-white rounded text-sm font-medium" data-act="stop">' + stopLabel + '</button>' +
        '<button class="px-3 py-1.5 bg-amber-200 dark:bg-amber-800 hover:bg-amber-300 dark:hover:bg-amber-700 text-amber-900 dark:text-amber-100 rounded text-sm font-medium" data-act="snooze">' + snoozeLabel + '</button>' +
        '<button class="px-3 py-1.5 text-amber-700 dark:text-amber-300 hover:underline text-sm" data-act="dismiss">' + dismissLabel + '</button></div>';
      toastEl.querySelector('[data-act="stop"]').addEventListener('click', function(){ toastEl.remove(); stopAt(stopTs); });
      toastEl.querySelector('[data-act="snooze"]').addEventListener('click', function(){ lastActivity = Date.now(); promptShown = false; toastEl.remove(); });
      toastEl.querySelector('[data-act="dismiss"]').addEventListener('click', function(){ toastEl.remove(); });
      const container = document.getElementById('toast-notification-container') || document.getElementById('flash-messages-container') || document.body;
      container.appendChild(toastEl);
      setTimeout(function(){ try { toastEl.remove(); } catch(e){}; promptShown = false; }, 60000);
      return;
    }

    const t = document.createElement('div');
    t.className = 'toast align-items-center text-white bg-warning border-0 fade show';
    t.innerHTML = '<div class="d-flex"><div class="toast-body">' + msg + '</div><div class="d-flex gap-2 align-items-center me-2"><button class="btn btn-sm btn-light" data-act="stop">' + stopLabel + '</button><button class="btn btn-sm btn-outline-light" data-act="snooze">' + snoozeLabel + '</button><button class="btn btn-sm btn-outline-light" data-act="dismiss">' + dismissLabel + '</button></div></div>';
    const container = document.getElementById('toast-container') || document.body;
    container.appendChild(t);
    t.querySelector('[data-act="stop"]').addEventListener('click', () => { t.remove(); stopAt(stopTs); });
    t.querySelector('[data-act="snooze"]').addEventListener('click', () => { lastActivity = Date.now(); promptShown = false; t.remove(); });
    t.querySelector('[data-act="dismiss"]').addEventListener('click', () => { t.remove(); });
    setTimeout(() => { try { t.remove(); } catch(e){}; promptShown = false; }, 60000);
  }

  async function tick(){
    const active = await getTimer();
    if (!active) return;
    const threshold = getIdleThresholdMs();
    const idleFor = Date.now() - lastActivity;
    if (idleFor >= threshold){
      const stopTs = Date.now() - idleFor;
      showIdlePrompt(stopTs);
    }
  }

  setInterval(tick, CHECK_INTERVAL_MS);
})();


