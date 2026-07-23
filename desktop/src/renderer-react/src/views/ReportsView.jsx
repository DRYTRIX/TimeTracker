import React, { useState } from 'react';
import { classifyAxiosError } from '../services/api.js';
import { EmptyState, Panel, SkeletonList, StatCard, ViewHeader } from '../components/ui.jsx';
import { daysAgoISO, listItems, todayISO } from '../utils/format.js';

export function ReportsView({ projects, apiClient, showToast }) {
  const [startDate, setStartDate] = useState(daysAgoISO(30));
  const [endDate, setEndDate] = useState(todayISO());
  const [projectId, setProjectId] = useState('');
  const [summary, setSummary] = useState(null);
  const [loading, setLoading] = useState(false);

  const load = async () => {
    setLoading(true);
    try {
      const params = { start_date: startDate, end_date: endDate };
      if (projectId) params.project_id = projectId;
      const payload = await apiClient.getReportSummary(params);
      setSummary(apiClient.unwrapReportSummary(payload));
    } catch (error) {
      showToast(classifyAxiosError(error).message, 'error');
    } finally {
      setLoading(false);
    }
  };

  const byProject = listItems(summary, 'by_project');

  return (
    <div className="view-stack">
      <ViewHeader
        title="Reports"
        subtitle="Hours summary from the server report API."
        action={
          <button className="btn primary" onClick={load} disabled={loading}>
            {loading ? 'Loading…' : 'Run report'}
          </button>
        }
      />
      <div className="form-grid report-filters">
        <label>
          Start
          <input type="date" value={startDate} onChange={(e) => setStartDate(e.target.value)} />
        </label>
        <label>
          End
          <input type="date" value={endDate} onChange={(e) => setEndDate(e.target.value)} />
        </label>
        <label>
          Project
          <select value={projectId} onChange={(e) => setProjectId(e.target.value)}>
            <option value="">All projects</option>
            {projects.map((p) => (
              <option key={p.id} value={p.id}>
                {p.name}
              </option>
            ))}
          </select>
        </label>
      </div>
      {loading && <SkeletonList />}
      {!loading && summary && (
        <>
          <div className="stats-grid">
            <StatCard label="Total hours" value={summary.total_hours ?? '—'} />
            <StatCard label="Billable hours" value={summary.billable_hours ?? '—'} />
            <StatCard label="Entries" value={summary.total_entries ?? '—'} />
          </div>
          <Panel title="By project">
            {byProject.length ? (
              byProject.map((row) => (
                <div className="list-row" key={row.project_id || row.project_name}>
                  <strong>{row.project_name || `Project ${row.project_id}`}</strong>
                  <span>
                    {row.hours}h · {row.entries} entries
                  </span>
                </div>
              ))
            ) : (
              <EmptyState title="No project breakdown" text="Try a wider date range." />
            )}
          </Panel>
        </>
      )}
      {!loading && !summary && <EmptyState title="No report yet" text="Choose a range and run the report." />}
    </div>
  );
}
