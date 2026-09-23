"""API v1 - Weekly time goals."""

from flask import Blueprint, g, jsonify, request

from app.models import WeeklyTimeGoal
from app.utils.api_auth import require_api_token
from app.utils.api_responses import not_found_response

api_v1_weekly_goals_bp = Blueprint("api_v1_weekly_goals", __name__, url_prefix="/api/v1")


@api_v1_weekly_goals_bp.route("/weekly-goals", methods=["GET"])
@require_api_token("read:users")
def list_weekly_goals():
    """List weekly goals for the authenticated user."""
    status = request.args.get("status")
    q = WeeklyTimeGoal.query.filter_by(user_id=g.api_user.id)
    if status:
        q = q.filter(WeeklyTimeGoal.status == status.strip())
    goals = q.order_by(WeeklyTimeGoal.week_start_date.desc()).limit(100).all()
    return jsonify({"weekly_goals": [g.to_dict() for g in goals]})


@api_v1_weekly_goals_bp.route("/weekly-goals/<int:goal_id>", methods=["GET"])
@require_api_token("read:users")
def get_weekly_goal(goal_id):
    """Get a weekly goal (own goals only unless admin)."""
    goal = WeeklyTimeGoal.query.get(goal_id)
    if not goal:
        return not_found_response("Weekly goal not found")
    if goal.user_id != g.api_user.id and not g.api_user.is_admin:
        return not_found_response("Weekly goal not found")
    return jsonify({"weekly_goal": goal.to_dict()})
