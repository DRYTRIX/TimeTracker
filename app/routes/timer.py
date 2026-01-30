from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, current_app
from flask_babel import gettext as _
from flask_login import login_required, current_user
from app import db, socketio, log_event, track_event
from app.models import User, Project, TimeEntry, Task, Settings, Activity, Client
from app.utils.timezone import parse_local_datetime, parse_user_local_datetime, utc_to_local
from datetime import datetime, timedelta
import json
from app.utils.db import safe_commit
from app.utils.posthog_funnels import track_onboarding_first_timer, track_onboarding_first_time_entry
from sqlalchemy import inspect, text
from sqlalchemy.exc import ProgrammingError

timer_bp = Blueprint("timer", __name__)


def _parse_optional_int(value):
    """Return int(value) if value is a non-empty string that converts to int, else None."""
    if value is None or (isinstance(value, str) and not value.strip()):
        return None
    try:
        return int(value)
    except (ValueError, TypeError):
        return None


@timer_bp.route("/timer/start", methods=["POST"])
@login_required
def start_timer():
    """Start a new timer for the current user"""
    project_id = _parse_optional_int(request.form.get("project_id"))
    client_id = _parse_optional_int(request.form.get("client_id"))
    task_id = _parse_optional_int(request.form.get("task_id"))
    notes = request.form.get("notes", "").strip()
    template_id = _parse_optional_int(request.form.get("template_id"))
    current_app.logger.info(
        "POST /timer/start user=%s project_id=%s task_id=%s template_id=%s",
        current_user.username,
        project_id,
        task_id,
        template_id,
    )

    # Load template data if template_id is provided
    if template_id:
        from app.models import TimeEntryTemplate

        template = TimeEntryTemplate.query.filter_by(id=template_id, user_id=current_user.id).first()
        if template:
            # Override with template values if not explicitly set
            if not project_id and template.project_id:
                project_id = template.project_id
            if not task_id and template.task_id:
                task_id = template.task_id
            if not notes and template.default_notes:
                notes = template.default_notes
            # Mark template as used
            template.record_usage()
            db.session.commit()

    # Require either project or client
    if not project_id and not client_id:
        flash(_("Either a project or a client is required"), "error")
        current_app.logger.warning("Start timer failed: missing project_id and client_id")
        return redirect(url_for("main.dashboard"))

    project = None
    client = None

    # Validate project if provided
    if project_id:
        project = Project.query.get(project_id)
        if not project:
            flash(_("Invalid project selected"), "error")
            current_app.logger.warning("Start timer failed: invalid project_id=%s", project_id)
            return redirect(url_for("main.dashboard"))

        # Check if project is active (not archived or inactive)
        if project.status == "archived":
            flash(_("Cannot start timer for an archived project. Please unarchive the project first."), "error")
            current_app.logger.warning("Start timer failed: project_id=%s is archived", project_id)
            return redirect(url_for("main.dashboard"))
        elif project.status != "active":
            flash(_("Cannot start timer for an inactive project"), "error")
            current_app.logger.warning("Start timer failed: project_id=%s is not active", project_id)
            return redirect(url_for("main.dashboard"))

        # If a task is provided, validate it belongs to the project
        if task_id:
            task = Task.query.filter_by(id=task_id, project_id=project_id).first()
            if not task:
                flash(_("Selected task is invalid for the chosen project"), "error")
                current_app.logger.warning(
                    "Start timer failed: task_id=%s does not belong to project_id=%s", task_id, project_id
                )
                return redirect(url_for("main.dashboard"))
        else:
            task = None
    else:
        task = None

    # Validate client if provided (and no project)
    if client_id and not project_id:
        client = Client.query.filter_by(id=client_id, status="active").first()
        if not client:
            flash(_("Invalid client selected"), "error")
            current_app.logger.warning("Start timer failed: invalid client_id=%s", client_id)
            return redirect(url_for("main.dashboard"))

        # Tasks are not allowed for client-only timers
        if task_id:
            flash(_("Tasks can only be selected for project-based timers"), "error")
            current_app.logger.warning(
                "Start timer failed: task_id=%s provided for client-only timer (client_id=%s)", task_id, client_id
            )
            return redirect(url_for("main.dashboard"))

    # Check if user already has an active timer
    active_timer = current_user.active_timer
    if active_timer:
        flash(_("You already have an active timer. Stop it before starting a new one."), "error")
        current_app.logger.info("Start timer blocked: user already has an active timer")
        return redirect(url_for("main.dashboard"))

    # Create new timer
    from app.models.time_entry import local_now

    new_timer = TimeEntry(
        user_id=current_user.id,
        project_id=project_id if project_id else None,
        client_id=client_id if client_id and not project_id else None,
        task_id=task.id if task else None,
        start_time=local_now(),
        notes=notes if notes else None,
        source="auto",
    )

    db.session.add(new_timer)
    if not safe_commit(
        "start_timer",
        {
            "user_id": current_user.id,
            "project_id": project_id,
            "client_id": client_id,
            "task_id": task_id,
        },
    ):
        flash(_("Could not start timer due to a database error. Please check server logs."), "error")
        return redirect(url_for("main.dashboard"))
    current_app.logger.info(
        "Started new timer id=%s for user=%s project_id=%s client_id=%s task_id=%s",
        new_timer.id,
        current_user.username,
        project_id,
        client_id,
        task_id,
    )

    # Track timer started event
    log_event(
        "timer.started",
        user_id=current_user.id,
        project_id=project_id,
        client_id=client_id,
        task_id=task_id,
        description=notes,
    )
    track_event(
        current_user.id,
        "timer.started",
        {
            "project_id": project_id,
            "client_id": client_id,
            "task_id": task_id,
            "has_description": bool(notes),
        },
    )

    # Log activity
    Activity.log(
        user_id=current_user.id,
        action="started",
        entity_type="time_entry",
        entity_id=new_timer.id,
        entity_name=(f"{project.name}" if project else f"{client.name if client else _('Unknown')}")
        + (f" - {task.name}" if task else ""),
        description=(
            f"Started timer for {project.name}"
            if project
            else f"Started timer for {client.name if client else _('Unknown')}"
        )
        + (f" - {task.name}" if task else ""),
        extra_data={"project_id": project_id, "client_id": client_id, "task_id": task_id},
        ip_address=request.remote_addr,
        user_agent=request.headers.get("User-Agent"),
    )

    # Check if this is user's first timer (onboarding milestone)
    timer_count = TimeEntry.query.filter_by(user_id=current_user.id, source="auto").count()

    if timer_count == 1:  # First timer ever
        track_onboarding_first_timer(
            current_user.id,
            {
                "project_id": project_id,
                "client_id": client_id,
                "has_task": bool(task_id),
                "has_notes": bool(notes),
            },
        )

    # Emit WebSocket event for real-time updates
    try:
        payload = {
            "user_id": current_user.id,
            "timer_id": new_timer.id,
            "project_name": project.name if project else None,
            "client_name": client.name if client else None,
            "start_time": new_timer.start_time.isoformat(),
        }
        if task:
            payload["task_id"] = task.id
            payload["task_name"] = task.name
        socketio.emit("timer_started", payload)
    except Exception as e:
        current_app.logger.warning("Socket emit failed for timer_started: %s", e)

    # Invalidate dashboard cache so timer appears immediately
    try:
        from app.utils.cache import get_cache
        cache = get_cache()
        cache_key = f"dashboard:{current_user.id}"
        cache.delete(cache_key)
        current_app.logger.debug("Invalidated dashboard cache for user %s", current_user.id)
    except Exception as e:
        current_app.logger.warning("Failed to invalidate dashboard cache: %s", e)

    if task:
        flash(f"Timer started for {project.name} - {task.name}", "success")
    elif project:
        flash(f"Timer started for {project.name}", "success")
    elif client:
        flash(f"Timer started for {client.name}", "success")
    else:
        flash(_("Timer started"), "success")
    return redirect(url_for("main.dashboard"))


@timer_bp.route("/timer/start/from-template/<int:template_id>", methods=["GET", "POST"])
@login_required
def start_timer_from_template(template_id):
    """Start a timer directly from a template"""
    from app.models import TimeEntryTemplate

    # Load template
    template = TimeEntryTemplate.query.filter_by(id=template_id, user_id=current_user.id).first_or_404()

    # Check if user already has an active timer
    active_timer = current_user.active_timer
    if active_timer:
        flash(_("You already have an active timer. Stop it before starting a new one."), "error")
        return redirect(url_for("main.dashboard"))

    # Validate template has required data
    if not template.project_id:
        flash(_("Template must have a project to start a timer"), "error")
        return redirect(url_for("time_entry_templates.list_templates"))

    # Check if project is active
    project = Project.query.get(template.project_id)
    if not project or project.status != "active":
        flash(_("Cannot start timer for this project"), "error")
        return redirect(url_for("time_entry_templates.list_templates"))

    # Create new timer from template
    from app.models.time_entry import local_now

    new_timer = TimeEntry(
        user_id=current_user.id,
        project_id=template.project_id,
        task_id=template.task_id,
        start_time=local_now(),
        notes=template.default_notes,
        tags=template.tags,
        source="auto",
        billable=template.billable,
    )

    db.session.add(new_timer)

    # Mark template as used
    template.record_usage()

    if not safe_commit("start_timer_from_template", {"template_id": template_id}):
        flash(_("Could not start timer due to a database error. Please check server logs."), "error")
        return redirect(url_for("time_entry_templates.list_templates"))

    # Track events
    log_event(
        "timer.started.from_template", user_id=current_user.id, template_id=template_id, project_id=template.project_id
    )
    track_event(
        current_user.id,
        "timer.started.from_template",
        {
            "template_id": template_id,
            "template_name": template.name,
            "project_id": template.project_id,
            "has_task": bool(template.task_id),
        },
    )

    # Invalidate dashboard cache so timer appears immediately
    try:
        from app.utils.cache import get_cache
        cache = get_cache()
        cache_key = f"dashboard:{current_user.id}"
        cache.delete(cache_key)
        current_app.logger.debug("Invalidated dashboard cache for user %s", current_user.id)
    except Exception as e:
        current_app.logger.warning("Failed to invalidate dashboard cache: %s", e)

    flash(f'Timer started from template "{template.name}"', "success")
    return redirect(url_for("main.dashboard"))


@timer_bp.route("/timer/start/<int:project_id>")
@login_required
def start_timer_for_project(project_id):
    """Start a timer for a specific project (GET route for direct links)"""
    task_id = request.args.get("task_id", type=int)
    current_app.logger.info("GET /timer/start/%s user=%s task_id=%s", project_id, current_user.username, task_id)

    # Check if project exists
    project = Project.query.get(project_id)
    if not project:
        flash(_("Invalid project selected"), "error")
        current_app.logger.warning("Start timer (GET) failed: invalid project_id=%s", project_id)
        return redirect(url_for("main.dashboard"))

    # Check if project is active (not archived or inactive)
    if project.status == "archived":
        flash(_("Cannot start timer for an archived project. Please unarchive the project first."), "error")
        current_app.logger.warning("Start timer (GET) failed: project_id=%s is archived", project_id)
        return redirect(url_for("main.dashboard"))
    elif project.status != "active":
        flash(_("Cannot start timer for an inactive project"), "error")
        current_app.logger.warning("Start timer (GET) failed: project_id=%s is not active", project_id)
        return redirect(url_for("main.dashboard"))

    # Check if user already has an active timer
    active_timer = current_user.active_timer
    if active_timer:
        flash(_("You already have an active timer. Stop it before starting a new one."), "error")
        current_app.logger.info("Start timer (GET) blocked: user already has an active timer")
        return redirect(url_for("main.dashboard"))

    # Create new timer
    from app.models.time_entry import local_now

    new_timer = TimeEntry(
        user_id=current_user.id, project_id=project_id, task_id=task_id, start_time=local_now(), source="auto"
    )

    db.session.add(new_timer)
    if not safe_commit(
        "start_timer_for_project", {"user_id": current_user.id, "project_id": project_id, "task_id": task_id}
    ):
        flash(_("Could not start timer due to a database error. Please check server logs."), "error")
        return redirect(url_for("main.dashboard"))
    current_app.logger.info(
        "Started new timer id=%s for user=%s project_id=%s task_id=%s",
        new_timer.id,
        current_user.username,
        project_id,
        task_id,
    )

    # Emit WebSocket event for real-time updates
    try:
        socketio.emit(
            "timer_started",
            {
                "user_id": current_user.id,
                "timer_id": new_timer.id,
                "project_name": project.name,
                "task_id": task_id,
                "start_time": new_timer.start_time.isoformat(),
            },
        )
    except Exception as e:
        current_app.logger.warning("Socket emit failed for timer_started (GET): %s", e)

    # Invalidate dashboard cache so timer appears immediately
    try:
        from app.utils.cache import get_cache
        cache = get_cache()
        cache_key = f"dashboard:{current_user.id}"
        cache.delete(cache_key)
        current_app.logger.debug("Invalidated dashboard cache for user %s", current_user.id)
    except Exception as e:
        current_app.logger.warning("Failed to invalidate dashboard cache: %s", e)

    if task_id:
        task = Task.query.get(task_id)
        task_name = task.name if task else "Unknown Task"
        flash(f"Timer started for {project.name} - {task_name}", "success")
    else:
        flash(f"Timer started for {project.name}", "success")

    return redirect(url_for("main.dashboard"))


@timer_bp.route("/timer/stop", methods=["POST"])
@login_required
def stop_timer():
    """Stop the current user's active timer"""
    active_timer = current_user.active_timer
    current_app.logger.info("POST /timer/stop user=%s active_timer=%s", current_user.username, bool(active_timer))

    if not active_timer:
        flash(_("No active timer to stop"), "error")
        return redirect(url_for("main.dashboard"))

    # Stop the timer
    try:
        active_timer.stop_timer()
        current_app.logger.info("Stopped timer id=%s for user=%s", active_timer.id, current_user.username)

        # Track timer stopped event
        duration_seconds = active_timer.duration_seconds if active_timer.duration_seconds else 0
        log_event(
            "timer.stopped",
            user_id=current_user.id,
            time_entry_id=active_timer.id,
            project_id=active_timer.project_id,
            task_id=active_timer.task_id,
            duration_seconds=duration_seconds,
        )
        track_event(
            current_user.id,
            "timer.stopped",
            {
                "time_entry_id": active_timer.id,
                "project_id": active_timer.project_id,
                "task_id": active_timer.task_id,
                "duration_seconds": duration_seconds,
            },
        )

        # Log activity
        project_name = active_timer.project.name if active_timer.project else "No project"
        task_name = active_timer.task.name if active_timer.task else None
        Activity.log(
            user_id=current_user.id,
            action="stopped",
            entity_type="time_entry",
            entity_id=active_timer.id,
            entity_name=f"{project_name}" + (f" - {task_name}" if task_name else ""),
            description=f"Stopped timer for {project_name}"
            + (f" - {task_name}" if task_name else "")
            + f" - Duration: {active_timer.duration_formatted}",
            extra_data={
                "duration_hours": active_timer.duration_hours,
                "project_id": active_timer.project_id,
                "task_id": active_timer.task_id,
            },
            ip_address=request.remote_addr,
            user_agent=request.headers.get("User-Agent"),
        )

        # Check if this is user's first completed time entry (onboarding milestone)
        entry_count = TimeEntry.query.filter_by(user_id=current_user.id).filter(TimeEntry.end_time.isnot(None)).count()

        if entry_count == 1:  # First completed time entry ever
            track_onboarding_first_time_entry(
                current_user.id,
                {"source": "timer", "duration_seconds": duration_seconds, "has_task": bool(active_timer.task_id)},
            )

        # Emit WebSocket event for real-time updates
        try:
            socketio.emit(
                "timer_stopped",
                {"user_id": current_user.id, "timer_id": active_timer.id, "duration": active_timer.duration_formatted},
            )
        except Exception as e:
            current_app.logger.warning("Socket emit failed for timer_stopped: %s", e)

        # Invalidate dashboard cache so timer disappears immediately
        try:
            from app.utils.cache import get_cache
            cache = get_cache()
            cache_key = f"dashboard:{current_user.id}"
            cache.delete(cache_key)
            current_app.logger.debug("Invalidated dashboard cache for user %s", current_user.id)
        except Exception as e:
            current_app.logger.warning("Failed to invalidate dashboard cache: %s", e)

        flash(f"Timer stopped. Duration: {active_timer.duration_formatted}", "success")
        return redirect(url_for("main.dashboard"))
    except ValueError as e:
        # Timer already stopped or invalid state
        current_app.logger.warning("Cannot stop timer: %s", e)
        flash(_("Cannot stop timer: %(error)s", error=str(e)), "error")
        return redirect(url_for("main.dashboard"))
    except Exception as e:
        current_app.logger.exception("Error stopping timer: %s", e)
        flash(_("Could not stop timer due to an error. Please try again or contact support if the problem persists."), "error")
        return redirect(url_for("main.dashboard"))


@timer_bp.route("/timer/status")
@login_required
def timer_status():
    """Get current timer status as JSON"""
    active_timer = current_user.active_timer

    if not active_timer:
        return jsonify({"active": False, "timer": None})

    return jsonify(
        {
            "active": True,
            "timer": {
                "id": active_timer.id,
                "project_name": active_timer.project.name if active_timer.project else None,
                "client_name": active_timer.client.name if active_timer.client else None,
                "start_time": active_timer.start_time.isoformat(),
                "current_duration": active_timer.current_duration_seconds,
                "duration_formatted": active_timer.duration_formatted,
            },
        }
    )


@timer_bp.route("/timer/edit/<int:timer_id>", methods=["GET", "POST"])
@login_required
def edit_timer(timer_id):
    """Edit a completed timer entry"""
    timer = TimeEntry.query.get_or_404(timer_id)

    # Check if user can edit this timer
    if timer.user_id != current_user.id and not current_user.is_admin:
        flash(_("You can only edit your own timers"), "error")
        return redirect(url_for("main.dashboard"))

    if request.method == "POST":
        # Get reason for change
        reason = request.form.get("reason", "").strip() or None
        
        # Use service layer for update to get enhanced audit logging
        from app.services import TimeTrackingService
        service = TimeTrackingService()
        
        # Prepare update parameters
        update_params = {
            "entry_id": timer_id,
            "user_id": current_user.id,
            "is_admin": current_user.is_admin,
            "notes": request.form.get("notes", "").strip() or None,
            "tags": request.form.get("tags", "").strip() or None,
            "billable": request.form.get("billable") == "on",
            "paid": request.form.get("paid") == "on",
            "reason": reason,
        }
        
        # Update invoice number
        invoice_number = request.form.get("invoice_number", "").strip()
        update_params["invoice_number"] = invoice_number if invoice_number else None
        # Clear invoice number if marking as unpaid
        if update_params["paid"] is False:
            update_params["invoice_number"] = None

        # Admin users can edit additional fields
        if current_user.is_admin:
            # Update project if changed
            new_project_id = request.form.get("project_id", type=int)
            if new_project_id and new_project_id != timer.project_id:
                new_project = Project.query.filter_by(id=new_project_id, status="active").first()
                if new_project:
                    update_params["project_id"] = new_project_id
                else:
                    flash(_("Invalid project selected"), "error")
                    return render_template(
                        "timer/edit_timer.html",
                        timer=timer,
                        projects=Project.query.filter_by(status="active").order_by(Project.name).all(),
                        tasks=(
                            []
                            if not new_project_id
                            else Task.query.filter_by(project_id=new_project_id).order_by(Task.name).all()
                        ),
                    )
            else:
                update_params["project_id"] = None  # Don't change if not provided

            # Update task if changed
            new_task_id = request.form.get("task_id", type=int)
            if new_task_id != timer.task_id:
                if new_task_id:
                    new_task = Task.query.filter_by(id=new_task_id, project_id=update_params.get("project_id") or timer.project_id).first()
                    if new_task:
                        update_params["task_id"] = new_task_id
                    else:
                        flash(_("Invalid task selected for the chosen project"), "error")
                        return render_template(
                            "timer/edit_timer.html",
                            timer=timer,
                            projects=Project.query.filter_by(status="active").order_by(Project.name).all(),
                            tasks=Task.query.filter_by(project_id=timer.project_id).order_by(Task.name).all(),
                        )
                else:
                    update_params["task_id"] = None
            else:
                update_params["task_id"] = None  # Don't change if not provided

            # Update start and end times if provided
            start_date = request.form.get("start_date")
            start_time = request.form.get("start_time")
            end_date = request.form.get("end_date")
            end_time = request.form.get("end_time")

            if start_date and start_time:
                try:
                    # Convert parsed UTC-aware to local naive to match model storage
                    parsed_start_utc = parse_local_datetime(start_date, start_time)
                    new_start_time = utc_to_local(parsed_start_utc).replace(tzinfo=None)

                    # Validate that start time is not in the future
                    from app.models.time_entry import local_now

                    current_time = local_now()
                    if new_start_time > current_time:
                        flash(_("Start time cannot be in the future"), "error")
                        return render_template(
                            "timer/edit_timer.html",
                            timer=timer,
                            projects=Project.query.filter_by(status="active").order_by(Project.name).all(),
                            tasks=Task.query.filter_by(project_id=timer.project_id).order_by(Task.name).all(),
                        )

                    update_params["start_time"] = new_start_time
                except ValueError:
                    flash(_("Invalid start date/time format"), "error")
                    return render_template(
                        "timer/edit_timer.html",
                        timer=timer,
                        projects=Project.query.filter_by(status="active").order_by(Project.name).all(),
                        tasks=Task.query.filter_by(project_id=timer.project_id).order_by(Task.name).all(),
                    )
            else:
                update_params["start_time"] = None

            if end_date and end_time:
                try:
                    # Convert parsed UTC-aware to local naive to match model storage
                    parsed_end_utc = parse_local_datetime(end_date, end_time)
                    new_end_time = utc_to_local(parsed_end_utc).replace(tzinfo=None)

                    # Validate that end time is after start time
                    start_time_for_validation = update_params.get("start_time") or timer.start_time
                    if new_end_time <= start_time_for_validation:
                        flash(_("End time must be after start time"), "error")
                        return render_template(
                            "timer/edit_timer.html",
                            timer=timer,
                            projects=Project.query.filter_by(status="active").order_by(Project.name).all(),
                            tasks=Task.query.filter_by(project_id=timer.project_id).order_by(Task.name).all(),
                        )

                    update_params["end_time"] = new_end_time
                except ValueError:
                    flash(_("Invalid end date/time format"), "error")
                    return render_template(
                        "timer/edit_timer.html",
                        timer=timer,
                        projects=Project.query.filter_by(status="active").order_by(Project.name).all(),
                        tasks=Task.query.filter_by(project_id=timer.project_id).order_by(Task.name).all(),
                    )
            else:
                update_params["end_time"] = None

        # Call service layer to update
        result = service.update_entry(**update_params)
        
        if not result.get("success"):
            flash(_(result.get("message", "Could not update timer")), "error")
            return render_template(
                "timer/edit_timer.html",
                timer=timer,
                projects=Project.query.filter_by(status="active").order_by(Project.name).all() if current_user.is_admin else [],
                tasks=Task.query.filter_by(project_id=timer.project_id).order_by(Task.name).all() if current_user.is_admin and timer.project_id else [],
            )

        entry = result.get("entry")
        
        # Log activity
        if entry:
            entity_name = entry.project.name if entry.project else (entry.client.name if entry.client else "Unknown")
            task_name = entry.task.name if entry.task else None
            
            Activity.log(
                user_id=current_user.id,
                action="updated",
                entity_type="time_entry",
                entity_id=entry.id,
                entity_name=f"{entity_name}" + (f" - {task_name}" if task_name else ""),
                description=f'Updated time entry for {entity_name}' + (f" - {task_name}" if task_name else ""),
                extra_data={
                    "project_name": entry.project.name if entry.project else None,
                    "client_name": entry.client.name if entry.client else None,
                    "task_name": task_name,
                },
                ip_address=request.remote_addr,
                user_agent=request.headers.get("User-Agent"),
            )

        # Invalidate dashboard cache for the timer owner so changes appear immediately
        try:
            from app.utils.cache import get_cache
            cache = get_cache()
            cache_key = f"dashboard:{timer.user_id}"
            cache.delete(cache_key)
            current_app.logger.debug("Invalidated dashboard cache for user %s after timer edit", timer.user_id)
        except Exception as e:
            current_app.logger.warning("Failed to invalidate dashboard cache: %s", e)

        flash(_("Timer updated successfully"), "success")
        return redirect(url_for("main.dashboard"))

    # Get projects and tasks for admin users
    projects = []
    tasks = []
    if current_user.is_admin:
        projects = Project.query.filter_by(status="active").order_by(Project.name).all()
        if timer.project_id:
            tasks = Task.query.filter_by(project_id=timer.project_id).order_by(Task.name).all()

    return render_template("timer/edit_timer.html", timer=timer, projects=projects, tasks=tasks)


@timer_bp.route("/timer/view/<int:timer_id>")
@login_required
def view_timer(timer_id):
    """View a time entry (read-only)"""
    timer = TimeEntry.query.get_or_404(timer_id)

    # Check if user can view this timer
    can_view_all = current_user.is_admin or current_user.has_permission("view_all_time_entries")
    if not can_view_all and timer.user_id != current_user.id:
        flash(_("You do not have permission to view this time entry"), "error")
        return redirect(url_for("main.dashboard"))

    # Get link templates for invoice_number (for clickable values)
    from app.models import LinkTemplate
    from sqlalchemy.exc import ProgrammingError
    link_templates_by_field = {}
    try:
        for template in LinkTemplate.get_active_templates():
            if template.field_key == 'invoice_number':
                link_templates_by_field['invoice_number'] = template
    except ProgrammingError as e:
        # Handle case where link_templates table doesn't exist (migration not run)
        if "does not exist" in str(e.orig) or "relation" in str(e.orig).lower():
            current_app.logger.warning(
                "link_templates table does not exist. Run migration: flask db upgrade"
            )
            link_templates_by_field = {}
        else:
            raise

    return render_template("timer/view_timer.html", timer=timer, link_templates_by_field=link_templates_by_field)


@timer_bp.route("/timer/delete/<int:timer_id>", methods=["POST"])
@login_required
def delete_timer(timer_id):
    """Delete a timer entry"""
    timer = TimeEntry.query.get_or_404(timer_id)

    # Check if user can delete this timer
    if timer.user_id != current_user.id and not current_user.is_admin:
        flash(_("You can only delete your own timers"), "error")
        return redirect(url_for("main.dashboard"))

    # Don't allow deletion of active timers
    if timer.is_active:
        flash(_("Cannot delete an active timer"), "error")
        return redirect(url_for("main.dashboard"))

    # Get the name for the success message (project or client)
    if timer.project:
        target_name = timer.project.name
    elif timer.client:
        target_name = timer.client.name
    else:
        target_name = _("Unknown")

    # Capture entry info for logging before deletion
    entry_id = timer.id
    duration_formatted = timer.duration_formatted
    project_name = timer.project.name if timer.project else None
    client_name = timer.client.name if timer.client else None
    entity_name = project_name or client_name or _("Unknown")
    timer_user_id = timer.user_id  # Capture user_id before deletion

    # Check if time_entry_approvals table exists before deletion
    # This prevents errors when the table doesn't exist but the relationship is defined
    inspector = inspect(db.engine)
    approvals_table_exists = "time_entry_approvals" in inspector.get_table_names()
    
    # If the approvals table exists, manually delete related approvals first
    # to avoid SQLAlchemy trying to query a non-existent table
    if approvals_table_exists:
        try:
            # Delete related approvals if they exist
            from app.models.time_entry_approval import TimeEntryApproval
            TimeEntryApproval.query.filter_by(time_entry_id=entry_id).delete()
        except Exception as e:
            current_app.logger.warning(
                f"Could not delete related approvals for time entry {entry_id}: {e}"
            )
            # Continue with deletion anyway

    # If the approvals table doesn't exist, we need to prevent SQLAlchemy from
    # trying to query the relationship. We'll expunge the object and use a direct delete.
    if not approvals_table_exists:
        try:
            # Expunge the object from the session to prevent relationship queries
            db.session.expunge(timer)
            # Use a direct SQL delete to avoid relationship queries
            db.session.execute(
                text("DELETE FROM time_entries WHERE id = :id"),
                {"id": entry_id}
            )
        except Exception as e:
            current_app.logger.error(f"Error deleting time entry {entry_id} with direct SQL: {e}")
            flash(_("Could not delete timer due to a database error. Please check server logs."), "error")
            return redirect(url_for("main.dashboard"))
    else:
        # Normal deletion path when the table exists
        db.session.delete(timer)
    
    if not safe_commit("delete_timer", {"timer_id": entry_id}):
        flash(_("Could not delete timer due to a database error. Please check server logs."), "error")
        return redirect(url_for("main.dashboard"))

    # Invalidate dashboard cache for the timer owner so changes appear immediately
    try:
        from app.utils.cache import get_cache
        cache = get_cache()
        cache_key = f"dashboard:{timer_user_id}"
        cache.delete(cache_key)
        current_app.logger.debug("Invalidated dashboard cache for user %s after timer deletion", timer_user_id)
    except Exception as e:
        current_app.logger.warning("Failed to invalidate dashboard cache: %s", e)

    # Log activity
    Activity.log(
        user_id=current_user.id,
        action="deleted",
        entity_type="time_entry",
        entity_id=entry_id,
        entity_name=entity_name,
        description=f'Deleted time entry for {entity_name} - {duration_formatted}',
        extra_data={"project_name": project_name, "client_name": client_name, "duration_formatted": duration_formatted},
        ip_address=request.remote_addr,
        user_agent=request.headers.get("User-Agent"),
    )

    # Invalidate dashboard cache so deleted entry disappears immediately
    try:
        from app.utils.cache import get_cache
        cache = get_cache()
        cache_key = f"dashboard:{current_user.id}"
        cache.delete(cache_key)
        current_app.logger.debug("Invalidated dashboard cache for user %s after deleting timer", current_user.id)
    except Exception as e:
        current_app.logger.warning("Failed to invalidate dashboard cache: %s", e)

    flash(f"Timer for {target_name} deleted successfully", "success")
    
    # Add cache-busting parameter to ensure fresh page load
    import time
    dashboard_url = url_for("main.dashboard")
    separator = "&" if "?" in dashboard_url else "?"
    redirect_url = f"{dashboard_url}{separator}_refresh={int(time.time())}"
    return redirect(redirect_url)


@timer_bp.route("/time-entries/bulk-delete", methods=["POST"])
@login_required
def bulk_delete_time_entries():
    """Bulk delete time entries"""
    from app.services import TimeTrackingService
    
    entry_ids = request.form.getlist("entry_ids[]")
    reason = request.form.get("reason", "").strip() or None  # Optional reason for bulk deletion
    
    if not entry_ids:
        flash(_("No time entries selected"), "warning")
        return redirect(url_for("timer.time_entries_overview"))
    
    # Load entries
    entry_ids_int = [int(eid) for eid in entry_ids if eid.isdigit()]
    if not entry_ids_int:
        flash(_("Invalid entry IDs"), "error")
        return redirect(url_for("timer.time_entries_overview"))
    
    entries = TimeEntry.query.filter(TimeEntry.id.in_(entry_ids_int)).all()
    
    if not entries:
        flash(_("No time entries found"), "error")
        return redirect(url_for("timer.time_entries_overview"))
    
    # Permission check
    can_view_all = current_user.is_admin or current_user.has_permission("view_all_time_entries")
    deleted_count = 0
    skipped_count = 0
    
    # Use service layer for proper audit logging
    service = TimeTrackingService()
    
    for entry in entries:
        # Check permissions
        if not can_view_all and entry.user_id != current_user.id:
            skipped_count += 1
            continue
        
        # Don't allow deletion of active timers
        if entry.is_active:
            skipped_count += 1
            continue
        
        # Delete using service layer to get enhanced audit logging
        result = service.delete_entry(
            user_id=current_user.id,
            entry_id=entry.id,
            is_admin=current_user.is_admin,
            reason=reason,  # Use same reason for all entries in bulk delete
        )
        
        if result.get("success"):
            deleted_count += 1
        else:
            skipped_count += 1
    
    if deleted_count > 0:
        flash(
            _("Successfully deleted %(count)d time entry/entries", count=deleted_count),
            "success"
        )
    
    if skipped_count > 0:
        flash(
            _("Skipped %(count)d time entry/entries (no permission or active timer)", count=skipped_count),
            "warning"
        )
    
    # Track event
    track_event(
        current_user.id,
        "time_entries.bulk_delete",
        {"count": deleted_count}
    )
    
    # Preserve filters in redirect
    redirect_url = url_for("timer.time_entries_overview")
    filters = {}
    for key in ["user_id", "project_id", "client_id", "start_date", "end_date", "paid", "billable", "search", "page"]:
        value = request.form.get(key) or request.args.get(key)
        if value:
            filters[key] = value
    
    if filters:
        redirect_url += "?" + "&".join(f"{k}={v}" for k, v in filters.items())
    
    return redirect(redirect_url)


@timer_bp.route("/timer/manual", methods=["GET", "POST"])
@login_required
def manual_entry():
    """Create a manual time entry"""
    from app.models import Client
    from app.services import TimeTrackingService

    # Get active projects and clients for dropdown (used for both GET and error re-renders on POST)
    active_projects = Project.query.filter_by(status="active").order_by(Project.name).all()
    active_clients = Client.query.filter_by(status="active").order_by(Client.name).all()

    # Get project_id, client_id, and task_id from query parameters for pre-filling
    project_id = request.args.get("project_id", type=int)
    client_id = request.args.get("client_id", type=int)
    task_id = request.args.get("task_id", type=int)
    template_id = request.args.get("template", type=int)

    # Load template data if template_id is provided
    template_data = None
    if template_id:
        from app.models import TimeEntryTemplate

        template = TimeEntryTemplate.query.filter_by(id=template_id, user_id=current_user.id).first()
        if template:
            template_data = {
                "project_id": template.project_id,
                "task_id": template.task_id,
                "notes": template.default_notes,
                "tags": template.tags,
                "billable": template.billable,
            }
            # Override with template values if not explicitly set
            if not project_id and template.project_id:
                project_id = template.project_id
            if not task_id and template.task_id:
                task_id = template.task_id

    if request.method == "POST":
        project_id = request.form.get("project_id", type=int) or None
        client_id = request.form.get("client_id", type=int) or None
        task_id = request.form.get("task_id", type=int) or None
        start_date = request.form.get("start_date")
        start_time = request.form.get("start_time")
        end_date = request.form.get("end_date")
        end_time = request.form.get("end_time")
        notes = request.form.get("notes", "").strip()
        tags = request.form.get("tags", "").strip()
        billable = request.form.get("billable") == "on"

        # Validate required fields
        if not all([start_date, start_time, end_date, end_time]):
            flash(_("Date and time fields are required"), "error")
            return render_template(
                "timer/manual_entry.html",
                projects=active_projects,
                clients=active_clients,
                selected_project_id=project_id,
                selected_client_id=client_id,
                selected_task_id=task_id,
                template_data=template_data,
                prefill_notes=notes,
                prefill_tags=tags,
                prefill_billable=billable,
                prefill_start_date=start_date,
                prefill_start_time=start_time,
                prefill_end_date=end_date,
                prefill_end_time=end_time,
            )

        # Validate that either project or client is selected
        if not project_id and not client_id:
            flash(_("Either a project or a client must be selected"), "error")
            return render_template(
                "timer/manual_entry.html",
                projects=active_projects,
                clients=active_clients,
                selected_project_id=project_id,
                selected_client_id=client_id,
                selected_task_id=task_id,
                template_data=template_data,
                prefill_notes=notes,
                prefill_tags=tags,
                prefill_billable=billable,
                prefill_start_date=start_date,
                prefill_start_time=start_time,
                prefill_end_date=end_date,
                prefill_end_time=end_time,
            )

        # Parse datetime: treat form input as user's local time, store in app timezone
        try:
            start_time_parsed = parse_user_local_datetime(start_date, start_time, current_user)
            end_time_parsed = parse_user_local_datetime(end_date, end_time, current_user)
        except ValueError:
            flash(_("Invalid date/time format"), "error")
            return render_template(
                "timer/manual_entry.html",
                projects=active_projects,
                clients=active_clients,
                selected_project_id=project_id,
                selected_client_id=client_id,
                selected_task_id=task_id,
                template_data=template_data,
                prefill_notes=notes,
                prefill_tags=tags,
                prefill_billable=billable,
                prefill_start_date=start_date,
                prefill_start_time=start_time,
                prefill_end_date=end_date,
                prefill_end_time=end_time,
            )

        # Validate time range
        if end_time_parsed <= start_time_parsed:
            flash(_("End time must be after start time"), "error")
            return render_template(
                "timer/manual_entry.html",
                projects=active_projects,
                clients=active_clients,
                selected_project_id=project_id,
                selected_client_id=client_id,
                selected_task_id=task_id,
                template_data=template_data,
                prefill_notes=notes,
                prefill_tags=tags,
                prefill_billable=billable,
                prefill_start_date=start_date,
                prefill_start_time=start_time,
                prefill_end_date=end_date,
                prefill_end_time=end_time,
            )

        # Use service to create entry (handles validation)
        time_tracking_service = TimeTrackingService()
        result = time_tracking_service.create_manual_entry(
            user_id=current_user.id,
            project_id=project_id,
            client_id=client_id,
            start_time=start_time_parsed,
            end_time=end_time_parsed,
            task_id=task_id,
            notes=notes if notes else None,
            tags=tags if tags else None,
            billable=billable,
        )

        if not result.get("success"):
            flash(_(result.get("message", "Could not create manual entry")), "error")
            return render_template(
                "timer/manual_entry.html",
                projects=active_projects,
                clients=active_clients,
                selected_project_id=project_id,
                selected_client_id=client_id,
                selected_task_id=task_id,
                template_data=template_data,
                prefill_notes=notes,
                prefill_tags=tags,
                prefill_billable=billable,
                prefill_start_date=start_date,
                prefill_start_time=start_time,
                prefill_end_date=end_date,
                prefill_end_time=end_time,
            )

        entry = result.get("entry")

        # Create success message
        if entry:
            if entry.project:
                target_name = entry.project.name
            elif entry.client:
                target_name = entry.client.name
            else:
                target_name = "Unknown"

            if task_id and entry.project:
                task = Task.query.get(task_id)
                task_name = task.name if task else "Unknown Task"
                flash(
                    _("Manual entry created for %(project)s - %(task)s", project=target_name, task=task_name), "success"
                )
            else:
                flash(_("Manual entry created for %(target)s", target=target_name), "success")

            # Log activity
            entity_name = entry.project.name if entry.project else (entry.client.name if entry.client else "Unknown")
            task_name = entry.task.name if entry.task else None
            duration_formatted = entry.duration_formatted if hasattr(entry, 'duration_formatted') else "0:00"
            
            Activity.log(
                user_id=current_user.id,
                action="created",
                entity_type="time_entry",
                entity_id=entry.id,
                entity_name=f"{entity_name}" + (f" - {task_name}" if task_name else ""),
                description=f'Created time entry for {entity_name}' + (f" - {task_name}" if task_name else "") + f' - {duration_formatted}',
                extra_data={
                    "project_name": entry.project.name if entry.project else None,
                    "client_name": entry.client.name if entry.client else None,
                    "task_name": task_name,
                    "duration_formatted": duration_formatted,
                    "duration_hours": entry.duration_hours if hasattr(entry, 'duration_hours') else None,
                },
                ip_address=request.remote_addr,
                user_agent=request.headers.get("User-Agent"),
            )

        # Invalidate dashboard cache so new entry appears immediately
        try:
            from app.utils.cache import get_cache
            cache = get_cache()
            cache_key = f"dashboard:{current_user.id}"
            cache.delete(cache_key)
            current_app.logger.debug("Invalidated dashboard cache for user %s after manual entry creation", current_user.id)
        except Exception as e:
            current_app.logger.warning("Failed to invalidate dashboard cache: %s", e)

        return redirect(url_for("main.dashboard"))

    return render_template(
        "timer/manual_entry.html",
        projects=active_projects,
        clients=active_clients,
        selected_project_id=project_id,
        selected_client_id=client_id,
        selected_task_id=task_id,
        template_data=template_data,
    )


@timer_bp.route("/timer/manual/<int:project_id>")
@login_required
def manual_entry_for_project(project_id):
    """Create a manual time entry for a specific project"""
    task_id = request.args.get("task_id", type=int)

    # Check if project exists and is active
    project = Project.query.filter_by(id=project_id, status="active").first()
    if not project:
        flash("Invalid project selected", "error")
        return redirect(url_for("main.dashboard"))

    # Get active projects for dropdown
    active_projects = Project.query.filter_by(status="active").order_by(Project.name).all()

    return render_template(
        "timer/manual_entry.html", projects=active_projects, selected_project_id=project_id, selected_task_id=task_id
    )


@timer_bp.route("/timer/bulk", methods=["GET", "POST"])
@login_required
def bulk_entry():
    """Create bulk time entries for multiple days"""
    # Get active projects for dropdown
    active_projects = Project.query.filter_by(status="active").order_by(Project.name).all()

    # Get project_id and task_id from query parameters for pre-filling
    project_id = request.args.get("project_id", type=int)
    task_id = request.args.get("task_id", type=int)

    if request.method == "POST":
        project_id = request.form.get("project_id", type=int)
        task_id = request.form.get("task_id", type=int)
        start_date = request.form.get("start_date")
        end_date = request.form.get("end_date")
        start_time = request.form.get("start_time")
        end_time = request.form.get("end_time")
        notes = request.form.get("notes", "").strip()
        tags = request.form.get("tags", "").strip()
        billable = request.form.get("billable") == "on"
        skip_weekends = request.form.get("skip_weekends") == "on"

        # Validate required fields
        if not all([project_id, start_date, end_date, start_time, end_time]):
            flash(_("All fields are required"), "error")
            return render_template(
                "timer/bulk_entry.html",
                projects=active_projects,
                selected_project_id=project_id,
                selected_task_id=task_id,
            )

        # Check if project exists
        project = Project.query.get(project_id)
        if not project:
            flash(_("Invalid project selected"), "error")
            return render_template(
                "timer/bulk_entry.html",
                projects=active_projects,
                selected_project_id=project_id,
                selected_task_id=task_id,
            )

        # Check if project is active (not archived or inactive)
        if project.status == "archived":
            flash(_("Cannot create time entries for an archived project. Please unarchive the project first."), "error")
            return render_template(
                "timer/bulk_entry.html",
                projects=active_projects,
                selected_project_id=project_id,
                selected_task_id=task_id,
            )
        elif project.status != "active":
            flash(_("Cannot create time entries for an inactive project"), "error")
            return render_template(
                "timer/bulk_entry.html",
                projects=active_projects,
                selected_project_id=project_id,
                selected_task_id=task_id,
            )

        # Validate task if provided
        if task_id:
            task = Task.query.filter_by(id=task_id, project_id=project_id).first()
            if not task:
                flash(_("Invalid task selected"), "error")
                return render_template(
                    "timer/bulk_entry.html",
                    projects=active_projects,
                    selected_project_id=project_id,
                    selected_task_id=task_id,
                )

        # Parse and validate dates
        try:
            from datetime import datetime, timedelta

            start_date_obj = datetime.strptime(start_date, "%Y-%m-%d").date()
            end_date_obj = datetime.strptime(end_date, "%Y-%m-%d").date()

            if end_date_obj < start_date_obj:
                flash(_("End date must be after or equal to start date"), "error")
                return render_template(
                    "timer/bulk_entry.html",
                    projects=active_projects,
                    selected_project_id=project_id,
                    selected_task_id=task_id,
                )

            # Check for reasonable date range (max 31 days)
            if (end_date_obj - start_date_obj).days > 31:
                flash(_("Date range cannot exceed 31 days"), "error")
                return render_template(
                    "timer/bulk_entry.html",
                    projects=active_projects,
                    selected_project_id=project_id,
                    selected_task_id=task_id,
                )
        except ValueError:
            flash(_("Invalid date format"), "error")
            return render_template(
                "timer/bulk_entry.html",
                projects=active_projects,
                selected_project_id=project_id,
                selected_task_id=task_id,
            )

        # Parse and validate times
        try:
            start_time_obj = datetime.strptime(start_time, "%H:%M").time()
            end_time_obj = datetime.strptime(end_time, "%H:%M").time()

            if end_time_obj <= start_time_obj:
                flash("End time must be after start time", "error")
                return render_template(
                    "timer/bulk_entry.html",
                    projects=active_projects,
                    selected_project_id=project_id,
                    selected_task_id=task_id,
                )
        except ValueError:
            flash(_("Invalid time format"), "error")
            return render_template(
                "timer/bulk_entry.html",
                projects=active_projects,
                selected_project_id=project_id,
                selected_task_id=task_id,
            )

        # Generate date range
        current_date = start_date_obj
        dates_to_create = []

        while current_date <= end_date_obj:
            # Skip weekends if requested
            if skip_weekends and current_date.weekday() >= 5:  # Saturday = 5, Sunday = 6
                current_date += timedelta(days=1)
                continue

            dates_to_create.append(current_date)
            current_date += timedelta(days=1)

        if not dates_to_create:
            flash(_("No valid dates found in the selected range"), "error")
            return render_template(
                "timer/bulk_entry.html",
                projects=active_projects,
                selected_project_id=project_id,
                selected_task_id=task_id,
            )

        # Check for existing entries on the same dates/times
        from app.models.time_entry import local_now

        existing_entries = []

        for date_obj in dates_to_create:
            start_datetime = datetime.combine(date_obj, start_time_obj)
            end_datetime = datetime.combine(date_obj, end_time_obj)

            # Check for overlapping entries
            overlapping = TimeEntry.query.filter(
                TimeEntry.user_id == current_user.id,
                TimeEntry.start_time <= end_datetime,
                TimeEntry.end_time >= start_datetime,
                TimeEntry.end_time.isnot(None),
            ).first()

            if overlapping:
                existing_entries.append(date_obj.strftime("%Y-%m-%d"))

        if existing_entries:
            flash(
                f'Time entries already exist for these dates: {", ".join(existing_entries[:5])}{"..." if len(existing_entries) > 5 else ""}',
                "error",
            )
            return render_template(
                "timer/bulk_entry.html",
                projects=active_projects,
                selected_project_id=project_id,
                selected_task_id=task_id,
            )

        # Create bulk entries
        created_entries = []

        try:
            for date_obj in dates_to_create:
                start_datetime = datetime.combine(date_obj, start_time_obj)
                end_datetime = datetime.combine(date_obj, end_time_obj)

                entry = TimeEntry(
                    user_id=current_user.id,
                    project_id=project_id,
                    task_id=task_id,
                    start_time=start_datetime,
                    end_time=end_datetime,
                    notes=notes,
                    tags=tags,
                    source="manual",
                    billable=billable,
                )

                db.session.add(entry)
                created_entries.append(entry)

            if not safe_commit(
                "bulk_entry", {"user_id": current_user.id, "project_id": project_id, "count": len(created_entries)}
            ):
                flash(_("Could not create bulk entries due to a database error. Please check server logs."), "error")
                return render_template(
                    "timer/bulk_entry.html",
                    projects=active_projects,
                    selected_project_id=project_id,
                    selected_task_id=task_id,
                )

            task_name = ""
            if task_id:
                task = Task.query.get(task_id)
                task_name = f" - {task.name}" if task else ""

            flash(f"Successfully created {len(created_entries)} time entries for {project.name}{task_name}", "success")
            return redirect(url_for("main.dashboard"))

        except Exception as e:
            db.session.rollback()
            current_app.logger.exception("Error creating bulk entries: %s", e)
            flash(_("An error occurred while creating bulk entries. Please try again."), "error")
            return render_template(
                "timer/bulk_entry.html",
                projects=active_projects,
                selected_project_id=project_id,
                selected_task_id=task_id,
            )

    return render_template(
        "timer/bulk_entry.html", projects=active_projects, selected_project_id=project_id, selected_task_id=task_id
    )


@timer_bp.route("/timer")
@login_required
def timer_page():
    """Dedicated timer page with visual progress ring and quick project selection"""
    active_timer = current_user.active_timer

    # Get active projects and clients for dropdown
    active_projects = Project.query.filter_by(status="active").order_by(Project.name).all()
    active_clients = Client.query.filter_by(status="active").order_by(Client.name).all()

    # Get recent projects (projects used in last 30 days)
    thirty_days_ago = datetime.utcnow() - timedelta(days=30)
    recent_project_ids = (
        db.session.query(TimeEntry.project_id)
        .filter(
            TimeEntry.user_id == current_user.id,
            TimeEntry.start_time >= thirty_days_ago,
            TimeEntry.end_time.isnot(None),
        )
        .group_by(TimeEntry.project_id)
        .order_by(db.func.max(TimeEntry.start_time).desc())
        .limit(5)
        .all()
    )

    recent_project_ids_list = [pid[0] for pid in recent_project_ids]
    if recent_project_ids_list:
        # Create a dict to preserve order from recent_project_ids_list
        order_map = {pid: idx for idx, pid in enumerate(recent_project_ids_list)}
        recent_projects = Project.query.filter(
            Project.id.in_(recent_project_ids_list), Project.status == "active"
        ).all()
        # Sort by order in recent_project_ids_list
        recent_projects.sort(key=lambda p: order_map.get(p.id, 999))
    else:
        recent_projects = []

    # Get tasks for active timer's project if timer is active
    tasks = []
    if active_timer and active_timer.project_id:
        tasks = (
            Task.query.filter(
                Task.project_id == active_timer.project_id, Task.status.in_(["todo", "in_progress", "review"])
            )
            .order_by(Task.name)
            .all()
        )

    # Get user's time entry templates (most recently used first)
    from app.models import TimeEntryTemplate
    from sqlalchemy import desc
    from sqlalchemy.orm import joinedload

    templates = (
        TimeEntryTemplate.query.options(joinedload(TimeEntryTemplate.project), joinedload(TimeEntryTemplate.task))
        .filter_by(user_id=current_user.id)
        .order_by(desc(TimeEntryTemplate.last_used_at))
        .limit(5)
        .all()
    )

    return render_template(
        "timer/timer_page.html",
        active_timer=active_timer,
        projects=active_projects,
        clients=active_clients,
        recent_projects=recent_projects,
        tasks=tasks,
        templates=templates,
    )


@timer_bp.route("/timer/calendar")
@login_required
def calendar_view():
    """Calendar UI combining day/week/month with list toggle."""
    # Provide projects for quick assignment during drag-create
    active_projects = Project.query.filter_by(status="active").order_by(Project.name).all()
    return render_template("timer/calendar.html", projects=active_projects)


@timer_bp.route("/timer/bulk/<int:project_id>")
@login_required
def bulk_entry_for_project(project_id):
    """Create bulk time entries for a specific project"""
    task_id = request.args.get("task_id", type=int)

    # Check if project exists and is active
    project = Project.query.filter_by(id=project_id, status="active").first()
    if not project:
        flash("Invalid project selected", "error")
        return redirect(url_for("main.dashboard"))

    # Get active projects for dropdown
    active_projects = Project.query.filter_by(status="active").order_by(Project.name).all()

    return render_template(
        "timer/bulk_entry.html", projects=active_projects, selected_project_id=project_id, selected_task_id=task_id
    )


@timer_bp.route("/timer/duplicate/<int:timer_id>")
@login_required
def duplicate_timer(timer_id):
    """Duplicate an existing time entry - opens manual entry form with pre-filled data"""
    timer = TimeEntry.query.get_or_404(timer_id)

    # Check if user can duplicate this timer
    if timer.user_id != current_user.id and not current_user.is_admin:
        flash(_("You can only duplicate your own timers"), "error")
        return redirect(url_for("main.dashboard"))

    # Get active projects for dropdown
    active_projects = Project.query.filter_by(status="active").order_by(Project.name).all()

    # Track duplication event
    log_event(
        "timer.duplicated",
        user_id=current_user.id,
        time_entry_id=timer.id,
        project_id=timer.project_id,
        task_id=timer.task_id,
    )
    track_event(
        current_user.id,
        "timer.duplicated",
        {
            "time_entry_id": timer.id,
            "project_id": timer.project_id,
            "task_id": timer.task_id,
            "has_notes": bool(timer.notes),
            "has_tags": bool(timer.tags),
        },
    )

    # Render the manual entry form with pre-filled data
    return render_template(
        "timer/manual_entry.html",
        projects=active_projects,
        selected_project_id=timer.project_id,
        selected_task_id=timer.task_id,
        prefill_notes=timer.notes,
        prefill_tags=timer.tags,
        prefill_billable=timer.billable,
        is_duplicate=True,
        original_entry=timer,
    )


@timer_bp.route("/timer/resume/<int:timer_id>")
@login_required
def resume_timer(timer_id):
    """Resume an existing time entry - starts a new active timer with same properties"""
    timer = TimeEntry.query.get_or_404(timer_id)

    # Check if user can resume this timer
    if timer.user_id != current_user.id and not current_user.is_admin:
        flash(_("You can only resume your own timers"), "error")
        return redirect(url_for("main.dashboard"))

    # Check if user already has an active timer
    active_timer = current_user.active_timer
    if active_timer:
        flash("You already have an active timer. Stop it before resuming another one.", "error")
        current_app.logger.info("Resume timer blocked: user already has an active timer")
        return redirect(url_for("main.dashboard"))

    project = None
    client = None
    project_id = None
    client_id = None

    # Check if timer is linked to a project or client
    if timer.project_id:
        # Timer is linked to a project
        project = Project.query.get(timer.project_id)
        if not project:
            flash(_("Project no longer exists"), "error")
            return redirect(url_for("main.dashboard"))

        if project.status == "archived":
            flash(_("Cannot start timer for an archived project. Please unarchive the project first."), "error")
            return redirect(url_for("main.dashboard"))
        elif project.status != "active":
            flash(_("Cannot start timer for an inactive project"), "error")
            return redirect(url_for("main.dashboard"))

        project_id = timer.project_id

        # Validate task if it exists
        if timer.task_id:
            task = Task.query.filter_by(id=timer.task_id, project_id=timer.project_id).first()
            if not task:
                # Task was deleted, continue without it
                task_id = None
            else:
                task_id = timer.task_id
        else:
            task_id = None
    elif timer.client_id:
        # Timer is linked to a client
        client = Client.query.filter_by(id=timer.client_id, status="active").first()
        if not client:
            flash(_("Client no longer exists or is inactive"), "error")
            return redirect(url_for("main.dashboard"))

        client_id = timer.client_id
        task_id = None  # Tasks are not allowed for client-only timers
    else:
        flash(_("Timer is not linked to a project or client"), "error")
        return redirect(url_for("main.dashboard"))

    # Create new timer with copied properties
    from app.models.time_entry import local_now

    new_timer = TimeEntry(
        user_id=current_user.id,
        project_id=project_id,
        client_id=client_id,
        task_id=task_id,
        start_time=local_now(),
        notes=timer.notes,
        tags=timer.tags,
        source="auto",
        billable=timer.billable,
    )

    db.session.add(new_timer)
    if not safe_commit(
        "resume_timer",
        {
            "user_id": current_user.id,
            "original_timer_id": timer_id,
            "project_id": project_id,
            "client_id": client_id,
        },
    ):
        flash(_("Could not resume timer due to a database error. Please check server logs."), "error")
        return redirect(url_for("main.dashboard"))

    current_app.logger.info(
        "Resumed timer id=%s from original timer=%s for user=%s project_id=%s client_id=%s",
        new_timer.id,
        timer_id,
        current_user.username,
        project_id,
        client_id,
    )

    # Track timer resumed event
    log_event(
        "timer.resumed",
        user_id=current_user.id,
        time_entry_id=new_timer.id,
        original_timer_id=timer_id,
        project_id=project_id,
        client_id=client_id,
        task_id=task_id,
        description=timer.notes,
    )
    track_event(
        current_user.id,
        "timer.resumed",
        {
            "time_entry_id": new_timer.id,
            "original_timer_id": timer_id,
            "project_id": project_id,
            "client_id": client_id,
            "task_id": task_id,
            "has_notes": bool(timer.notes),
            "has_tags": bool(timer.tags),
        },
    )

    # Log activity
    if project:
        project_name = project.name
        task = Task.query.get(task_id) if task_id else None
        task_name = task.name if task else None
        entity_name = f"{project_name}" + (f" - {task_name}" if task_name else "")
        description = f"Resumed timer for {project_name}" + (f" - {task_name}" if task_name else "")
    elif client:
        client_name = client.name
        entity_name = client_name
        description = f"Resumed timer for {client_name}"
        task_name = None
    else:
        entity_name = _("Unknown")
        description = _("Resumed timer")
        task_name = None

    Activity.log(
        user_id=current_user.id,
        action="started",
        entity_type="time_entry",
        entity_id=new_timer.id,
        entity_name=entity_name,
        description=description,
        extra_data={"project_id": project_id, "client_id": client_id, "task_id": task_id, "resumed_from": timer_id},
        ip_address=request.remote_addr,
        user_agent=request.headers.get("User-Agent"),
    )

    # Emit WebSocket event for real-time updates
    try:
        payload = {
            "user_id": current_user.id,
            "timer_id": new_timer.id,
            "start_time": new_timer.start_time.isoformat(),
        }
        if project:
            payload["project_name"] = project.name
        if client:
            payload["client_name"] = client.name
        if task_id:
            task = Task.query.get(task_id)
            if task:
                payload["task_id"] = task_id
                payload["task_name"] = task.name
        socketio.emit("timer_started", payload)
    except Exception as e:
        current_app.logger.warning("Socket emit failed for timer_resumed: %s", e)

    # Invalidate dashboard cache so timer appears immediately
    try:
        from app.utils.cache import get_cache
        cache = get_cache()
        cache_key = f"dashboard:{current_user.id}"
        cache.delete(cache_key)
        current_app.logger.debug("Invalidated dashboard cache for user %s", current_user.id)
    except Exception as e:
        current_app.logger.warning("Failed to invalidate dashboard cache: %s", e)

    # Create success message
    if project:
        if task_name:
            flash(f"Timer resumed for {project_name} - {task_name}", "success")
        else:
            flash(f"Timer resumed for {project_name}", "success")
    elif client:
        flash(f"Timer resumed for {client_name}", "success")
    else:
        flash(_("Timer resumed"), "success")

    return redirect(url_for("main.dashboard"))


@timer_bp.route("/time-entries")
@login_required
def time_entries_overview():
    """Overview page showing all time entries with filters and bulk actions"""
    from sqlalchemy import or_, func, desc
    from sqlalchemy.orm import joinedload
    from app.repositories import TimeEntryRepository, ProjectRepository, UserRepository
    
    # Get filter parameters
    user_id = request.args.get("user_id", type=int)
    project_id = request.args.get("project_id", type=int)
    client_id = request.args.get("client_id", type=int)
    start_date = request.args.get("start_date", "")
    end_date = request.args.get("end_date", "")
    paid_filter = request.args.get("paid", "")  # "true", "false", or ""
    billable_filter = request.args.get("billable", "")  # "true", "false", or ""
    search = request.args.get("search", "").strip()
    page = request.args.get("page", 1, type=int)
    per_page = request.args.get("per_page", 50, type=int)
    
    # Get custom field filters for clients
    # Format: custom_field_<field_key>=value
    client_custom_field = {}
    from app.models import CustomFieldDefinition
    active_definitions = CustomFieldDefinition.get_active_definitions()
    for definition in active_definitions:
        field_value = request.args.get(f"custom_field_{definition.field_key}", "").strip()
        if field_value:
            client_custom_field[definition.field_key] = field_value
    
    # Permission check: can user view all entries?
    can_view_all = current_user.is_admin or current_user.has_permission("view_all_time_entries")
    
    # Build query with eager loading to avoid N+1 queries
    query = TimeEntry.query.options(
        joinedload(TimeEntry.user),
        joinedload(TimeEntry.project),
        joinedload(TimeEntry.client),
        joinedload(TimeEntry.task)
    ).filter(TimeEntry.end_time.isnot(None))  # Only completed entries
    
    # Filter by user
    if user_id:
        if can_view_all:
            query = query.filter(TimeEntry.user_id == user_id)
        elif user_id == current_user.id:
            query = query.filter(TimeEntry.user_id == current_user.id)
        else:
            flash(_("You do not have permission to view other users' time entries"), "error")
            return redirect(url_for("timer.time_entries_overview"))
    elif not can_view_all:
        # Non-admin users can only see their own entries
        query = query.filter(TimeEntry.user_id == current_user.id)
    
    # Filter by project
    if project_id:
        query = query.filter(TimeEntry.project_id == project_id)
    
    # Filter by client
    if client_id:
        query = query.filter(TimeEntry.client_id == client_id)
    
    # Filter by client custom fields
    if client_custom_field:
        # Join Client table to filter by custom fields
        query = query.join(Client, TimeEntry.client_id == Client.id)
        
        # Determine database type for custom field filtering
        is_postgres = False
        try:
            from sqlalchemy import inspect
            engine = db.engine
            is_postgres = 'postgresql' in str(engine.url).lower()
        except Exception as e:
            # Log but continue - database type detection failure is not critical
            current_app.logger.debug(f"Failed to detect database type: {e}")
        
        # Build custom field filter conditions
        custom_field_conditions = []
        for field_key, field_value in client_custom_field.items():
            if not field_key or not field_value:
                continue
            
            if is_postgres:
                # PostgreSQL: Use JSONB operators
                try:
                    from sqlalchemy import cast, String
                    # Match exact value in custom_fields JSONB
                    custom_field_conditions.append(
                        db.cast(Client.custom_fields[field_key].astext, String) == str(field_value)
                    )
                except Exception as e:
                    # Fallback to Python filtering if JSONB fails
                    current_app.logger.debug(f"JSONB filtering failed for field {field_key}, will use Python filtering: {e}")
        
        if custom_field_conditions:
            query = query.filter(db.or_(*custom_field_conditions))
    
    # Filter by date range
    if start_date:
        try:
            start_dt = datetime.strptime(start_date, "%Y-%m-%d")
            query = query.filter(TimeEntry.start_time >= start_dt)
        except ValueError:
            pass
    
    if end_date:
        try:
            end_dt = datetime.strptime(end_date, "%Y-%m-%d")
            # Include the entire end date
            end_dt = end_dt.replace(hour=23, minute=59, second=59)
            query = query.filter(TimeEntry.start_time <= end_dt)
        except ValueError:
            pass
    
    # Filter by paid status
    if paid_filter == "true":
        query = query.filter(TimeEntry.paid == True)
    elif paid_filter == "false":
        query = query.filter(TimeEntry.paid == False)
    
    # Filter by billable status
    if billable_filter == "true":
        query = query.filter(TimeEntry.billable == True)
    elif billable_filter == "false":
        query = query.filter(TimeEntry.billable == False)
    
    # Search in notes and tags
    if search:
        search_pattern = f"%{search}%"
        query = query.filter(
            or_(
                TimeEntry.notes.ilike(search_pattern),
                TimeEntry.tags.ilike(search_pattern)
            )
        )
    
    # Order by start time (most recent first)
    query = query.order_by(desc(TimeEntry.start_time))
    
    # Pagination
    pagination = query.paginate(page=page, per_page=per_page, error_out=False)
    time_entries = pagination.items
    
    # For SQLite or if JSONB filtering didn't work, filter by custom fields in Python
    if client_custom_field:
        try:
            from sqlalchemy import inspect
            engine = db.engine
            is_postgres = 'postgresql' in str(engine.url).lower()
            
            if not is_postgres:
                # SQLite: Filter in Python
                filtered_entries = []
                for entry in time_entries:
                    if not entry.client:
                        continue
                    
                    # Check if client matches all custom field filters
                    matches = True
                    for field_key, field_value in client_custom_field.items():
                        if not field_key or not field_value:
                            continue
                        
                        client_value = entry.client.custom_fields.get(field_key) if entry.client.custom_fields else None
                        if str(client_value) != str(field_value):
                            matches = False
                            break
                    
                    if matches:
                        filtered_entries.append(entry)
                
                # Update pagination with filtered results
                time_entries = filtered_entries
                # Recalculate pagination manually
                total = len(filtered_entries)
                start = (page - 1) * per_page
                end = start + per_page
                time_entries = filtered_entries[start:end]
                
                # Create a pagination-like object
                from flask_sqlalchemy import Pagination
                pagination = Pagination(
                    query=None,
                    page=page,
                    per_page=per_page,
                    total=total,
                    items=time_entries
                )
        except Exception:
            # If filtering fails, use original results
            pass
    
    # Get filter options
    projects = []
    clients = []
    users = []
    
    if can_view_all:
        project_repo = ProjectRepository()
        projects = project_repo.get_active_projects()
        clients = Client.query.filter_by(status="active").order_by(Client.name).all()
        user_repo = UserRepository()
        users = user_repo.get_active_users()
    else:
        # For non-admin users, only show their projects
        # Get projects from user's time entries
        user_project_ids = (
            db.session.query(TimeEntry.project_id)
            .filter(TimeEntry.user_id == current_user.id, TimeEntry.project_id.isnot(None))
            .distinct()
            .all()
        )
        user_project_ids = [pid[0] for pid in user_project_ids]
        if user_project_ids:
            projects = Project.query.filter(Project.id.in_(user_project_ids), Project.status == "active").order_by(Project.name).all()
            # Get clients from user's projects
            client_ids = set(p.client_id for p in projects if p.client_id)
            if client_ids:
                clients = Client.query.filter(Client.id.in_(client_ids), Client.status == "active").order_by(Client.name).all()
        users = [current_user]
    
    # Calculate totals
    total_hours = sum(entry.duration_hours for entry in time_entries)
    total_billable_hours = sum(entry.duration_hours for entry in time_entries if entry.billable)
    total_paid_hours = sum(entry.duration_hours for entry in time_entries if entry.paid)
    
    # Track page view
    track_event(
        current_user.id,
        "time_entries_overview.viewed",
        {
            "has_filters": bool(user_id or project_id or client_id or start_date or end_date or paid_filter or billable_filter or search),
            "page": page,
            "per_page": per_page
        }
    )
    
    filters_dict = {
        "user_id": user_id,
        "project_id": project_id,
        "client_id": client_id,
        "start_date": start_date,
        "end_date": end_date,
        "paid": paid_filter,
        "billable": billable_filter,
        "search": search,
        "client_custom_field": client_custom_field,
        "page": page,
        "per_page": per_page
    }
    
    # Build URL-safe filters for url_for (exclude dict and page; expand client_custom_field).
    # Passing client_custom_field (a dict) or page into url_for breaks URL building and can
    # cause 500s. Pagination links pass page explicitly, so we omit it here.
    url_filters = {
        k: v
        for k, v in filters_dict.items()
        if k not in ("client_custom_field", "page") and v is not None and v != ""
    }
    for k, v in (filters_dict.get("client_custom_field") or {}).items():
        if v:
            url_filters[f"custom_field_{k}"] = v
    
    # Get custom field definitions for filter UI
    from app.models import CustomFieldDefinition
    custom_field_definitions = CustomFieldDefinition.get_active_definitions()
    
    # Get link templates for invoice_number (for clickable values)
    from app.models import LinkTemplate
    from sqlalchemy.exc import ProgrammingError
    link_templates_by_field = {}
    try:
        for template in LinkTemplate.get_active_templates():
            if template.field_key == 'invoice_number':
                link_templates_by_field['invoice_number'] = template
    except ProgrammingError as e:
        # Handle case where link_templates table doesn't exist (migration not run)
        if "does not exist" in str(e.orig) or "relation" in str(e.orig).lower():
            current_app.logger.warning(
                "link_templates table does not exist. Run migration: flask db upgrade"
            )
            link_templates_by_field = {}
        else:
            raise
    
    # Check if this is an AJAX request
    if request.headers.get("X-Requested-With") == "XMLHttpRequest":
        # Return only the time entries list HTML for AJAX requests
        from flask import make_response
        response = make_response(render_template(
            "timer/_time_entries_list.html",
            time_entries=time_entries,
            pagination=pagination,
            can_view_all=can_view_all,
            filters=filters_dict,
            url_filters=url_filters,
            custom_field_definitions=custom_field_definitions,
            link_templates_by_field=link_templates_by_field,
        ))
        response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
        return response
    
    return render_template(
        "timer/time_entries_overview.html",
        time_entries=time_entries,
        pagination=pagination,
        projects=projects,
        clients=clients,
        users=users,
        can_view_all=can_view_all,
        filters=filters_dict,
        url_filters=url_filters,
        custom_field_definitions=custom_field_definitions,
        link_templates_by_field=link_templates_by_field,
        totals={
            "total_hours": round(total_hours, 2),
            "total_billable_hours": round(total_billable_hours, 2),
            "total_paid_hours": round(total_paid_hours, 2),
            "total_entries": len(time_entries)
        }
    )


@timer_bp.route("/time-entries/bulk-paid", methods=["POST"])
@login_required
def bulk_mark_paid():
    """Bulk mark time entries as paid or unpaid"""
    from app.utils.db import safe_commit
    
    entry_ids = request.form.getlist("entry_ids[]")
    paid_status = request.form.get("paid", "").strip().lower()
    invoice_reference = request.form.get("invoice_reference", "").strip()
    
    if not entry_ids:
        flash(_("No time entries selected"), "warning")
        return redirect(url_for("timer.time_entries_overview"))
    
    if paid_status not in ("true", "false"):
        flash(_("Invalid paid status"), "error")
        return redirect(url_for("timer.time_entries_overview"))
    
    is_paid = paid_status == "true"
    
    # Load entries
    entry_ids_int = [int(eid) for eid in entry_ids if eid.isdigit()]
    if not entry_ids_int:
        flash(_("Invalid entry IDs"), "error")
        return redirect(url_for("timer.time_entries_overview"))
    
    entries = TimeEntry.query.filter(TimeEntry.id.in_(entry_ids_int)).all()
    
    if not entries:
        flash(_("No time entries found"), "error")
        return redirect(url_for("timer.time_entries_overview"))
    
    # Permission check
    can_view_all = current_user.is_admin or current_user.has_permission("view_all_time_entries")
    updated_count = 0
    skipped_count = 0
    
    for entry in entries:
        # Check permissions
        if not can_view_all and entry.user_id != current_user.id:
            skipped_count += 1
            continue
        
        # Skip active timers
        if entry.is_active:
            skipped_count += 1
            continue
        
        # Update paid status with invoice reference if provided
        if is_paid and invoice_reference:
            entry.set_paid(is_paid, invoice_number=invoice_reference)
        else:
            entry.set_paid(is_paid)
        updated_count += 1
        
        # Log activity
        Activity.log(
            user_id=current_user.id,
            action="updated",
            entity_type="time_entry",
            entity_id=entry.id,
            entity_name=f"Time entry #{entry.id}",
            description=f"Marked time entry as {'paid' if is_paid else 'unpaid'}",
            extra_data={"paid": is_paid, "project_id": entry.project_id, "client_id": entry.client_id},
            ip_address=request.remote_addr,
            user_agent=request.headers.get("User-Agent"),
        )
    
    if updated_count > 0:
        if not safe_commit("bulk_mark_paid", {"count": updated_count, "paid": is_paid}):
            flash(_("Could not update time entries due to a database error. Please check server logs."), "error")
            return redirect(url_for("timer.time_entries_overview"))
        
        flash(
            _("Successfully marked %(count)d time entry/entries as %(status)s", count=updated_count, status=_("paid") if is_paid else _("unpaid")),
            "success"
        )
    
    if skipped_count > 0:
        flash(
            _("Skipped %(count)d time entry/entries (no permission or active timer)", count=skipped_count),
            "warning"
        )
    
    # Track event
    track_event(
        current_user.id,
        "time_entries.bulk_mark_paid",
        {"count": updated_count, "paid": is_paid}
    )
    
    # Preserve filters in redirect
    redirect_url = url_for("timer.time_entries_overview")
    filters = {}
    for key in ["user_id", "project_id", "client_id", "start_date", "end_date", "paid", "billable", "search", "page"]:
        value = request.form.get(key) or request.args.get(key)
        if value:
            filters[key] = value
    
    if filters:
        redirect_url += "?" + "&".join(f"{k}={v}" for k, v in filters.items())
    
    return redirect(redirect_url)
