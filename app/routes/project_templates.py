"""
Routes for project template management.
"""

from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_babel import gettext as _
from flask_login import login_required, current_user
from app import db
from app.models import ProjectTemplate, Client
from app.services.project_template_service import ProjectTemplateService
from app.utils.permissions import admin_or_permission_required
from app.utils.module_helpers import module_enabled
import json

project_templates_bp = Blueprint("project_templates", __name__)


def _parse_tasks_from_request_form():
    """
    Best-effort fallback parser for template tasks.

    The UI posts either:
    - a hidden JSON field named "tasks" (preferred), OR
    - parallel arrays: task_names[], task_priorities[], task_hours[]
    """
    names = request.form.getlist("task_names[]")
    priorities = request.form.getlist("task_priorities[]")
    hours = request.form.getlist("task_hours[]")

    tasks = []
    for idx, raw_name in enumerate(names):
        name = (raw_name or "").strip()
        if not name:
            continue

        priority = (priorities[idx] if idx < len(priorities) else "medium") or "medium"

        estimated_hours = None
        if idx < len(hours):
            raw_hours = (hours[idx] or "").strip()
            if raw_hours:
                try:
                    estimated_hours = float(raw_hours)
                except (ValueError, TypeError):
                    estimated_hours = None

        tasks.append(
            {
                "name": name,
                "priority": priority,
                "estimated_hours": estimated_hours,
                "status": "todo",
            }
        )

    return tasks


@project_templates_bp.route("/project-templates")
@login_required
@module_enabled("project_templates")
def list_templates():
    """List project templates"""
    page = request.args.get("page", 1, type=int)
    category = request.args.get("category", "").strip()
    show_public = request.args.get("public", "false").lower() == "true"

    service = ProjectTemplateService()

    result = service.list_templates(
        user_id=current_user.id,
        category=category if category else None,
        is_public=show_public if show_public else None,
        page=page,
        per_page=20,
    )

    templates = result.items
    pagination = result

    # Get unique categories
    categories = db.session.query(ProjectTemplate.category).distinct().all()
    categories = [c[0] for c in categories if c[0]]

    return render_template(
        "project_templates/list.html",
        templates=templates,
        pagination=pagination,
        categories=categories,
        current_category=category,
        show_public=show_public,
    )


@project_templates_bp.route("/project-templates/create", methods=["GET", "POST"])
@login_required
@module_enabled("project_templates")
@admin_or_permission_required("create_projects")
def create_template():
    """Create a new project template"""
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        description = request.form.get("description", "").strip()
        category = request.form.get("category", "").strip()
        is_public = request.form.get("is_public", "false").lower() == "true"

        # Get config
        config = {
            "description": description,
            "billable": request.form.get("billable", "true").lower() == "true",
            "hourly_rate": request.form.get("hourly_rate") or None,
            "billing_ref": request.form.get("billing_ref", "").strip() or None,
            "code": request.form.get("code", "").strip().upper() or None,
            "estimated_hours": request.form.get("estimated_hours") or None,
            "budget_amount": request.form.get("budget_amount") or None,
            "budget_threshold_percent": int(request.form.get("budget_threshold_percent", 80)),
        }

        # Get tasks (from JSON or form)
        tasks = []
        tasks_json = request.form.get("tasks", "[]")
        try:
            parsed_tasks = json.loads(tasks_json)
            # Ensure it's a list
            if isinstance(parsed_tasks, list):
                tasks = parsed_tasks
            else:
                import logging
                logging.getLogger(__name__).warning(f"Tasks JSON is not a list: {type(parsed_tasks)}")
        except json.JSONDecodeError as e:
            import logging
            logging.getLogger(__name__).warning(f"Failed to parse tasks JSON: {e}, raw: {tasks_json}")
        except Exception as e:
            import logging
            logging.getLogger(__name__).warning(f"Unexpected error parsing tasks: {e}")

        # Fallback: parse from form arrays if JS didn't serialize tasks
        if not tasks:
            tasks = _parse_tasks_from_request_form()

        # Get tags
        tags_str = request.form.get("tags", "").strip()
        tags = [t.strip() for t in tags_str.split(",") if t.strip()]

        service = ProjectTemplateService()
        result = service.create_template(
            name=name,
            created_by=current_user.id,
            description=description or None,
            config=config,
            tasks=tasks,
            category=category or None,
            tags=tags,
            is_public=is_public,
        )

        if result["success"]:
            flash(_("Template created successfully."), "success")
            return redirect(url_for("project_templates.list_templates"))
        else:
            error_msg = result.get("message", "An error occurred while creating the template.")
            flash(str(error_msg), "error")

    clients = Client.get_active_clients()
    return render_template("project_templates/create.html", clients=clients)


@project_templates_bp.route("/project-templates/<int:template_id>")
@login_required
@module_enabled("project_templates")
def view_template(template_id):
    """View a project template"""
    service = ProjectTemplateService()
    template = service.get_template(template_id)

    if not template:
        flash(_("Template not found."), "error")
        return redirect(url_for("project_templates.list_templates"))

    # Check permissions
    if not template.is_public and template.created_by != current_user.id:
        flash(_("You do not have permission to view this template."), "error")
        return redirect(url_for("project_templates.list_templates"))

    return render_template("project_templates/view.html", template=template)


@project_templates_bp.route("/project-templates/<int:template_id>/edit", methods=["GET", "POST"])
@login_required
@module_enabled("project_templates")
def edit_template(template_id):
    """Edit a project template"""
    service = ProjectTemplateService()
    template = service.get_template(template_id)

    if not template:
        flash(_("Template not found."), "error")
        return redirect(url_for("project_templates.list_templates"))

    if template.created_by != current_user.id:
        flash(_("You do not have permission to edit this template."), "error")
        return redirect(url_for("project_templates.view_template", template_id=template_id))

    if request.method == "POST":
        name = request.form.get("name", "").strip()
        description = request.form.get("description", "").strip()
        category = request.form.get("category", "").strip()
        is_public = request.form.get("is_public", "false").lower() == "true"

        # Get config
        config = {
            "description": description,
            "billable": request.form.get("billable", "true").lower() == "true",
            "hourly_rate": request.form.get("hourly_rate") or None,
            "billing_ref": request.form.get("billing_ref", "").strip() or None,
            "code": request.form.get("code", "").strip().upper() or None,
            "estimated_hours": request.form.get("estimated_hours") or None,
            "budget_amount": request.form.get("budget_amount") or None,
            "budget_threshold_percent": int(request.form.get("budget_threshold_percent", 80)),
        }

        # Get tasks
        tasks = []
        tasks_json = request.form.get("tasks", "[]")
        
        try:
            parsed_tasks = json.loads(tasks_json)
            # Ensure it's a list
            if isinstance(parsed_tasks, list):
                tasks = parsed_tasks
            else:
                import logging
                logging.getLogger(__name__).warning(f"Tasks JSON is not a list: {type(parsed_tasks)}")
        except json.JSONDecodeError as e:
            import logging
            logging.getLogger(__name__).warning(f"Failed to parse tasks JSON: {e}, raw: {tasks_json}")
        except Exception as e:
            import logging
            logging.getLogger(__name__).warning(f"Unexpected error parsing tasks: {e}")

        # Fallback: parse from form arrays if JS didn't serialize tasks
        if not tasks:
            tasks = _parse_tasks_from_request_form()

        # Get tags
        tags_str = request.form.get("tags", "").strip()
        tags = [t.strip() for t in tags_str.split(",") if t.strip()]

        result = service.update_template(
            template_id=template_id,
            user_id=current_user.id,
            name=name,
            description=description or None,
            config=config,
            tasks=tasks,
            category=category or None,
            tags=tags,
            is_public=is_public,
        )

        if result["success"]:
            flash(_("Template updated successfully."), "success")
            return redirect(url_for("project_templates.view_template", template_id=template_id))
        else:
            error_msg = result.get("message", "An error occurred while updating the template.")
            flash(str(error_msg), "error")

    clients = Client.get_active_clients()
    return render_template("project_templates/edit.html", template=template, clients=clients)


@project_templates_bp.route("/project-templates/<int:template_id>/delete", methods=["POST"])
@login_required
@module_enabled("project_templates")
def delete_template(template_id):
    """Delete a project template"""
    service = ProjectTemplateService()
    result = service.delete_template(template_id, current_user.id)

    if result["success"]:
        flash(_("Template deleted successfully."), "success")
    else:
        error_msg = result.get("message", "An error occurred while deleting the template.")
        flash(str(error_msg), "error")

    return redirect(url_for("project_templates.list_templates"))


@project_templates_bp.route("/project-templates/<int:template_id>/create-project", methods=["GET", "POST"])
@login_required
@module_enabled("project_templates")
@admin_or_permission_required("create_projects")
def create_project_from_template(template_id):
    """Create a project from a template"""
    service = ProjectTemplateService()
    template = service.get_template(template_id)

    if not template:
        flash(_("Template not found."), "error")
        return redirect(url_for("project_templates.list_templates"))

    if request.method == "POST":
        client_id = request.form.get("client_id", type=int)
        name = request.form.get("name", "").strip()

        if not client_id:
            flash(_("Please select a client."), "error")
            return render_template(
                "project_templates/create_project.html", template=template, clients=Client.get_active_clients()
            )

        # Get override config
        override_config = {}
        if request.form.get("hourly_rate"):
            override_config["hourly_rate"] = request.form.get("hourly_rate")
        if request.form.get("billing_ref"):
            override_config["billing_ref"] = request.form.get("billing_ref", "").strip()
        if request.form.get("code"):
            override_config["code"] = request.form.get("code", "").strip().upper()

        result = service.create_project_from_template(
            template_id=template_id,
            client_id=client_id,
            created_by=current_user.id,
            name=name or None,
            override_config=override_config if override_config else None,
        )

        if result["success"]:
            flash(_("Project created from template successfully."), "success")
            return redirect(url_for("projects.view_project", project_id=result["project"].id))
        else:
            error_msg = result.get("message", "An error occurred while creating the project from template.")
            flash(str(error_msg), "error")

    clients = Client.get_active_clients()
    return render_template("project_templates/create_project.html", template=template, clients=clients)
