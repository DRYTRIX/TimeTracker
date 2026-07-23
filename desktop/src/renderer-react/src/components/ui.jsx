import React, { useEffect } from 'react';
import { formatMinutes } from '../utils/format.js';

export function LoadingScreen() {
  return (
    <div className="loading-screen">
      <img src="../assets/logo.svg" alt="TimeTracker" />
      <div className="spinner" />
      <h1>TimeTracker</h1>
      <p>Preparing your workspace…</p>
    </div>
  );
}

export function ViewHeader({ title, subtitle, action }) {
  return (
    <div className="view-header">
      <div>
        <p className="eyebrow">Workspace</p>
        <h2>{title}</h2>
        <p>{subtitle}</p>
      </div>
      {action}
    </div>
  );
}

export function Panel({ title, action, children }) {
  return (
    <section className="panel">
      <div className="panel-head">
        <h3>{title}</h3>
        {action}
      </div>
      {children}
    </section>
  );
}

export function StatCard({ label, value }) {
  return (
    <div className="stat-card">
      <span>{label}</span>
      <strong>{value}</strong>
    </div>
  );
}

export function EmptyState({ title, text }) {
  return (
    <div className="empty-state">
      <h3>{title}</h3>
      <p>{text}</p>
    </div>
  );
}

export function SkeletonGrid() {
  return (
    <div className="card-grid">
      {[1, 2, 3].map((i) => (
        <div className="skeleton-card" key={i} />
      ))}
    </div>
  );
}

export function SkeletonList() {
  return (
    <div className="list-card">
      {[1, 2, 3, 4].map((i) => (
        <div className="skeleton-row" key={i} />
      ))}
    </div>
  );
}

export function ConnectionPill({ connection }) {
  return <span className={`connection-pill ${connection.state}`}>{connection.message || connection.state}</span>;
}

export function ThemeSwitch({ theme, setTheme, expanded }) {
  return (
    <label className={expanded ? 'theme-switch expanded' : 'theme-switch'}>
      {expanded && <span>Theme</span>}
      <select value={theme} onChange={(e) => setTheme(e.target.value)}>
        <option value="system">System</option>
        <option value="light">Light</option>
        <option value="dark">Dark</option>
      </select>
    </label>
  );
}

export function Toast({ toast }) {
  return (
    <div className={`toast ${toast.type}`} role="status">
      {toast.message}
    </div>
  );
}

export function Dialog({ title, children, onClose }) {
  useEffect(() => {
    const handler = (event) => event.key === 'Escape' && onClose();
    window.addEventListener('keydown', handler);
    return () => window.removeEventListener('keydown', handler);
  }, [onClose]);
  return (
    <div className="dialog-backdrop" role="presentation" onMouseDown={onClose}>
      <section className="dialog" role="dialog" aria-modal="true" aria-label={title} onMouseDown={(e) => e.stopPropagation()}>
        <div className="dialog-head">
          <h2>{title}</h2>
          <button className="icon-btn" onClick={onClose}>
            ×
          </button>
        </div>
        <div className="form-grid">{children}</div>
      </section>
    </div>
  );
}

export function DiagnosticsPanel({ diagnostics }) {
  return (
    <details className="diagnostics">
      <summary>Connection diagnostics</summary>
      <ul>
        {diagnostics.checks.map((check) => (
          <li key={check}>{check}</li>
        ))}
      </ul>
      <pre>{diagnostics.technical}</pre>
    </details>
  );
}

export function EntryList({ entries }) {
  if (!entries?.length) return <EmptyState title="No time entries" text="Create one manually or sync with the server." />;
  return (
    <div className="list-card">
      {entries.map((entry, index) => (
        <div className="list-row" key={entry.id || index}>
          <div>
            <strong>{entry.project_name || entry.project?.name || 'Time entry'}</strong>
            <p>{entry.task_name || entry.notes || entry.description || 'No notes'}</p>
          </div>
          <span>{entry.duration_formatted || formatMinutes(entry.duration_minutes || entry.duration || 0)}</span>
        </div>
      ))}
    </div>
  );
}
