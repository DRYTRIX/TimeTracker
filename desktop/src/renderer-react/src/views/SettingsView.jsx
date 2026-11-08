import React, { useCallback, useEffect, useState } from 'react';
import { Panel, ThemeSwitch, ViewHeader } from '../components/ui.jsx';
import { getLocale, listLocales, setLocale, t } from '../i18n/i18n.js';
import { storeSet } from '../services/store.js';

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
    syncEngine,
  } = props;
  const [password, setPassword] = useState('');
  const [locale, setLocaleState] = useState(getLocale());
  const [failedItems, setFailedItems] = useState([]);
  const [failedLoading, setFailedLoading] = useState(false);

  const refreshFailed = useCallback(async () => {
    if (!syncEngine?.listFailed) {
      setFailedItems([]);
      return;
    }
    setFailedLoading(true);
    try {
      const items = await syncEngine.listFailed();
      setFailedItems(items || []);
    } finally {
      setFailedLoading(false);
    }
  }, [syncEngine]);

  useEffect(() => {
    refreshFailed();
  }, [refreshFailed, syncStatus.failedDepth, syncStatus.queueDepth, syncStatus.lastSyncAt]);

  const handleLocaleChange = async (next) => {
    setLocale(next);
    setLocaleState(next);
    await storeSet('locale', next);
    try {
      window.localStorage?.setItem('tt_desktop_locale', next);
    } catch {
      /* ignore */
    }
  };

  const handleRetry = async (id) => {
    await syncEngine?.retryItem?.(id);
    await refreshFailed();
    await onSyncNow?.();
  };

  const handleDiscard = async (id) => {
    await syncEngine?.discardItem?.(id);
    await refreshFailed();
  };

  const lastSyncLabel = syncStatus.lastSyncAt
    ? new Date(syncStatus.lastSyncAt).toLocaleString()
    : t('common.never');

  return (
    <div className="view-stack">
      <ViewHeader title={t('settings.title')} subtitle={t('settings.subtitle')} />
      <div className="settings-grid">
        <Panel title={t('settings.connection')}>
          <label>
            {t('settings.serverUrl')}
            <input value={serverUrl} onChange={(e) => setServerUrl(e.target.value)} />
          </label>
          <label>
            {t('settings.username')}
            <input value={username} onChange={(e) => setUsername(e.target.value)} />
          </label>
          <label>
            {t('settings.password')}
            <input
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              type="password"
              placeholder={t('settings.passwordPlaceholder')}
            />
          </label>
          <button
            className="btn primary"
            onClick={() =>
              onSave({ nextUrl: serverUrl, nextUsername: username, nextPassword: password, nextSettings: settings })
            }
          >
            {t('settings.saveSettings')}
          </button>
          <p className="hint">{t('settings.oidcHint')}</p>
        </Panel>
        <Panel title={t('settings.appearance')}>
          <ThemeSwitch theme={theme} setTheme={setTheme} expanded />
          <label>
            {t('settings.locale')}
            <select value={locale} onChange={(e) => handleLocaleChange(e.target.value)}>
              {listLocales().map((code) => (
                <option key={code} value={code}>
                  {code}
                </option>
              ))}
            </select>
          </label>
          <p className="hint">{t('settings.language')}: {locale}</p>
        </Panel>
        <Panel title={t('settings.offlineSync')}>
          <label className="switch-row">
            <input
              type="checkbox"
              checked={settings.autoSync}
              onChange={(e) => setSettings((s) => ({ ...s, autoSync: e.target.checked }))}
            />{' '}
            {t('settings.autoSync')}
          </label>
          <label>
            {t('settings.intervalSeconds')}
            <input
              type="number"
              min="10"
              value={settings.syncInterval}
              onChange={(e) => setSettings((s) => ({ ...s, syncInterval: Number(e.target.value || 60) }))}
            />
          </label>
          <p className="hint">
            {t('settings.queueDepth', { count: syncStatus.queueDepth, lastSync: lastSyncLabel })}
          </p>
          {syncStatus.lastError && <p className="message error">{syncStatus.lastError}</p>}
          <div className="button-row">
            <button className="btn" onClick={onSyncNow}>
              {t('settings.syncNow')}
            </button>
            <button className="btn danger" onClick={onReset}>
              {t('settings.resetApp')}
            </button>
          </div>
        </Panel>
        <Panel title={t('settings.syncProblems')}>
          <p className="hint">{t('settings.syncProblemsHint')}</p>
          {failedLoading && <p className="hint">{t('dashboard.refreshing')}</p>}
          {!failedLoading && failedItems.length === 0 && (
            <p className="hint">{t('settings.syncProblemsEmpty')}</p>
          )}
          {failedItems.length > 0 && (
            <ul className="failed-sync-list">
              {failedItems.map((item) => (
                <li key={item.id} className="failed-sync-item">
                  <div>
                    <strong>
                      {t('settings.failedItemType')}: {item.type}
                    </strong>
                    <p className="hint">{t('settings.failedAttempts', { count: item.attempts || 0 })}</p>
                    <p className="message error">
                      {t('settings.failedItemError')}: {item.lastError || t('common.none')}
                    </p>
                  </div>
                  <div className="button-row">
                    <button className="btn small" onClick={() => handleRetry(item.id)}>
                      {t('common.retry')}
                    </button>
                    <button className="btn small danger" onClick={() => handleDiscard(item.id)}>
                      {t('common.discard')}
                    </button>
                  </div>
                </li>
              ))}
            </ul>
          )}
        </Panel>
      </div>
    </div>
  );
}
