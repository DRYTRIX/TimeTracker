"""API v1 - Recurring tasks."""

from flask import Blueprint, g, jsonify, request

from app.models import RecurringTask
from app.utils.api_auth import require_api_token
from app.utils.api_responses import not_found_response

api_v1_recurring_tasks_bp = Blueprint("api_v1_recurring_tasks", __name__, url_prefix="/api/v1")


@api_v1_recurring_tasks_bp.route("/recurring-tasks", methods=["GET"])
@require_api_token("read:tasks")
def list_recurring_tasks():
    """List recurring task templates."""
    project_id = request.args.get("project_id", type=int)
    active_only = request.args.get("active_only", "true").lower() != "false"
    q = RecurringTask.query
    if project_id:
        q = q.filter(RecurringTask.project_id == project_id)
    if active_only:
        q = q.filter(RecurringTask.is_active == True)  # noqa: E712
    if not g.api_user.is_admin:
        q = q.filter(RecurringTask.created_by == g.api_user.id)
    items = q.order_by(RecurringTask.name.asc()).limit(200).all()
    return jsonify({"recurring_tasks": [t.to_dict() for t in items]})


@api_v1_recurring_tasks_bp.route("/recurring-tasks/<int:task_id>", methods=["GET"])
@require_api_token("read:tasks")
def get_recurring_task(task_id):
    """Get a recurring task template."""
    item = RecurringTask.query.get(task_id)
    if not item:
        return not_found_response("Recurring task not found")
    if not g.api_user.is_admin and item.created_by != g.api_user.id:
        return not_found_response("Recurring task not found")
    return jsonify({"recurring_task": item.to_dict()})
