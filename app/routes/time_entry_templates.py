"""
Time Entry Templates Routes

This module provides routes for managing reusable time entry templates.
Templates allow users to quickly create time entries with pre-filled data.
"""

from flask import Blueprint, render_template, request, jsonify, flash, redirect, url_for
from flask_login import login_required, current_user
from flask_babel import _
from app import db
from app.models import TimeEntryTemplate, Project, Task
from app.utils.db import safe_commit
from app import log_event, track_event
from app.models import Activity
from sqlalchemy import desc
import logging

logger = logging.getLogger(__name__)

time_entry_templates_bp = Blueprint("time_entry_templates", __name__)


@time_entry_templates_bp.route("/templates")
@login_required
def list_templates():
    """List all time entry templates for the current user."""
    templates = (
        TimeEntryTemplate.query.filter_by(user_id=current_user.id).order_by(desc(TimeEntryTemplate.last_used_at)).all()
    )

    return render_template("time_entry_templates/list.html", templates=templates)


@time_entry_templates_bp.route("/templates/create", methods=["GET", "POST"])
@login_required
def create_template():
    """Create a new time entry template."""
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        project_id = request.form.get("project_id")
        task_id = request.form.get("task_id")
        default_duration = request.form.get("default_duration")
        default_notes = request.form.get("default_notes", "").strip()
        tags = request.form.get("tags", "").strip()

        # Validation
        if not name:
            flash(_("Template name is required"), "error")
            return render_template(
                "time_entry_templates/create.html",
                projects=Project.query.filter_by(status="active").order_by(Project.name).all(),
            )

        # Check for duplicate name
        existing = TimeEntryTemplate.query.filter_by(user_id=current_user.id, name=name).first()

        if existing:
            flash(f'Template "{name}" already exists', "error")
            return render_template(
                "time_entry_templates/create.html",
                projects=Project.query.filter_by(status="active").order_by(Project.name).all(),
                form_data=request.form,
            )

        # Convert duration to float
        try:
            default_duration = float(default_duration) if default_duration else None
        except ValueError:
            default_duration = None

        # Create template
        template = TimeEntryTemplate(
            user_id=current_user.id,
            name=name,
            project_id=int(project_id) if project_id else None,
            task_id=int(task_id) if task_id else None,
            default_duration=default_duration,
            default_notes=default_notes if default_notes else None,
            tags=tags if tags else None,
        )

        db.session.add(template)
        if not safe_commit("create_time_entry_template", {"name": name}):
            flash(_("Could not create template due to a database error"), "error")
            return render_template(
                "time_entry_templates/create.html",
                projects=Project.query.filter_by(status="active").order_by(Project.name).all(),
                form_data=request.form,
            )

        # Log activity
        Activity.log(
            user_id=current_user.id,
            action="created",
            entity_type="time_entry_template",
            entity_id=template.id,
            entity_name=template.name,
            description=f'Created time entry template "{template.name}"',
            ip_address=request.remote_addr,
            user_agent=request.headers.get("User-Agent"),
        )

        # Track event
        log_event("time_entry_template.created", user_id=current_user.id, template_id=template.id, template_name=name)
        track_event(
            current_user.id,
            "time_entry_template.created",
            {
                "template_id": template.id,
                "template_name": name,
                "has_project": bool(project_id),
                "has_task": bool(task_id),
                "has_default_duration": bool(default_duration),
            },
        )

        flash(f'Template "{name}" created successfully', "success")
        return redirect(url_for("time_entry_templates.list_templates"))

    # GET request
    projects = Project.query.filter_by(status="active").order_by(Project.name).all()
    return render_template("time_entry_templates/create.html", projects=projects)


@time_entry_templates_bp.route("/templates/<int:template_id>")
@login_required
def view_template(template_id):
    """View a specific template."""
    template = TimeEntryTemplate.query.filter_by(id=template_id, user_id=current_user.id).first_or_404()

    return render_template("time_entry_templates/view.html", template=template)


@time_entry_templates_bp.route("/templates/<int:template_id>/edit", methods=["GET", "POST"])
@login_required
def edit_template(template_id):
    """Edit an existing time entry template."""
    template = TimeEntryTemplate.query.filter_by(id=template_id, user_id=current_user.id).first_or_404()

    if request.method == "POST":
        name = request.form.get("name", "").strip()
        project_id = request.form.get("project_id")
        task_id = request.form.get("task_id")
        default_duration = request.form.get("default_duration")
        default_notes = request.form.get("default_notes", "").strip()
        tags = request.form.get("tags", "").strip()

        # Validation
        if not name:
            flash(_("Template name is required"), "error")
            return render_template(
                "time_entry_templates/edit.html",
                template=template,
                projects=Project.query.filter_by(status="active").order_by(Project.name).all(),
            )

        # Check for duplicate name (excluding current template)
        existing = TimeEntryTemplate.query.filter(
            TimeEntryTemplate.user_id == current_user.id,
            TimeEntryTemplate.name == name,
            TimeEntryTemplate.id != template_id,
        ).first()

        if existing:
            flash(f'Template "{name}" already exists', "error")
            return render_template(
                "time_entry_templates/edit.html",
                template=template,
                projects=Project.query.filter_by(status="active").order_by(Project.name).all(),
            )

        # Convert duration to float
        try:
            default_duration = float(default_duration) if default_duration else None
        except ValueError:
            default_duration = None

        # Update template
        old_name = template.name
        template.name = name
        template.project_id = int(project_id) if project_id else None
        template.task_id = int(task_id) if task_id else None
        template.default_duration = default_duration
        template.default_notes = default_notes if default_notes else None
        template.tags = tags if tags else None

        if not safe_commit("update_time_entry_template", {"template_id": template_id}):
            flash(_("Could not update template due to a database error"), "error")
            return render_template(
                "time_entry_templates/edit.html",
                template=template,
                projects=Project.query.filter_by(status="active").order_by(Project.name).all(),
            )

        # Log activity
        Activity.log(
            user_id=current_user.id,
            action="updated",
            entity_type="time_entry_template",
            entity_id=template.id,
            entity_name=template.name,
            description=f'Updated time entry template "{template.name}"',
            extra_data={"old_name": old_name} if old_name != name else None,
            ip_address=request.remote_addr,
            user_agent=request.headers.get("User-Agent"),
        )

        # Track event
        log_event("time_entry_template.updated", user_id=current_user.id, template_id=template.id)
        track_event(current_user.id, "time_entry_template.updated", {"template_id": template.id, "template_name": name})

        flash(f'Template "{name}" updated successfully', "success")
        return redirect(url_for("time_entry_templates.list_templates"))

    # GET request
    projects = Project.query.filter_by(status="active").order_by(Project.name).all()
    return render_template("time_entry_templates/edit.html", template=template, projects=projects)


@time_entry_templates_bp.route("/templates/<int:template_id>/delete", methods=["POST"])
@login_required
def delete_template(template_id):
    """Delete a time entry template."""
    template = TimeEntryTemplate.query.filter_by(id=template_id, user_id=current_user.id).first_or_404()

    template_name = template.name

    db.session.delete(template)
    if not safe_commit("delete_time_entry_template", {"template_id": template_id}):
        flash(_("Could not delete template due to a database error"), "error")
        return redirect(url_for("time_entry_templates.list_templates"))

    # Log activity
    Activity.log(
        user_id=current_user.id,
        action="deleted",
        entity_type="time_entry_template",
        entity_id=template_id,
        entity_name=template_name,
        description=f'Deleted time entry template "{template_name}"',
        ip_address=request.remote_addr,
        user_agent=request.headers.get("User-Agent"),
    )

    # Track event
    log_event(
        "time_entry_template.deleted", user_id=current_user.id, template_id=template_id, template_name=template_name
    )
    track_event(
        current_user.id, "time_entry_template.deleted", {"template_id": template_id, "template_name": template_name}
    )

    flash(f'Template "{template_name}" deleted successfully', "success")
    return redirect(url_for("time_entry_templates.list_templates"))


@time_entry_templates_bp.route("/api/templates", methods=["GET"])
@login_required
def get_templates_api():
    """Get templates as JSON (for AJAX requests)."""
    templates = (
        TimeEntryTemplate.query.filter_by(user_id=current_user.id).order_by(desc(TimeEntryTemplate.last_used_at)).all()
    )

    return jsonify({"templates": [t.to_dict() for t in templates]})


@time_entry_templates_bp.route("/api/templates/<int:template_id>", methods=["GET"])
@login_required
def get_template_api(template_id):
    """Get a specific template as JSON."""
    template = TimeEntryTemplate.query.filter_by(id=template_id, user_id=current_user.id).first_or_404()

    return jsonify(template.to_dict())


@time_entry_templates_bp.route("/api/templates/<int:template_id>/use", methods=["POST"])
@login_required
def use_template_api(template_id):
    """Mark template as used and update last_used_at."""
    template = TimeEntryTemplate.query.filter_by(id=template_id, user_id=current_user.id).first_or_404()

    template.record_usage()

    if not safe_commit("use_time_entry_template", {"template_id": template_id}):
        return jsonify({"error": "Could not record template usage"}), 500

    # Track event
    log_event("time_entry_template.used", user_id=current_user.id, template_id=template.id, template_name=template.name)
    track_event(
        current_user.id,
        "time_entry_template.used",
        {"template_id": template.id, "template_name": template.name, "usage_count": template.usage_count},
    )

    return jsonify({"success": True, "template": template.to_dict()})


@time_entry_templates_bp.route("/api/projects/<int:project_id>/tasks", methods=["GET"])
@login_required
def get_project_tasks_api(project_id):
    """Deprecated: use main API endpoint at /api/projects/<project_id>/tasks"""
    from app.routes.api import get_project_tasks as _api_get_project_tasks

    return _api_get_project_tasks(project_id)
