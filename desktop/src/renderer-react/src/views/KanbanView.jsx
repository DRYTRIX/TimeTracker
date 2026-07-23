import React, { useEffect, useState } from 'react';
import { classifyAxiosError } from '../services/api.js';
import { EmptyState, SkeletonList, ViewHeader } from '../components/ui.jsx';
import { listItems } from '../utils/format.js';

export function KanbanView({ projects, apiClient, showToast }) {
  const [projectId, setProjectId] = useState('');
  const [columns, setColumns] = useState([]);
  const [tasks, setTasks] = useState([]);
  const [loading, setLoading] = useState(false);
  const [newTaskName, setNewTaskName] = useState('');

  useEffect(() => {
    if (!projectId && projects[0]) setProjectId(String(projects[0].id));
  }, [projects, projectId]);

  const load = async (pid = projectId) => {
    if (!pid) return;
    setLoading(true);
    try {
      const [colsRes, tasksRes] = await Promise.all([
        apiClient.getKanbanColumns({ project_id: pid }),
        apiClient.getTasks({ project_id: pid, per_page: 100 }),
      ]);
      setColumns(listItems(colsRes, 'columns', 'kanban_columns'));
      setTasks(listItems(tasksRes, 'tasks'));
    } catch (error) {
      showToast(classifyAxiosError(error).message, 'error');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (projectId) load(projectId);
  }, [projectId]);

  const moveTask = async (taskId, columnKey) => {
    try {
      await apiClient.updateTask(taskId, { status: columnKey, kanban_column: columnKey });
      showToast('Task moved', 'success');
      await load();
    } catch (error) {
      showToast(classifyAxiosError(error).message, 'error');
    }
  };

  const createTask = async () => {
    if (!projectId || !newTaskName.trim()) return;
    try {
      const firstCol = columns[0];
      await apiClient.createTask({
        project_id: Number(projectId),
        name: newTaskName.trim(),
        status: firstCol?.key || 'todo',
      });
      setNewTaskName('');
      showToast('Task created', 'success');
      await load();
    } catch (error) {
      showToast(classifyAxiosError(error).message, 'error');
    }
  };

  const tasksForColumn = (col) => {
    const key = col.key || col.status || String(col.id);
    return tasks.filter((t) => {
      const status = t.status || t.kanban_column || t.column_key;
      return String(status) === String(key) || String(t.kanban_column_id) === String(col.id);
    });
  };

  return (
    <div className="view-stack">
      <ViewHeader
        title="Kanban"
        subtitle="Project board using API columns and tasks."
        action={
          <button className="btn small" onClick={() => load()} disabled={loading}>
            Refresh
          </button>
        }
      />
      <div className="form-grid report-filters">
        <label>
          Project
          <select value={projectId} onChange={(e) => setProjectId(e.target.value)}>
            <option value="">Select project</option>
            {projects.map((p) => (
              <option key={p.id} value={p.id}>
                {p.name}
              </option>
            ))}
          </select>
        </label>
        <label>
          New task
          <input value={newTaskName} onChange={(e) => setNewTaskName(e.target.value)} placeholder="Task name" />
        </label>
        <button className="btn primary" onClick={createTask} disabled={!projectId}>
          Add task
        </button>
      </div>
      {loading ? (
        <SkeletonList />
      ) : (
        <div className="kanban-board">
          {columns.length ? (
            columns.map((col) => {
              const colTasks = tasksForColumn(col);
              const wip = col.wip_limit ?? col.wipLimit;
              return (
                <div className="kanban-column" key={col.id || col.key}>
                  <div className="kanban-column-head">
                    <strong>{col.label || col.name || col.key}</strong>
                    <span>
                      {colTasks.length}
                      {wip != null ? ` / ${wip}` : ''}
                    </span>
                  </div>
                  {colTasks.map((task) => (
                    <div className="kanban-card" key={task.id}>
                      <strong>{task.name || task.title}</strong>
                      <select
                        value={task.status || task.kanban_column || col.key || ''}
                        onChange={(e) => moveTask(task.id, e.target.value)}
                      >
                        {columns.map((c) => (
                          <option key={c.id || c.key} value={c.key || c.status || c.id}>
                            Move to {c.label || c.name || c.key}
                          </option>
                        ))}
                      </select>
                    </div>
                  ))}
                </div>
              );
            })
          ) : (
            <EmptyState title="No columns" text="Create Kanban columns in the web app or enable the module." />
          )}
        </div>
      )}
    </div>
  );
}
