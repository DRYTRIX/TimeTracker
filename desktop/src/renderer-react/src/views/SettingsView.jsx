import React, { useState } from 'react';
import { Panel, ThemeSwitch, ViewHeader } from '../components/ui.jsx';

export function SettingsView(props) {
  const {
    serverUrl,
    setServerUrl,
    username,
    setUsername,
    settings,
    setSettings,
    syncStatus,
    theme,
    setTheme,
    onSave,
    onReset,
    onSyncNow,
  } = props;
  const [password, setPassword] = useState('');
  return (
    <div className="view-stack">
      <ViewHeader title="Settings" subtitle="Server, sign-in, theme, and sync controls." />
      <div className="settings-grid">
        <Panel title="Connection">
          <label>
            Server URL
            <input value={serverUrl} onChange={(e) => setServerUrl(e.target.value)} />
          </label>
          <label>
            Username
            <input value={username} onChange={(e) => setUsername(e.target.value)} />
          </label>
          <label>
            Password
            <input
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              type="password"
              placeholder="Enter to re-authenticate"
            />
          </label>
          <button
            className="btn primary"
            onClick={() =>
              onSave({ nextUrl: serverUrl, nextUsername: username, nextPassword: password, nextSettings: settings })
            }
          >
            Save settings
          </button>
        </Panel>
        <Panel title="Appearance">
          <ThemeSwitch theme={theme} setTheme={setTheme} expanded />
        </Panel>
        <Panel title="Offline sync">
          <label className="switch-row">
            <input
              type="checkbox"
              checked={settings.autoSync}
              onChange={(e) => setSettings((s) => ({ ...s, autoSync: e.target.checked }))}
            />{' '}
            Auto sync
          </label>
          <label>
            Interval seconds
            <input
              type="number"
              min="10"
              value={settings.syncInterval}
              onChange={(e) => setSettings((s) => ({ ...s, syncInterval: Number(e.target.value || 60) }))}
            />
          </label>
          <p className="hint">
            Queue depth: {syncStatus.queueDepth}. Last sync:{' '}
            {syncStatus.lastSyncAt ? new Date(syncStatus.lastSyncAt).toLocaleString() : 'Never'}.
          </p>
          {syncStatus.lastError && <p className="message error">{syncStatus.lastError}</p>}
          <div className="button-row">
            <button className="btn" onClick={onSyncNow}>
              Sync now
            </button>
            <button className="btn danger" onClick={onReset}>
              Reset app
            </button>
          </div>
        </Panel>
      </div>
    </div>
  );
}
