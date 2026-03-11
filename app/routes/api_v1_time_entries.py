"""
API v1 - Time Entries and Timer endpoints.
Sub-blueprint for /api/v1/time-entries and /api/v1/timer/*.
"""

from flask import Blueprint, jsonify, request, g
from marshmallow import ValidationError
from app.utils.api_auth import require_api_token
from app.utils.api_responses import validation_error_response, handle_validation_error
from app.routes.api_v1_common import paginate_query, parse_datetime, _parse_date_range
from app.schemas.time_entry_schema import TimeEntryCreateSchema, TimeEntryUpdateSchema

api_v1_time_entries_bp = Blueprint("api_v1_time_entries", __name__, url_prefix="/api/v1")


@api_v1_time_entries_bp.route("/time-entries", methods=["GET"])
@require_api_token("read:time_entries")
def list_time_entries():
    """List time entries with filters."""
    from sqlalchemy.orm import joinedload
    from app.models import TimeEntry

    project_id = request.args.get("project_id", type=int)
    user_id = request.args.get("user_id", type=int)
    if user_id:
        if not g.api_user.is_admin and user_id != g.api_user.id:
            return jsonify({"error": "Access denied"}), 403
    else:
        if not g.api_user.is_admin:
            user_id = g.api_user.id

    start_date = request.args.get("start_date")
    end_date = request.args.get("end_date")
    start_dt, end_dt = _parse_date_range(start_date, end_date)

    billable = request.args.get("billable")
    billable_filter = None
    if billable is not None:
        billable_filter = billable.lower() == "true"

    include_active = request.args.get("include_active") == "true"
    page = request.args.get("page", 1, type=int)
    per_page = request.args.get("per_page", 50, type=int)

    query = TimeEntry.query.options(
        joinedload(TimeEntry.project), joinedload(TimeEntry.user), joinedload(TimeEntry.task)
    )
    if project_id:
        query = query.filter(TimeEntry.project_id == project_id)
    if user_id:
        query = query.filter(TimeEntry.user_id == user_id)
    if start_dt:
        query = query.filter(TimeEntry.start_time >= start_dt)
    if end_dt:
        query = query.filter(TimeEntry.start_time <= end_dt)
    if billable_filter is not None:
        query = query.filter(TimeEntry.billable == billable_filter)
    if not include_active:
        query = query.filter(TimeEntry.end_time.isnot(None))

    query = query.order_by(TimeEntry.start_time.desc())
    result = paginate_query(query, page, per_page)
    return jsonify({"time_entries": [e.to_dict() for e in result["items"]], "pagination": result["pagination"]})


@api_v1_time_entries_bp.route("/time-entries/<int:entry_id>", methods=["GET"])
@require_api_token("read:time_entries")
def get_time_entry(entry_id):
    """Get a specific time entry."""
    from sqlalchemy.orm import joinedload
    from app.models import TimeEntry

    entry = (
        TimeEntry.query.options(joinedload(TimeEntry.project), joinedload(TimeEntry.user), joinedload(TimeEntry.task))
        .filter_by(id=entry_id)
        .first_or_404()
    )
    if not g.api_user.is_admin and entry.user_id != g.api_user.id:
        return jsonify({"error": "Access denied"}), 403
    return jsonify({"time_entry": entry.to_dict()})


@api_v1_time_entries_bp.route("/time-entries", methods=["POST"])
@require_api_token("write:time_entries")
def create_time_entry():
    """Create a new time entry."""
    from app.services import TimeTrackingService

    data = request.get_json() or {}
    schema = TimeEntryCreateSchema()
    try:
        validated = schema.load(data)
    except ValidationError as err:
        return handle_validation_error(err)

    start_time = validated["start_time"]
    end_time = validated.get("end_time") or start_time

    time_tracking_service = TimeTrackingService()
    result = time_tracking_service.create_manual_entry(
        user_id=g.api_user.id,
        project_id=validated.get("project_id"),
        client_id=validated.get("client_id"),
        start_time=start_time,
        end_time=end_time,
        task_id=validated.get("task_id"),
        notes=validated.get("notes"),
        tags=validated.get("tags"),
        billable=validated.get("billable", True),
        paid=validated.get("paid", False),
        invoice_number=validated.get("invoice_number"),
    )

    if not result.get("success"):
        return jsonify({"error": result.get("message", "Could not create time entry")}), 400

    entry = result.get("entry")
    if entry:
        from app.models import Activity
        from app.utils.audit import get_request_info

        entity_name = entry.project.name if entry.project else (entry.client.name if entry.client else "Unknown")
        task_name = entry.task.name if entry.task else None
        duration_formatted = entry.duration_formatted if hasattr(entry, "duration_formatted") else "0:00"
        ip_address, user_agent, _ = get_request_info()
        Activity.log(
            user_id=g.api_user.id,
            action="created",
            entity_type="time_entry",
            entity_id=entry.id,
            entity_name=f"{entity_name}" + (f" - {task_name}" if task_name else ""),
            description=f"Created time entry for {entity_name}"
            + (f" - {task_name}" if task_name else "")
            + f" - {duration_formatted}",
            extra_data={
                "project_name": entry.project.name if entry.project else None,
                "client_name": entry.client.name if entry.client else None,
                "task_name": task_name,
                "duration_formatted": duration_formatted,
                "duration_hours": entry.duration_hours if hasattr(entry, "duration_hours") else None,
            },
            ip_address=ip_address,
            user_agent=user_agent,
        )

    return jsonify({"message": "Time entry created successfully", "time_entry": result["entry"].to_dict()}), 201


@api_v1_time_entries_bp.route("/time-entries/<int:entry_id>", methods=["PUT", "PATCH"])
@require_api_token("write:time_entries")
def update_time_entry(entry_id):
    """Update a time entry."""
    from app.services import TimeTrackingService

    data = request.get_json() or {}
    schema = TimeEntryUpdateSchema()
    try:
        validated = schema.load(data, partial=True)
    except ValidationError as err:
        return handle_validation_error(err)

    time_tracking_service = TimeTrackingService()
    result = time_tracking_service.update_entry(
        entry_id=entry_id,
        user_id=g.api_user.id,
        is_admin=g.api_user.is_admin,
        project_id=validated.get("project_id"),
        client_id=validated.get("client_id"),
        task_id=validated.get("task_id"),
        start_time=validated.get("start_time"),
        end_time=validated.get("end_time"),
        notes=validated.get("notes"),
        tags=validated.get("tags"),
        billable=validated.get("billable"),
        paid=validated.get("paid"),
        invoice_number=validated.get("invoice_number"),
        reason=data.get("reason"),
    )

    if not result.get("success"):
        return jsonify({"error": result.get("message", "Could not update time entry")}), 400

    entry = result.get("entry")
    if entry:
        from app.models import Activity
        from app.utils.audit import get_request_info

        entity_name = entry.project.name if entry.project else (entry.client.name if entry.client else "Unknown")
        task_name = entry.task.name if entry.task else None
        ip_address, user_agent, _ = get_request_info()
        Activity.log(
            user_id=g.api_user.id,
            action="updated",
            entity_type="time_entry",
            entity_id=entry.id,
            entity_name=f"{entity_name}" + (f" - {task_name}" if task_name else ""),
            description=f"Updated time entry for {entity_name}" + (f" - {task_name}" if task_name else ""),
            extra_data={
                "project_name": entry.project.name if entry.project else None,
                "client_name": entry.client.name if entry.client else None,
                "task_name": task_name,
            },
            ip_address=ip_address,
            user_agent=user_agent,
        )

    return jsonify({"message": "Time entry updated successfully", "time_entry": result["entry"].to_dict()})


@api_v1_time_entries_bp.route("/time-entries/<int:entry_id>", methods=["DELETE"])
@require_api_token("write:time_entries")
def delete_time_entry(entry_id):
    """Delete a time entry."""
    from app.services import TimeTrackingService

    data = request.get_json() or {}
    reason = data.get("reason")
    time_tracking_service = TimeTrackingService()
    result = time_tracking_service.delete_entry(
        entry_id=entry_id,
        user_id=g.api_user.id,
        is_admin=g.api_user.is_admin,
        reason=reason,
    )
    if not result.get("success"):
        return jsonify({"error": result.get("message", "Could not delete time entry")}), 400
    return jsonify({"message": "Time entry deleted successfully"})


@api_v1_time_entries_bp.route("/timer/status", methods=["GET"])
@require_api_token("read:time_entries")
def timer_status():
    """Get current timer status."""
    active_timer = g.api_user.active_timer
    if not active_timer:
        return jsonify({"active": False, "timer": None})
    return jsonify({"active": True, "timer": active_timer.to_dict()})


@api_v1_time_entries_bp.route("/timer/start", methods=["POST"])
@require_api_token("write:time_entries")
def start_timer():
    """Start a new timer."""
    from app.services import TimeTrackingService

    data = request.get_json() or {}
    project_id = data.get("project_id")
    if not project_id:
        return jsonify({"error": "project_id is required"}), 400
    time_tracking_service = TimeTrackingService()
    result = time_tracking_service.start_timer(
        user_id=g.api_user.id,
        project_id=project_id,
        task_id=data.get("task_id"),
        notes=data.get("notes"),
        template_id=data.get("template_id"),
    )
    if not result.get("success"):
        return jsonify({"error": result.get("message", "Could not start timer")}), 400
    return jsonify({"message": "Timer started successfully", "timer": result["timer"].to_dict()}), 201


@api_v1_time_entries_bp.route("/timer/stop", methods=["POST"])
@require_api_token("write:time_entries")
def stop_timer():
    """Stop the active timer."""
    from app.services import TimeTrackingService

    active_timer = g.api_user.active_timer
    if not active_timer:
        return jsonify({"error": "No active timer to stop", "error_code": "no_active_timer"}), 400
    time_tracking_service = TimeTrackingService()
    result = time_tracking_service.stop_timer(user_id=g.api_user.id, entry_id=active_timer.id)
    if not result.get("success"):
        return jsonify({
            "error": result.get("message", "Could not stop timer"),
            "error_code": result.get("error", "stop_failed"),
        }), 400
    return jsonify({"message": "Timer stopped successfully", "time_entry": result["entry"].to_dict()})
