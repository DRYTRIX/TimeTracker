import axios from 'axios';
import { storeGet } from './store.js';

export function normalizeServerUrlInput(value) {
  let url = String(value || '').trim();
  if (!url) return '';
  if (!/^https?:\/\//i.test(url)) url = `https://${url}`;
  return url.replace(/\/+$/, '');
}

function isTlsRelatedError(error) {
  const code = error?.code;
  const message = error?.message || '';
  return (
    [
      'DEPTH_ZERO_SELF_SIGNED_CERT',
      'CERT_HAS_EXPIRED',
      'CERT_NOT_YET_VALID',
      'UNABLE_TO_VERIFY_LEAF_SIGNATURE',
      'ERR_TLS_CERT_ALTNAME_INVALID',
      'SELF_SIGNED_CERT_IN_CHAIN',
      'UNABLE_TO_GET_ISSUER_CERT_LOCALLY',
    ].includes(code) || /certificate|ssl|tls|UNABLE_TO_VERIFY/i.test(message)
  );
}

export function classifyAxiosError(error) {
  if (isTlsRelatedError(error)) {
    return {
      ok: false,
      code: 'TLS',
      message:
        'SSL/TLS certificate could not be verified. For local/private servers, trust the host or use a valid certificate.',
    };
  }
  if (error?.response) {
    const status = error.response.status;
    const data = error.response.data;
    if (status === 401) return { ok: false, code: 'UNAUTHORIZED', message: 'Authentication failed. Sign in again.' };
    if (status === 403) return { ok: false, code: 'FORBIDDEN', message: 'Access denied for this account.' };
    if (status === 404) return { ok: false, code: 'NOT_FOUND', message: data?.error || 'Resource not found.' };
    if (status >= 500) return { ok: false, code: 'SERVER_ERROR', message: 'Server error. Try again later.' };
    if (data?.error) return { ok: false, code: `HTTP_${status}`, message: String(data.error) };
    return { ok: false, code: `HTTP_${status}`, message: `Server returned HTTP ${status}.` };
  }
  if (error?.code === 'ECONNABORTED' || error?.code === 'ETIMEDOUT') {
    return { ok: false, code: 'TIMEOUT', message: 'Request timed out. Check URL, VPN, or firewall.' };
  }
  if (error?.code === 'ENOTFOUND') return { ok: false, code: 'DNS', message: 'Host not found. Check the server URL.' };
  if (error?.code === 'ECONNREFUSED') {
    return { ok: false, code: 'REFUSED', message: 'Connection refused. Check the server and port.' };
  }
  if (error?.code === 'ENETUNREACH' || error?.code === 'EHOSTUNREACH') {
    return { ok: false, code: 'UNREACHABLE', message: 'Network unreachable.' };
  }
  return {
    ok: false,
    code: 'UNKNOWN',
    message: 'Server not reachable. Check the URL, VPN, firewall, and that TimeTracker is running.',
  };
}

function isInfoPayload(data) {
  return data && typeof data === 'object' && data.api_version === 'v1' && typeof data.endpoints === 'object';
}

export class ApiClient {
  constructor(baseUrl, token = null, options = {}) {
    this.baseUrl = ApiClient.normalizeBaseUrl(baseUrl);
    this.token = token;
    this.client = axios.create({
      baseURL: this.baseUrl,
      timeout: options.timeoutMs || 15000,
      headers: {
        Accept: 'application/json',
        'Content-Type': 'application/json',
      },
    });
    this.client.interceptors.request.use(async (config) => {
      const currentToken = this.token || (await storeGet('api_token'));
      if (currentToken) config.headers.Authorization = `Bearer ${currentToken}`;
      return config;
    });
  }

  static normalizeBaseUrl(url) {
    return String(url || '').trim().replace(/\/+$/, '');
  }

  static async testPublicServerInfo(baseUrl) {
    const normalized = ApiClient.normalizeBaseUrl(normalizeServerUrlInput(baseUrl));
    if (!normalized) return { ok: false, code: 'NO_URL', message: 'Please enter a server URL.' };
    try {
      const parsed = new URL(normalized);
      if (parsed.protocol !== 'http:' && parsed.protocol !== 'https:') {
        return { ok: false, code: 'BAD_URL', message: 'Server URL must start with http:// or https://.' };
      }
    } catch {
      return { ok: false, code: 'BAD_URL', message: 'Server URL is not valid.' };
    }
    try {
      const response = await axios.get(`${normalized}/api/v1/info`, { timeout: 10000, headers: { Accept: 'application/json' } });
      if (!isInfoPayload(response.data)) {
        return {
          ok: false,
          code: 'NOT_TIMETRACKER',
          message: 'This address did not return a TimeTracker API response. Use the base URL only.',
        };
      }
      if (response.data.setup_required === true) {
        return {
          ok: false,
          code: 'SETUP_REQUIRED',
          message: 'TimeTracker is not fully set up yet. Finish setup in a browser first.',
        };
      }
      return { ok: true, app_version: response.data.app_version || null, timezone: response.data.timezone || null };
    } catch (error) {
      return classifyAxiosError(error);
    }
  }

  static async loginWithPassword(baseUrl, username, password) {
    const normalized = ApiClient.normalizeBaseUrl(normalizeServerUrlInput(baseUrl));
    try {
      const response = await axios.post(
        `${normalized}/api/v1/auth/login`,
        { username, password },
        { timeout: 15000, headers: { Accept: 'application/json', 'Content-Type': 'application/json' } },
      );
      const token = response.data?.token;
      if (typeof token !== 'string' || !token.startsWith('tt_')) {
        return { ok: false, code: 'INVALID_RESPONSE', message: 'Login did not return a valid desktop token.' };
      }
      return { ok: true, token };
    } catch (error) {
      return classifyAxiosError(error);
    }
  }

  async validateSession() {
    try {
      const response = await this.client.get('/api/v1/users/me');
      if (response.status === 200 && response.data?.user) return { ok: true };
      return { ok: false, code: 'INVALID_RESPONSE', message: 'Server returned an invalid user payload.' };
    } catch (error) {
      const status = error?.response?.status;
      if (status === 403) {
        try {
          const fallback = await this.client.get('/api/v1/timer/status');
          if (fallback.status === 200) return { ok: true };
        } catch (fallbackError) {
          return classifyAxiosError(fallbackError);
        }
      }
      return classifyAxiosError(error);
    }
  }

  async unwrap(promise) {
    const response = await promise;
    return response.data;
  }

  getUsersMe() { return this.unwrap(this.client.get('/api/v1/users/me')); }
  getTimerStatus() { return this.unwrap(this.client.get('/api/v1/timer/status')); }
  startTimer(data) { return this.unwrap(this.client.post('/api/v1/timer/start', { project_id: data.projectId, task_id: data.taskId || null, notes: data.notes || '' })); }
  stopTimer() { return this.unwrap(this.client.post('/api/v1/timer/stop')); }
  pauseTimer() { return this.unwrap(this.client.post('/api/v1/timer/pause')); }
  resumeTimer() { return this.unwrap(this.client.post('/api/v1/timer/resume')); }
  getProjects(params = {}) { return this.unwrap(this.client.get('/api/v1/projects', { params })); }
  getTasks(params = {}) { return this.unwrap(this.client.get('/api/v1/tasks', { params })); }
  updateTask(id, data) { return this.unwrap(this.client.patch(`/api/v1/tasks/${id}`, data)); }
  createTask(data) { return this.unwrap(this.client.post('/api/v1/tasks', data)); }
  getTimeEntries(params = {}) { return this.unwrap(this.client.get('/api/v1/time-entries', { params })); }
  createTimeEntry(data) { return this.unwrap(this.client.post('/api/v1/time-entries', data)); }
  updateTimeEntry(id, data) { return this.unwrap(this.client.put(`/api/v1/time-entries/${id}`, data)); }
  deleteTimeEntry(id) { return this.unwrap(this.client.delete(`/api/v1/time-entries/${id}`)); }
  getInvoices(params = {}) { return this.unwrap(this.client.get('/api/v1/invoices', { params })); }
  getInvoice(id) { return this.unwrap(this.client.get(`/api/v1/invoices/${id}`)); }
  createInvoice(data) { return this.unwrap(this.client.post('/api/v1/invoices', data)); }
  updateInvoice(id, data) { return this.unwrap(this.client.patch(`/api/v1/invoices/${id}`, data)); }
  setInvoiceItems(id, items) { return this.unwrap(this.client.put(`/api/v1/invoices/${id}/items`, { items })); }
  generateInvoiceFromTime(id, timeEntryIds, replaceExisting = true) {
    return this.unwrap(this.client.post(`/api/v1/invoices/${id}/generate-from-time`, { time_entry_ids: timeEntryIds, replace_existing: replaceExisting }));
  }
  async downloadInvoicePdf(id) {
    const response = await this.client.get(`/api/v1/invoices/${id}/pdf`, { responseType: 'arraybuffer' });
    return response.data;
  }
  getExpenses(params = {}) { return this.unwrap(this.client.get('/api/v1/expenses', { params })); }
  createExpense(data) { return this.unwrap(this.client.post('/api/v1/expenses', data)); }
  getClients(params = {}) { return this.unwrap(this.client.get('/api/v1/clients', { params })); }
  getUsers(params = {}) { return this.unwrap(this.client.get('/api/v1/users', { params })); }
  getReportSummary(params = {}) { return this.unwrap(this.client.get('/api/v1/reports/summary', { params })); }
  unwrapReportSummary(payload) {
    return payload?.summary || payload || {};
  }
  getTimeEntryApprovals() { return this.unwrap(this.client.get('/api/v1/time-entry-approvals')); }
  approveTimeEntryApproval(id, comment) { return this.unwrap(this.client.post(`/api/v1/time-entry-approvals/${id}/approve`, { comment })); }
  rejectTimeEntryApproval(id, reason) { return this.unwrap(this.client.post(`/api/v1/time-entry-approvals/${id}/reject`, { reason })); }
  getInvoiceApprovals() { return this.unwrap(this.client.get('/api/v1/invoice-approvals')); }
  approveInvoiceApproval(id, comment) { return this.unwrap(this.client.post(`/api/v1/invoice-approvals/${id}/approve`, { comment })); }
  rejectInvoiceApproval(id, reason) { return this.unwrap(this.client.post(`/api/v1/invoice-approvals/${id}/reject`, { reason })); }
  requestInvoiceApproval(invoiceId, approverIds) {
    return this.unwrap(this.client.post(`/api/v1/invoices/${invoiceId}/request-approval`, { approver_ids: approverIds }));
  }
  submitTimesheetPeriod(periodId) { return this.unwrap(this.client.post(`/api/v1/timesheet-periods/${periodId}/submit`)); }
  approveTimesheetPeriod(periodId, comment) { return this.unwrap(this.client.post(`/api/v1/timesheet-periods/${periodId}/approve`, { comment })); }
  rejectTimesheetPeriod(periodId, reason) { return this.unwrap(this.client.post(`/api/v1/timesheet-periods/${periodId}/reject`, { reason })); }
  closeTimesheetPeriod(periodId, reason) { return this.unwrap(this.client.post(`/api/v1/timesheet-periods/${periodId}/close`, { reason })); }
  deleteTimesheetPeriod(periodId) { return this.unwrap(this.client.delete(`/api/v1/timesheet-periods/${periodId}`)); }
  createTimeOffRequest(data) { return this.unwrap(this.client.post('/api/v1/time-off/requests', data)); }
  approveTimeOffRequest(id, comment) { return this.unwrap(this.client.post(`/api/v1/time-off/requests/${id}/approve`, { comment })); }
  rejectTimeOffRequest(id, comment) { return this.unwrap(this.client.post(`/api/v1/time-off/requests/${id}/reject`, { comment })); }
  getCapacityReport(params = {}) { return this.unwrap(this.client.get('/api/v1/reports/capacity', { params })); }
  getTimesheetPeriods(params = {}) { return this.unwrap(this.client.get('/api/v1/timesheet-periods', { params })); }
  getTimeOffRequests(params = {}) { return this.unwrap(this.client.get('/api/v1/time-off/requests', { params })); }

  getAttendanceStatus() { return this.unwrap(this.client.get('/api/v1/attendance/status')); }
  startWorkday(data = {}) {
    return this.unwrap(this.client.post('/api/v1/workday/start', { notes: data.notes || '', source: data.source || 'desktop' }));
  }
  endWorkday(data = {}) { return this.unwrap(this.client.post('/api/v1/workday/end', { notes: data.notes || '' })); }
  startBreak(data = {}) {
    return this.unwrap(this.client.post('/api/v1/attendance/break/start', { break_type: data.breakType || 'rest' }));
  }
  endBreak() { return this.unwrap(this.client.post('/api/v1/attendance/break/end')); }

  getKanbanColumns(params = {}) { return this.unwrap(this.client.get('/api/v1/kanban/columns', { params })); }
  createKanbanColumn(data) { return this.unwrap(this.client.post('/api/v1/kanban/columns', data)); }
  updateKanbanColumn(id, data) { return this.unwrap(this.client.patch(`/api/v1/kanban/columns/${id}`, data)); }
  deleteKanbanColumn(id) { return this.unwrap(this.client.delete(`/api/v1/kanban/columns/${id}`)); }
  reorderKanbanColumns(columnIds, projectId = null) {
    return this.unwrap(this.client.post('/api/v1/kanban/columns/reorder', { column_ids: columnIds, project_id: projectId }));
  }

  getLeads(params = {}) { return this.unwrap(this.client.get('/api/v1/leads', { params })); }
  getLead(id) { return this.unwrap(this.client.get(`/api/v1/leads/${id}`)); }
  createLead(data) { return this.unwrap(this.client.post('/api/v1/leads', data)); }
  updateLead(id, data) { return this.unwrap(this.client.patch(`/api/v1/leads/${id}`, data)); }
  deleteLead(id) { return this.unwrap(this.client.delete(`/api/v1/leads/${id}`)); }
  getDeals(params = {}) { return this.unwrap(this.client.get('/api/v1/deals', { params })); }
  getDeal(id) { return this.unwrap(this.client.get(`/api/v1/deals/${id}`)); }
  createDeal(data) { return this.unwrap(this.client.post('/api/v1/deals', data)); }
  updateDeal(id, data) { return this.unwrap(this.client.patch(`/api/v1/deals/${id}`, data)); }
  deleteDeal(id) { return this.unwrap(this.client.delete(`/api/v1/deals/${id}`)); }
  getContacts(clientId) { return this.unwrap(this.client.get(`/api/v1/clients/${clientId}/contacts`)); }
  createContact(clientId, data) { return this.unwrap(this.client.post(`/api/v1/clients/${clientId}/contacts`, data)); }
  updateContact(id, data) { return this.unwrap(this.client.patch(`/api/v1/contacts/${id}`, data)); }
  deleteContact(id) { return this.unwrap(this.client.delete(`/api/v1/contacts/${id}`)); }
  getClientNotes(clientId) { return this.unwrap(this.client.get(`/api/v1/clients/${clientId}/notes`)); }
  createClientNote(clientId, data) { return this.unwrap(this.client.post(`/api/v1/clients/${clientId}/notes`, data)); }
  updateClientNote(id, data) { return this.unwrap(this.client.patch(`/api/v1/client-notes/${id}`, data)); }
  deleteClientNote(id) { return this.unwrap(this.client.delete(`/api/v1/client-notes/${id}`)); }

  getPayments(params = {}) { return this.unwrap(this.client.get('/api/v1/payments', { params })); }
  createPayment(data) { return this.unwrap(this.client.post('/api/v1/payments', data)); }
  getMileage(params = {}) { return this.unwrap(this.client.get('/api/v1/mileage', { params })); }
  createMileage(data) { return this.unwrap(this.client.post('/api/v1/mileage', data)); }
  updateMileage(id, data) { return this.unwrap(this.client.patch(`/api/v1/mileage/${id}`, data)); }
  getQuotes(params = {}) { return this.unwrap(this.client.get('/api/v1/quotes', { params })); }
  getQuote(id) { return this.unwrap(this.client.get(`/api/v1/quotes/${id}`)); }
  createQuote(data) { return this.unwrap(this.client.post('/api/v1/quotes', data)); }
  getRecurringInvoices(params = {}) { return this.unwrap(this.client.get('/api/v1/recurring-invoices', { params })); }
  generateRecurringInvoice(id) { return this.unwrap(this.client.post(`/api/v1/recurring-invoices/${id}/generate`)); }
  getCreditNotes(params = {}) { return this.unwrap(this.client.get('/api/v1/credit-notes', { params })); }
  getCreditNote(id) { return this.unwrap(this.client.get(`/api/v1/credit-notes/${id}`)); }
  createCreditNote(data) { return this.unwrap(this.client.post('/api/v1/credit-notes', data)); }
}
