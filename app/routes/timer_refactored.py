"""
REFERENCE ONLY — This module is not registered as an active blueprint.

Refactored timer routes using service layer and app.utils.api_responses.
It demonstrates the intended architecture pattern. The active routes live in
app/routes/timer.py. Do not register this blueprint; use it as reference when
refactoring or when adding new timer routes.
"""

from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, current_app
from flask_babel import gettext as _
from flask_login import login_required, current_user
from app import db, socketio, log_event, track_event
from app.services import TimeTrackingService
from app.repositories import TimeEntryRepository
from app.models import Project, Task, Activity
from app.utils.db import safe_commit
from app.utils.api_responses import success_response, error_response
from app.utils.event_bus import emit_event
from app.constants import WebhookEvent
from app.utils.posthog_funnels import track_onboarding_first_timer

timer_bp = Blueprint("timer", __name__)


@timer_bp.route("/timer/start", methods=["POST"])
@login_required
def start_timer():
    """Start a new timer for the current user - REFACTORED VERSION"""
    project_id = request.form.get("project_id", type=int)
    task_id = request.form.get("task_id", type=int)
    notes = request.form.get("notes", "").strip()
    template_id = request.form.get("template_id", type=int)

    current_app.logger.info(
        "POST /timer/start user=%s project_id=%s task_id=%s template_id=%s",
        current_user.username,
        project_id,
        task_id,
        template_id,
    )

    # Use service layer
    service = TimeTrackingService()
    result = service.start_timer(
        user_id=current_user.id, project_id=project_id, task_id=task_id, notes=notes, template_id=template_id
    )

    if not result["success"]:
        flash(_(result["message"]), "error")
        current_app.logger.warning("Start timer failed: %s", result.get("error", "unknown"))
        return redirect(url_for("main.dashboard"))

    timer = result["timer"]

    # Log activity
    project = Project.query.get(project_id)
    task = Task.query.get(task_id) if task_id else None

    Activity.log(
        user_id=current_user.id,
        action="started",
        entity_type="time_entry",
        entity_id=timer.id,
        entity_name=f"{project.name}" + (f" - {task.name}" if task else ""),
        description=f"Started timer for {project.name}" + (f" - {task.name}" if task else ""),
        extra_data={"project_id": project_id, "task_id": task_id},
        ip_address=request.remote_addr,
        user_agent=request.headers.get("User-Agent"),
    )

    # Track events
    log_event("timer.started", user_id=current_user.id, project_id=project_id, task_id=task_id)
    track_event(
        current_user.id, "timer.started", {"project_id": project_id, "task_id": task_id, "has_description": bool(notes)}
    )

    # Emit domain event
    emit_event(
        WebhookEvent.TIME_ENTRY_CREATED.value,
        {"entry_id": timer.id, "user_id": current_user.id, "project_id": project_id},
    )

    # Check if first timer (onboarding)
    time_entry_repo = TimeEntryRepository()
    timer_count = len(time_entry_repo.find_by(user_id=current_user.id, source="auto"))
    if timer_count == 1:
        track_onboarding_first_timer(
            current_user.id, {"project_id": project_id, "has_task": bool(task_id), "has_notes": bool(notes)}
        )

    # Emit WebSocket event
    try:
        payload = {
            "user_id": current_user.id,
            "timer_id": timer.id,
            "project_name": project.name,
            "start_time": timer.start_time.isoformat(),
        }
        if task:
            payload["task_id"] = task.id
            payload["task_name"] = task.name
        socketio.emit("timer_started", payload)
    except Exception as e:
        current_app.logger.warning("Socket emit failed for timer_started: %s", e)

    if task:
        flash(f"Timer started for {project.name} - {task.name}", "success")
    else:
        flash(f"Timer started for {project.name}", "success")

    return redirect(url_for("main.dashboard"))


@timer_bp.route("/timer/stop", methods=["POST"])
@login_required
def stop_timer():
    """Stop the active timer - REFACTORED VERSION"""
    entry_id = request.form.get("entry_id", type=int)

    # Use service layer
    service = TimeTrackingService()
    result = service.stop_timer(user_id=current_user.id, entry_id=entry_id)

    if not result["success"]:
        flash(_(result["message"]), "error")
        return redirect(url_for("main.dashboard"))

    entry = result["entry"]

    # Log activity
    Activity.log(
        user_id=current_user.id,
        action="stopped",
        entity_type="time_entry",
        entity_id=entry.id,
        entity_name=f'{entry.project.name if entry.project else "Unknown"}',
        description=f"Stopped timer",
        extra_data={"project_id": entry.project_id},
        ip_address=request.remote_addr,
        user_agent=request.headers.get("User-Agent"),
    )

    # Track events
    log_event("timer.stopped", user_id=current_user.id, entry_id=entry.id)
    track_event(current_user.id, "timer.stopped", {"entry_id": entry.id, "duration_seconds": entry.duration_seconds})

    # Emit domain event
    emit_event(
        WebhookEvent.TIME_ENTRY_UPDATED.value,
        {"entry_id": entry.id, "user_id": current_user.id, "project_id": entry.project_id},
    )

    # Emit WebSocket event
    try:
        socketio.emit(
            "timer_stopped",
            {"user_id": current_user.id, "entry_id": entry.id, "duration_seconds": entry.duration_seconds},
        )
    except Exception as e:
        current_app.logger.warning("Socket emit failed for timer_stopped: %s", e)

    flash(_("Timer stopped successfully"), "success")
    return redirect(url_for("main.dashboard"))


@timer_bp.route("/api/timer/status", methods=["GET"])
@login_required
def api_timer_status():
    """Get timer status - REFACTORED VERSION"""
    service = TimeTrackingService()
    timer = service.get_active_timer(current_user.id)

    if timer:
        return success_response(
            data={
                "active": True,
                "timer": {
                    "id": timer.id,
                    "project_id": timer.project_id,
                    "project_name": timer.project.name if timer.project else None,
                    "task_id": timer.task_id,
                    "task_name": timer.task.name if timer.task else None,
                    "start_time": timer.start_time.isoformat(),
                    "notes": timer.notes,
                },
            }
        )
    else:
        return success_response(data={"active": False})


@timer_bp.route("/api/timer/start", methods=["POST"])
@login_required
def api_start_timer():
    """Start timer via API - REFACTORED VERSION"""
    from app.utils.validation import validate_json_request
    from app.schemas import TimerStartSchema

    try:
        data = validate_json_request()
        schema = TimerStartSchema()
        validated_data = schema.load(data)
    except Exception as e:
        return error_response(str(e), error_code="validation_error", status_code=400)

    service = TimeTrackingService()
    result = service.start_timer(
        user_id=current_user.id,
        project_id=validated_data["project_id"],
        task_id=validated_data.get("task_id"),
        notes=validated_data.get("notes"),
        template_id=validated_data.get("template_id"),
    )

    if result["success"]:
        # Emit domain event
        emit_event(
            WebhookEvent.TIME_ENTRY_CREATED.value,
            {"entry_id": result["timer"].id, "user_id": current_user.id, "project_id": validated_data["project_id"]},
        )

        return success_response(
            data=result["timer"].to_dict() if hasattr(result["timer"], "to_dict") else result["timer"],
            message=result["message"],
            status_code=201,
        )
    else:
        return error_response(message=result["message"], error_code=result.get("error", "error"), status_code=400)
