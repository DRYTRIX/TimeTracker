import React, { useEffect, useState } from 'react';
import { EntryList, Panel, StatCard } from '../components/ui.jsx';
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
    const id = window.setInterval(() => setTick((t) => t + 1), 1000);
    return () => window.clearInterval(id);
  }, [active, paused]);
  void tick;
  const seconds = timerElapsedSeconds(data.timer);

  return (
    <div className="view-stack">
      <WorkdayCard
        attendance={attendance}
        loading={attendanceLoading}
        onAction={onAttendanceAction}
      />
      <div className="hero-card">
        <div>
          <p className="eyebrow">Active timer</p>
          <h2>{active ? formatDuration(seconds) : 'No timer running'}</h2>
          <p>
            {active
              ? `${paused ? 'Paused · ' : ''}${data.timer?.timer?.project_name || 'Tracking time'}`
              : 'Start a focused session when you are ready.'}
          </p>
        </div>
        <div className="button-row">
          <button className="btn primary" onClick={onStart} disabled={active}>
            Start timer
          </button>
          {active && !paused && (
            <button className="btn" onClick={onPause}>
              Pause
            </button>
          )}
          {active && paused && (
            <button className="btn primary" onClick={onResume}>
              Resume
            </button>
          )}
          <button className="btn danger" onClick={onStop} disabled={!active}>
            Stop
          </button>
          <button className="btn ghost" onClick={onRefresh}>
            {loading ? 'Refreshing…' : 'Refresh'}
          </button>
        </div>
      </div>
      <div className="stats-grid">
        <StatCard label="Projects" value={data.projects.length} />
        <StatCard label="Recent entries" value={data.entries.length} />
        <StatCard label="Queued sync" value={syncStatus.queueDepth} />
      </div>
      <Panel title="Recent time entries" action={<button className="btn small" onClick={onRefresh}>Reload</button>}>
        <EntryList entries={data.entries.slice(0, 8)} />
      </Panel>
    </div>
  );
}
