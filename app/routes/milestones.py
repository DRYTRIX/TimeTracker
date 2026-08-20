from datetime import datetime

from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_babel import gettext as _
from flask_login import current_user, login_required

from app import db
from app.models import Milestone, Project, Task
from app.utils.db import safe_commit
from app.utils.scope_filter import user_can_access_project

milestones_bp = Blueprint("milestones", __name__)


def _parse_due_date(value):
    value = (value or "").strip()
    if not value:
        return None
    return datetime.strptime(value, "%Y-%m-%d").date()


def _can_edit_project(project_id):
    return current_user.is_admin or current_user.has_permission("edit_projects")


@milestones_bp.route("/projects/<int:project_id>/milestones")
@login_required
def list_project_milestones(project_id):
    if not user_can_access_project(current_user, project_id):
        from flask import abort

        abort(403)
    project = Project.query.get_or_404(project_id)
    milestones = (
        Milestone.query.filter_by(project_id=project_id)
        .order_by(Milestone.due_date.asc().nullslast(), Milestone.created_at.asc())
        .all()
    )
    for milestone in milestones:
        milestone.refresh_status()
    safe_commit("refresh_milestone_status", {"project_id": project_id})
    return render_template("milestones/list.html", project=project, milestones=milestones)


@milestones_bp.route("/projects/<int:project_id>/milestones/create", methods=["GET", "POST"])
@login_required
def create_milestone(project_id):
    if not user_can_access_project(current_user, project_id):
        from flask import abort

        abort(403)
    if not _can_edit_project(project_id):
        flash(_("You do not have permission to create milestones"), "error")
        return redirect(url_for("milestones.list_project_milestones", project_id=project_id))

    project = Project.query.get_or_404(project_id)
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        if not name:
            flash(_("Name is required"), "error")
            return render_template("milestones/form.html", project=project, milestone=None)
        try:
            due_date = _parse_due_date(request.form.get("due_date"))
        except ValueError:
            flash(_("Invalid due date"), "error")
            return render_template("milestones/form.html", project=project, milestone=None)
        milestone = Milestone(
            project_id=project.id,
            name=name,
            created_by=current_user.id,
            description=request.form.get("description", "").strip() or None,
            due_date=due_date,
            status=request.form.get("status", "upcoming") or "upcoming",
        )
        db.session.add(milestone)
        if not safe_commit("create_milestone", {"project_id": project.id}):
            flash(_("Could not create milestone"), "error")
            return render_template("milestones/form.html", project=project, milestone=None)
        flash(_("Milestone created"), "success")
        return redirect(url_for("milestones.list_project_milestones", project_id=project.id))
    return render_template("milestones/form.html", project=project, milestone=None)


@milestones_bp.route("/milestones/<int:milestone_id>/edit", methods=["GET", "POST"])
@login_required
def edit_milestone(milestone_id):
    milestone = Milestone.query.get_or_404(milestone_id)
    if not user_can_access_project(current_user, milestone.project_id):
        from flask import abort

        abort(403)
    if not _can_edit_project(milestone.project_id):
        flash(_("You do not have permission to edit milestones"), "error")
        return redirect(url_for("milestones.list_project_milestones", project_id=milestone.project_id))

    if request.method == "POST":
        name = request.form.get("name", "").strip()
        if not name:
            flash(_("Name is required"), "error")
            return render_template("milestones/form.html", project=milestone.project, milestone=milestone)
        try:
            due_date = _parse_due_date(request.form.get("due_date"))
        except ValueError:
            flash(_("Invalid due date"), "error")
            return render_template("milestones/form.html", project=milestone.project, milestone=milestone)
        milestone.name = name
        milestone.description = request.form.get("description", "").strip() or None
        milestone.due_date = due_date
        status = request.form.get("status", "").strip()
        if status in ("upcoming", "in_progress", "completed", "missed"):
            milestone.status = status
        if not safe_commit("edit_milestone", {"milestone_id": milestone.id}):
            flash(_("Could not update milestone"), "error")
            return render_template("milestones/form.html", project=milestone.project, milestone=milestone)
        flash(_("Milestone updated"), "success")
        return redirect(url_for("milestones.list_project_milestones", project_id=milestone.project_id))
    return render_template("milestones/form.html", project=milestone.project, milestone=milestone)


@milestones_bp.route("/milestones/<int:milestone_id>/delete", methods=["POST"])
@login_required
def delete_milestone(milestone_id):
    milestone = Milestone.query.get_or_404(milestone_id)
    project_id = milestone.project_id
    if not user_can_access_project(current_user, project_id):
        from flask import abort

        abort(403)
    if not _can_edit_project(project_id):
        flash(_("You do not have permission to delete milestones"), "error")
        return redirect(url_for("milestones.list_project_milestones", project_id=project_id))
    Task.query.filter_by(milestone_id=milestone.id).update({"milestone_id": None}, synchronize_session=False)
    db.session.delete(milestone)
    if not safe_commit("delete_milestone", {"milestone_id": milestone_id}):
        flash(_("Could not delete milestone"), "error")
    else:
        flash(_("Milestone deleted"), "success")
    return redirect(url_for("milestones.list_project_milestones", project_id=project_id))
