import React, { useMemo, useState } from 'react';
import { Dialog } from '../components/ui.jsx';

export function StartTimerDialog({ projects, tasks, clients = [], onClose, onSubmit }) {
  const [clientId, setClientId] = useState('');
  const [projectId, setProjectId] = useState('');
  const [taskId, setTaskId] = useState('');
  const [notes, setNotes] = useState('');

  const filteredProjects = useMemo(() => {
    if (!clientId) return projects;
    return projects.filter(
      (p) => !p.client_id || String(p.client_id) === String(clientId),
    );
  }, [projects, clientId]);

  const filteredTasks = useMemo(
    () => tasks.filter((task) => !projectId || String(task.project_id) === String(projectId)),
    [tasks, projectId],
  );

  const canStart = Boolean(projectId || clientId);

  const handleClientChange = (value) => {
    setClientId(value);
    if (projectId) {
      const stillValid = projects.some(
        (p) =>
          String(p.id) === String(projectId) &&
          (!value || !p.client_id || String(p.client_id) === String(value)),
      );
      if (!stillValid) {
        setProjectId('');
        setTaskId('');
      }
    }
  };

  const handleProjectChange = (value) => {
    setProjectId(value);
    setTaskId('');
    if (value) {
      const project = projects.find((p) => String(p.id) === String(value));
      if (project?.client_id) setClientId(String(project.client_id));
    }
  };

  return (
    <Dialog title="Start timer" onClose={onClose}>
      <label>
        Client
        <select value={clientId} onChange={(e) => handleClientChange(e.target.value)}>
          <option value="">Any client</option>
          {clients.map((c) => (
            <option key={c.id} value={c.id}>
              {c.name}
            </option>
          ))}
        </select>
      </label>
      <label>
        Project {clientId ? '(optional)' : ''}
        <select value={projectId} onChange={(e) => handleProjectChange(e.target.value)}>
          <option value="">{clientId ? 'No project (client-only)' : 'Choose project'}</option>
          {filteredProjects.map((p) => (
            <option key={p.id} value={p.id}>
              {p.name}
            </option>
          ))}
        </select>
      </label>
      <label>
        Task
        <select
          value={taskId}
          onChange={(e) => setTaskId(e.target.value)}
          disabled={!projectId}
        >
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
        <button
          className="btn primary"
          disabled={!canStart}
          onClick={() =>
            onSubmit({
              projectId: projectId || null,
              clientId: projectId ? null : clientId || null,
              taskId: projectId ? taskId || null : null,
              notes,
            })
          }
        >
          Start
        </button>
      </div>
    </Dialog>
  );
}

export function TimeEntryDialog({ projects, tasks, clients = [], onClose, onSubmit }) {
  const [clientId, setClientId] = useState('');
  const [projectId, setProjectId] = useState('');
  const [taskId, setTaskId] = useState('');
  const [notes, setNotes] = useState('');
  const [duration, setDuration] = useState(60);
  const today = new Date().toISOString().slice(0, 10);
  const [date, setDate] = useState(today);
  const [startTime, setStartTime] = useState('09:00');

  const filteredProjects = useMemo(() => {
    if (!clientId) return projects;
    return projects.filter(
      (p) => !p.client_id || String(p.client_id) === String(clientId),
    );
  }, [projects, clientId]);

  const filteredTasks = useMemo(
    () => tasks.filter((task) => !projectId || String(task.project_id) === String(projectId)),
    [tasks, projectId],
  );

  const canCreate = Boolean(projectId || clientId);

  const handleClientChange = (value) => {
    setClientId(value);
    if (projectId) {
      const stillValid = projects.some(
        (p) =>
          String(p.id) === String(projectId) &&
          (!value || !p.client_id || String(p.client_id) === String(value)),
      );
      if (!stillValid) {
        setProjectId('');
        setTaskId('');
      }
    }
  };

  const handleProjectChange = (value) => {
    setProjectId(value);
    setTaskId('');
    if (value) {
      const project = projects.find((p) => String(p.id) === String(value));
      if (project?.client_id) setClientId(String(project.client_id));
    }
  };

  const buildPayload = () => {
    const minutes = Math.max(1, Number(duration) || 0);
    const start = new Date(`${date}T${startTime}:00`);
    if (Number.isNaN(start.getTime())) {
      throw new Error('Invalid start date/time');
    }
    const end = new Date(start.getTime() + minutes * 60 * 1000);
    return {
      project_id: projectId ? Number(projectId) : null,
      client_id: projectId ? null : clientId ? Number(clientId) : null,
      task_id: projectId && taskId ? Number(taskId) : null,
      start_time: start.toISOString(),
      end_time: end.toISOString(),
      notes: notes || null,
    };
  };

  return (
    <Dialog title="New time entry" onClose={onClose}>
      <label>
        Client
        <select value={clientId} onChange={(e) => handleClientChange(e.target.value)}>
          <option value="">Any client</option>
          {clients.map((c) => (
            <option key={c.id} value={c.id}>
              {c.name}
            </option>
          ))}
        </select>
      </label>
      <label>
        Project {clientId ? '(optional)' : ''}
        <select value={projectId} onChange={(e) => handleProjectChange(e.target.value)}>
          <option value="">{clientId ? 'No project (client-only)' : 'Choose project'}</option>
          {filteredProjects.map((p) => (
            <option key={p.id} value={p.id}>
              {p.name}
            </option>
          ))}
        </select>
      </label>
      <label>
        Task
        <select
          value={taskId}
          onChange={(e) => setTaskId(e.target.value)}
          disabled={!projectId}
        >
          <option value="">No task</option>
          {filteredTasks.map((t) => (
            <option key={t.id} value={t.id}>
              {t.name}
            </option>
          ))}
        </select>
      </label>
      <label>
        Date
        <input type="date" value={date} onChange={(e) => setDate(e.target.value)} />
      </label>
      <label>
        Start time
        <input type="time" value={startTime} onChange={(e) => setStartTime(e.target.value)} />
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
          onClick={() => {
            try {
              onSubmit(buildPayload());
            } catch (err) {
              console.error(err);
            }
          }}
          disabled={!canCreate}
        >
          Create
        </button>
      </div>
    </Dialog>
  );
}
