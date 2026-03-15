"""
Routes for Gantt chart visualization.
"""

from datetime import datetime, timedelta

from flask import Blueprint, jsonify, render_template, request
from flask_babel import gettext as _
from flask_login import current_user, login_required

from app.models import Project
from app.services.gantt_service import GanttService
from app.utils.module_helpers import module_enabled

gantt_bp = Blueprint("gantt", __name__)


@gantt_bp.route("/gantt")
@login_required
@module_enabled("gantt")
def gantt_view():
    """Main Gantt chart view."""
    project_id = request.args.get("project_id", type=int)
    projects = Project.query.filter_by(status="active").order_by(Project.name).all()
    return render_template("gantt/view.html", projects=projects, selected_project_id=project_id)


@gantt_bp.route("/api/gantt/data")
@login_required
@module_enabled("gantt")
def gantt_data():
    """Get Gantt chart data as JSON."""
    project_id = request.args.get("project_id", type=int)
    start_date = request.args.get("start_date")
    end_date = request.args.get("end_date")

    if start_date:
        start_dt = datetime.strptime(start_date, "%Y-%m-%d")
    else:
        start_dt = datetime.utcnow() - timedelta(days=90)
    if end_date:
        end_dt = datetime.strptime(end_date, "%Y-%m-%d")
    else:
        end_dt = datetime.utcnow() + timedelta(days=90)

    has_view_all_projects = current_user.is_admin or current_user.has_permission("view_projects")
    result = GanttService().get_gantt_data(
        project_id=project_id,
        start_dt=start_dt,
        end_dt=end_dt,
        user_id=current_user.id,
        has_view_all_projects=has_view_all_projects,
    )
    return jsonify(result)
