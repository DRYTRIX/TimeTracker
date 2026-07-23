import React from 'react';
import { EntryList, SkeletonList, ViewHeader } from '../components/ui.jsx';

export function EntriesView({ entries, filter, setFilter, onNew, loading }) {
  return (
    <div className="view-stack">
      <ViewHeader
        title="Time entries"
        subtitle="Review recent work and add manual entries."
        action={
          <button className="btn primary" onClick={onNew}>
            New entry
          </button>
        }
      />
      <input
        className="command-input"
        value={filter}
        onChange={(e) => setFilter(e.target.value)}
        placeholder="Search notes, projects, tasks…"
      />
      {loading ? <SkeletonList /> : <EntryList entries={entries} />}
    </div>
  );
}
