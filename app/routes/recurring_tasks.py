"""
Recurring Tasks routes
"""

from datetime import date, datetime

from flask import Blueprint, flash, jsonify, redirect, render_template, request, url_for
from flask_babel import gettext as _
from flask_login import current_user, login_required

from app import db
from app.models import Project, User
from app.models.recurring_task import RecurringTask
from app.utils.db import safe_commit
from app.utils.module_helpers import module_enabled

recurring_tasks_bp = Blueprint("recurring_tasks", __name__)


def _can_manage_recurring_task(recurring_task):
    return current_user.is_admin or recurring_task.created_by == current_user.id


def _active_projects():
    return Project.query.filter_by(status="active").order_by(Project.name).all()


def _active_users():
    return User.query.filter_by(is_active=True).order_by(User.username).all()


def _parse_recurring_task_form(data):
    """Parse recurring task fields from form or JSON payload."""
    end_date_raw = data.get("end_date")
    estimated_raw = data.get("estimated_hours")
    assigned_raw = data.get("assigned_to")

    return {
        "name": (data.get("name") or "").strip(),
        "project_id": int(data.get("project_id")),
        "frequency": data.get("frequency"),
        "next_run_date": datetime.strptime(data.get("next_run_date"), "%Y-%m-%d").date(),
        "interval": int(data.get("interval", 1) or 1),
        "end_date": datetime.strptime(end_date_raw, "%Y-%m-%d").date() if end_date_raw else None,
        "task_name_template": (data.get("task_name_template") or data.get("name") or "").strip(),
        "description": data.get("description"),
        "priority": data.get("priority", "medium"),
        "estimated_hours": float(estimated_raw) if estimated_raw else None,
        "assigned_to": int(assigned_raw) if assigned_raw else None,
        "auto_assign": bool(data.get("auto_assign", False)),
    }


def _apply_recurring_task_fields(recurring_task, fields):
    recurring_task.name = fields["name"]
    recurring_task.project_id = fields["project_id"]
    recurring_task.frequency = fields["frequency"]
    recurring_task.next_run_date = fields["next_run_date"]
    recurring_task.interval = fields["interval"]
    recurring_task.end_date = fields["end_date"]
    recurring_task.task_name_template = fields["task_name_template"]
    recurring_task.description = fields["description"]
    recurring_task.priority = fields["priority"]
    recurring_task.estimated_hours = fields["estimated_hours"]
    recurring_task.assigned_to = fields["assigned_to"]
    recurring_task.auto_assign = fields["auto_assign"]


@recurring_tasks_bp.route("/recurring-tasks")
@login_required
@module_enabled("recurring_tasks")
def list_recurring_tasks():
    """List all recurring tasks"""
    if current_user.is_admin:
        recurring_tasks = RecurringTask.query.order_by(RecurringTask.next_run_date.asc()).all()
    else:
        recurring_tasks = (
            RecurringTask.query.filter_by(created_by=current_user.id).order_by(RecurringTask.next_run_date.asc()).all()
        )

    return render_template("recurring_tasks/list.html", recurring_tasks=recurring_tasks)


@recurring_tasks_bp.route("/recurring-tasks/create", methods=["GET", "POST"])
@login_required
@module_enabled("recurring_tasks")
def create_recurring_task():
    """Create a new recurring task"""
    if request.method == "POST":
        data = request.get_json() if request.is_json else request.form
        fields = _parse_recurring_task_form(data)

        recurring_task = RecurringTask(
            name=fields["name"],
            project_id=fields["project_id"],
            frequency=fields["frequency"],
            next_run_date=fields["next_run_date"],
            created_by=current_user.id,
            interval=fields["interval"],
            end_date=fields["end_date"],
            task_name_template=fields["task_name_template"],
            description=fields["description"],
            priority=fields["priority"],
            estimated_hours=fields["estimated_hours"],
            assigned_to=fields["assigned_to"],
            auto_assign=fields["auto_assign"],
        )

        db.session.add(recurring_task)
        if not safe_commit("create_recurring_task"):
            if request.is_json:
                return jsonify({"error": "Database error"}), 500
            flash(_("Could not create recurring task due to a database error."), "error")
            return render_template(
                "recurring_tasks/create.html",
                projects=_active_projects(),
                users=_active_users(),
            )

        if request.is_json:
            return jsonify({"success": True, "recurring_task": recurring_task.to_dict()})

        flash(_("Recurring task created successfully"), "success")
        return redirect(url_for("recurring_tasks.list_recurring_tasks"))

    return render_template(
        "recurring_tasks/create.html",
        projects=_active_projects(),
        users=_active_users(),
    )


@recurring_tasks_bp.route("/recurring-tasks/<int:task_id>")
@login_required
@module_enabled("recurring_tasks")
def view_recurring_task(task_id):
    """View recurring task details"""
    recurring_task = RecurringTask.query.get_or_404(task_id)

    if not _can_manage_recurring_task(recurring_task):
        flash(_("Access denied"), "error")
        return redirect(url_for("recurring_tasks.list_recurring_tasks"))

    return render_template("recurring_tasks/view.html", recurring_task=recurring_task)


@recurring_tasks_bp.route("/recurring-tasks/<int:task_id>/edit", methods=["GET", "POST"])
@login_required
@module_enabled("recurring_tasks")
def edit_recurring_task(task_id):
    """Edit a recurring task"""
    recurring_task = RecurringTask.query.get_or_404(task_id)

    if not _can_manage_recurring_task(recurring_task):
        flash(_("Access denied"), "error")
        return redirect(url_for("recurring_tasks.list_recurring_tasks"))

    if request.method == "POST":
        data = request.get_json() if request.is_json else request.form
        fields = _parse_recurring_task_form(data)
        _apply_recurring_task_fields(recurring_task, fields)

        if not safe_commit("edit_recurring_task", {"task_id": task_id}):
            if request.is_json:
                return jsonify({"error": "Database error"}), 500
            flash(_("Could not update recurring task due to a database error."), "error")
            return render_template(
                "recurring_tasks/edit.html",
                recurring_task=recurring_task,
                projects=_active_projects(),
                users=_active_users(),
            )

        if request.is_json:
            return jsonify({"success": True, "recurring_task": recurring_task.to_dict()})

        flash(_("Recurring task updated successfully"), "success")
        return redirect(url_for("recurring_tasks.view_recurring_task", task_id=recurring_task.id))

    return render_template(
        "recurring_tasks/edit.html",
        recurring_task=recurring_task,
        projects=_active_projects(),
        users=_active_users(),
    )


@recurring_tasks_bp.route("/recurring-tasks/<int:task_id>/delete", methods=["POST"])
@login_required
@module_enabled("recurring_tasks")
def delete_recurring_task(task_id):
    """Delete a recurring task"""
    recurring_task = RecurringTask.query.get_or_404(task_id)

    if not _can_manage_recurring_task(recurring_task):
        flash(_("Access denied"), "error")
        return redirect(url_for("recurring_tasks.list_recurring_tasks"))

    name = recurring_task.name
    db.session.delete(recurring_task)
    if not safe_commit("delete_recurring_task", {"task_id": task_id}):
        flash(_("Could not delete recurring task due to a database error."), "error")
        return redirect(url_for("recurring_tasks.list_recurring_tasks"))

    flash(_("Recurring task \"%(name)s\" deleted successfully", name=name), "success")
    return redirect(url_for("recurring_tasks.list_recurring_tasks"))


@recurring_tasks_bp.route("/recurring-tasks/<int:task_id>/toggle", methods=["POST"])
@login_required
@module_enabled("recurring_tasks")
def toggle_recurring_task(task_id):
    """Toggle recurring task active status"""
    recurring_task = RecurringTask.query.get_or_404(task_id)

    if recurring_task.created_by != current_user.id and not current_user.is_admin:
        return jsonify({"error": "Access denied"}), 403

    recurring_task.is_active = not recurring_task.is_active
    db.session.commit()

    return jsonify({"success": True, "is_active": recurring_task.is_active})
