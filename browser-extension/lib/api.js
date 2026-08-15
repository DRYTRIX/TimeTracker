/**
 * TimeTracker /api/v1 client for the browser extension.
 * Mirrors desktop/mobile: Bearer tt_… tokens, no session cookies.
 */

export function normalizeServerUrl(value) {
  let url = String(value || '').trim();
  if (!url) return '';
  if (!/^https?:\/\//i.test(url)) url = `https://${url}`;
  return url.replace(/\/+$/, '');
}

export function originFromServerUrl(serverUrl) {
  const normalized = normalizeServerUrl(serverUrl);
  if (!normalized) return null;
  try {
    return new URL(normalized).origin + '/*';
  } catch {
    return null;
  }
}

function isInfoPayload(data) {
  return data && typeof data === 'object' && data.api_version === 'v1' && typeof data.endpoints === 'object';
}

export function classifyError(error, response, data) {
  if (response) {
    const status = response.status;
    if (status === 401) {
      return { ok: false, code: 'UNAUTHORIZED', message: 'Authentication failed. Sign in again.', status };
    }
    if (status === 403) {
      return { ok: false, code: 'FORBIDDEN', message: data?.error || 'Access denied for this account.', status };
    }
    if (status === 409) {
      return {
        ok: false,
        code: data?.error_code || 'CONFLICT',
        message: data?.error || data?.message || 'Conflict',
        status,
        data,
      };
    }
    if (status === 400) {
      return {
        ok: false,
        code: data?.error_code || 'VALIDATION',
        message: data?.error || data?.message || 'Request failed',
        status,
        data,
      };
    }
    if (status >= 500) {
      return { ok: false, code: 'SERVER_ERROR', message: 'Server error. Try again later.', status };
    }
    return {
      ok: false,
      code: `HTTP_${status}`,
      message: data?.error || data?.message || `Server returned HTTP ${status}`,
      status,
      data,
    };
  }
  if (error?.name === 'AbortError') {
    return { ok: false, code: 'TIMEOUT', message: 'Request timed out. Check URL, VPN, or firewall.' };
  }
  return {
    ok: false,
    code: 'NETWORK',
    message: 'Server not reachable. Check the URL, VPN, firewall, and that TimeTracker is running.',
  };
}

async function parseJsonSafe(response) {
  const text = await response.text();
  if (!text) return null;
  try {
    return JSON.parse(text);
  } catch {
    return null;
  }
}

export class ApiClient {
  constructor(baseUrl, token = null, options = {}) {
    this.baseUrl = normalizeServerUrl(baseUrl);
    this.token = token;
    this.timeoutMs = options.timeoutMs || 15000;
  }

  static normalizeBaseUrl(url) {
    return normalizeServerUrl(url);
  }

  async request(method, path, body = undefined) {
    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), this.timeoutMs);
    const headers = {
      Accept: 'application/json',
    };
    if (body !== undefined) headers['Content-Type'] = 'application/json';
    if (this.token) headers.Authorization = `Bearer ${this.token}`;

    try {
      const response = await fetch(`${this.baseUrl}${path}`, {
        method,
        headers,
        body: body !== undefined ? JSON.stringify(body) : undefined,
        signal: controller.signal,
      });
      const data = await parseJsonSafe(response);
      if (!response.ok) {
        throw Object.assign(new Error('api_error'), { response, data });
      }
      return data;
    } catch (error) {
      if (error.response) {
        const classified = classifyError(error, error.response, error.data);
        const err = new Error(classified.message);
        Object.assign(err, classified);
        throw err;
      }
      const classified = classifyError(error);
      const err = new Error(classified.message);
      Object.assign(err, classified);
      throw err;
    } finally {
      clearTimeout(timer);
    }
  }

  static async testPublicServerInfo(baseUrl) {
    const normalized = normalizeServerUrl(baseUrl);
    if (!normalized) return { ok: false, code: 'NO_URL', message: 'Please enter a server URL.' };
    try {
      const parsed = new URL(normalized);
      if (parsed.protocol !== 'http:' && parsed.protocol !== 'https:') {
        return { ok: false, code: 'BAD_URL', message: 'Server URL must start with http:// or https://.' };
      }
    } catch {
      return { ok: false, code: 'BAD_URL', message: 'Server URL is not valid.' };
    }

    const client = new ApiClient(normalized);
    try {
      const data = await client.request('GET', '/api/v1/info');
      if (!isInfoPayload(data)) {
        return {
          ok: false,
          code: 'NOT_TIMETRACKER',
          message: 'This address did not return a TimeTracker API response. Use the base URL only.',
        };
      }
      if (data.setup_required === true) {
        return {
          ok: false,
          code: 'SETUP_REQUIRED',
          message: 'TimeTracker is not fully set up yet. Finish setup in a browser first.',
        };
      }
      return { ok: true, app_version: data.app_version || null, timezone: data.timezone || null };
    } catch (error) {
      return {
        ok: false,
        code: error.code || 'NETWORK',
        message: error.message || 'Could not reach server.',
      };
    }
  }

  static async loginWithPassword(baseUrl, username, password) {
    const normalized = normalizeServerUrl(baseUrl);
    const client = new ApiClient(normalized);
    try {
      const data = await client.request('POST', '/api/v1/auth/login', { username, password });
      const token = data?.token;
      if (typeof token !== 'string' || !token.startsWith('tt_')) {
        return { ok: false, code: 'INVALID_RESPONSE', message: 'Login did not return a valid API token.' };
      }
      return { ok: true, token };
    } catch (error) {
      return {
        ok: false,
        code: error.code || 'NETWORK',
        message: error.message || 'Login failed.',
        status: error.status,
      };
    }
  }

  async validateSession() {
    try {
      const data = await this.request('GET', '/api/v1/users/me');
      if (data?.user) return { ok: true, user: data.user };
      return { ok: false, code: 'INVALID_RESPONSE', message: 'Server returned an invalid user payload.' };
    } catch (error) {
      if (error.status === 403) {
        try {
          await this.request('GET', '/api/v1/timer/status');
          return { ok: true };
        } catch (fallbackError) {
          return {
            ok: false,
            code: fallbackError.code || 'FORBIDDEN',
            message: fallbackError.message || 'Access denied.',
          };
        }
      }
      return {
        ok: false,
        code: error.code || 'NETWORK',
        message: error.message || 'Session validation failed.',
        status: error.status,
      };
    }
  }

  getTimerStatus() {
    return this.request('GET', '/api/v1/timer/status');
  }

  startTimer({ projectId = null, clientId = null, taskId = null, notes = '' }) {
    const body = {};
    if (projectId) body.project_id = projectId;
    if (clientId) body.client_id = clientId;
    if (taskId) body.task_id = taskId;
    if (notes) body.notes = notes;
    return this.request('POST', '/api/v1/timer/start', body);
  }

  pauseTimer() {
    return this.request('POST', '/api/v1/timer/pause');
  }

  resumeTimer() {
    return this.request('POST', '/api/v1/timer/resume');
  }

  stopTimer({ stopTime = null } = {}) {
    const body = {};
    if (stopTime) body.stop_time = stopTime;
    return this.request('POST', '/api/v1/timer/stop', Object.keys(body).length ? body : undefined);
  }

  sendHeartbeat() {
    return this.request('POST', '/api/v1/timer/heartbeat');
  }

  getProjects(params = {}) {
    const qs = new URLSearchParams();
    if (params.status) qs.set('status', params.status);
    if (params.client_id) qs.set('client_id', String(params.client_id));
    if (params.page) qs.set('page', String(params.page));
    if (params.per_page) qs.set('per_page', String(params.per_page));
    const q = qs.toString();
    return this.request('GET', `/api/v1/projects${q ? `?${q}` : ''}`);
  }

  /** Fetch every page of projects matching the given filters. */
  async getAllProjects(params = {}) {
    const perPage = params.per_page || 100;
    let page = 1;
    const byId = new Map();
    while (true) {
      const resp = await this.getProjects({ ...params, per_page: perPage, page });
      for (const p of resp?.projects || []) {
        if (p && p.id != null && !byId.has(p.id)) {
          byId.set(p.id, p);
        }
      }
      const pages = resp?.pagination?.pages ?? 1;
      if (page >= pages) break;
      page += 1;
    }
    return { projects: Array.from(byId.values()) };
  }

  createProject({ name, clientId = null, description }) {
    const body = { name };
    if (clientId) body.client_id = clientId;
    if (description) body.description = description;
    return this.request('POST', '/api/v1/projects', body);
  }

  getTasks(params = {}) {
    const qs = new URLSearchParams();
    if (params.project_id) qs.set('project_id', String(params.project_id));
    if (params.status) qs.set('status', params.status);
    if (params.page) qs.set('page', String(params.page));
    if (params.per_page) qs.set('per_page', String(params.per_page));
    const q = qs.toString();
    return this.request('GET', `/api/v1/tasks${q ? `?${q}` : ''}`);
  }

  createTask({ name, projectId, description }) {
    const body = { name, project_id: projectId };
    if (description) body.description = description;
    return this.request('POST', '/api/v1/tasks', body);
  }

  getClients(params = {}) {
    const qs = new URLSearchParams();
    if (params.page) qs.set('page', String(params.page));
    if (params.per_page) qs.set('per_page', String(params.per_page));
    const q = qs.toString();
    return this.request('GET', `/api/v1/clients${q ? `?${q}` : ''}`);
  }

  createClient({ name, email, company }) {
    const body = { name };
    if (email) body.email = email;
    if (company) body.company = company;
    return this.request('POST', '/api/v1/clients', body);
  }

  getFavoriteProjects() {
    return this.request('GET', '/api/v1/users/me/favorites/projects');
  }

  getUsersMe() {
    return this.request('GET', '/api/v1/users/me');
  }
}

/** Elapsed work seconds from a timer payload (respects break_seconds and paused_at). */
export function elapsedSecondsFromTimer(timer, now = Date.now()) {
  if (!timer?.start_time) return 0;
  const start = Date.parse(timer.start_time);
  if (Number.isNaN(start)) return 0;
  const endRef = timer.paused_at ? Date.parse(timer.paused_at) : now;
  if (Number.isNaN(endRef)) return 0;
  const breakSec = Number(timer.break_seconds) || 0;
  return Math.max(0, Math.floor((endRef - start) / 1000) - breakSec);
}

/** Format as HHh:MMm (issue #700). */
export function formatElapsedHhMm(totalSeconds) {
  const s = Math.max(0, Math.floor(totalSeconds || 0));
  const hours = Math.floor(s / 3600);
  const minutes = Math.floor((s % 3600) / 60);
  return `${String(hours).padStart(2, '0')}h:${String(minutes).padStart(2, '0')}m`;
}

/** Compact badge text, e.g. "1:23" or "12h". */
export function formatBadgeText(totalSeconds) {
  const s = Math.max(0, Math.floor(totalSeconds || 0));
  const hours = Math.floor(s / 3600);
  const minutes = Math.floor((s % 3600) / 60);
  if (hours >= 10) return `${hours}h`;
  if (hours > 0) return `${hours}:${String(minutes).padStart(2, '0')}`;
  return `:${String(minutes).padStart(2, '0')}`;
}
