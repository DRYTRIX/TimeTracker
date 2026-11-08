"""API v1 - Gantt chart data."""

from datetime import datetime, timedelta

from flask import Blueprint, g, jsonify, request

from app.services.gantt_service import GanttService
from app.utils.api_auth import require_api_token

api_v1_gantt_bp = Blueprint("api_v1_gantt", __name__, url_prefix="/api/v1")


@api_v1_gantt_bp.route("/gantt", methods=["GET"])
@require_api_token(("read:projects", "read:tasks"))
def get_gantt_data():
    """Return Gantt chart data via GanttService."""
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

    user = g.api_user
    has_view_all_projects = bool(user.is_admin or user.has_permission("view_projects"))
    result = GanttService().get_gantt_data(
        project_id=project_id,
        start_dt=start_dt,
        end_dt=end_dt,
        user_id=user.id,
        has_view_all_projects=has_view_all_projects,
    )
    return jsonify(result)
