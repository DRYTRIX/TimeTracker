import React from 'react';
import { classifyAxiosError } from '../services/api.js';
import { EmptyState, Panel } from '../components/ui.jsx';

export function WorkdayCard({ attendance, loading, onAction }) {
  const data = attendance?.data || attendance || {};
  const workActive = Boolean(data.work_active);
  const breakActive = Boolean(data.break_active);

  return (
    <Panel
      title="Workday"
      action={
        <button className="btn small" onClick={() => onAction('refresh')} disabled={loading}>
          {loading ? '…' : 'Refresh'}
        </button>
      }
    >
      <div className="workday-card">
        <div>
          <strong>{workActive ? 'At work' : 'Not clocked in'}</strong>
          {breakActive && <p className="hint">On break</p>}
        </div>
        <div className="button-row">
          {!workActive ? (
            <button className="btn primary" disabled={loading} onClick={() => onAction('start')}>
              Start workday
            </button>
          ) : (
            <>
              <button className="btn danger" disabled={loading} onClick={() => onAction('end')}>
                End workday
              </button>
              {!breakActive ? (
                <button className="btn" disabled={loading} onClick={() => onAction('break_start')}>
                  Start break
                </button>
              ) : (
                <button className="btn primary" disabled={loading} onClick={() => onAction('break_end')}>
                  End break
                </button>
              )}
            </>
          )}
        </div>
      </div>
      {!attendance && !loading && <EmptyState title="Attendance unavailable" text="Workday module may be disabled on this server." />}
    </Panel>
  );
}

export async function runAttendanceAction(apiClient, action) {
  if (action === 'refresh') return apiClient.getAttendanceStatus();
  if (action === 'start') {
    await apiClient.startWorkday({ source: 'desktop' });
    return apiClient.getAttendanceStatus();
  }
  if (action === 'end') {
    await apiClient.endWorkday();
    return apiClient.getAttendanceStatus();
  }
  if (action === 'break_start') {
    await apiClient.startBreak({ breakType: 'rest' });
    return apiClient.getAttendanceStatus();
  }
  if (action === 'break_end') {
    await apiClient.endBreak();
    return apiClient.getAttendanceStatus();
  }
  throw new Error(`Unknown attendance action: ${action}`);
}

export function formatAttendanceError(error) {
  return classifyAxiosError(error).message;
}
