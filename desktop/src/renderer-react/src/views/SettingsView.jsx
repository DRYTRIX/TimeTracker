import React, { useCallback, useEffect, useState } from 'react';
import { Panel, ThemeSwitch, ViewHeader } from '../components/ui.jsx';
import { getLocale, listLocales, setLocale, t } from '../i18n/i18n.js';
import { storeGet, storeSet } from '../services/store.js';

const defaultActivitySettings = {
  enabled: false,
  intervalSec: 60,
  exclusionsText: '',
  retentionDays: 14,
  awSync: false,
  awHost: '127.0.0.1',
  awPort: 5600,
};

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
  const [activity, setActivity] = useState(defaultActivitySettings);
  const [activityStatus, setActivityStatus] = useState(null);
  const [activityMessage, setActivityMessage] = useState('');

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

  const refreshActivityStatus = useCallback(async () => {
    try {
      const status = await window.electronAPI?.activityTrackerStatus?.();
      setActivityStatus(status || null);
    } catch {
      setActivityStatus(null);
    }
  }, []);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      const enabled = Boolean(await storeGet('activity_tracker_enabled'));
      const intervalSec = Number(await storeGet('activity_tracker_interval_sec')) || 60;
      const exclusions = (await storeGet('activity_tracker_exclusions')) || [];
      const retentionDays = Number(await storeGet('activity_tracker_retention_days')) || 14;
      const awSync = Boolean(await storeGet('activity_tracker_aw_sync'));
      const awHost = (await storeGet('activity_tracker_aw_host')) || '127.0.0.1';
      const awPort = Number(await storeGet('activity_tracker_aw_port')) || 5600;
      if (cancelled) return;
      setActivity({
        enabled,
        intervalSec,
        exclusionsText: Array.isArray(exclusions) ? exclusions.join('\n') : String(exclusions || ''),
        retentionDays,
        awSync,
        awHost,
        awPort,
      });
      await refreshActivityStatus();
    })();
    return () => {
      cancelled = true;
    };
  }, [refreshActivityStatus]);

  const saveActivitySettings = async () => {
    const exclusions = activity.exclusionsText
      .split(/[\n,]/)
      .map((s) => s.trim())
      .filter(Boolean);
    await storeSet('activity_tracker_enabled', Boolean(activity.enabled));
    await storeSet('activity_tracker_interval_sec', Math.max(15, Number(activity.intervalSec) || 60));
    await storeSet('activity_tracker_exclusions', exclusions);
    await storeSet('activity_tracker_retention_days', Math.max(1, Number(activity.retentionDays) || 14));
    await storeSet('activity_tracker_aw_sync', Boolean(activity.awSync));
    await storeSet('activity_tracker_aw_host', String(activity.awHost || '127.0.0.1').trim());
    await storeSet('activity_tracker_aw_port', Number(activity.awPort) || 5600);
    await window.electronAPI?.activityTrackerRestart?.();
    setActivityMessage(t('settings.activityTrackerSave'));
    await refreshActivityStatus();
  };

  const handlePurgeActivity = async () => {
    await window.electronAPI?.activityTrackerPurge?.();
    setActivityMessage(t('settings.activityTrackerPurge'));
    await refreshActivityStatus();
  };

  const handleSyncActivity = async () => {
    const result = await window.electronAPI?.activityTrackerSync?.();
    setActivityMessage(result?.message || result?.error || '');
    await refreshActivityStatus();
  };

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
        <Panel title={t('settings.activityTracker')}>
          <p className="hint">{t('settings.activityTrackerHint')}</p>
          <label className="switch-row">
            <input
              type="checkbox"
              checked={activity.enabled}
              onChange={(e) => setActivity((s) => ({ ...s, enabled: e.target.checked }))}
            />{' '}
            {t('settings.activityTrackerEnable')}
          </label>
          <label>
            {t('settings.activityTrackerInterval')}
            <input
              type="number"
              min="15"
              value={activity.intervalSec}
              onChange={(e) => setActivity((s) => ({ ...s, intervalSec: Number(e.target.value || 60) }))}
            />
          </label>
          <label>
            {t('settings.activityTrackerExclusions')}
            <textarea
              rows={4}
              value={activity.exclusionsText}
              placeholder={t('settings.activityTrackerExclusionsPlaceholder')}
              onChange={(e) => setActivity((s) => ({ ...s, exclusionsText: e.target.value }))}
            />
          </label>
          <label>
            {t('settings.activityTrackerRetention')}
            <input
              type="number"
              min="1"
              max="90"
              value={activity.retentionDays}
              onChange={(e) => setActivity((s) => ({ ...s, retentionDays: Number(e.target.value || 14) }))}
            />
          </label>
          <label className="switch-row">
            <input
              type="checkbox"
              checked={activity.awSync}
              onChange={(e) => setActivity((s) => ({ ...s, awSync: e.target.checked }))}
            />{' '}
            {t('settings.activityTrackerAwSync')}
          </label>
          <label>
            {t('settings.activityTrackerAwHost')}
            <input
              value={activity.awHost}
              onChange={(e) => setActivity((s) => ({ ...s, awHost: e.target.value }))}
            />
          </label>
          <label>
            {t('settings.activityTrackerAwPort')}
            <input
              type="number"
              min="1"
              value={activity.awPort}
              onChange={(e) => setActivity((s) => ({ ...s, awPort: Number(e.target.value || 5600) }))}
            />
          </label>
          <p className="hint">
            {t('settings.activityTrackerStatus', {
              count: activityStatus?.sampleCount ?? 0,
              unsynced: activityStatus?.unsyncedCount ?? 0,
              last: activityStatus?.lastSampleAt
                ? new Date(activityStatus.lastSampleAt).toLocaleString()
                : t('common.never'),
            })}
          </p>
          {activityMessage && <p className="message success">{activityMessage}</p>}
          <div className="button-row">
            <button className="btn primary" type="button" onClick={saveActivitySettings}>
              {t('settings.activityTrackerSave')}
            </button>
            <button className="btn" type="button" onClick={handleSyncActivity}>
              {t('settings.activityTrackerSyncNow')}
            </button>
            <button className="btn danger" type="button" onClick={handlePurgeActivity}>
              {t('settings.activityTrackerPurge')}
            </button>
          </div>
        </Panel>
      </div>
    </div>
  );
}
