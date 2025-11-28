"""
Routes for Gantt chart visualization.
"""

from flask import Blueprint, render_template, request, jsonify
from flask_babel import gettext as _
from flask_login import login_required, current_user
from app import db
from app.models import Project, Task, TimeEntry
from datetime import datetime, timedelta
from sqlalchemy import func

gantt_bp = Blueprint("gantt", __name__)


@gantt_bp.route("/gantt")
@login_required
def gantt_view():
    """Main Gantt chart view."""
    project_id = request.args.get("project_id", type=int)
    projects = Project.query.filter_by(status="active").order_by(Project.name).all()

    return render_template("gantt/view.html", projects=projects, selected_project_id=project_id)


@gantt_bp.route("/api/gantt/data")
@login_required
def gantt_data():
    """Get Gantt chart data as JSON."""
    project_id = request.args.get("project_id", type=int)
    start_date = request.args.get("start_date")
    end_date = request.args.get("end_date")

    # Parse dates
    if start_date:
        start_dt = datetime.strptime(start_date, "%Y-%m-%d")
    else:
        start_dt = datetime.utcnow() - timedelta(days=90)

    if end_date:
        end_dt = datetime.strptime(end_date, "%Y-%m-%d")
    else:
        end_dt = datetime.utcnow() + timedelta(days=90)

    # Get projects
    query = Project.query.filter_by(status="active")
    if project_id:
        query = query.filter_by(id=project_id)

    if not current_user.is_admin:
        # Filter by user's projects or projects they have time entries for
        query = query.filter(
            db.or_(
                Project.created_by == current_user.id,
                Project.id.in_(
                    db.session.query(TimeEntry.project_id).filter_by(user_id=current_user.id).distinct().subquery()
                ),
            )
        )

    projects = query.all()

    # Build Gantt data
    gantt_data = []

    for project in projects:
        # Get project start and end dates from tasks
        tasks = Task.query.filter_by(project_id=project.id).all()

        if not tasks:
            # If no tasks, use project creation date
            project_start = project.created_at or datetime.utcnow()
            project_end = project_start + timedelta(days=30)
        else:
            # Calculate project timeline from tasks
            task_dates = []
            for task in tasks:
                if task.due_date:
                    task_dates.append(datetime.combine(task.due_date, datetime.min.time()))
                if task.created_at:
                    task_dates.append(task.created_at)

            if task_dates:
                project_start = min(task_dates)
                project_end = max(task_dates) + timedelta(days=7)  # Add buffer
            else:
                project_start = project.created_at or datetime.utcnow()
                project_end = project_start + timedelta(days=30)

        # Ensure dates are within requested range
        if project_start < start_dt:
            project_start = start_dt
        if project_end > end_dt:
            project_end = end_dt

        # Add project as parent task
        gantt_data.append(
            {
                "id": f"project-{project.id}",
                "name": project.name,
                "start": project_start.strftime("%Y-%m-%d"),
                "end": project_end.strftime("%Y-%m-%d"),
                "progress": calculate_project_progress(project),
                "type": "project",
                "project_id": project.id,
                "dependencies": [],
            }
        )

        # Add tasks as child items
        for task in tasks:
            # Use due_date if available, otherwise estimate from created_at
            if task.due_date:
                task_end = datetime.combine(task.due_date, datetime.min.time())
                task_start = task_end - timedelta(days=7)  # Default 7-day duration
            else:
                task_start = task.created_at or project_start
                task_end = task_start + timedelta(days=7)

            # Ensure dates are within range
            if task_start < start_dt:
                task_start = start_dt
            if task_end > end_dt:
                task_end = end_dt

            dependencies = []
            # Task dependencies would need to be added to Task model if needed

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
                    "dependencies": dependencies,
                    "status": task.status,
                }
            )

    return jsonify(
        {"data": gantt_data, "start_date": start_dt.strftime("%Y-%m-%d"), "end_date": end_dt.strftime("%Y-%m-%d")}
    )


def calculate_project_progress(project):
    """Calculate project progress percentage."""
    tasks = Task.query.filter_by(project_id=project.id).all()
    if not tasks:
        return 0

    completed = sum(1 for t in tasks if t.status == "done")
    return int((completed / len(tasks)) * 100)


def calculate_task_progress(task):
    """Calculate task progress percentage."""
    if task.status == "done":
        return 100
    elif task.status == "in_progress":
        return 50
    elif task.status == "review":
        return 75
    else:
        return 0
