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

test('loginWithPassword returns REQUIRES_2FA when server asks for TOTP', async () => {
  globalThis.fetch = async () => ({
    ok: false,
    status: 403,
    text: async () =>
      JSON.stringify({
        requires_2fa: true,
        temp_token: 'tmp_abc',
        error: 'Two-factor authentication required.',
      }),
  });

  const result = await ApiClient.loginWithPassword('https://tracker.test', 'alice', 'secret');
  assert.equal(result.ok, false);
  assert.equal(result.code, 'REQUIRES_2FA');
  assert.equal(result.requires_2fa, true);
  assert.equal(result.temp_token, 'tmp_abc');

  delete globalThis.fetch;
});

test('verifyLogin2fa posts temp_token and code then returns API token', async () => {
  const calls = [];
  globalThis.fetch = async (url, init) => {
    calls.push({ url, init });
    return {
      ok: true,
      status: 200,
      text: async () => JSON.stringify({ token: 'tt_final' }),
    };
  };

  const result = await ApiClient.verifyLogin2fa('https://tracker.test', 'tmp_abc', '123456');
  assert.equal(result.ok, true);
  assert.equal(result.token, 'tt_final');
  assert.equal(calls[0].url, 'https://tracker.test/api/v1/auth/2fa/verify');
  const body = JSON.parse(calls[0].init.body);
  assert.equal(body.temp_token, 'tmp_abc');
  assert.equal(body.code, '123456');

  delete globalThis.fetch;
});

test('suggestProjectFromUrl matches project name substring in hostname/path', async () => {
  const { suggestProjectFromUrl } = await import('../lib/url_suggest.js');
  const projects = [
    { id: 1, name: 'Acme Website', code: 'ACME' },
    { id: 2, name: 'Internal', code: null },
  ];
  assert.equal(suggestProjectFromUrl('https://acme.example.com/dashboard', projects)?.id, 1);
  assert.equal(suggestProjectFromUrl('https://example.com/acme-website/tickets', projects)?.id, 1);
  assert.equal(suggestProjectFromUrl('https://other.example.com/', projects), null);
});
