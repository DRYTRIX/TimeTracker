"""Compare estimated hours (tasks/projects) vs logged time entries."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from sqlalchemy import func

from app import db
from app.models import Project, Task, TimeEntry


class EstimateActualsService:
    """Estimates vs actuals reporting."""

    def get_report(
        self,
        *,
        project_id: Optional[int] = None,
        user_id: Optional[int] = None,
        is_admin: bool = False,
    ) -> Dict[str, Any]:
        task_query = Task.query
        project_query = Project.query.filter(Project.status != "cancelled")

        if project_id:
            task_query = task_query.filter(Task.project_id == project_id)
            project_query = project_query.filter(Project.id == project_id)

        if not is_admin and user_id is not None:
            from app.utils.scope_filter import get_accessible_project_and_client_ids_for_user

            allowed, _client_ids = get_accessible_project_and_client_ids_for_user(user_id)
            if allowed is not None:
                task_query = task_query.filter(Task.project_id.in_(allowed))
                project_query = project_query.filter(Project.id.in_(allowed))

        tasks = task_query.all()
        task_ids = [t.id for t in tasks]

        actual_by_task: Dict[int, float] = {}
        if task_ids:
            rows = (
                db.session.query(TimeEntry.task_id, func.sum(TimeEntry.duration_seconds))
                .filter(TimeEntry.task_id.in_(task_ids), TimeEntry.end_time.isnot(None))
                .group_by(TimeEntry.task_id)
                .all()
            )
            actual_by_task = {tid: round((secs or 0) / 3600.0, 2) for tid, secs in rows if tid}

        task_rows: List[Dict[str, Any]] = []
        for task in tasks:
            estimated = float(task.estimated_hours) if task.estimated_hours is not None else None
            actual = actual_by_task.get(task.id, 0.0)
            variance = round(actual - estimated, 2) if estimated is not None else None
            task_rows.append(
                {
                    "task_id": task.id,
                    "task_name": task.name,
                    "project_id": task.project_id,
                    "estimated_hours": estimated,
                    "actual_hours": actual,
                    "variance_hours": variance,
                }
            )

        project_rows: List[Dict[str, Any]] = []
        for project in project_query.all():
            project_tasks = [r for r in task_rows if r["project_id"] == project.id]
            task_estimated_sum = sum(r["estimated_hours"] or 0 for r in project_tasks)
            task_actual_sum = sum(r["actual_hours"] for r in project_tasks)
            project_estimated = float(project.estimated_hours) if project.estimated_hours is not None else None
            effective_estimate = project_estimated if project_estimated is not None else (
                round(task_estimated_sum, 2) if task_estimated_sum else None
            )
            variance = (
                round(task_actual_sum - effective_estimate, 2) if effective_estimate is not None else None
            )
            project_rows.append(
                {
                    "project_id": project.id,
                    "project_name": project.name,
                    "estimated_hours": effective_estimate,
                    "actual_hours": round(task_actual_sum, 2),
                    "variance_hours": variance,
                    "task_count": len(project_tasks),
                }
            )

        return {
            "projects": sorted(project_rows, key=lambda r: r["project_name"].lower()),
            "tasks": sorted(task_rows, key=lambda r: (r["project_id"], r["task_name"].lower())),
        }
