/**
 * Pure formatting/grouping helpers shared by popup, options and tests.
 * No DOM or chrome.* dependencies.
 */

/** Apple-style palette assigned deterministically per project id. */
const PROJECT_PALETTE = [
  '#5856d6', // indigo
  '#ff2d55', // pink
  '#30b0c7', // teal
  '#ff9f0a', // orange
  '#34c759', // green
  '#bf5af2', // purple
  '#64d2ff', // cyan
  '#ff9500', // amber
];

export function colorForProject(projectId) {
  const id = Number(projectId);
  if (!Number.isFinite(id)) return PROJECT_PALETTE[0];
  return PROJECT_PALETTE[Math.abs(id) % PROJECT_PALETTE.length];
}

function pad2(n) {
  return String(n).padStart(2, '0');
}

/** h:mm:ss when hours > 0, otherwise m:ss (mockup style). */
export function formatClock(totalSeconds) {
  const s = Math.max(0, Math.floor(totalSeconds || 0));
  const h = Math.floor(s / 3600);
  const m = Math.floor((s % 3600) / 60);
  const sec = s % 60;
  return h > 0 ? `${h}:${pad2(m)}:${pad2(sec)}` : `${m}:${pad2(sec)}`;
}

/** "5:12" style hours:minutes for stats. */
export function formatHM(totalSeconds) {
  const s = Math.max(0, Math.floor(totalSeconds || 0));
  const h = Math.floor(s / 3600);
  const m = Math.floor((s % 3600) / 60);
  return `${h}:${pad2(m)}`;
}

/** Local YYYY-MM-DD for API date filters. */
export function localDateKey(date) {
  const d = date instanceof Date ? date : new Date(date);
  return `${d.getFullYear()}-${pad2(d.getMonth() + 1)}-${pad2(d.getDate())}`;
}

export function addDays(date, days) {
  const d = new Date(date.getTime());
  d.setDate(d.getDate() + days);
  return d;
}

const WEEKDAY_LETTERS = ['S', 'M', 'T', 'W', 'T', 'F', 'S'];

export function weekdayLetter(date) {
  const d = date instanceof Date ? date : new Date(date);
  return WEEKDAY_LETTERS[d.getDay()];
}

const WEEKDAY_LONG = ['Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday'];

/** "13:02" from an ISO-ish datetime string, rendered in local time. */
export function formatTimeOf(iso) {
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return '';
  return `${pad2(d.getHours())}:${pad2(d.getMinutes())}`;
}

/** Elapsed work seconds for a time-entry dict (running or finished). */
export function entryDurationSeconds(entry, now = Date.now()) {
  if (!entry) return 0;
  if (entry.duration_seconds != null && !entry.is_active) return Number(entry.duration_seconds) || 0;
  const start = Date.parse(entry.start_time || '');
  if (Number.isNaN(start)) return 0;
  const endRef = entry.paused_at ? Date.parse(entry.paused_at) : now;
  if (Number.isNaN(endRef)) return 0;
  const breakSec = Number(entry.break_seconds) || 0;
  return Math.max(0, Math.floor((endRef - start) / 1000) - breakSec);
}

/**
 * Group time entries into display buckets, newest first.
 * Returns [{ key, label, entries: [...] }] with Today/Yesterday/weekday labels.
 */
export function groupEntriesByDay(entries, now = new Date()) {
  const todayKey = localDateKey(now);
  const yesterdayKey = localDateKey(addDays(now, -1));
  const buckets = new Map();

  const sorted = [...(entries || [])].sort((a, b) => {
    const at = Date.parse(a?.start_time || '') || 0;
    const bt = Date.parse(b?.start_time || '') || 0;
    return bt - at;
  });

  for (const entry of sorted) {
    const start = new Date(entry?.start_time || '');
    if (Number.isNaN(start.getTime())) continue;
    const key = localDateKey(start);
    if (!buckets.has(key)) {
      let label;
      if (key === todayKey) label = 'Today';
      else if (key === yesterdayKey) label = 'Yesterday';
      else label = WEEKDAY_LONG[start.getDay()];
      buckets.set(key, { key, label, entries: [] });
    }
    buckets.get(key).entries.push(entry);
  }

  return Array.from(buckets.values());
}

/** Sum worked hours per local day for the last `days` days, oldest first. */
export function dailyTotals(entries, days = 7, now = new Date()) {
  const out = [];
  const byDay = new Map();
  for (const entry of entries || []) {
    const start = new Date(entry?.start_time || '');
    if (Number.isNaN(start.getTime())) continue;
    const key = localDateKey(start);
    const hours = entryDurationSeconds(entry, now.getTime()) / 3600;
    byDay.set(key, (byDay.get(key) || 0) + hours);
  }
  for (let i = days - 1; i >= 0; i--) {
    const date = addDays(now, -i);
    const key = localDateKey(date);
    out.push({ date, key, letter: weekdayLetter(date), hours: byDay.get(key) || 0 });
  }
  return out;
}

/** Unique, non-trivial note strings from entries, preserving recency order. */
export function noteSuggestions(entries, limit = 3) {
  const seen = new Set();
  const out = [];
  for (const entry of entries || []) {
    const note = String(entry?.notes || '').trim();
    const key = note.toLowerCase();
    if (note.length < 3 || seen.has(key)) continue;
    seen.add(key);
    out.push(note);
    if (out.length >= limit) break;
  }
  return out;
}
