import React from 'react';
import { EmptyState, SkeletonGrid, ViewHeader } from '../components/ui.jsx';

export function ProjectsView({ projects, filter, setFilter, loading }) {
  return (
    <div className="view-stack">
      <ViewHeader title="Projects" subtitle="Search and pick work quickly." />
      <input
        className="command-input"
        value={filter}
        onChange={(e) => setFilter(e.target.value)}
        placeholder="Search projects…"
      />
      {loading ? (
        <SkeletonGrid />
      ) : (
        <div className="card-grid">
          {projects.map((project) => (
            <article className="project-card" key={project.id || project.name}>
              <span className="status-dot" />
              <h3>{project.name}</h3>
              <p>{project.client_name || project.status || 'Active project'}</p>
            </article>
          ))}
          {!projects.length && <EmptyState title="No projects found" text="Try a different search or sync with the server." />}
        </div>
      )}
    </div>
  );
}
