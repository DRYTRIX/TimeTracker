export function formatDuration(totalSeconds) {
  const hours = Math.floor(totalSeconds / 3600);
  const minutes = Math.floor((totalSeconds % 3600) / 60);
  const seconds = totalSeconds % 60;
  if (hours) return `${hours}h ${minutes}m`;
  return `${minutes}m ${seconds}s`;
}

export function formatMinutes(minutes) {
  if (!minutes) return '0m';
  const h = Math.floor(minutes / 60);
  const m = minutes % 60;
  return h ? `${h}h ${m}m` : `${m}m`;
}

/** Elapsed seconds for an active timer, respecting pause / break_seconds. */
export function timerElapsedSeconds(timerPayload) {
  const timer = timerPayload?.timer || timerPayload;
  if (!timer?.start_time) return 0;
  const start = new Date(timer.start_time).getTime();
  const breakSec = Number(timer.break_seconds || 0);
  const end = timer.paused_at ? new Date(timer.paused_at).getTime() : Date.now();
  return Math.max(0, Math.floor((end - start) / 1000) - breakSec);
}

export function isTimerPaused(timerPayload) {
  const timer = timerPayload?.timer || timerPayload;
  return Boolean(timer?.paused_at);
}

export function todayISO() {
  return new Date().toISOString().slice(0, 10);
}

export function daysAgoISO(days) {
  const d = new Date();
  d.setDate(d.getDate() - days);
  return d.toISOString().slice(0, 10);
}

export function listItems(payload, ...keys) {
  if (!payload) return [];
  for (const key of keys) {
    if (Array.isArray(payload[key])) return payload[key];
  }
  if (Array.isArray(payload.items)) return payload.items;
  if (Array.isArray(payload)) return payload;
  return [];
}
