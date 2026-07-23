import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { createRoot } from 'react-dom/client';
import './styles/app.css';
import { ApiClient, classifyAxiosError, normalizeServerUrlInput } from './services/api.js';
import { storeClear, storeDelete, storeGet, storeSet } from './services/store.js';
import { buildDiagnostics } from './services/diagnostics.js';
import { createSyncEngine } from './sync/syncEngine.js';
import { LoadingScreen, Toast } from './components/ui.jsx';
import { formatDuration, isTimerPaused, timerElapsedSeconds } from './utils/format.js';
import { AuthFlow, Sidebar, TopBar } from './views/Shell.jsx';
import { DashboardView } from './views/DashboardView.jsx';
import { ProjectsView } from './views/ProjectsView.jsx';
import { EntriesView } from './views/EntriesView.jsx';
import { InvoicesView } from './views/InvoicesView.jsx';
import { ExpensesView } from './views/ExpensesView.jsx';
import { WorkforceView } from './views/WorkforceView.jsx';
import { SettingsView } from './views/SettingsView.jsx';
import { ReportsView } from './views/ReportsView.jsx';
import { KanbanView } from './views/KanbanView.jsx';
import { CrmView } from './views/CrmView.jsx';
import { FinanceExtraView } from './views/FinanceExtraView.jsx';
import { StartTimerDialog, TimeEntryDialog } from './views/Dialogs.jsx';
import { formatAttendanceError, runAttendanceAction } from './views/WorkdayCard.jsx';

const defaultConnection = {
  state: 'not_configured',
  serverUrl: '',
  message: 'Not configured',
  lastOk: null,
};

const emptyData = {
  user: null,
  timer: null,
  projects: [],
  tasks: [],
  entries: [],
  invoices: [],
  expenses: [],
  clients: [],
  workforce: {},
  invoiceApprovals: [],
  timeEntryApprovals: [],
};

function App() {
  const [booting, setBooting] = useState(true);
  const [authStep, setAuthStep] = useState('server');
  const [serverUrl, setServerUrl] = useState('');
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [authError, setAuthError] = useState('');
  const [authInfo, setAuthInfo] = useState('');
  const [diagnostics, setDiagnostics] = useState(null);
  const [apiClient, setApiClient] = useState(null);
  const [connection, setConnection] = useState(defaultConnection);
  const [activeView, setActiveView] = useState('dashboard');
  const [theme, setTheme] = useState('system');
  const [toast, setToast] = useState(null);
  const [data, setData] = useState(emptyData);
  const [loading, setLoading] = useState({});
  const [filters, setFilters] = useState({ project: '', entrySearch: '' });
  const [settings, setSettings] = useState({ autoSync: true, syncInterval: 60 });
  const [syncStatus, setSyncStatus] = useState({
    queueDepth: 0,
    syncing: false,
    lastSyncAt: null,
    lastError: '',
  });
  const [startTimerOpen, setStartTimerOpen] = useState(false);
  const [newEntryOpen, setNewEntryOpen] = useState(false);
  const [attendance, setAttendance] = useState(null);
  const [attendanceLoading, setAttendanceLoading] = useState(false);
  const syncEngineRef = useRef(null);

  const showToast = useCallback((message, type = 'info') => {
    setToast({ message, type });
    window.clearTimeout(showToast._timer);
    showToast._timer = window.setTimeout(() => setToast(null), type === 'error' ? 7000 : 4000);
  }, []);

  useEffect(() => {
    let cancelled = false;
    async function boot() {
      const savedTheme = (await storeGet('theme_mode')) || 'system';
      const savedUrl = (await storeGet('server_url')) || '';
      const savedUsername = (await storeGet('username')) || '';
      const token = await storeGet('api_token');
      const tokenServer = await storeGet('api_token_server_url');
      const autoSync = await storeGet('auto_sync');
      const syncInterval = await storeGet('sync_interval');

      if (cancelled) return;
      setTheme(savedTheme);
      setServerUrl(savedUrl || '');
      setUsername(savedUsername || '');
      setSettings({
        autoSync: autoSync !== null && autoSync !== undefined ? Boolean(autoSync) : true,
        syncInterval: Number(syncInterval || 60),
      });

      if (!savedUrl) {
        setAuthStep('server');
        setConnection(defaultConnection);
        setBooting(false);
        return;
      }

      if (!token || (tokenServer && tokenServer !== savedUrl)) {
        setAuthStep(tokenServer && tokenServer !== savedUrl ? 'server' : 'credentials');
        setConnection({ state: 'not_configured', serverUrl: savedUrl, message: 'Sign in required', lastOk: null });
        setBooting(false);
        return;
      }

      const client = new ApiClient(savedUrl, token);
      setConnection({ state: 'connecting', serverUrl: savedUrl, message: 'Checking session…', lastOk: null });
      const session = await client.validateSession();
      if (cancelled) return;

      if (!session.ok) {
        setAuthStep('credentials');
        setAuthError(session.message || 'Please sign in again.');
        setDiagnostics(buildDiagnostics(savedUrl, session));
        setConnection({ state: 'error', serverUrl: savedUrl, message: session.message || 'Session unavailable', lastOk: null });
        setBooting(false);
        return;
      }

      setApiClient(client);
      setConnection({ state: 'connected', serverUrl: savedUrl, message: 'Connected', lastOk: Date.now() });
      setBooting(false);
    }

    boot().catch((error) => {
      console.error('Desktop boot failed', error);
      setDiagnostics(buildDiagnostics(serverUrl, classifyAxiosError(error)));
      setAuthError('Startup failed. Check your server URL and sign in again.');
      setAuthStep('server');
      setBooting(false);
    });

    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    document.documentElement.dataset.theme = theme === 'system' ? '' : theme;
    storeSet('theme_mode', theme);
  }, [theme]);

  const refreshAttendance = useCallback(async () => {
    if (!apiClient) return;
    setAttendanceLoading(true);
    try {
      const status = await apiClient.getAttendanceStatus();
      setAttendance(status);
    } catch {
      setAttendance(null);
    } finally {
      setAttendanceLoading(false);
    }
  }, [apiClient]);

  const refreshCoreData = useCallback(async () => {
    if (!apiClient) return;
    setLoading((s) => ({ ...s, core: true }));
    try {
      const [user, timer, projects, tasks, entries] = await Promise.all([
        apiClient.getUsersMe().catch(() => ({ user: null })),
        apiClient.getTimerStatus().catch(() => ({ active: false })),
        apiClient.getProjects().catch(() => ({ projects: [] })),
        apiClient.getTasks().catch(() => ({ tasks: [] })),
        apiClient.getTimeEntries({ perPage: 25 }).catch(() => ({ time_entries: [] })),
      ]);
      setData((current) => ({
        ...current,
        user: user.user || null,
        timer,
        projects: projects.projects || projects.items || [],
        tasks: tasks.tasks || tasks.items || [],
        entries: entries.time_entries || entries.entries || entries.items || [],
      }));
      syncEngineRef.current?.cacheReadData({
        projects: projects.projects || projects.items || [],
        tasks: tasks.tasks || tasks.items || [],
        timeEntries: entries.time_entries || entries.entries || entries.items || [],
      });
      setConnection((c) => ({ ...c, state: 'connected', message: 'Connected', lastOk: Date.now() }));
      refreshAttendance();
    } catch (error) {
      const classified = classifyAxiosError(error);
      setConnection((c) => ({ ...c, state: 'error', message: classified.message }));
      showToast(classified.message, 'error');
    } finally {
      setLoading((s) => ({ ...s, core: false }));
    }
  }, [apiClient, showToast, refreshAttendance]);

  useEffect(() => {
    if (!apiClient) return;
    const engine = createSyncEngine({
      apiClient,
      settings,
      onStatus: setSyncStatus,
      onToast: showToast,
      onRefresh: refreshCoreData,
    });
    syncEngineRef.current = engine;
    engine.start();
    refreshCoreData();
    return () => engine.stop();
  }, [apiClient, settings.autoSync, settings.syncInterval, refreshCoreData, showToast]);

  const revalidateSession = useCallback(async ({ refresh = false } = {}) => {
    if (!apiClient) return false;
    const session = await apiClient.validateSession();
    if (!session.ok) {
      setConnection((c) => ({ ...c, state: 'error', message: session.message }));
      return false;
    }
    setConnection((c) => ({
      ...c,
      state: 'connected',
      message: 'Connected',
      lastOk: Date.now(),
    }));
    if (refresh) {
      await refreshCoreData();
    }
    return true;
  }, [apiClient, refreshCoreData]);

  const lastResumeRevalidateRef = useRef(0);
  const revalidateOnResume = useCallback(() => {
    const now = Date.now();
    if (now - lastResumeRevalidateRef.current < 5000) return;
    lastResumeRevalidateRef.current = now;
    revalidateSession({ refresh: true });
  }, [revalidateSession]);

  useEffect(() => {
    if (!apiClient) return undefined;
    const id = window.setInterval(() => {
      revalidateSession();
    }, 30000);
    return () => window.clearInterval(id);
  }, [apiClient, revalidateSession]);

  useEffect(() => {
    if (!apiClient) return undefined;

    const onVisible = () => {
      if (document.visibilityState === 'visible') {
        revalidateOnResume();
      }
    };
    const onFocus = () => {
      revalidateOnResume();
    };
    const onAppResume = () => {
      revalidateOnResume();
    };

    document.addEventListener('visibilitychange', onVisible);
    window.addEventListener('focus', onFocus);
    const unsubscribeResume = window.electronAPI?.onAppResume?.(onAppResume);

    return () => {
      document.removeEventListener('visibilitychange', onVisible);
      window.removeEventListener('focus', onFocus);
      if (typeof unsubscribeResume === 'function') {
        unsubscribeResume();
      }
    };
  }, [apiClient, revalidateOnResume]);

  const pushTimerStatusToTray = useCallback((timerPayload) => {
    if (!window.electronAPI?.sendTimerStatus) return;
    const active = Boolean(timerPayload?.active);
    const timer = timerPayload?.timer;
    const paused = isTimerPaused(timerPayload);
    let elapsedLabel = '';
    if (active && timer?.start_time) {
      elapsedLabel = formatDuration(timerElapsedSeconds(timerPayload));
    }
    window.electronAPI.sendTimerStatus({ active, paused, timer, elapsedLabel });
  }, []);

  useEffect(() => {
    if (!apiClient) return undefined;
    pushTimerStatusToTray(data.timer);
    const id = window.setInterval(() => {
      if (data.timer?.active) pushTimerStatusToTray(data.timer);
    }, 1000);
    return () => window.clearInterval(id);
  }, [apiClient, data.timer, pushTimerStatusToTray]);

  const handleServerTest = async () => {
    const normalized = ApiClient.normalizeBaseUrl(normalizeServerUrlInput(serverUrl));
    setAuthError('');
    setAuthInfo('');
    setDiagnostics(null);
    if (!normalized) {
      setAuthError('Enter your TimeTracker server URL.');
      return;
    }
    setConnection({ state: 'connecting', serverUrl: normalized, message: 'Testing server…', lastOk: null });
    const result = await ApiClient.testPublicServerInfo(normalized);
    if (!result.ok) {
      setAuthError(result.message);
      setDiagnostics(buildDiagnostics(normalized, result));
      setConnection({ state: 'error', serverUrl: normalized, message: result.message, lastOk: null });
      return;
    }
    setServerUrl(normalized);
    setAuthInfo(`TimeTracker server detected${result.app_version ? ` (${result.app_version})` : ''}.`);
    setConnection({ state: 'connected', serverUrl: normalized, message: 'Server reachable', lastOk: Date.now() });
    setAuthStep('credentials');
  };

  const handleLogin = async (event, overrides = {}) => {
    event.preventDefault();
    const loginServerUrl = overrides.serverUrl ?? serverUrl;
    const loginUsername = overrides.username ?? username;
    const loginPassword = overrides.password ?? password;
    const normalized = ApiClient.normalizeBaseUrl(normalizeServerUrlInput(loginServerUrl));
    setAuthError('');
    setDiagnostics(null);
    if (!normalized || !loginUsername || !loginPassword) {
      setAuthError('Enter server URL, username, and password.');
      return;
    }

    setConnection({ state: 'connecting', serverUrl: normalized, message: 'Signing in…', lastOk: null });
    const info = await ApiClient.testPublicServerInfo(normalized);
    if (!info.ok) {
      setAuthError(info.message);
      setDiagnostics(buildDiagnostics(normalized, info));
      setConnection({ state: 'error', serverUrl: normalized, message: info.message, lastOk: null });
      return;
    }

    const login = await ApiClient.loginWithPassword(normalized, loginUsername, loginPassword);
    if (!login.ok) {
      setAuthError(login.message || 'Login failed.');
      setDiagnostics(buildDiagnostics(normalized, login));
      setConnection({ state: 'error', serverUrl: normalized, message: login.message || 'Login failed', lastOk: null });
      return;
    }

    const client = new ApiClient(normalized, login.token);
    const session = await client.validateSession();
    if (!session.ok) {
      setAuthError(session.message || 'The account cannot access the desktop API.');
      setDiagnostics(buildDiagnostics(normalized, session));
      setConnection({ state: 'error', serverUrl: normalized, message: session.message || 'Session failed', lastOk: null });
      return;
    }

    await storeSet('server_url', normalized);
    await storeSet('username', loginUsername.trim());
    await storeSet('api_token', login.token);
    await storeSet('api_token_server_url', normalized);
    setUsername(loginUsername.trim());
    setPassword('');
    setApiClient(client);
    setConnection({ state: 'connected', serverUrl: normalized, message: 'Connected', lastOk: Date.now() });
    showToast('Signed in successfully', 'success');
  };

  const handleLogout = async () => {
    await storeDelete('api_token');
    await storeDelete('api_token_server_url');
    setApiClient(null);
    setAuthStep(serverUrl ? 'credentials' : 'server');
    setConnection({ state: 'not_configured', serverUrl, message: 'Signed out', lastOk: null });
  };

  const handleReset = async () => {
    if (!window.confirm('Reset desktop configuration and local cache?')) return;
    await syncEngineRef.current?.clearAll();
    await storeClear();
    setApiClient(null);
    setServerUrl('');
    setUsername('');
    setPassword('');
    setAuthStep('server');
    setData(emptyData);
    setAttendance(null);
    setConnection(defaultConnection);
  };

  const loadView = useCallback(
    async (view) => {
      if (!apiClient) return;
      setLoading((s) => ({ ...s, [view]: true }));
      try {
        if (view === 'invoices' || view === 'payments' || view === 'credit' || view === 'quotes') {
          const [response, clients] = await Promise.all([
            apiClient.getInvoices({ perPage: 25 }).catch(() => ({ invoices: [] })),
            apiClient.getClients({ perPage: 100 }).catch(() => ({ clients: [] })),
          ]);
          setData((d) => ({
            ...d,
            invoices: response.invoices || response.items || [],
            clients: clients.clients || clients.items || [],
          }));
        } else if (view === 'expenses' || view === 'mileage') {
          const response = await apiClient.getExpenses({ perPage: 25 }).catch(() => ({ expenses: [] }));
          setData((d) => ({ ...d, expenses: response.expenses || response.items || [] }));
        } else if (view === 'crm') {
          const clients = await apiClient.getClients({ perPage: 100 }).catch(() => ({ clients: [] }));
          setData((d) => ({ ...d, clients: clients.clients || clients.items || [] }));
        } else if (view === 'workforce') {
          const [periods, capacity, requests, invoiceApprovals, timeEntryApprovals] = await Promise.all([
            apiClient.getTimesheetPeriods({}).catch(() => ({ timesheet_periods: [] })),
            apiClient.getCapacityReport({}).catch(() => ({ capacity: [] })),
            apiClient.getTimeOffRequests({}).catch(() => ({ time_off_requests: [] })),
            apiClient.getInvoiceApprovals().catch(() => ({ invoice_approvals: [] })),
            apiClient.getTimeEntryApprovals().catch(() => ({ approvals: [] })),
          ]);
          setData((d) => ({
            ...d,
            workforce: { periods, capacity, requests },
            invoiceApprovals: invoiceApprovals.invoice_approvals || [],
            timeEntryApprovals: timeEntryApprovals.approvals || [],
          }));
        }
      } catch (error) {
        showToast(classifyAxiosError(error).message, 'error');
      } finally {
        setLoading((s) => ({ ...s, [view]: false }));
      }
    },
    [apiClient, showToast],
  );

  const changeView = (view) => {
    setActiveView(view);
    loadView(view);
  };

  const startTimer = async ({ projectId, taskId, notes }) => {
    if (!apiClient) return;
    try {
      if (!navigator.onLine) {
        await syncEngineRef.current?.queueOperation('timer_start', { projectId, taskId, notes });
        showToast('Offline: timer start queued for sync', 'info');
        setStartTimerOpen(false);
        return;
      }
      await apiClient.startTimer({ projectId, taskId, notes });
      setStartTimerOpen(false);
      await refreshCoreData();
      showToast('Timer started', 'success');
    } catch (error) {
      showToast(classifyAxiosError(error).message, 'error');
    }
  };

  const stopTimer = async () => {
    if (!apiClient) return;
    try {
      if (!navigator.onLine) {
        await syncEngineRef.current?.queueOperation('timer_stop', {});
        showToast('Offline: timer stop queued for sync', 'info');
        return;
      }
      await apiClient.stopTimer();
      await refreshCoreData();
      showToast('Timer stopped', 'success');
    } catch (error) {
      showToast(classifyAxiosError(error).message, 'error');
    }
  };

  const pauseTimer = async () => {
    if (!apiClient) return;
    try {
      await apiClient.pauseTimer();
      await refreshCoreData();
      showToast('Timer paused', 'success');
    } catch (error) {
      showToast(classifyAxiosError(error).message, 'error');
    }
  };

  const resumeTimer = async () => {
    if (!apiClient) return;
    try {
      await apiClient.resumeTimer();
      await refreshCoreData();
      showToast('Timer resumed', 'success');
    } catch (error) {
      showToast(classifyAxiosError(error).message, 'error');
    }
  };

  const handleAttendanceAction = async (action) => {
    if (!apiClient) return;
    setAttendanceLoading(true);
    try {
      const status = await runAttendanceAction(apiClient, action);
      setAttendance(status);
      if (action !== 'refresh') showToast('Workday updated', 'success');
    } catch (error) {
      showToast(formatAttendanceError(error), 'error');
    } finally {
      setAttendanceLoading(false);
    }
  };

  useEffect(() => {
    if (!apiClient || !window.electronAPI) return undefined;
    const handleTray = async (action) => {
      if (action === 'start-timer') {
        if (data.timer?.active) return;
        if (data.projects?.length) await startTimer({ projectId: data.projects[0].id, taskId: null, notes: '' });
        else {
          setStartTimerOpen(true);
          window.electronAPI?.showWindow?.();
        }
      } else if (action === 'stop-timer' && data.timer?.active) {
        await stopTimer();
      } else if (action === 'pause-timer' && data.timer?.active && !isTimerPaused(data.timer)) {
        await pauseTimer();
      } else if (action === 'resume-timer' && data.timer?.active && isTimerPaused(data.timer)) {
        await resumeTimer();
      }
    };
    const handleShortcut = async (action) => {
      if (action !== 'toggle-timer') return;
      if (data.timer?.active) await stopTimer();
      else if (data.projects?.length) await startTimer({ projectId: data.projects[0].id, taskId: null, notes: '' });
      else {
        setStartTimerOpen(true);
        window.electronAPI?.showWindow?.();
      }
    };
    window.electronAPI.onTrayAction?.(handleTray);
    window.electronAPI.onShortcutAction?.(handleShortcut);
    return undefined;
  }, [apiClient, data.timer, data.projects]);

  const createTimeEntry = async (payload) => {
    if (!apiClient) return;
    try {
      if (!navigator.onLine) {
        await syncEngineRef.current?.queueOperation('time_entry_create', payload);
        showToast('Offline: time entry queued for sync', 'info');
        setNewEntryOpen(false);
        return;
      }
      await apiClient.createTimeEntry(payload);
      setNewEntryOpen(false);
      await refreshCoreData();
      showToast('Time entry created', 'success');
    } catch (error) {
      showToast(classifyAxiosError(error).message, 'error');
    }
  };

  const filteredProjects = useMemo(() => {
    const q = filters.project.trim().toLowerCase();
    if (!q) return data.projects;
    return data.projects.filter((p) => String(p.name || '').toLowerCase().includes(q));
  }, [data.projects, filters.project]);

  const filteredEntries = useMemo(() => {
    const q = filters.entrySearch.trim().toLowerCase();
    if (!q) return data.entries;
    return data.entries.filter((entry) => {
      const haystack = [entry.project_name, entry.task_name, entry.notes, entry.description].join(' ').toLowerCase();
      return haystack.includes(q);
    });
  }, [data.entries, filters.entrySearch]);

  if (booting) return <LoadingScreen />;

  if (!apiClient) {
    return (
      <AuthFlow
        step={authStep}
        setStep={setAuthStep}
        serverUrl={serverUrl}
        setServerUrl={setServerUrl}
        username={username}
        setUsername={setUsername}
        password={password}
        setPassword={setPassword}
        error={authError}
        info={authInfo}
        diagnostics={diagnostics}
        connection={connection}
        onTestServer={handleServerTest}
        onLogin={handleLogin}
        theme={theme}
        setTheme={setTheme}
      />
    );
  }

  return (
    <div className="app-shell">
      <Sidebar activeView={activeView} onChange={changeView} />
      <main className="workspace">
        <TopBar
          connection={connection}
          user={data.user}
          syncStatus={syncStatus}
          theme={theme}
          setTheme={setTheme}
          onSyncNow={() => syncEngineRef.current?.syncNow()}
          onLogout={handleLogout}
        />
        <section className="view-frame">
          {activeView === 'dashboard' && (
            <DashboardView
              data={data}
              loading={loading.core}
              onRefresh={refreshCoreData}
              onStart={() => setStartTimerOpen(true)}
              onStop={stopTimer}
              onPause={pauseTimer}
              onResume={resumeTimer}
              syncStatus={syncStatus}
              attendance={attendance}
              onAttendanceAction={handleAttendanceAction}
              attendanceLoading={attendanceLoading}
            />
          )}
          {activeView === 'projects' && (
            <ProjectsView
              projects={filteredProjects}
              filter={filters.project}
              setFilter={(value) => setFilters((f) => ({ ...f, project: value }))}
              loading={loading.core}
            />
          )}
          {activeView === 'entries' && (
            <EntriesView
              entries={filteredEntries}
              filter={filters.entrySearch}
              setFilter={(value) => setFilters((f) => ({ ...f, entrySearch: value }))}
              onNew={() => setNewEntryOpen(true)}
              loading={loading.core}
            />
          )}
          {activeView === 'reports' && (
            <ReportsView projects={data.projects} apiClient={apiClient} showToast={showToast} />
          )}
          {activeView === 'kanban' && (
            <KanbanView projects={data.projects} apiClient={apiClient} showToast={showToast} />
          )}
          {activeView === 'crm' && (
            <CrmView clients={data.clients} apiClient={apiClient} showToast={showToast} />
          )}
          {activeView === 'invoices' && (
            <InvoicesView
              invoices={data.invoices}
              projects={data.projects}
              clients={data.clients}
              loading={loading.invoices}
              apiClient={apiClient}
              onRefresh={() => loadView('invoices')}
              showToast={showToast}
            />
          )}
          {activeView === 'expenses' && (
            <ExpensesView
              expenses={data.expenses}
              projects={data.projects}
              loading={loading.expenses}
              apiClient={apiClient}
              onRefresh={() => loadView('expenses')}
              showToast={showToast}
            />
          )}
          {activeView === 'payments' && (
            <FinanceExtraView
              kind="payments"
              title="Payments"
              subtitle="Record and review payments."
              clients={data.clients}
              projects={data.projects}
              invoices={data.invoices}
              apiClient={apiClient}
              showToast={showToast}
            />
          )}
          {activeView === 'mileage' && (
            <FinanceExtraView
              kind="mileage"
              title="Mileage"
              subtitle="Log trips (GPS tracking stays in the web app)."
              clients={data.clients}
              projects={data.projects}
              invoices={data.invoices}
              apiClient={apiClient}
              showToast={showToast}
            />
          )}
          {activeView === 'quotes' && (
            <FinanceExtraView
              kind="quotes"
              title="Quotes"
              subtitle="Create and review quotes."
              clients={data.clients}
              projects={data.projects}
              invoices={data.invoices}
              apiClient={apiClient}
              showToast={showToast}
            />
          )}
          {activeView === 'recurring' && (
            <FinanceExtraView
              kind="recurring"
              title="Recurring invoices"
              subtitle="List schedules and generate invoices."
              clients={data.clients}
              projects={data.projects}
              invoices={data.invoices}
              apiClient={apiClient}
              showToast={showToast}
            />
          )}
          {activeView === 'credit' && (
            <FinanceExtraView
              kind="credit"
              title="Credit notes"
              subtitle="Create and review credit notes."
              clients={data.clients}
              projects={data.projects}
              invoices={data.invoices}
              apiClient={apiClient}
              showToast={showToast}
            />
          )}
          {activeView === 'workforce' && (
            <WorkforceView
              workforce={data.workforce}
              user={data.user}
              invoiceApprovals={data.invoiceApprovals}
              timeEntryApprovals={data.timeEntryApprovals}
              loading={loading.workforce}
              apiClient={apiClient}
              onRefresh={() => loadView('workforce')}
              showToast={showToast}
            />
          )}
          {activeView === 'settings' && (
            <SettingsView
              serverUrl={serverUrl}
              setServerUrl={setServerUrl}
              username={username}
              setUsername={setUsername}
              settings={settings}
              setSettings={setSettings}
              syncStatus={syncStatus}
              theme={theme}
              setTheme={setTheme}
              onSave={async ({ nextUrl, nextUsername, nextPassword, nextSettings }) => {
                setServerUrl(nextUrl);
                setUsername(nextUsername);
                setSettings(nextSettings);
                if (nextPassword) {
                  await handleLogin(
                    { preventDefault() {} },
                    { serverUrl: nextUrl, username: nextUsername, password: nextPassword },
                  );
                }
                await storeSet('auto_sync', nextSettings.autoSync);
                await storeSet('sync_interval', nextSettings.syncInterval);
                showToast('Settings saved', 'success');
              }}
              onReset={handleReset}
              onSyncNow={() => syncEngineRef.current?.syncNow()}
            />
          )}
        </section>
      </main>
      {startTimerOpen && (
        <StartTimerDialog
          projects={data.projects}
          tasks={data.tasks}
          onClose={() => setStartTimerOpen(false)}
          onSubmit={startTimer}
        />
      )}
      {newEntryOpen && (
        <TimeEntryDialog
          projects={data.projects}
          tasks={data.tasks}
          onClose={() => setNewEntryOpen(false)}
          onSubmit={createTimeEntry}
        />
      )}
      {toast && <Toast toast={toast} />}
    </div>
  );
}

createRoot(document.getElementById('root')).render(<App />);
