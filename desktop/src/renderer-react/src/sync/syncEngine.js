import Dexie from 'dexie';

const db = new Dexie('TimeTrackerDesktop');

db.version(1).stores({
  projects: 'id,name,status,updated_at',
  tasks: 'id,project_id,name,status,updated_at',
  timeEntries: 'id,project_id,task_id,date,updated_at',
  queue: '++id,type,createdAt,status',
  meta: 'key',
});

/** After this many failed sync attempts, queue items are marked `failed`. */
export const MAX_SYNC_ATTEMPTS = 8;

function newIdempotencyKey() {
  if (typeof crypto !== 'undefined' && crypto.randomUUID) {
    return crypto.randomUUID();
  }
  return `desktop-${Date.now()}-${Math.random().toString(16).slice(2)}`;
}

function errorMessage(error) {
  if (error?.response?.data?.error) return String(error.response.data.error);
  if (error?.message) return error.message;
  return String(error);
}

function httpStatus(error) {
  return error?.response?.status ?? null;
}

async function getQueueDepth() {
  return db.queue.where('status').equals('pending').count();
}

export function createSyncEngine({ apiClient, settings, onStatus, onToast, onRefresh }) {
  let interval = null;
  let stopped = false;

  async function publish(partial = {}) {
    const [queueDepth, lastSyncAt, lastError] = await Promise.all([
      getQueueDepth(),
      db.meta.get('lastSyncAt'),
      db.meta.get('lastError'),
    ]);
    onStatus({
      queueDepth,
      syncing: false,
      lastSyncAt: lastSyncAt?.value || null,
      lastError: lastError?.value || '',
      ...partial,
    });
  }

  async function queueOperation(type, payload) {
    const item = {
      type,
      payload: { ...(payload || {}) },
      status: 'pending',
      attempts: 0,
      createdAt: Date.now(),
      updatedAt: Date.now(),
    };
    if (type === 'time_entry_create' && !item.payload.idempotencyKey) {
      item.payload.idempotencyKey = newIdempotencyKey();
    }
    await db.queue.add(item);
    await publish();
  }

  async function cacheReadData({ projects = [], tasks = [], timeEntries = [] }) {
    await db.transaction('rw', db.projects, db.tasks, db.timeEntries, async () => {
      if (projects.length) await db.projects.bulkPut(projects);
      if (tasks.length) await db.tasks.bulkPut(tasks);
      if (timeEntries.length) await db.timeEntries.bulkPut(timeEntries);
    });
    await publish();
  }

  async function processItem(item) {
    const payload = item.payload || {};
    if (item.type === 'time_entry_create') {
      const { idempotencyKey, ...body } = payload;
      await apiClient.createTimeEntry(body, { idempotencyKey });
    } else if (item.type === 'time_entry_update') {
      await apiClient.updateTimeEntry(payload.id, payload.data || {});
    } else if (item.type === 'time_entry_delete') {
      await apiClient.deleteTimeEntry(payload.id);
    } else if (item.type === 'timer_start') {
      await apiClient.startTimer(payload);
    } else if (item.type === 'timer_stop') {
      await apiClient.stopTimer(payload);
    }
  }

  async function syncNow() {
    if (stopped || !navigator.onLine) {
      await publish({ syncing: false });
      return;
    }
    await publish({ syncing: true, lastError: '' });
    try {
      const items = await db.queue.where('status').equals('pending').sortBy('createdAt');
      let syncedCount = 0;
      let lastError = '';

      for (const item of items) {
        await db.queue.update(item.id, { status: 'syncing', updatedAt: Date.now() });
        try {
          await processItem(item);
          await db.queue.delete(item.id);
          syncedCount += 1;
        } catch (error) {
          const status = httpStatus(error);
          if (item.type === 'time_entry_update' && status === 409) {
            await db.queue.delete(item.id);
            continue;
          }

          const attempts = (item.attempts || 0) + 1;
          const failed = attempts >= MAX_SYNC_ATTEMPTS;
          const msg = errorMessage(error);
          await db.queue.update(item.id, {
            status: failed ? 'failed' : 'pending',
            attempts,
            lastError: msg,
            updatedAt: Date.now(),
          });
          lastError = failed
            ? `Sync gave up after ${MAX_SYNC_ATTEMPTS} attempts: ${msg}`
            : msg;
        }
      }

      await db.meta.put({ key: 'lastSyncAt', value: Date.now() });
      await db.meta.put({ key: 'lastError', value: lastError });
      await publish({ syncing: false, lastError });
      if (syncedCount) {
        onToast?.(`Synced ${syncedCount} queued change${syncedCount === 1 ? '' : 's'}`, 'success');
        await onRefresh?.();
      } else if (lastError) {
        onToast?.('Sync failed. Changes remain queued.', 'error');
      }
    } catch (error) {
      const msg = errorMessage(error);
      await db.meta.put({ key: 'lastError', value: msg });
      await publish({ syncing: false, lastError: msg });
      onToast?.('Sync failed. Changes remain queued.', 'error');
    }
  }

  function start() {
    stopped = false;
    publish();
    window.addEventListener('online', syncNow);
    if (settings.autoSync) {
      interval = window.setInterval(syncNow, Math.max(10, Number(settings.syncInterval || 60)) * 1000);
    }
    syncNow();
  }

  function stop() {
    stopped = true;
    window.removeEventListener('online', syncNow);
    if (interval) window.clearInterval(interval);
  }

  async function clearAll() {
    await db.transaction('rw', db.projects, db.tasks, db.timeEntries, db.queue, db.meta, async () => {
      await Promise.all([db.projects.clear(), db.tasks.clear(), db.timeEntries.clear(), db.queue.clear(), db.meta.clear()]);
    });
    await publish();
  }

  return {
    start,
    stop,
    syncNow,
    queueOperation,
    cacheReadData,
    clearAll,
  };
}
