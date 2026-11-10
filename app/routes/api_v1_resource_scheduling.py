"""API v1 - Resource scheduling (team schedule allocations)."""

from datetime import date, datetime, timedelta

from flask import Blueprint, g, jsonify, request

from app import db
from app.models import Task, TimeEntry, User
from app.utils.api_auth import require_api_token
from app.utils.api_responses import not_found_response, validation_error_response

api_v1_resource_scheduling_bp = Blueprint("api_v1_resource_scheduling", __name__, url_prefix="/api/v1")


def _week_start(value: date) -> date:
    return value - timedelta(days=value.weekday())


def _build_schedule(week_of: date, user_ids=None, viewer=None):
    start = _week_start(week_of)
    days = [start + timedelta(days=i) for i in range(7)]
    end = days[-1]

    users_query = User.query.filter_by(is_active=True).order_by(User.username)
    if user_ids:
        users_query = users_query.filter(User.id.in_(user_ids))
    elif viewer and not (viewer.is_admin or viewer.has_permission("view_all_time_entries")):
        users_query = users_query.filter(User.id == viewer.id)
    users = users_query.all()

    from app.services.task_service import task_assigned_to_any_clause

    tasks = (
        Task.query.filter(
            task_assigned_to_any_clause([u.id for u in users]),
            Task.due_date.between(start, end),
        ).all()
        if users
        else []
    )
    tasks_by_user_day = {}
    user_id_set = {u.id for u in users}
    for task in tasks:
        for uid in task.assignee_ids:
            if uid in user_id_set:
                tasks_by_user_day.setdefault((uid, task.due_date), []).append(task)

    actuals = {}
    if users:
        start_dt = datetime.combine(start, datetime.min.time())
        end_dt = datetime.combine(end, datetime.max.time())
        rows = (
            db.session.query(
                TimeEntry.user_id,
                TimeEntry.start_time,
                TimeEntry.duration_seconds,
            )
            .filter(
                TimeEntry.user_id.in_([u.id for u in users]),
                TimeEntry.end_time.isnot(None),
                TimeEntry.start_time >= start_dt,
                TimeEntry.start_time <= end_dt,
            )
            .all()
        )
        for user_id, start_time, seconds in rows:
            day = start_time.date() if start_time else None
            if day:
                actuals[(user_id, day)] = actuals.get((user_id, day), 0) + (seconds or 0)

    allocations = []
    lanes = []
    for user in users:
        daily_cap = float(user.daily_hour_limit_override or user.standard_hours_per_day or 8)
        cells = []
        for day in days:
            day_tasks = tasks_by_user_day.get((user.id, day), [])
            planned = sum(float(t.estimated_hours or 0) for t in day_tasks)
            actual_hours = round(actuals.get((user.id, day), 0) / 3600, 2)
            for task in day_tasks:
                allocations.append(
                    {
                        "user_id": user.id,
                        "task_id": task.id,
                        "project_id": task.project_id,
                        "date": day.isoformat(),
                        "planned_hours": float(task.estimated_hours or 0),
                        "task_name": task.name,
                    }
                )
            cells.append(
                {
                    "date": day.isoformat(),
                    "task_ids": [t.id for t in day_tasks],
                    "planned_hours": planned,
                    "actual_hours": actual_hours,
                    "capacity": daily_cap,
                    "over_capacity": planned > daily_cap,
                }
            )
        lanes.append({"user_id": user.id, "username": user.username, "cells": cells})

    return {
        "week_start": start.isoformat(),
        "days": [d.isoformat() for d in days],
        "lanes": lanes,
        "allocations": allocations,
    }


@api_v1_resource_scheduling_bp.route("/resource-scheduling", methods=["GET"])
@require_api_token(("read:projects", "read:tasks"))
def list_resource_schedule():
    """List weekly resource schedule / task allocations (same data as web team schedule)."""
    week_of_str = (request.args.get("week_of") or "").strip()
    try:
        week_of = datetime.strptime(week_of_str, "%Y-%m-%d").date() if week_of_str else date.today()
    except ValueError:
        return validation_error_response({"week_of": ["Invalid date; use YYYY-MM-DD"]})

    user_ids = request.args.getlist("user_id", type=int)
    payload = _build_schedule(week_of, user_ids=user_ids or None, viewer=g.api_user)
    return jsonify(payload)


@api_v1_resource_scheduling_bp.route("/resource-scheduling/allocations", methods=["POST"])
@require_api_token(("write:tasks", "write:projects"))
def create_resource_allocation():
    """Create an allocation by assigning a task to a user on a due date (web schedule model)."""
    data = request.get_json() or {}
    errors = {}
    task_id = data.get("task_id")
    user_id = data.get("user_id")
    due_date_raw = data.get("date") or data.get("due_date")

    if not task_id:
        errors.setdefault("task_id", []).append("Required")
    if not user_id:
        errors.setdefault("user_id", []).append("Required")
    if not due_date_raw:
        errors.setdefault("date", []).append("Required (YYYY-MM-DD)")
    if errors:
        return validation_error_response(errors)

    try:
        due_date = datetime.strptime(str(due_date_raw), "%Y-%m-%d").date()
    except ValueError:
        return validation_error_response({"date": ["Invalid date; use YYYY-MM-DD"]})

    task = Task.query.get(task_id)
    if not task:
        return not_found_response("Task not found")
    user = User.query.get(user_id)
    if not user or not user.is_active:
        return not_found_response("User not found")

    task.due_date = due_date
    current_ids = list(task.assignee_ids)
    if user.id not in current_ids:
        current_ids.append(user.id)
        task.set_assignees(current_ids)
    if data.get("estimated_hours") is not None:
        try:
            task.estimated_hours = float(data.get("estimated_hours"))
        except (TypeError, ValueError):
            return validation_error_response({"estimated_hours": ["Must be a number"]})

    db.session.commit()
    return (
        jsonify(
            {
                "allocation": {
                    "user_id": user.id,
                    "task_id": task.id,
                    "project_id": task.project_id,
                    "date": due_date.isoformat(),
                    "planned_hours": float(task.estimated_hours or 0),
                    "task_name": task.name,
                }
            }
        ),
        201,
    )
