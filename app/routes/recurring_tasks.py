"""
Recurring Tasks routes
"""

from flask import Blueprint, render_template, request, jsonify, redirect, url_for, flash
from flask_login import login_required, current_user
from app import db
from app.models.recurring_task import RecurringTask
from app.models import Project
from flask_babel import gettext as _
from datetime import datetime, date

recurring_tasks_bp = Blueprint("recurring_tasks", __name__)


@recurring_tasks_bp.route("/recurring-tasks")
@login_required
def list_recurring_tasks():
    """List all recurring tasks"""
    if current_user.is_admin:
        recurring_tasks = RecurringTask.query.order_by(RecurringTask.next_run_date.asc()).all()
    else:
        recurring_tasks = RecurringTask.query.filter_by(created_by=current_user.id).order_by(
            RecurringTask.next_run_date.asc()
        ).all()

    return render_template("recurring_tasks/list.html", recurring_tasks=recurring_tasks)


@recurring_tasks_bp.route("/recurring-tasks/create", methods=["GET", "POST"])
@login_required
def create_recurring_task():
    """Create a new recurring task"""
    if request.method == "POST":
        data = request.get_json() if request.is_json else request.form

        recurring_task = RecurringTask(
            name=data.get("name"),
            project_id=int(data.get("project_id")),
            frequency=data.get("frequency"),
            next_run_date=datetime.strptime(data.get("next_run_date"), "%Y-%m-%d").date(),
            created_by=current_user.id,
            interval=int(data.get("interval", 1)),
            end_date=datetime.strptime(data.get("end_date"), "%Y-%m-%d").date() if data.get("end_date") else None,
            task_name_template=data.get("task_name_template", data.get("name")),
            description=data.get("description"),
            priority=data.get("priority", "medium"),
            estimated_hours=float(data.get("estimated_hours")) if data.get("estimated_hours") else None,
            assigned_to=int(data.get("assigned_to")) if data.get("assigned_to") else None,
            auto_assign=bool(data.get("auto_assign", False))
        )

        db.session.add(recurring_task)
        db.session.commit()

        if request.is_json:
            return jsonify({"success": True, "recurring_task": recurring_task.to_dict()})

        flash(_("Recurring task created successfully"), "success")
        return redirect(url_for("recurring_tasks.list_recurring_tasks"))

    # GET - Show form
    projects = Project.query.filter_by(status="active").order_by(Project.name).all()
    
    return render_template("recurring_tasks/create.html", projects=projects)


@recurring_tasks_bp.route("/recurring-tasks/<int:task_id>")
@login_required
def view_recurring_task(task_id):
    """View recurring task details"""
    recurring_task = RecurringTask.query.get_or_404(task_id)

    if recurring_task.created_by != current_user.id and not current_user.is_admin:
        flash(_("Access denied"), "error")
        return redirect(url_for("recurring_tasks.list_recurring_tasks"))

    return render_template("recurring_tasks/view.html", recurring_task=recurring_task)


@recurring_tasks_bp.route("/recurring-tasks/<int:task_id>/toggle", methods=["POST"])
@login_required
def toggle_recurring_task(task_id):
    """Toggle recurring task active status"""
    recurring_task = RecurringTask.query.get_or_404(task_id)

    if recurring_task.created_by != current_user.id and not current_user.is_admin:
        return jsonify({"error": "Access denied"}), 403

    recurring_task.is_active = not recurring_task.is_active
    db.session.commit()

    return jsonify({"success": True, "is_active": recurring_task.is_active})

