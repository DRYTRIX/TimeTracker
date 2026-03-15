"""
Service for Gantt chart data and progress calculation.
"""

from collections import defaultdict
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from app import db
from app.models import Project, Task
from app.repositories import TimeEntryRepository


def calculate_project_progress(project: Project, tasks: Optional[List[Task]] = None) -> int:
    """Calculate project progress percentage (0-100). Pass tasks to avoid extra query."""
    if tasks is None:
        tasks = Task.query.filter_by(project_id=project.id).all()
    if not tasks:
        return 0
    completed = sum(1 for t in tasks if t.status == "done")
    return int((completed / len(tasks)) * 100)


def calculate_task_progress(task: Task) -> int:
    """Calculate task progress percentage (0-100) from status."""
    if task.status == "done":
        return 100
    if task.status == "in_progress":
        return 50
    if task.status == "review":
        return 75
    return 0


class GanttService:
    """Service for Gantt chart data."""

    def get_gantt_data(
        self,
        project_id: Optional[int],
        start_dt: datetime,
        end_dt: datetime,
        user_id: int,
        has_view_all_projects: bool,
    ) -> Dict[str, Any]:
        """
        Build Gantt chart data (projects and tasks with dates and progress).

        Returns:
            dict with "data" (list of gantt items), "start_date", "end_date" (formatted strings).
        """
        from sqlalchemy import false

        query = Project.query.filter_by(status="active")
        if project_id:
            query = query.filter_by(id=project_id)
        if not has_view_all_projects:
            time_entry_repo = TimeEntryRepository()
            user_project_ids = time_entry_repo.get_distinct_project_ids_for_user(user_id)
            query = query.filter(
                db.or_(
                    Project.created_by == user_id,
                    Project.id.in_(user_project_ids) if user_project_ids else false(),
                )
            )
        projects = query.all()
        project_ids = [p.id for p in projects]

        all_tasks = (
            Task.query.filter(Task.project_id.in_(project_ids)).order_by(Task.project_id, Task.id).all()
            if project_ids
            else []
        )
        tasks_by_project = defaultdict(list)
        for t in all_tasks:
            tasks_by_project[t.project_id].append(t)

        gantt_data: List[Dict[str, Any]] = []
        for project in projects:
            tasks = tasks_by_project.get(project.id, [])
            if not tasks:
                project_start = project.created_at or datetime.utcnow()
                project_end = project_start + timedelta(days=30)
            else:
                task_dates = []
                for task in tasks:
                    if task.due_date:
                        task_dates.append(datetime.combine(task.due_date, datetime.min.time()))
                    if task.created_at:
                        task_dates.append(task.created_at)
                if task_dates:
                    project_start = min(task_dates)
                    project_end = max(task_dates) + timedelta(days=7)
                else:
                    project_start = project.created_at or datetime.utcnow()
                    project_end = project_start + timedelta(days=30)
            if project_start < start_dt:
                project_start = start_dt
            if project_end > end_dt:
                project_end = end_dt

            proj_color = (project.color or "#3b82f6").lstrip("#")
            if len(proj_color) != 6 or not all(c in "0123456789aAbBcCdDeEfF" for c in proj_color):
                proj_color = "3b82f6"
            gantt_data.append(
                {
                    "id": f"project-{project.id}",
                    "name": project.name,
                    "start": project_start.strftime("%Y-%m-%d"),
                    "end": project_end.strftime("%Y-%m-%d"),
                    "progress": calculate_project_progress(project, tasks),
                    "type": "project",
                    "project_id": project.id,
                    "dependencies": [],
                    "color": proj_color,
                }
            )

            for task in tasks:
                if task.due_date:
                    task_end = datetime.combine(task.due_date, datetime.min.time())
                    task_start = task_end - timedelta(days=7)
                else:
                    task_start = task.created_at or project_start
                    task_end = task_start + timedelta(days=7)
                if task_start < start_dt:
                    task_start = start_dt
                if task_end > end_dt:
                    task_end = end_dt
                raw = (task.color or "").strip().lstrip("#")
                if raw and len(raw) == 6 and all(c in "0123456789aAbBcCdDeEfF" for c in raw):
                    task_color = raw.lower()
                else:
                    task_color = proj_color
                gantt_data.append(
                    {
                        "id": f"task-{task.id}",
                        "name": task.name,
                        "start": task_start.strftime("%Y-%m-%d"),
                        "end": task_end.strftime("%Y-%m-%d"),
                        "progress": calculate_task_progress(task),
                        "type": "task",
                        "task_id": task.id,
                        "project_id": project.id,
                        "parent": f"project-{project.id}",
                        "dependencies": [],
                        "status": task.status,
                        "color": task_color,
                    }
                )

        return {
            "data": gantt_data,
            "start_date": start_dt.strftime("%Y-%m-%d"),
            "end_date": end_dt.strftime("%Y-%m-%d"),
        }
