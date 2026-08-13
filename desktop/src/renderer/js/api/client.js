const axios = require('axios');
// In renderer, config is provided by shared/config.js (loaded before bundle). In Node (tests), use require.
const cfg = (typeof window !== 'undefined' && window.config) ? window.config : (function() { try { return require('../../../shared/config'); } catch (_) { return {}; } })();
const storeGet = cfg.storeGet || (async (k) => null);
const storeSet = cfg.storeSet || (async (k, v) => {});

/** @typedef {{ ok: true }} OkResult */
/** @typedef {{ ok: false, code: string, message: string }} ErrResult */
/** @typedef {OkResult | ErrResult} ValidationResult */

function isTlsRelatedError(error) {
  const code = error && error.code;
  const msg = (error && error.message) || '';
  const tlsCodes = new Set([
    'DEPTH_ZERO_SELF_SIGNED_CERT',
    'CERT_HAS_EXPIRED',
    'CERT_NOT_YET_VALID',
    'UNABLE_TO_VERIFY_LEAF_SIGNATURE',
    'ERR_TLS_CERT_ALTNAME_INVALID',
    'SELF_SIGNED_CERT_IN_CHAIN',
    'UNABLE_TO_GET_ISSUER_CERT_LOCALLY',
  ]);
  if (code && tlsCodes.has(code)) return true;
  if (/certificate|ssl|tls|UNABLE_TO_VERIFY/i.test(msg)) return true;
  return false;
}

/**
 * Map axios/network errors to a stable code + user-facing message.
 * @param {import('axios').AxiosError} error
 * @returns {{ code: string, message: string }}
 */
function classifyAxiosError(error) {
  if (isTlsRelatedError(error)) {
    return {
      code: 'TLS',
      message:
        'SSL/TLS certificate could not be verified. If the server uses a self-signed certificate, install a trusted CA or use http:// only on trusted networks.',
    };
  }
  if (error.response) {
    const status = error.response.status;
    const data = error.response.data;
    if (status === 401) {
      return {
        code: 'UNAUTHORIZED',
        message: 'Authentication failed. Sign in again.',
      };
    }
    if (status === 403) {
      return {
        code: 'FORBIDDEN',
        message: 'Access denied. Your token may not have the required permissions (e.g. read:users).',
      };
    }
    if (status === 404) {
      return {
        code: 'NOT_FOUND',
        message: data?.error || 'Resource not found. Is the base URL correct (no extra path)?',
      };
    }
    if (status >= 500) {
      return { code: 'SERVER_ERROR', message: 'Server error. Please try again later.' };
    }
    if (data && typeof data === 'object' && data.error) {
      return { code: 'HTTP_' + status, message: String(data.error) };
    }
    return { code: 'HTTP_' + status, message: `Server returned HTTP ${status}.` };
  }
  if (error.code === 'ECONNABORTED' || error.code === 'ETIMEDOUT') {
    return {
      code: 'TIMEOUT',
      message: 'Request timed out. Check the server URL, firewall, and network.',
    };
  }
  if (error.code === 'ENOTFOUND') {
    return {
      code: 'DNS',
      message: 'Host not found (DNS). Check the hostname in your server URL.',
    };
  }
  if (error.code === 'ECONNREFUSED') {
    return {
      code: 'REFUSED',
      message: 'Connection refused. Check the host, port, and that the TimeTracker server is running.',
    };
  }
  if (error.code === 'ENETUNREACH' || error.code === 'EHOSTUNREACH') {
    return {
      code: 'UNREACHABLE',
      message: 'Network unreachable. Check your connection and server address.',
    };
  }
  const msg = error.message || 'Unknown error';
  if (!error.response) {
    return {
      code: 'UNKNOWN',
      message:
        'Server not reachable. Check the URL, VPN, firewall, and that the TimeTracker server is running.',
    };
  }
  return { code: 'UNKNOWN', message: msg };
}

/**
 * @param {unknown} data
 * @returns {boolean}
 */
function isTimeTrackerInfoPayload(data) {
  return (
    data !== null &&
    typeof data === 'object' &&
    !Array.isArray(data) &&
    data.api_version === 'v1' &&
    typeof data.endpoints === 'object'
  );
}

const { attachIdempotentRetryInterceptors } = require('../connection/request_policy');

class ApiClient {
  /**
   * @param {string} baseUrl
   * @param {{ enableIdempotentRetry?: boolean, timeoutMs?: number }} [options]
   */
  constructor(baseUrl, options = {}) {
    const normalized = ApiClient.normalizeBaseUrl(baseUrl);
    this.baseUrl = normalized;
    this.client = axios.create({
      baseURL: normalized,
      timeout: options.timeoutMs ?? 10000,
      headers: {
        'Content-Type': 'application/json',
        Accept: 'application/json',
      },
    });

    this.setupInterceptors();
    if (options.enableIdempotentRetry !== false) {
      attachIdempotentRetryInterceptors(this.client);
    }
  }

  setupInterceptors() {
    this.client.interceptors.request.use(async (config) => {
      const token = await storeGet('api_token');
      if (token) {
        config.headers.Authorization = `Bearer ${token}`;
      }
      return config;
    });

    this.client.interceptors.response.use(
      (response) => response,
      (error) => {
        if (error.response) {
          const status = error.response.status;
          const data = error.response.data;

          if (status === 401) {
            error.message = 'Authentication failed. Please sign in again.';
          } else if (status === 403) {
            error.message = 'Access denied. Your token may not have the required permissions.';
          } else if (status === 404) {
            error.message = data?.error || 'Resource not found.';
          } else if (status >= 500) {
            error.message = 'Server error. Please try again later.';
          } else if (data?.error) {
            error.message = data.error;
          }
        } else if (error.code === 'ECONNABORTED') {
          error.message = 'Request timeout. Please check your internet connection.';
        } else if (error.code === 'ENOTFOUND' || error.code === 'ECONNREFUSED') {
          error.message =
            'Unable to connect to server. Please check the server URL and your internet connection.';
        } else if (isTlsRelatedError(error)) {
          error.message =
            'SSL/TLS error: certificate could not be verified. Use a trusted certificate or verify the server URL.';
        }

        return Promise.reject(error);
      }
    );
  }

  static normalizeBaseUrl(url) {
    let u = String(url || '').trim();
    if (!u) return u;
    u = u.replace(/\/+$/, '');
    return u;
  }

  /**
   * Unauthenticated check: reachable TimeTracker JSON at GET /api/v1/info.
   * @param {string} baseUrl
   * @returns {Promise<ValidationResult>}
   */
  static async testPublicServerInfo(baseUrl) {
    const normalized = ApiClient.normalizeBaseUrl(baseUrl);
    if (!normalized) {
      return { ok: false, code: 'NO_URL', message: 'Please enter a server URL.' };
    }
    let parsed;
    try {
      parsed = new URL(normalized);
    } catch (_) {
      return { ok: false, code: 'BAD_URL', message: 'Server URL is not valid.' };
    }
    if (parsed.protocol !== 'http:' && parsed.protocol !== 'https:') {
      return { ok: false, code: 'BAD_URL', message: 'Server URL must start with http:// or https://.' };
    }

    const plain = axios.create({
      baseURL: normalized,
      timeout: 10000,
      headers: { Accept: 'application/json' },
    });

    try {
      const response = await plain.get('/api/v1/info');
      if (response.status !== 200) {
        return {
          ok: false,
          code: 'HTTP_' + response.status,
          message: `Server returned HTTP ${response.status}. Check the URL and port.`,
        };
      }
      const data = response.data;
      if (!isTimeTrackerInfoPayload(data)) {
        return {
          ok: false,
          code: 'NOT_TIMETRACKER',
          message:
            'This address did not return a TimeTracker API response. Check the URL (base URL only, no path) and port.',
        };
      }
      if (data.setup_required === true) {
        return {
          ok: false,
          code: 'SETUP_REQUIRED',
          message:
            'TimeTracker is not fully set up yet. Open this server URL in a browser, complete initial setup, then try again.',
        };
      }
      const appVersion = typeof data.app_version === 'string' ? data.app_version : null;
      return { ok: true, app_version: appVersion };
    } catch (error) {
      const { code, message } = classifyAxiosError(error);
      return { ok: false, code, message };
    }
  }

  /**
   * Login with the same username/password flow used by the mobile app.
   * The server returns an API token, which the desktop stores internally.
   * @param {string} baseUrl
   * @param {string} username
   * @param {string} password
   * @returns {Promise<{ ok: true, token: string } | ValidationResult>}
   */
  static async loginWithPassword(baseUrl, username, password) {
    const normalized = ApiClient.normalizeBaseUrl(baseUrl);
    const plain = axios.create({
      baseURL: normalized,
      timeout: 15000,
      headers: {
        Accept: 'application/json',
        'Content-Type': 'application/json',
      },
    });

    try {
      const response = await plain.post('/api/v1/auth/login', {
        username,
        password,
      });
      const token = response.data && response.data.token;
      if (response.status !== 200 || typeof token !== 'string' || !token.startsWith('tt_')) {
        return {
          ok: false,
          code: 'INVALID_RESPONSE',
          message: 'Server login response did not include a valid app token.',
        };
      }
      return { ok: true, token };
    } catch (error) {
      const { code, message } = classifyAxiosError(error);
      return { ok: false, code, message };
    }
  }

  async setAuthToken(token) {
    await storeSet('api_token', token);
  }

  /**
   * Authenticated session check: prefers GET /api/v1/users/me (read:users).
   * Falls back to GET /api/v1/timer/status (read:time_entries) for narrower tokens.
   * @returns {Promise<ValidationResult>}
   */
  async validateSession() {
    try {
      const response = await this.client.get('/api/v1/users/me');
      if (response.status !== 200) {
        return {
          ok: false,
          code: 'HTTP_' + response.status,
          message: `Unexpected HTTP ${response.status} from the server.`,
        };
      }
      const data = response.data;
      if (!data || typeof data !== 'object' || !data.user) {
        return {
          ok: false,
          code: 'INVALID_RESPONSE',
          message: 'Server response was not a valid TimeTracker user payload.',
        };
      }
      return { ok: true };
    } catch (error) {
      const status = error.response && error.response.status;
      if (status === 401) {
        const { code, message } = classifyAxiosError(error);
        return { ok: false, code, message };
      }
      if (status === 403) {
        try {
          const res2 = await this.client.get('/api/v1/timer/status');
          if (res2.status === 200 && res2.data && typeof res2.data.active === 'boolean') {
            return { ok: true };
          }
        } catch (e2) {
          const { code, message } = classifyAxiosError(e2);
          return { ok: false, code, message };
        }
        return {
          ok: false,
          code: 'FORBIDDEN',
          message:
            'This signed-in account cannot access your profile or timer.',
        };
      }
      const { code, message } = classifyAxiosError(error);
      return { ok: false, code, message };
    }
  }

  /** @deprecated Prefer validateSession() for correct auth + error detail */
  async validateToken() {
    const r = await this.validateSession();
    return r.ok;
  }

  async getUsersMe() {
    const response = await this.client.get('/api/v1/users/me');
    return response.data;
  }

  async getTimerStatus() {
    return await this.client.get('/api/v1/timer/status');
  }

  async startTimer({ projectId, taskId, notes }) {
    return await this.client.post('/api/v1/timer/start', {
      project_id: projectId,
      task_id: taskId,
      notes: notes,
    });
  }

  async stopTimer() {
    return await this.client.post('/api/v1/timer/stop');
  }

  async sendHeartbeat() {
    return await this.client.post('/api/v1/timer/heartbeat');
  }

  async getTimeEntries({ projectId, startDate, endDate, billable, page, perPage }) {
    const params = {};
    if (projectId) params.project_id = projectId;
    if (startDate) params.start_date = startDate;
    if (endDate) params.end_date = endDate;
    if (billable !== undefined) params.billable = billable;
    if (page) params.page = page;
    if (perPage) params.per_page = perPage;

    return await this.client.get('/api/v1/time-entries', { params });
  }

  async createTimeEntry(data) {
    return await this.client.post('/api/v1/time-entries', data);
  }

  async updateTimeEntry(id, data) {
    return await this.client.put(`/api/v1/time-entries/${id}`, data);
  }

  async deleteTimeEntry(id) {
    return await this.client.delete(`/api/v1/time-entries/${id}`);
  }

  async getProjects({ status, clientId, page, perPage }) {
    const params = {};
    if (status) params.status = status;
    if (clientId) params.client_id = clientId;
    if (page) params.page = page;
    if (perPage) params.per_page = perPage;

    return await this.client.get('/api/v1/projects', { params });
  }

  async getProject(id) {
    return await this.client.get(`/api/v1/projects/${id}`);
  }

  async getClients({ status, page, perPage }) {
    const params = {};
    if (status) params.status = status;
    if (page) params.page = page;
    if (perPage) params.per_page = perPage;
    return await this.client.get('/api/v1/clients', { params });
  }

  async getTasks({ projectId, status, page, perPage }) {
    const params = {};
    if (projectId) params.project_id = projectId;
    if (status) params.status = status;
    if (page) params.page = page;
    if (perPage) params.per_page = perPage;

    return await this.client.get('/api/v1/tasks', { params });
  }

  async getTask(id) {
    return await this.client.get(`/api/v1/tasks/${id}`);
  }

  async getTimeEntry(id) {
    return await this.client.get(`/api/v1/time-entries/${id}`);
  }

  async getInvoices({ status, clientId, projectId, page, perPage }) {
    const params = {};
    if (status) params.status = status;
    if (clientId) params.client_id = clientId;
    if (projectId) params.project_id = projectId;
    if (page) params.page = page;
    if (perPage) params.per_page = perPage;

    return await this.client.get('/api/v1/invoices', { params });
  }

  async getInvoice(id) {
    return await this.client.get(`/api/v1/invoices/${id}`);
  }

  async createInvoice(data) {
    return await this.client.post('/api/v1/invoices', data);
  }

  async updateInvoice(id, data) {
    return await this.client.put(`/api/v1/invoices/${id}`, data);
  }

  async getExpenses({ projectId, category, startDate, endDate, page, perPage }) {
    const params = {};
    if (projectId) params.project_id = projectId;
    if (category) params.category = category;
    if (startDate) params.start_date = startDate;
    if (endDate) params.end_date = endDate;
    if (page) params.page = page;
    if (perPage) params.per_page = perPage;

    return await this.client.get('/api/v1/expenses', { params });
  }

  async createExpense(data) {
    return await this.client.post('/api/v1/expenses', data);
  }

  async getCapacityReport({ startDate, endDate }) {
    return await this.client.get('/api/v1/reports/capacity', {
      params: { start_date: startDate, end_date: endDate },
    });
  }

  async getTimesheetPeriods({ status, startDate, endDate }) {
    const params = {};
    if (status) params.status = status;
    if (startDate) params.start_date = startDate;
    if (endDate) params.end_date = endDate;
    return await this.client.get('/api/v1/timesheet-periods', { params });
  }

  async submitTimesheetPeriod(periodId) {
    return await this.client.post(`/api/v1/timesheet-periods/${periodId}/submit`);
  }

  async approveTimesheetPeriod(periodId, { comment } = {}) {
    const data = {};
    if (comment) data.comment = comment;
    return await this.client.post(`/api/v1/timesheet-periods/${periodId}/approve`, data);
  }

  async rejectTimesheetPeriod(periodId, { reason } = {}) {
    const data = {};
    if (reason) data.reason = reason;
    return await this.client.post(`/api/v1/timesheet-periods/${periodId}/reject`, data);
  }

  async deleteTimesheetPeriod(periodId) {
    return await this.client.delete(`/api/v1/timesheet-periods/${periodId}`);
  }

  async getLeaveTypes() {
    return await this.client.get('/api/v1/time-off/leave-types');
  }

  async getTimeOffRequests({ status, startDate, endDate }) {
    const params = {};
    if (status) params.status = status;
    if (startDate) params.start_date = startDate;
    if (endDate) params.end_date = endDate;
    return await this.client.get('/api/v1/time-off/requests', { params });
  }

  async createTimeOffRequest({ leaveTypeId, startDate, endDate, requestedHours, comment, submit }) {
    const data = {
      leave_type_id: leaveTypeId,
      start_date: startDate,
      end_date: endDate,
      submit: submit !== undefined ? submit : true,
    };
    if (requestedHours !== undefined && requestedHours !== null) data.requested_hours = requestedHours;
    if (comment) data.comment = comment;
    return await this.client.post('/api/v1/time-off/requests', data);
  }

  async getTimeOffBalances({ userId } = {}) {
    const params = {};
    if (userId) params.user_id = userId;
    return await this.client.get('/api/v1/time-off/balances', { params });
  }

  async approveTimeOffRequest(requestId, { comment } = {}) {
    const data = {};
    if (comment) data.comment = comment;
    return await this.client.post(`/api/v1/time-off/requests/${requestId}/approve`, data);
  }

  async rejectTimeOffRequest(requestId, { comment } = {}) {
    const data = {};
    if (comment) data.comment = comment;
    return await this.client.post(`/api/v1/time-off/requests/${requestId}/reject`, data);
  }

  async deleteTimeOffRequest(requestId) {
    return await this.client.delete(`/api/v1/time-off/requests/${requestId}`);
  }
}

if (typeof module !== 'undefined' && module.exports) {
  module.exports = ApiClient;
  module.exports.classifyAxiosError = classifyAxiosError;
  module.exports.isTimeTrackerInfoPayload = isTimeTrackerInfoPayload;
}
