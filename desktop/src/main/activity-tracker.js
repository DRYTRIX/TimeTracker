/**
 * Privacy-first desktop activity autotracker (Phases B–D).
 *
 * Opt-in only. Samples active window app/title locally, applies exclusions,
 * retains a bounded buffer, and can push ActivityWatch-compatible events to
 * a localhost aw-server so the existing server PendingActivity pipeline works.
 *
 * See docs/design/DESKTOP_ACTIVITY_AUTOTRACKER.md
 */

'use strict';

const fs = require('fs');
const path = require('path');
const os = require('os');
const { execFile } = require('child_process');
const { promisify } = require('util');
const http = require('http');

const execFileAsync = promisify(execFile);

const DEFAULT_INTERVAL_SEC = 60;
const DEFAULT_RETENTION_DAYS = 14;
const DEFAULT_AW_HOST = '127.0.0.1';
const DEFAULT_AW_PORT = 5600;
const STORE_FILENAME = 'activity-samples.json';

let enabled = false;
let intervalHandle = null;
let storeRef = null;
let userDataPath = null;
let lastSampleKey = null;
let lastSampleAt = null;

function logDebug(msg) {
  if (process.env.TIMETRACKER_DEBUG_ACTIVITY === '1') {
    console.log(`[activity-tracker] ${msg}`);
  }
}

function getConfig() {
  const store = storeRef;
  const intervalSec = Math.max(
    15,
    Number(store?.get('activity_tracker_interval_sec', DEFAULT_INTERVAL_SEC) || DEFAULT_INTERVAL_SEC)
  );
  const exclusionsRaw = store?.get('activity_tracker_exclusions', []) || [];
  const exclusions = Array.isArray(exclusionsRaw)
    ? exclusionsRaw.map((s) => String(s || '').trim()).filter(Boolean)
    : String(exclusionsRaw || '')
        .split(/[\n,]/)
        .map((s) => s.trim())
        .filter(Boolean);
  const retentionDays = Math.max(
    1,
    Number(store?.get('activity_tracker_retention_days', DEFAULT_RETENTION_DAYS) || DEFAULT_RETENTION_DAYS)
  );
  const awSync = Boolean(store?.get('activity_tracker_aw_sync', false));
  const awHost = String(store?.get('activity_tracker_aw_host', DEFAULT_AW_HOST) || DEFAULT_AW_HOST).trim();
  const awPort = Number(store?.get('activity_tracker_aw_port', DEFAULT_AW_PORT) || DEFAULT_AW_PORT);
  return { intervalSec, exclusions, retentionDays, awSync, awHost, awPort };
}

function samplesFilePath() {
  const base = userDataPath || path.join(os.tmpdir(), 'timetracker-activity');
  return path.join(base, STORE_FILENAME);
}

function readSamples() {
  const file = samplesFilePath();
  try {
    if (!fs.existsSync(file)) return [];
    const raw = JSON.parse(fs.readFileSync(file, 'utf8'));
    return Array.isArray(raw?.samples) ? raw.samples : [];
  } catch {
    return [];
  }
}

function writeSamples(samples) {
  const file = samplesFilePath();
  const dir = path.dirname(file);
  if (!fs.existsSync(dir)) {
    fs.mkdirSync(dir, { recursive: true });
  }
  const payload = {
    updated_at: new Date().toISOString(),
    samples,
  };
  fs.writeFileSync(file, JSON.stringify(payload), { encoding: 'utf8', mode: 0o600 });
}

/**
 * Return true if app or title matches any exclusion pattern (substring, case-insensitive).
 */
function isExcluded(app, title, exclusions) {
  const haystacks = [String(app || ''), String(title || '')].map((s) => s.toLowerCase());
  for (const rule of exclusions || []) {
    const needle = String(rule || '').toLowerCase().trim();
    if (!needle) continue;
    if (haystacks.some((h) => h.includes(needle))) return true;
  }
  return false;
}

function pruneSamples(samples, retentionDays) {
  const cutoff = Date.now() - retentionDays * 24 * 60 * 60 * 1000;
  return (samples || []).filter((s) => {
    const t = Date.parse(s.timestamp || '');
    return Number.isFinite(t) && t >= cutoff;
  });
}

function execCapture(cmd, args, opts = {}) {
  return execFileAsync(cmd, args, {
    timeout: opts.timeout || 2500,
    windowsHide: true,
    maxBuffer: 1024 * 64,
    encoding: 'utf8',
  }).then(
    (r) => String(r.stdout || '').trim(),
    () => ''
  );
}

async function getActiveWindowLinux() {
  const winId = await execCapture('xdotool', ['getactivewindow']);
  if (!winId) return null;
  const title = await execCapture('xdotool', ['getwindowname', winId]);
  let app = '';
  const wmClass = await execCapture('xprop', ['-id', winId, 'WM_CLASS']);
  const match = wmClass.match(/WM_CLASS\(STRING\)\s*=\s*"([^"]*)"(?:\s*,\s*"([^"]*)")?/i);
  if (match) {
    app = match[2] || match[1] || '';
  }
  if (!app) {
    const pidOut = await execCapture('xdotool', ['getwindowpid', winId]);
    const pid = Number(pidOut);
    if (pid > 0) {
      try {
        app = fs.readFileSync(`/proc/${pid}/comm`, 'utf8').trim();
      } catch {
        /* ignore */
      }
    }
  }
  return { app: app || 'unknown', title: title || '' };
}

async function getActiveWindowMac() {
  const app = await execCapture('osascript', [
    '-e',
    'tell application "System Events" to get name of first application process whose frontmost is true',
  ]);
  if (!app) return null;
  let title = '';
  try {
    title = await execCapture('osascript', [
      '-e',
      `tell application "System Events" to tell (first process whose frontmost is true) to if (count of windows) > 0 then get name of window 1 else return ""`,
    ]);
  } catch {
    title = '';
  }
  return { app, title: title || '' };
}

async function getActiveWindowWindows() {
  // Keep PowerShell backticks out of JS template literals (they are escapes in JS).
  const script = [
    "$ErrorActionPreference = 'Stop'",
    'Add-Type @"',
    'using System;',
    'using System.Runtime.InteropServices;',
    'using System.Text;',
    'public class TtFg {',
    '  [DllImport("user32.dll")] public static extern IntPtr GetForegroundWindow();',
    '  [DllImport("user32.dll")] public static extern int GetWindowText(IntPtr hWnd, StringBuilder text, int count);',
    '  [DllImport("user32.dll")] public static extern uint GetWindowThreadProcessId(IntPtr hWnd, out uint pid);',
    '}',
    '"@',
    '$hwnd = [TtFg]::GetForegroundWindow()',
    'if ($hwnd -eq [IntPtr]::Zero) { exit 0 }',
    '$sb = New-Object System.Text.StringBuilder 512',
    '[void][TtFg]::GetWindowText($hwnd, $sb, $sb.Capacity)',
    '$pidOut = 0',
    '[void][TtFg]::GetWindowThreadProcessId($hwnd, [ref]$pidOut)',
    "$procName = ''",
    'try { $procName = (Get-Process -Id $pidOut -ErrorAction SilentlyContinue).ProcessName } catch {}',
    'Write-Output (($procName) + [char]9 + ($sb.ToString()))',
  ].join('\n');
  const out = await execCapture('powershell.exe', ['-NoProfile', '-NonInteractive', '-Command', script], {
    timeout: 4000,
  });
  if (!out) return null;
  const tab = out.indexOf('\t');
  if (tab === -1) return { app: out || 'unknown', title: '' };
  return { app: out.slice(0, tab) || 'unknown', title: out.slice(tab + 1) || '' };
}

async function getActiveWindow() {
  const platform = process.platform;
  try {
    if (platform === 'linux') return await getActiveWindowLinux();
    if (platform === 'darwin') return await getActiveWindowMac();
    if (platform === 'win32') return await getActiveWindowWindows();
  } catch (e) {
    logDebug(`capture failed: ${e.message}`);
  }
  return null;
}

function getSystemIdleSeconds() {
  try {
    const { powerMonitor } = require('electron');
    if (powerMonitor && typeof powerMonitor.getSystemIdleTime === 'function') {
      return Number(powerMonitor.getSystemIdleTime()) || 0;
    }
  } catch {
    /* not in electron or unavailable */
  }
  return 0;
}

async function sampleOnce() {
  if (!enabled) return null;
  const cfg = getConfig();
  const win = await getActiveWindow();
  if (!win) return null;

  if (isExcluded(win.app, win.title, cfg.exclusions)) {
    logDebug('sample excluded');
    return null;
  }

  const now = new Date();
  const idleSeconds = getSystemIdleSeconds();
  const idle = idleSeconds >= Math.min(cfg.intervalSec, 60);

  const key = `${win.app}\0${win.title}`;
  let durationSec = cfg.intervalSec;
  if (lastSampleKey === key && lastSampleAt) {
    durationSec = Math.max(1, Math.round((now.getTime() - lastSampleAt.getTime()) / 1000));
  }
  lastSampleKey = key;
  lastSampleAt = now;

  const sample = {
    timestamp: now.toISOString(),
    duration: durationSec,
    app: win.app,
    title: win.title,
    idle: Boolean(idle),
    synced: false,
  };

  let samples = readSamples();
  samples.push(sample);
  samples = pruneSamples(samples, cfg.retentionDays);
  writeSamples(samples);

  if (cfg.awSync && !idle) {
    try {
      await pushSamplesToActivityWatch([sample], cfg);
      sample.synced = true;
      // Mark last matching sample synced in store
      samples = readSamples().map((s) =>
        s.timestamp === sample.timestamp && s.app === sample.app && s.title === sample.title
          ? { ...s, synced: true }
          : s
      );
      writeSamples(samples);
    } catch (e) {
      logDebug(`aw sync failed: ${e.message}`);
    }
  }

  return sample;
}

function httpJson(method, host, port, urlPath, body) {
  return new Promise((resolve, reject) => {
    const payload = body == null ? null : JSON.stringify(body);
    const req = http.request(
      {
        host,
        port,
        path: urlPath,
        method,
        headers: {
          Accept: 'application/json',
          ...(payload
            ? { 'Content-Type': 'application/json', 'Content-Length': Buffer.byteLength(payload) }
            : {}),
        },
        timeout: 4000,
      },
      (res) => {
        const chunks = [];
        res.on('data', (c) => chunks.push(c));
        res.on('end', () => {
          const text = Buffer.concat(chunks).toString('utf8');
          if (res.statusCode >= 200 && res.statusCode < 300) {
            resolve({ status: res.statusCode, body: text });
          } else {
            reject(new Error(`AW HTTP ${res.statusCode}: ${text.slice(0, 200)}`));
          }
        });
      }
    );
    req.on('error', reject);
    req.on('timeout', () => {
      req.destroy();
      reject(new Error('AW request timeout'));
    });
    if (payload) req.write(payload);
    req.end();
  });
}

function bucketId() {
  const host = os.hostname().replace(/[^a-zA-Z0-9._-]/g, '-') || 'local';
  return `aw-watcher-window_${host}`;
}

async function ensureAwBucket(cfg) {
  const id = bucketId();
  try {
    await httpJson('GET', cfg.awHost, cfg.awPort, `/api/0/buckets/${encodeURIComponent(id)}`);
    return id;
  } catch {
    await httpJson('POST', cfg.awHost, cfg.awPort, `/api/0/buckets/${encodeURIComponent(id)}`, {
      client: 'timetracker-desktop',
      type: 'currentwindow',
      hostname: os.hostname(),
    });
    return id;
  }
}

/**
 * Map local samples to ActivityWatch event shape and POST to localhost aw-server.
 */
async function pushSamplesToActivityWatch(samples, cfg) {
  if (!samples || !samples.length) return { pushed: 0 };
  const id = await ensureAwBucket(cfg);
  const events = samples.map((s) => ({
    timestamp: s.timestamp,
    duration: Number(s.duration) || 1,
    data: {
      app: s.app || '',
      title: s.title || '',
      url: '',
    },
  }));
  await httpJson('POST', cfg.awHost, cfg.awPort, `/api/0/buckets/${encodeURIComponent(id)}/events`, events);
  return { pushed: events.length, bucket: id };
}

/**
 * @param {object} [options]
 * @param {object} [options.store]
 * @param {string} [options.userDataPath]
 * @param {number} [options.intervalMs]
 */
function start(options = {}) {
  storeRef = options.store || storeRef;
  userDataPath = options.userDataPath || userDataPath;

  const flagOn = storeRef ? Boolean(storeRef.get('activity_tracker_enabled', false)) : false;
  if (!flagOn) {
    stop();
    return { started: false, reason: 'feature_flag_off' };
  }

  const cfg = getConfig();
  const intervalMs =
    Number(options.intervalMs) > 0 ? Number(options.intervalMs) : cfg.intervalSec * 1000;

  enabled = true;
  if (intervalHandle) {
    clearInterval(intervalHandle);
    intervalHandle = null;
  }

  // Immediate sample then interval
  sampleOnce().catch((e) => logDebug(`initial sample: ${e.message}`));
  intervalHandle = setInterval(() => {
    sampleOnce().catch((e) => logDebug(`sample: ${e.message}`));
  }, intervalMs);

  return { started: true, intervalMs };
}

function stop() {
  enabled = false;
  lastSampleKey = null;
  lastSampleAt = null;
  if (intervalHandle) {
    clearInterval(intervalHandle);
    intervalHandle = null;
  }
  return { stopped: true };
}

function isEnabled() {
  return Boolean(enabled);
}

function getStatus() {
  const cfg = getConfig();
  const samples = readSamples();
  const unsynced = samples.filter((s) => !s.synced).length;
  return {
    enabled: isEnabled(),
    flag: storeRef ? Boolean(storeRef.get('activity_tracker_enabled', false)) : false,
    intervalSec: cfg.intervalSec,
    exclusions: cfg.exclusions,
    retentionDays: cfg.retentionDays,
    awSync: cfg.awSync,
    awHost: cfg.awHost,
    awPort: cfg.awPort,
    sampleCount: samples.length,
    unsyncedCount: unsynced,
    lastSampleAt: samples.length ? samples[samples.length - 1].timestamp : null,
    storePath: samplesFilePath(),
  };
}

function purgeLocal() {
  writeSamples([]);
  lastSampleKey = null;
  lastSampleAt = null;
  return { purged: true, sampleCount: 0 };
}

function listSamples(limit = 50) {
  const samples = readSamples();
  const n = Math.max(1, Math.min(500, Number(limit) || 50));
  return samples.slice(-n);
}

async function syncNow() {
  const cfg = getConfig();
  const samples = readSamples().filter((s) => !s.synced && !s.idle);
  if (!samples.length) return { pushed: 0, message: 'Nothing to sync' };
  const result = await pushSamplesToActivityWatch(samples, cfg);
  const syncedKeys = new Set(samples.map((s) => `${s.timestamp}|${s.app}|${s.title}`));
  const next = readSamples().map((s) =>
    syncedKeys.has(`${s.timestamp}|${s.app}|${s.title}`) ? { ...s, synced: true } : s
  );
  writeSamples(next);
  return { ...result, message: `Pushed ${result.pushed} events to ActivityWatch` };
}

function restart(options = {}) {
  stop();
  return start({ store: storeRef, userDataPath, ...options });
}

module.exports = {
  start,
  stop,
  restart,
  isEnabled,
  getStatus,
  purgeLocal,
  listSamples,
  syncNow,
  sampleOnce,
  // Test helpers
  isExcluded,
  pruneSamples,
  getConfig,
};
