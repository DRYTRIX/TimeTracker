/**
 * Application state - single source of truth for view, timer, cache, and filters.
 * Used by app.js to avoid scattered globals.
 */
module.exports = {
  apiClient: null,
  currentView: 'dashboard',
  timerInterval: null,
  isTimerRunning: false,
  connectionCheckInterval: null,
  currentUserProfile: { is_admin: false, can_approve: false },
  cachedInvoices: [],
  cachedExpenses: [],
  cachedWorkforce: { periods: [], capacity: [], timeOffRequests: [], balances: [] },
  viewFilters: { invoiceQuery: '', expenseQuery: '', timeoffQuery: '' },
  viewLimits: { invoices: 20, expenses: 20, timeoff: 20 },
  pagination: {
    invoices: { page: 1, perPage: 20, totalPages: 1, total: 0 },
    expenses: { page: 1, perPage: 20, totalPages: 1, total: 0 },
  },
};
