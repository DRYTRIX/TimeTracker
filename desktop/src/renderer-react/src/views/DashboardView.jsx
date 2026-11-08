import React, { useEffect, useState } from 'react';
import { EntryList, Panel, StatCard } from '../components/ui.jsx';
import { t } from '../i18n/i18n.js';
import { formatDuration, isTimerPaused, timerElapsedSeconds } from '../utils/format.js';
import { WorkdayCard } from './WorkdayCard.jsx';

export function DashboardView({
  data,
  loading,
  onRefresh,
  onStart,
  onStop,
  onPause,
  onResume,
  syncStatus,
  attendance,
  onAttendanceAction,
  attendanceLoading,
}) {
  const active = data.timer?.active;
  const paused = isTimerPaused(data.timer);
  const [tick, setTick] = useState(0);
  useEffect(() => {
    if (!active || paused) return undefined;
    const id = window.setInterval(() => setTick((n) => n + 1), 1000);
    return () => window.clearInterval(id);
  }, [active, paused]);
  void tick;
  const seconds = timerElapsedSeconds(data.timer);
  const projectLabel =
    data.timer?.timer?.project || data.timer?.timer?.client || data.timer?.timer?.project_name || t('dashboard.trackingTime');

  return (
    <div className="view-stack">
      <WorkdayCard
        attendance={attendance}
        loading={attendanceLoading}
        onAction={onAttendanceAction}
      />
      <div className="hero-card">
        <div>
          <p className="eyebrow">{t('dashboard.activeTimer')}</p>
          <h2>{active ? formatDuration(seconds) : t('dashboard.noTimer')}</h2>
          <p>
            {active
              ? `${paused ? `${t('dashboard.paused')} · ` : ''}${projectLabel}`
              : t('dashboard.startHint')}
          </p>
        </div>
        <div className="button-row">
          <button className="btn primary" onClick={onStart} disabled={active}>
            {t('dashboard.startTimer')}
          </button>
          {active && !paused && (
            <button className="btn" onClick={onPause}>
              {t('dashboard.pause')}
            </button>
          )}
          {active && paused && (
            <button className="btn primary" onClick={onResume}>
              {t('dashboard.resume')}
            </button>
          )}
          <button className="btn danger" onClick={onStop} disabled={!active}>
            {t('dashboard.stop')}
          </button>
          <button className="btn ghost" onClick={onRefresh}>
            {loading ? t('dashboard.refreshing') : t('common.refresh')}
          </button>
        </div>
      </div>
      <div className="stats-grid">
        <StatCard label={t('dashboard.projects')} value={data.projects.length} />
        <StatCard label={t('dashboard.recentEntries')} value={data.entries.length} />
        <StatCard label={t('dashboard.queuedSync')} value={syncStatus.queueDepth} />
      </div>
      <Panel
        title={t('dashboard.recentTimeEntries')}
        action={
          <button className="btn small" onClick={onRefresh}>
            {t('common.reload')}
          </button>
        }
      >
        <EntryList entries={data.entries.slice(0, 8)} />
      </Panel>
    </div>
  );
}
