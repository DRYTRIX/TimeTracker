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
