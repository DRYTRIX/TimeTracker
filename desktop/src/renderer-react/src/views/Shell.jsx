import React from 'react';
import { ConnectionPill, DiagnosticsPanel, ThemeSwitch } from '../components/ui.jsx';
import { t } from '../i18n/i18n.js';

const APP_VERSION = typeof __APP_VERSION__ !== 'undefined' ? __APP_VERSION__ : 'dev';

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
    authPhase,
    totpCode,
    setTotpCode,
    onBackFrom2fa,
    apiTokenPaste,
    setApiTokenPaste,
    onConnectWithToken,
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
        ) : authPhase === '2fa' ? (
          <form className="form-grid" onSubmit={onLogin}>
            <p className="hint">Enter the 6-digit code from your authenticator app.</p>
            <label>
              Authentication code
              <input
                value={totpCode}
                onChange={(e) => setTotpCode(e.target.value)}
                inputMode="numeric"
                autoComplete="one-time-code"
                placeholder="123456"
              />
            </label>
            <div className="button-row">
              <button type="button" className="btn ghost" onClick={onBackFrom2fa}>
                Back
              </button>
              <button className="btn primary" type="submit">
                Verify
              </button>
            </div>
          </form>
        ) : (
          <>
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
            <div className="form-grid auth-token-paste">
              <p className="hint">
                OIDC-only servers: create an API token in the web admin (Admin → API tokens) and paste it below.
              </p>
              <label>
                Or paste API token
                <input
                  value={apiTokenPaste}
                  onChange={(e) => setApiTokenPaste(e.target.value)}
                  type="password"
                  placeholder="tt_…"
                  autoComplete="off"
                />
              </label>
              <button type="button" className="btn" onClick={onConnectWithToken}>
                Connect with token
              </button>
            </div>
          </>
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
    labelKey: 'nav.groups.work',
    items: [
      { id: 'dashboard', labelKey: 'nav.dashboard' },
      { id: 'projects', labelKey: 'nav.projects' },
      { id: 'entries', labelKey: 'nav.entries' },
      { id: 'kanban', labelKey: 'nav.kanban' },
      { id: 'reports', labelKey: 'nav.reports' },
    ],
  },
  {
    labelKey: 'nav.groups.crm',
    items: [{ id: 'crm', labelKey: 'nav.crm' }],
  },
  {
    labelKey: 'nav.groups.finance',
    items: [
      { id: 'invoices', labelKey: 'nav.invoices' },
      { id: 'expenses', labelKey: 'nav.expenses' },
      { id: 'payments', labelKey: 'nav.payments' },
      { id: 'mileage', labelKey: 'nav.mileage' },
      { id: 'quotes', labelKey: 'nav.quotes' },
      { id: 'recurring', labelKey: 'nav.recurring' },
      { id: 'credit', labelKey: 'nav.credit' },
    ],
  },
  {
    labelKey: 'nav.groups.workforce',
    items: [{ id: 'workforce', labelKey: 'nav.workforce' }],
  },
  {
    labelKey: 'nav.groups.app',
    items: [{ id: 'settings', labelKey: 'nav.settings' }],
  },
];

export function Sidebar({ activeView, onChange }) {
  return (
    <aside className="sidebar">
      <div className="sidebar-brand">
        <img src="../assets/logo.svg" alt="" />
        <div>
          <strong>TimeTracker</strong>
          <span>{`Desktop ${APP_VERSION}`}</span>
        </div>
      </div>
      <nav>
        {NAV_GROUPS.map((group) => (
          <div className="nav-group" key={group.labelKey}>
            <p className="nav-group-label">{t(group.labelKey)}</p>
            {group.items.map((view) => (
              <button
                key={view.id}
                className={activeView === view.id ? 'active' : ''}
                onClick={() => onChange(view.id)}
                aria-current={activeView === view.id ? 'page' : undefined}
              >
                {t(view.labelKey)}
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
