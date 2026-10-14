import test from 'node:test';
import assert from 'node:assert/strict';
import { buildAuthHeaders, ApiClient, normalizeServerUrl } from '../lib/api.js';

test('buildAuthHeaders adds Bearer token and Accept', () => {
  const headers = buildAuthHeaders('tt_secret', { 'Content-Type': 'application/json' });
  assert.equal(headers.Authorization, 'Bearer tt_secret');
  assert.equal(headers.Accept, 'application/json');
  assert.equal(headers['Content-Type'], 'application/json');
});

test('buildAuthHeaders omits Authorization when token is empty', () => {
  const headers = buildAuthHeaders(null);
  assert.equal(headers.Authorization, undefined);
  assert.equal(headers.Accept, 'application/json');
});

test('normalizeServerUrl adds https scheme', () => {
  assert.equal(normalizeServerUrl('example.com'), 'https://example.com');
});

test('ApiClient.startTimer posts expected body', async () => {
  const calls = [];
  globalThis.fetch = async (url, init) => {
    calls.push({ url, init });
    return {
      ok: true,
      text: async () => JSON.stringify({ timer: { id: 1, start_time: '2026-01-01T00:00:00Z' } }),
    };
  };

  const client = new ApiClient('https://tracker.test', 'tt_demo');
  await client.startTimer({ projectId: 42, taskId: 7, notes: 'focus' });

  assert.equal(calls.length, 1);
  assert.equal(calls[0].url, 'https://tracker.test/api/v1/timer/start');
  assert.equal(calls[0].init.method, 'POST');
  assert.equal(calls[0].init.headers.Authorization, 'Bearer tt_demo');
  const body = JSON.parse(calls[0].init.body);
  assert.equal(body.project_id, 42);
  assert.equal(body.task_id, 7);
  assert.equal(body.notes, 'focus');

  delete globalThis.fetch;
});

test('ApiClient.stopTimer posts stop_time when provided', async () => {
  const calls = [];
  globalThis.fetch = async (url, init) => {
    calls.push({ url, init });
    return {
      ok: true,
      text: async () => JSON.stringify({ time_entry: { id: 99 } }),
    };
  };

  const client = new ApiClient('https://tracker.test/', 'tt_demo');
  await client.stopTimer({ stopTime: '2026-01-01T12:00:00Z' });

  assert.equal(calls[0].url, 'https://tracker.test/api/v1/timer/stop');
  const body = JSON.parse(calls[0].init.body);
  assert.equal(body.stop_time, '2026-01-01T12:00:00Z');

  delete globalThis.fetch;
});

test('getSummary builds date-range query', async () => {
  const calls = [];
  globalThis.fetch = async (url, init) => {
    calls.push({ url, init });
    return { ok: true, text: async () => JSON.stringify({ summary: {} }) };
  };

  const client = new ApiClient('https://tracker.test', 'tt_demo');
  await client.getSummary({ startDate: '2026-10-13', endDate: '2026-10-13' });

  assert.equal(calls[0].url, 'https://tracker.test/api/v1/reports/summary?start_date=2026-10-13&end_date=2026-10-13');

  delete globalThis.fetch;
});

test('getTimeEntries passes range, paging and include_active flags', async () => {
  const calls = [];
  globalThis.fetch = async (url, init) => {
    calls.push({ url, init });
    return { ok: true, text: async () => JSON.stringify({ time_entries: [] }) };
  };

  const client = new ApiClient('https://tracker.test', 'tt_demo');
  await client.getTimeEntries({
    startDate: '2026-10-07',
    endDate: '2026-10-13',
    perPage: 200,
    includeActive: true,
  });

  const url = new URL(calls[0].url);
  assert.equal(url.pathname, '/api/v1/time-entries');
  assert.equal(url.searchParams.get('start_date'), '2026-10-07');
  assert.equal(url.searchParams.get('end_date'), '2026-10-13');
  assert.equal(url.searchParams.get('per_page'), '200');
  assert.equal(url.searchParams.get('include_active'), 'true');

  delete globalThis.fetch;
});

test('getWeeklyGoals forwards status filter', async () => {
  const calls = [];
  globalThis.fetch = async (url, init) => {
    calls.push({ url, init });
    return { ok: true, text: async () => JSON.stringify({ weekly_goals: [] }) };
  };

  const client = new ApiClient('https://tracker.test', 'tt_demo');
  await client.getWeeklyGoals({ status: 'active' });

  assert.equal(calls[0].url, 'https://tracker.test/api/v1/weekly-goals?status=active');

  delete globalThis.fetch;
});

test('updateTimeEntry PATCHes partial fields on the entry', async () => {
  const calls = [];
  globalThis.fetch = async (url, init) => {
    calls.push({ url, init });
    return { ok: true, text: async () => JSON.stringify({ time_entry: { id: 501 } }) };
  };

  const client = new ApiClient('https://tracker.test', 'tt_demo');
  await client.updateTimeEntry(501, { notes: 'Design review — updated' });

  assert.equal(calls[0].url, 'https://tracker.test/api/v1/time-entries/501');
  assert.equal(calls[0].init.method, 'PATCH');
  const body = JSON.parse(calls[0].init.body);
  assert.equal(body.notes, 'Design review — updated');

  delete globalThis.fetch;
});
