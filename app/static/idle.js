// Idle detection: when user is inactive, offer to stop timer at last active time
(function(){
  if (window.__ttIdleLoaded) return; window.__ttIdleLoaded = true;
  const IDLE_THRESHOLD_MS = 5 * 60 * 1000; // 5 minutes
  const CHECK_INTERVAL_MS = 60 * 1000; // 1 minute

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
      if (r.ok){ showToast(window.i18n?.messages?.timerStoppedInactivity || 'Timer stopped due to inactivity', 'warning'); location.reload(); }
    } catch(e) {}
  }

  function showIdlePrompt(stopTs){
    if (promptShown) return; promptShown = true;
    // Create a lightweight inline prompt toast
    const t = document.createElement('div');
    t.className = 'toast align-items-center text-white bg-warning border-0 fade show';
    t.innerHTML = `<div class="d-flex"><div class="toast-body">You seem inactive since ${formatTime(new Date(stopTs))}. Stop the timer at that time?</div><div class="d-flex gap-2 align-items-center me-2"><button class="btn btn-sm btn-light" data-act="stop">Stop</button><button class="btn btn-sm btn-outline-light" data-act="dismiss">Dismiss</button></div></div>`;
    const container = document.getElementById('toast-container') || document.body;
    container.appendChild(t);
    t.querySelector('[data-act="stop"]').addEventListener('click', () => { t.remove(); stopAt(stopTs); });
    t.querySelector('[data-act="dismiss"]').addEventListener('click', () => { t.remove(); });
    setTimeout(() => { try { t.remove(); } catch(e){} }, 60_000);
  }

  async function tick(){
    const active = await getTimer();
    if (!active) return;
    const idleFor = Date.now() - lastActivity;
    if (idleFor >= IDLE_THRESHOLD_MS){
      const stopTs = Date.now() - idleFor; // last active time
      showIdlePrompt(stopTs);
    }
  }

  setInterval(tick, CHECK_INTERVAL_MS);
})();


