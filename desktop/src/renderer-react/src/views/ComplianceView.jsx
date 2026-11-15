import React, { useCallback, useEffect, useState } from 'react';
import { classifyAxiosError } from '../services/api.js';
import { EmptyState, Panel, ViewHeader } from '../components/ui.jsx';

function ymd(date) {
  return date.toISOString().slice(0, 10);
}

function monthRange() {
  const now = new Date();
  const start = new Date(now.getFullYear(), now.getMonth(), 1);
  const end = new Date(now.getFullYear(), now.getMonth() + 1, 0);
  return { start: ymd(start), end: ymd(end) };
}

function extractRecords(payload) {
  const data = payload?.data || payload || {};
  return data.records || data.items || data.days || [];
}

function extractBelgiumRows(payload) {
  const data = payload?.data || payload || {};
  return data.rows || data.records || data.items || [];
}

export function CompliancePanel({ apiClient, showToast }) {
  const range = monthRange();
  const [history, setHistory] = useState([]);
  const [belgiumRows, setBelgiumRows] = useState([]);
  const [startDate, setStartDate] = useState(range.start);
  const [endDate, setEndDate] = useState(range.end);
  const [loading, setLoading] = useState(false);
  const [selectedDay, setSelectedDay] = useState(null);
  const [reason, setReason] = useState('');
  const [startTime, setStartTime] = useState('09:00');
  const [endTime, setEndTime] = useState('17:00');
  const [submitting, setSubmitting] = useState(false);

  const refresh = useCallback(async () => {
    if (!apiClient) return;
    setLoading(true);
    try {
      const [hist, report] = await Promise.all([
        apiClient.getAttendanceHistory({ days: 45 }).catch(() => ({ records: [] })),
        apiClient
          .getBelgiumAttendanceReport({ startDate, endDate })
          .catch(() => ({ rows: [] })),
      ]);
      setHistory(extractRecords(hist));
      setBelgiumRows(extractBelgiumRows(report));
    } catch (error) {
      showToast?.(classifyAxiosError(error).message, 'error');
    } finally {
      setLoading(false);
    }
  }, [apiClient, startDate, endDate, showToast]);

  useEffect(() => {
    refresh();
  }, [refresh]);

  const submitCorrection = async () => {
    if (!selectedDay || !reason.trim()) {
      showToast?.('Select a day and enter a reason.', 'error');
      return;
    }
    const dayId = selectedDay.id || selectedDay.attendance_day_id;
    if (!dayId) {
      showToast?.('Missing attendance day id.', 'error');
      return;
    }
    const dateStr = selectedDay.work_date || selectedDay.date || ymd(new Date());
    const startIso = new Date(`${dateStr}T${startTime}:00`).toISOString();
    const endIso = new Date(`${dateStr}T${endTime}:00`).toISOString();
    setSubmitting(true);
    try {
      await apiClient.requestAttendanceCorrection({
        attendanceDayId: dayId,
        entityType: 'AddWorkPeriod',
        entityId: 0,
        reason: reason.trim(),
        correctedValues: { start_time: startIso, end_time: endIso },
      });
      showToast?.('Correction requested', 'success');
      setSelectedDay(null);
      setReason('');
      await refresh();
    } catch (error) {
      showToast?.(classifyAxiosError(error).message, 'error');
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="view-stack">
      <ViewHeader
        title="Belgium compliance"
        subtitle="Attendance history, correction requests, and inspector report."
        action={
          <button className="btn small" onClick={refresh} disabled={loading}>
            {loading ? '…' : 'Refresh'}
          </button>
        }
      />
      <Panel title="Attendance history">
        {!history.length && !loading && (
          <EmptyState title="No attendance days" text="Clock in via Workday on the dashboard to create records." />
        )}
        {history.map((record) => {
          const label = record.work_date || record.date || `#${record.id}`;
          const hours = record.total_hours ?? record.worked_hours ?? record.hours;
          return (
            <div className="list-row" key={record.id || label}>
              <span>
                {label}
                {hours != null ? ` · ${hours}h` : ''}
                {record.status ? ` · ${record.status}` : ''}
              </span>
              <button className="btn small" type="button" onClick={() => setSelectedDay(record)}>
                Request correction
              </button>
            </div>
          );
        })}
      </Panel>
      {selectedDay && (
        <Panel title={`Correction for ${selectedDay.work_date || selectedDay.date || selectedDay.id}`}>
          <label>
            Start time
            <input type="time" value={startTime} onChange={(e) => setStartTime(e.target.value)} />
          </label>
          <label>
            End time
            <input type="time" value={endTime} onChange={(e) => setEndTime(e.target.value)} />
          </label>
          <label>
            Reason *
            <textarea rows={3} value={reason} onChange={(e) => setReason(e.target.value)} />
          </label>
          <div className="button-row">
            <button className="btn primary" type="button" disabled={submitting} onClick={submitCorrection}>
              Submit correction
            </button>
            <button className="btn ghost" type="button" onClick={() => setSelectedDay(null)}>
              Cancel
            </button>
          </div>
        </Panel>
      )}
      <Panel title="Belgium attendance report">
        <div className="button-row" style={{ marginBottom: '0.75rem' }}>
          <label>
            From
            <input type="date" value={startDate} onChange={(e) => setStartDate(e.target.value)} />
          </label>
          <label>
            To
            <input type="date" value={endDate} onChange={(e) => setEndDate(e.target.value)} />
          </label>
          <button className="btn small" type="button" onClick={refresh} disabled={loading}>
            Load report
          </button>
        </div>
        {!belgiumRows.length && !loading && (
          <EmptyState
            title="No report rows"
            text="Enable Belgium compliance on the server, or widen the date range."
          />
        )}
        {belgiumRows.slice(0, 50).map((row, idx) => (
          <div className="list-row" key={row.id || row.work_date || idx}>
            <span>
              {(row.user_name || row.username || row.user || 'User') +
                ' · ' +
                (row.work_date || row.date || '—') +
                (row.total_hours != null ? ` · ${row.total_hours}h` : '')}
            </span>
          </div>
        ))}
      </Panel>
    </div>
  );
}
