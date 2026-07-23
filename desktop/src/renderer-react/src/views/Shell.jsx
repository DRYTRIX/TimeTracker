import React from 'react';
import { ConnectionPill, DiagnosticsPanel, ThemeSwitch } from '../components/ui.jsx';

export function AuthFlow(props) {
  const {
    step,
    setStep,
    serverUrl,
    setServerUrl,
    username,
    setUsername,
    password,
    setPassword,
    error,
    info,
    diagnostics,
    connection,
    onTestServer,
    onLogin,
    theme,
    setTheme,
  } = props;
  return (
    <div className="auth-shell">
      <section className="auth-card">
        <div className="auth-brand">
          <img src="../assets/logo.svg" alt="" />
          <div>
            <p className="eyebrow">Desktop workspace</p>
            <h1>Connect to TimeTracker</h1>
            <p>Use your server URL and normal TimeTracker account.</p>
          </div>
        </div>
        <div className="stepper" aria-label="Setup progress">
          <span className={step === 'server' ? 'active' : ''}>1. Server</span>
          <span className={step === 'credentials' ? 'active' : ''}>2. Sign in</span>
        </div>
        {step === 'server' ? (
          <div className="form-grid">
            <label>
              Server URL
              <input value={serverUrl} onChange={(e) => setServerUrl(e.target.value)} placeholder="https://127.0.0.1" />
            </label>
            <p className="hint">Use the base URL only. For your Docker stack this is usually https://127.0.0.1.</p>
            <button className="btn primary" onClick={onTestServer}>
              Test server
            </button>
          </div>
        ) : (
          <form className="form-grid" onSubmit={onLogin}>
            <label>
              Server URL
              <input value={serverUrl} onChange={(e) => setServerUrl(e.target.value)} />
            </label>
            <label>
              Username
              <input value={username} onChange={(e) => setUsername(e.target.value)} autoComplete="username" />
            </label>
            <label>
              Password
              <input
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                type="password"
                autoComplete="current-password"
              />
            </label>
            <div className="button-row">
              <button type="button" className="btn ghost" onClick={() => setStep('server')}>
                Back
              </button>
              <button className="btn primary" type="submit">
                Sign in
              </button>
            </div>
          </form>
        )}
        {info && <div className="message success">{info}</div>}
        {error && <div className="message error">{error}</div>}
        {diagnostics && <DiagnosticsPanel diagnostics={diagnostics} />}
        <div className="auth-footer">
          <ConnectionPill connection={connection} />
          <ThemeSwitch theme={theme} setTheme={setTheme} />
        </div>
      </section>
      <aside className="auth-hero">
        <p className="eyebrow">Modern offline-ready app</p>
        <h2>Track time, sync safely, stay in control.</h2>
        <ul>
          <li>Server diagnostics for bad URLs, TLS, and network issues.</li>
          <li>Local cache and queued writes when your network drops.</li>
          <li>Light, dark, and system theme modes.</li>
        </ul>
      </aside>
    </div>
  );
}

export const NAV_GROUPS = [
  {
    label: 'Work',
    items: [
      { id: 'dashboard', label: 'Dashboard' },
      { id: 'projects', label: 'Projects' },
      { id: 'entries', label: 'Time Entries' },
      { id: 'kanban', label: 'Kanban' },
      { id: 'reports', label: 'Reports' },
    ],
  },
  {
    label: 'CRM',
    items: [{ id: 'crm', label: 'CRM' }],
  },
  {
    label: 'Finance',
    items: [
      { id: 'invoices', label: 'Invoices' },
      { id: 'expenses', label: 'Expenses' },
      { id: 'payments', label: 'Payments' },
      { id: 'mileage', label: 'Mileage' },
      { id: 'quotes', label: 'Quotes' },
      { id: 'recurring', label: 'Recurring' },
      { id: 'credit', label: 'Credit notes' },
    ],
  },
  {
    label: 'Workforce',
    items: [{ id: 'workforce', label: 'Workforce' }],
  },
  {
    label: 'App',
    items: [{ id: 'settings', label: 'Settings' }],
  },
];

export function Sidebar({ activeView, onChange }) {
  return (
    <aside className="sidebar">
      <div className="sidebar-brand">
        <img src="../assets/logo.svg" alt="" />
        <div>
          <strong>TimeTracker</strong>
          <span>Desktop 5.9.3</span>
        </div>
      </div>
      <nav>
        {NAV_GROUPS.map((group) => (
          <div className="nav-group" key={group.label}>
            <p className="nav-group-label">{group.label}</p>
            {group.items.map((view) => (
              <button
                key={view.id}
                className={activeView === view.id ? 'active' : ''}
                onClick={() => onChange(view.id)}
                aria-current={activeView === view.id ? 'page' : undefined}
              >
                {view.label}
              </button>
            ))}
          </div>
        ))}
      </nav>
    </aside>
  );
}

export function TopBar({ connection, user, syncStatus, theme, setTheme, onSyncNow, onLogout }) {
  return (
    <header className="topbar">
      <div>
        <p className="eyebrow">Welcome{user?.username ? `, ${user.username}` : ''}</p>
        <h1>{new Date().toLocaleDateString(undefined, { weekday: 'long', month: 'long', day: 'numeric' })}</h1>
      </div>
      <div className="topbar-actions">
        <ConnectionPill connection={connection} />
        <button className="sync-pill" onClick={onSyncNow} title={syncStatus.lastError || 'Sync now'}>
          {syncStatus.syncing ? 'Syncing…' : `Queue ${syncStatus.queueDepth}`}
        </button>
        <ThemeSwitch theme={theme} setTheme={setTheme} />
        <button className="btn ghost" onClick={onLogout}>
          Sign out
        </button>
      </div>
    </header>
  );
}
