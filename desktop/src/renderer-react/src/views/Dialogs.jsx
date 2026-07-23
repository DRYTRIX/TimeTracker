import React, { useState } from 'react';
import { Dialog } from '../components/ui.jsx';

export function StartTimerDialog({ projects, tasks, onClose, onSubmit }) {
  const [projectId, setProjectId] = useState('');
  const [taskId, setTaskId] = useState('');
  const [notes, setNotes] = useState('');
  const filteredTasks = tasks.filter((task) => !projectId || String(task.project_id) === String(projectId));
  return (
    <Dialog title="Start timer" onClose={onClose}>
      <label>
        Project
        <select value={projectId} onChange={(e) => setProjectId(e.target.value)}>
          <option value="">Choose project</option>
          {projects.map((p) => (
            <option key={p.id} value={p.id}>
              {p.name}
            </option>
          ))}
        </select>
      </label>
      <label>
        Task
        <select value={taskId} onChange={(e) => setTaskId(e.target.value)}>
          <option value="">No task</option>
          {filteredTasks.map((t) => (
            <option key={t.id} value={t.id}>
              {t.name}
            </option>
          ))}
        </select>
      </label>
      <label>
        Notes
        <textarea value={notes} onChange={(e) => setNotes(e.target.value)} />
      </label>
      <div className="button-row">
        <button className="btn ghost" onClick={onClose}>
          Cancel
        </button>
        <button className="btn primary" onClick={() => onSubmit({ projectId, taskId, notes })}>
          Start
        </button>
      </div>
    </Dialog>
  );
}

export function TimeEntryDialog({ projects, tasks, onClose, onSubmit }) {
  const [projectId, setProjectId] = useState('');
  const [taskId, setTaskId] = useState('');
  const [notes, setNotes] = useState('');
  const [duration, setDuration] = useState(60);
  const today = new Date().toISOString().slice(0, 10);
  const filteredTasks = tasks.filter((task) => !projectId || String(task.project_id) === String(projectId));
  return (
    <Dialog title="New time entry" onClose={onClose}>
      <label>
        Project
        <select value={projectId} onChange={(e) => setProjectId(e.target.value)}>
          <option value="">Choose project</option>
          {projects.map((p) => (
            <option key={p.id} value={p.id}>
              {p.name}
            </option>
          ))}
        </select>
      </label>
      <label>
        Task
        <select value={taskId} onChange={(e) => setTaskId(e.target.value)}>
          <option value="">No task</option>
          {filteredTasks.map((t) => (
            <option key={t.id} value={t.id}>
              {t.name}
            </option>
          ))}
        </select>
      </label>
      <label>
        Minutes
        <input type="number" min="1" value={duration} onChange={(e) => setDuration(Number(e.target.value || 0))} />
      </label>
      <label>
        Notes
        <textarea value={notes} onChange={(e) => setNotes(e.target.value)} />
      </label>
      <div className="button-row">
        <button className="btn ghost" onClick={onClose}>
          Cancel
        </button>
        <button
          className="btn primary"
          onClick={() =>
            onSubmit({ project_id: projectId, task_id: taskId || null, duration_minutes: duration, date: today, notes })
          }
        >
          Create
        </button>
      </div>
    </Dialog>
  );
}
