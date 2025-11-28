from flask import Blueprint, jsonify, request, current_app, send_from_directory, make_response
from flask_login import login_required, current_user
from app import db, socketio
from app.models import (
    User,
    Project,
    TimeEntry,
    Settings,
    Task,
    FocusSession,
    RecurringBlock,
    RateOverride,
    SavedFilter,
    Client,
)
from datetime import datetime, timedelta, time
from app.utils.db import safe_commit
from app.utils.timezone import parse_local_datetime, utc_to_local, convert_app_datetime_to_user
from app.models.time_entry import local_now
from sqlalchemy import or_
import json
import os
import uuid
from werkzeug.utils import secure_filename

api_bp = Blueprint("api", __name__)


@api_bp.route("/api/health")
def health_check():
    """Health check endpoint for monitoring and error handling"""
    return jsonify({"status": "ok", "timestamp": datetime.utcnow().isoformat()})


@api_bp.route("/api/timer/status")
@login_required
def timer_status():
    """Get current timer status"""
    active_timer = current_user.active_timer

    if not active_timer:
        return jsonify({"active": False, "timer": None})

    return jsonify(
        {
            "active": True,
            "timer": {
                "id": active_timer.id,
                "project_name": active_timer.project.name,
                "project_id": active_timer.project_id,
                "task_id": active_timer.task_id,
                "start_time": active_timer.start_time.isoformat(),
                "current_duration": active_timer.current_duration_seconds,
                "duration_formatted": active_timer.duration_formatted,
            },
        }
    )


@api_bp.route("/api/search")
@login_required
def search():
    """Global search endpoint for projects, tasks, clients, and time entries"""
    query = request.args.get("q", "").strip()
    limit = request.args.get("limit", 10, type=int)

    if not query or len(query) < 2:
        return jsonify({"results": []})

    results = []
    search_pattern = f"%{query}%"

    # Search projects
    try:
        projects = (
            Project.query.filter(
                Project.status == "active",
                or_(Project.name.ilike(search_pattern), Project.description.ilike(search_pattern)),
            )
            .limit(limit)
            .all()
        )

        for project in projects:
            results.append(
                {
                    "type": "project",
                    "category": "project",
                    "id": project.id,
                    "title": project.name,
                    "description": project.description or "",
                    "url": f"/projects/{project.id}",
                    "badge": "Project",
                }
            )
    except Exception as e:
        current_app.logger.error(f"Error searching projects: {e}")

    # Search tasks
    try:
        tasks = (
            Task.query.join(Project)
            .filter(
                Project.status == "active", or_(Task.name.ilike(search_pattern), Task.description.ilike(search_pattern))
            )
            .limit(limit)
            .all()
        )

        for task in tasks:
            results.append(
                {
                    "type": "task",
                    "category": "task",
                    "id": task.id,
                    "title": task.name,
                    "description": f"{task.project.name if task.project else 'No Project'}",
                    "url": f"/tasks/{task.id}",
                    "badge": task.status.replace("_", " ").title() if task.status else "Task",
                }
            )
    except Exception as e:
        current_app.logger.error(f"Error searching tasks: {e}")

    # Search clients
    try:
        clients = (
            Client.query.filter(
                or_(
                    Client.name.ilike(search_pattern),
                    Client.email.ilike(search_pattern),
                    Client.company.ilike(search_pattern),
                )
            )
            .limit(limit)
            .all()
        )

        for client in clients:
            results.append(
                {
                    "type": "client",
                    "category": "client",
                    "id": client.id,
                    "title": client.name,
                    "description": client.company or client.email or "",
                    "url": f"/clients/{client.id}",
                    "badge": "Client",
                }
            )
    except Exception as e:
        current_app.logger.error(f"Error searching clients: {e}")

    # Search time entries (notes and tags)
    try:
        entries = (
            TimeEntry.query.filter(
                TimeEntry.user_id == current_user.id,
                TimeEntry.end_time.isnot(None),
                or_(TimeEntry.notes.ilike(search_pattern), TimeEntry.tags.ilike(search_pattern)),
            )
            .order_by(TimeEntry.start_time.desc())
            .limit(limit)
            .all()
        )

        for entry in entries:
            title_parts = []
            if entry.project:
                title_parts.append(entry.project.name)
            if entry.task:
                title_parts.append(f"• {entry.task.name}")
            title = " ".join(title_parts) if title_parts else "Time Entry"

            description = entry.notes[:100] if entry.notes else ""
            if entry.tags:
                description += f" [{entry.tags}]"

            results.append(
                {
                    "type": "entry",
                    "category": "entry",
                    "id": entry.id,
                    "title": title,
                    "description": description,
                    "url": f"/timer/edit/{entry.id}",
                    "badge": entry.duration_formatted,
                }
            )
    except Exception as e:
        current_app.logger.error(f"Error searching time entries: {e}")

    # Limit total results
    results = results[:limit]

    return jsonify({"results": results})


@api_bp.route("/api/deadlines/upcoming")
@login_required
def upcoming_deadlines():
    """Return upcoming task deadlines for the current user."""
    now_utc = datetime.utcnow()
    today = now_utc.date()
    horizon = (now_utc + timedelta(days=2)).date()

    query = Task.query.join(Project).filter(
        Project.status == "active",
        Task.due_date.isnot(None),
        Task.status.in_(("todo", "in_progress", "review")),
        Task.due_date >= today,
        Task.due_date <= horizon,
    )

    if not current_user.is_admin:
        query = query.filter(or_(Task.assigned_to == current_user.id, Task.created_by == current_user.id))

    tasks = query.order_by(Task.due_date.asc(), Task.priority.desc(), Task.name.asc()).limit(20).all()

    end_of_day = time(hour=23, minute=59, second=59)
    deadlines = []
    for task in tasks:
        due_dt = datetime.combine(task.due_date, end_of_day)
        deadlines.append(
            {
                "task_id": task.id,
                "task_name": task.name,
                "project_id": task.project_id,
                "project_name": task.project.name if task.project else None,
                "due_date": due_dt.isoformat(),
                "priority": task.priority,
                "status": task.status,
            }
        )

    return jsonify(deadlines)


@api_bp.route("/api/tasks")
@login_required
def list_tasks_for_project():
    """List tasks for a given project (optionally filter by status)."""
    project_id = request.args.get("project_id", type=int)
    status = request.args.get("status")
    if not project_id:
        return jsonify({"error": "project_id is required"}), 400

    # Validate project exists and is active
    project = Project.query.filter_by(id=project_id, status="active").first()
    if not project:
        return jsonify({"error": "Invalid project"}), 400

    query = Task.query.filter_by(project_id=project_id)
    if status:
        query = query.filter_by(status=status)
    else:
        # Default to tasks not done/cancelled
        query = query.filter(Task.status.in_(["todo", "in_progress", "review"]))

    tasks = query.order_by(Task.priority.desc(), Task.name.asc()).all()
    return jsonify({"tasks": [{"id": t.id, "name": t.name, "status": t.status, "priority": t.priority} for t in tasks]})


@api_bp.route("/api/timer/start", methods=["POST"])
@login_required
def api_start_timer():
    """Start timer via API"""
    data = request.get_json()
    project_id = data.get("project_id")
    task_id = data.get("task_id")

    if not project_id:
        return jsonify({"error": "Project ID is required"}), 400

    # Check if project exists and is active
    project = Project.query.filter_by(id=project_id, status="active").first()
    if not project:
        return jsonify({"error": "Invalid project"}), 400

    # Validate task if provided
    task = None
    if task_id:
        task = Task.query.filter_by(id=task_id, project_id=project_id).first()
        if not task:
            return jsonify({"error": "Invalid task for selected project"}), 400

    # Check if user already has an active timer
    active_timer = current_user.active_timer
    if active_timer:
        return jsonify({"error": "User already has an active timer"}), 400

    # Create new timer
    from app.models.time_entry import local_now

    new_timer = TimeEntry(
        user_id=current_user.id,
        project_id=project_id,
        task_id=task.id if task else None,
        start_time=local_now(),
        source="auto",
    )

    db.session.add(new_timer)
    db.session.commit()

    # Emit WebSocket event
    socketio.emit(
        "timer_started",
        {
            "user_id": current_user.id,
            "timer_id": new_timer.id,
            "project_name": project.name,
            "task_id": task.id if task else None,
            "start_time": new_timer.start_time.isoformat(),
        },
    )

    return jsonify(
        {"success": True, "timer_id": new_timer.id, "project_name": project.name, "task_id": task.id if task else None}
    )


@api_bp.route("/api/timer/stop", methods=["POST"])
@login_required
def api_stop_timer():
    """Stop timer via API"""
    active_timer = current_user.active_timer

    if not active_timer:
        return jsonify({"error": "No active timer to stop"}), 400

    # Stop the timer
    active_timer.stop_timer()

    # Emit WebSocket event
    socketio.emit(
        "timer_stopped",
        {"user_id": current_user.id, "timer_id": active_timer.id, "duration": active_timer.duration_formatted},
    )

    return jsonify(
        {"success": True, "duration": active_timer.duration_formatted, "duration_hours": active_timer.duration_hours}
    )


# --- Idle control: stop at specific time ---
@api_bp.route("/api/timer/stop_at", methods=["POST"])
@login_required
def api_stop_timer_at():
    """Stop the active timer at a specific timestamp (idle adjustment)."""
    active_timer = current_user.active_timer
    if not active_timer:
        return jsonify({"error": "No active timer to stop"}), 400

    data = request.get_json() or {}
    stop_time_str = data.get("stop_time")  # ISO string
    if not stop_time_str:
        return jsonify({"error": "stop_time is required"}), 400

    try:
        # Accept ISO; handle trailing Z
        ts = stop_time_str.strip()
        if ts.endswith("Z"):
            ts = ts[:-1] + "+00:00"
        parsed = datetime.fromisoformat(ts)
        # Convert to local naive for storage consistency
        if parsed.tzinfo is not None:
            parsed_local_aware = utc_to_local(parsed)
            stop_time_local = parsed_local_aware.replace(tzinfo=None)
        else:
            stop_time_local = parsed
    except Exception:
        return jsonify({"error": "Invalid stop_time format"}), 400

    if stop_time_local <= active_timer.start_time:
        return jsonify({"error": "stop_time must be after start time"}), 400

    # Do not allow stopping in the future
    now_local = local_now()
    if stop_time_local > now_local:
        stop_time_local = now_local

    try:
        active_timer.stop_timer(end_time=stop_time_local)
    except Exception as e:
        current_app.logger.warning("Failed to stop timer at specific time: %s", e)
        return jsonify({"error": "Failed to stop timer"}), 500

    socketio.emit(
        "timer_stopped",
        {"user_id": current_user.id, "timer_id": active_timer.id, "duration": active_timer.duration_formatted},
    )

    return jsonify({"success": True, "duration": active_timer.duration_formatted})


# --- Resume last timer/project ---
@api_bp.route("/api/timer/resume", methods=["POST"])
@login_required
def api_resume_timer():
    """Resume timer for last used project/task or provided project/task."""
    if current_user.active_timer:
        return jsonify({"error": "Timer already running"}), 400

    data = request.get_json() or {}
    project_id = data.get("project_id")
    task_id = data.get("task_id")

    if not project_id:
        # Find most recent finished entry
        last = (
            TimeEntry.query.filter(TimeEntry.user_id == current_user.id)
            .order_by(TimeEntry.end_time.desc().nullslast(), TimeEntry.start_time.desc())
            .first()
        )
        if not last:
            return jsonify({"error": "No previous entry to resume"}), 404
        project_id = last.project_id
        task_id = last.task_id

    # Validate project is active
    project = Project.query.filter_by(id=project_id, status="active").first()
    if not project:
        return jsonify({"error": "Invalid or inactive project"}), 400

    if task_id:
        task = Task.query.filter_by(id=task_id, project_id=project_id).first()
        if not task:
            return jsonify({"error": "Invalid task for selected project"}), 400

    # Create new timer
    new_timer = TimeEntry(
        user_id=current_user.id, project_id=project_id, task_id=task_id, start_time=local_now(), source="auto"
    )
    db.session.add(new_timer)
    db.session.commit()

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

    return jsonify({"success": True, "timer_id": new_timer.id})


@api_bp.route("/api/entries")
@login_required
def get_entries():
    """Get time entries with pagination"""
    page = request.args.get("page", 1, type=int)
    per_page = request.args.get("per_page", 20, type=int)
    user_id = request.args.get("user_id", type=int)
    project_id = request.args.get("project_id", type=int)
    tag = (request.args.get("tag") or "").strip()
    saved_filter_id = request.args.get("saved_filter_id", type=int)

    query = TimeEntry.query.filter(TimeEntry.end_time.isnot(None))

    # Apply saved filter if provided
    if saved_filter_id:
        filt = SavedFilter.query.get(saved_filter_id)
        if filt and (filt.user_id == current_user.id or (filt.is_shared and current_user.is_admin)):
            payload = filt.payload or {}
            if "project_id" in payload:
                query = query.filter(TimeEntry.project_id == int(payload["project_id"]))
            if "user_id" in payload and current_user.is_admin:
                query = query.filter(TimeEntry.user_id == int(payload["user_id"]))
            if "billable" in payload:
                query = query.filter(TimeEntry.billable == bool(payload["billable"]))
            if "tag" in payload and payload["tag"]:
                query = query.filter(TimeEntry.tags.ilike(f"%{payload['tag']}%"))

    # Filter by user (if admin or own entries)
    if user_id and current_user.is_admin:
        query = query.filter(TimeEntry.user_id == user_id)
    elif not current_user.is_admin:
        query = query.filter(TimeEntry.user_id == current_user.id)

    # Filter by project
    if project_id:
        query = query.filter(TimeEntry.project_id == project_id)

    # Filter by tag (simple contains search on comma-separated tags)
    if tag:
        like = f"%{tag}%"
        query = query.filter(TimeEntry.tags.ilike(like))

    entries = query.order_by(TimeEntry.start_time.desc()).paginate(page=page, per_page=per_page, error_out=False)

    # Ensure frontend receives project_name like other endpoints
    entries_payload = []
    for entry in entries.items:
        e = entry.to_dict()
        e["project_name"] = e.get("project") or (entry.project.name if entry.project else None)
        entries_payload.append(e)

    return jsonify(
        {
            "entries": entries_payload,
            "total": entries.total,
            "pages": entries.pages,
            "current_page": entries.page,
            "has_next": entries.has_next,
            "has_prev": entries.has_prev,
        }
    )


@api_bp.route("/api/projects/<int:project_id>/burndown")
@login_required
def project_burndown(project_id):
    """Return burn-down data for a given project.

    Produces daily cumulative actual hours vs estimated hours line.
    """
    project = Project.query.get_or_404(project_id)
    # Permission: any authenticated can view if they have entries in project or are admin
    if not current_user.is_admin:
        has_entries = db.session.query(TimeEntry.id).filter_by(user_id=current_user.id, project_id=project_id).first()
        if not has_entries:
            return jsonify({"error": "Access denied"}), 403

    # Date range: last 30 days up to today
    end_date = datetime.utcnow().date()
    start_date = end_date - timedelta(days=29)

    # Fetch entries in range
    entries = (
        TimeEntry.query.filter(TimeEntry.project_id == project_id)
        .filter(TimeEntry.end_time.isnot(None))
        .filter(TimeEntry.start_time >= datetime.combine(start_date, datetime.min.time()))
        .filter(TimeEntry.start_time <= datetime.combine(end_date, datetime.max.time()))
        .order_by(TimeEntry.start_time.asc())
        .all()
    )

    # Build daily buckets
    labels = []
    actual_cumulative = []
    day_map = {}
    cur = start_date
    while cur <= end_date:
        labels.append(cur.isoformat())
        day_map[cur.isoformat()] = 0.0
        cur = cur + timedelta(days=1)

    for e in entries:
        d = e.start_time.date().isoformat()
        day_map[d] = day_map.get(d, 0.0) + (e.duration_seconds or 0) / 3600.0

    running = 0.0
    for d in labels:
        running += day_map.get(d, 0.0)
        actual_cumulative.append(round(running, 2))

    # Estimated line: flat line of project.estimated_hours
    estimated = float(project.estimated_hours or 0)
    estimate_series = [estimated for _ in labels]

    return jsonify(
        {
            "labels": labels,
            "actual_cumulative": actual_cumulative,
            "estimated": estimate_series,
            "estimated_hours": estimated,
        }
    )


@api_bp.route("/api/focus-sessions/start", methods=["POST"])
@login_required
def start_focus_session():
    data = request.get_json() or {}
    project_id = data.get("project_id")
    task_id = data.get("task_id")
    pomodoro_length = int(data.get("pomodoro_length") or 25)
    short_break_length = int(data.get("short_break_length") or 5)
    long_break_length = int(data.get("long_break_length") or 15)
    long_break_interval = int(data.get("long_break_interval") or 4)
    link_active_timer = bool(data.get("link_active_timer", True))

    time_entry_id = None
    if link_active_timer and current_user.active_timer:
        time_entry_id = current_user.active_timer.id

    fs = FocusSession(
        user_id=current_user.id,
        project_id=project_id,
        task_id=task_id,
        time_entry_id=time_entry_id,
        pomodoro_length=pomodoro_length,
        short_break_length=short_break_length,
        long_break_length=long_break_length,
        long_break_interval=long_break_interval,
    )
    db.session.add(fs)
    if not safe_commit("start_focus_session", {"user_id": current_user.id}):
        return jsonify({"error": "Database error while starting focus session"}), 500

    return jsonify({"success": True, "session": fs.to_dict()})


@api_bp.route("/api/focus-sessions/finish", methods=["POST"])
@login_required
def finish_focus_session():
    data = request.get_json() or {}
    session_id = data.get("session_id")
    if not session_id:
        return jsonify({"error": "session_id is required"}), 400
    fs = FocusSession.query.get_or_404(session_id)
    if fs.user_id != current_user.id and not current_user.is_admin:
        return jsonify({"error": "Access denied"}), 403

    fs.ended_at = datetime.utcnow()
    fs.cycles_completed = int(data.get("cycles_completed") or 0)
    fs.interruptions = int(data.get("interruptions") or 0)
    notes = (data.get("notes") or "").strip()
    fs.notes = notes or fs.notes
    if not safe_commit("finish_focus_session", {"session_id": fs.id}):
        return jsonify({"error": "Database error while finishing focus session"}), 500
    return jsonify({"success": True, "session": fs.to_dict()})


@api_bp.route("/api/focus-sessions/summary")
@login_required
def focus_sessions_summary():
    """Return simple summary counts for recent focus sessions for the current user."""
    days = int(request.args.get("days", 7))
    since = datetime.utcnow() - timedelta(days=days)
    q = FocusSession.query.filter(FocusSession.user_id == current_user.id, FocusSession.started_at >= since)
    sessions = q.order_by(FocusSession.started_at.desc()).all()
    total = len(sessions)
    cycles = sum(s.cycles_completed or 0 for s in sessions)
    interrupts = sum(s.interruptions or 0 for s in sessions)
    return jsonify({"total_sessions": total, "cycles_completed": cycles, "interruptions": interrupts})


@api_bp.route("/api/recurring-blocks", methods=["GET", "POST"])
@login_required
def recurring_blocks_list_create():
    if request.method == "GET":
        blocks = (
            RecurringBlock.query.filter_by(user_id=current_user.id).order_by(RecurringBlock.created_at.desc()).all()
        )
        return jsonify({"blocks": [b.to_dict() for b in blocks]})

    data = request.get_json() or {}
    name = (data.get("name") or "").strip()
    project_id = data.get("project_id")
    task_id = data.get("task_id")
    recurrence = (data.get("recurrence") or "weekly").strip()
    weekdays = (data.get("weekdays") or "").strip()
    start_time_local = (data.get("start_time_local") or "").strip()
    end_time_local = (data.get("end_time_local") or "").strip()
    starts_on = data.get("starts_on")
    ends_on = data.get("ends_on")
    is_active = bool(data.get("is_active", True))
    notes = (data.get("notes") or "").strip() or None
    tags = (data.get("tags") or "").strip() or None
    billable = bool(data.get("billable", True))

    if not all([name, project_id, start_time_local, end_time_local]):
        return jsonify({"error": "name, project_id, start_time_local, end_time_local are required"}), 400

    block = RecurringBlock(
        user_id=current_user.id,
        project_id=project_id,
        task_id=task_id,
        name=name,
        recurrence=recurrence,
        weekdays=weekdays,
        start_time_local=start_time_local,
        end_time_local=end_time_local,
        is_active=is_active,
        notes=notes,
        tags=tags,
        billable=billable,
    )

    # Optional dates
    try:
        if starts_on:
            block.starts_on = datetime.fromisoformat(starts_on).date()
        if ends_on:
            block.ends_on = datetime.fromisoformat(ends_on).date()
    except Exception:
        return jsonify({"error": "Invalid starts_on/ends_on date format"}), 400

    db.session.add(block)
    if not safe_commit("create_recurring_block", {"user_id": current_user.id}):
        return jsonify({"error": "Database error while creating recurring block"}), 500
    return jsonify({"success": True, "block": block.to_dict()})


@api_bp.route("/api/recurring-blocks/<int:block_id>", methods=["PUT", "DELETE"])
@login_required
def recurring_block_update_delete(block_id):
    block = RecurringBlock.query.get_or_404(block_id)
    if block.user_id != current_user.id and not current_user.is_admin:
        return jsonify({"error": "Access denied"}), 403

    if request.method == "DELETE":
        db.session.delete(block)
        if not safe_commit("delete_recurring_block", {"id": block.id}):
            return jsonify({"error": "Database error while deleting recurring block"}), 500
        return jsonify({"success": True})

    data = request.get_json() or {}
    for field in ["name", "recurrence", "weekdays", "start_time_local", "end_time_local", "notes", "tags"]:
        if field in data:
            setattr(block, field, (data.get(field) or "").strip())
    for field in ["project_id", "task_id"]:
        if field in data:
            setattr(block, field, data.get(field))
    if "is_active" in data:
        block.is_active = bool(data.get("is_active"))
    if "billable" in data:
        block.billable = bool(data.get("billable"))
    try:
        if "starts_on" in data:
            block.starts_on = datetime.fromisoformat(data.get("starts_on")).date() if data.get("starts_on") else None
        if "ends_on" in data:
            block.ends_on = datetime.fromisoformat(data.get("ends_on")).date() if data.get("ends_on") else None
    except Exception:
        return jsonify({"error": "Invalid starts_on/ends_on date format"}), 400

    if not safe_commit("update_recurring_block", {"id": block.id}):
        return jsonify({"error": "Database error while updating recurring block"}), 500
    return jsonify({"success": True, "block": block.to_dict()})


@api_bp.route("/api/saved-filters", methods=["GET", "POST"])
@login_required
def saved_filters_list_create():
    if request.method == "GET":
        scope = (request.args.get("scope") or "global").strip()
        items = SavedFilter.query.filter_by(user_id=current_user.id, scope=scope).order_by(SavedFilter.name.asc()).all()
        return jsonify({"filters": [f.to_dict() for f in items]})

    data = request.get_json() or {}
    name = (data.get("name") or "").strip()
    scope = (data.get("scope") or "global").strip()
    payload = data.get("payload") or {}
    is_shared = bool(data.get("is_shared", False))
    if not name:
        return jsonify({"error": "name is required"}), 400
    filt = SavedFilter(user_id=current_user.id, name=name, scope=scope, payload=payload, is_shared=is_shared)
    db.session.add(filt)
    if not safe_commit("create_saved_filter", {"name": name, "scope": scope}):
        return jsonify({"error": "Database error while creating saved filter"}), 500
    return jsonify({"success": True, "filter": filt.to_dict()})


@api_bp.route("/api/saved-filters/<int:filter_id>", methods=["DELETE"])
@login_required
def delete_saved_filter(filter_id):
    filt = SavedFilter.query.get_or_404(filter_id)
    if filt.user_id != current_user.id and not current_user.is_admin:
        return jsonify({"error": "Access denied"}), 403
    db.session.delete(filt)
    if not safe_commit("delete_saved_filter", {"id": filt.id}):
        return jsonify({"error": "Database error while deleting saved filter"}), 500
    return jsonify({"success": True})


@api_bp.route("/api/entries", methods=["POST"])
@login_required
def create_entry():
    """Create a finished time entry (used by calendar drag-create)."""
    data = request.get_json() or {}
    project_id = data.get("project_id")
    task_id = data.get("task_id")
    start_time_str = data.get("start_time")
    end_time_str = data.get("end_time")
    notes = (data.get("notes") or "").strip() or None
    tags = (data.get("tags") or "").strip() or None
    billable = bool(data.get("billable", True))

    if not (project_id and start_time_str and end_time_str):
        return jsonify({"error": "project_id, start_time, end_time are required"}), 400

    # Validate project
    project = Project.query.filter_by(id=project_id, status="active").first()
    if not project:
        return jsonify({"error": "Invalid project"}), 400

    if task_id:
        task = Task.query.filter_by(id=task_id, project_id=project_id).first()
        if not task:
            return jsonify({"error": "Invalid task for selected project"}), 400

    def parse_iso_local(s: str):
        try:
            ts = s.strip()
            if ts.endswith("Z"):
                ts = ts[:-1] + "+00:00"
            dt = datetime.fromisoformat(ts)
            if dt.tzinfo is not None:
                return utc_to_local(dt).replace(tzinfo=None)
            return dt
        except Exception:
            return None

    start_dt = parse_iso_local(start_time_str)
    end_dt = parse_iso_local(end_time_str)
    if not (start_dt and end_dt) or end_dt <= start_dt:
        return jsonify({"error": "Invalid start/end time"}), 400

    entry = TimeEntry(
        user_id=current_user.id if not current_user.is_admin else (data.get("user_id") or current_user.id),
        project_id=project_id,
        task_id=task_id,
        start_time=start_dt,
        end_time=end_dt,
        notes=notes,
        tags=tags,
        source="manual",
        billable=billable,
    )
    db.session.add(entry)
    if not safe_commit("api_create_entry", {"project_id": project_id}):
        return jsonify({"error": "Database error while creating entry"}), 500

    payload = entry.to_dict()
    payload["project_name"] = entry.project.name if entry.project else None
    return jsonify({"success": True, "entry": payload})


@api_bp.route("/api/entries/bulk", methods=["POST"])
@login_required
def bulk_entries_action():
    """Perform bulk actions on time entries: delete, set billable, add/remove tag."""
    data = request.get_json() or {}
    entry_ids = data.get("entry_ids") or []
    action = (data.get("action") or "").strip()
    value = data.get("value")

    if not entry_ids or not isinstance(entry_ids, list):
        return jsonify({"error": "entry_ids must be a non-empty list"}), 400
    if action not in {"delete", "set_billable", "add_tag", "remove_tag"}:
        return jsonify({"error": "Unsupported action"}), 400

    # Load entries with permission checks
    q = TimeEntry.query.filter(TimeEntry.id.in_(entry_ids))
    entries = q.all()
    if not entries:
        return jsonify({"error": "No entries found"}), 404

    # Permission: non-admins can only modify own entries
    if not current_user.is_admin:
        for e in entries:
            if e.user_id != current_user.id:
                return jsonify({"error": "Access denied for one or more entries"}), 403

    affected = 0
    if action == "delete":
        for e in entries:
            if e.is_active:
                continue
            db.session.delete(e)
            affected += 1
    elif action == "set_billable":
        flag = bool(value)
        for e in entries:
            if e.is_active:
                continue
            e.billable = flag
            e.updated_at = local_now()
            affected += 1
    elif action in {"add_tag", "remove_tag"}:
        tag = (value or "").strip()
        if not tag:
            return jsonify({"error": "Tag value is required"}), 400
        for e in entries:
            if e.is_active:
                continue
            tags = set(e.tag_list)
            if action == "add_tag":
                tags.add(tag)
            else:
                tags.discard(tag)
            e.tags = ", ".join(sorted(tags)) if tags else None
            e.updated_at = local_now()
            affected += 1

    if affected > 0:
        if not safe_commit("api_bulk_entries", {"action": action, "count": affected}):
            return jsonify({"error": "Database error during bulk operation"}), 500
    else:
        db.session.rollback()

    return jsonify({"success": True, "affected": affected})


@api_bp.route("/api/calendar/events")
@login_required
def calendar_events():
    """Return calendar events, tasks, and time entries for the current user in a date range."""
    from app.models import CalendarEvent as CalendarEventModel

    start = request.args.get("start")
    end = request.args.get("end")
    include_tasks = request.args.get("include_tasks", "true").lower() == "true"
    include_time_entries = request.args.get("include_time_entries", "true").lower() == "true"
    project_id = request.args.get("project_id", type=int)
    task_id = request.args.get("task_id", type=int)
    tags = request.args.get("tags", "").strip()

    # Get user_id from query param (admins only) or default to current user
    if current_user.is_admin and request.args.get("user_id"):
        user_id = request.args.get("user_id", type=int)
    else:
        user_id = current_user.id

    if not (start and end):
        return jsonify({"error": "start and end are required"}), 400

    def parse_iso(s: str):
        try:
            ts = s.strip()
            if ts.endswith("Z"):
                ts = ts[:-1] + "+00:00"
            dt = datetime.fromisoformat(ts)
            if dt.tzinfo is not None:
                return utc_to_local(dt).replace(tzinfo=None)
            return dt
        except Exception:
            return None

    start_dt = parse_iso(start)
    end_dt = parse_iso(end)
    if not (start_dt and end_dt):
        return jsonify({"error": "Invalid date range"}), 400

    # Get all calendar items using the new method
    result = CalendarEventModel.get_events_in_range(
        user_id=user_id,
        start_date=start_dt,
        end_date=end_dt,
        include_tasks=include_tasks,
        include_time_entries=include_time_entries,
    )

    # Color scheme for projects (deterministic based on project ID)
    def get_project_color(project_id):
        colors = [
            "#3b82f6",
            "#ef4444",
            "#10b981",
            "#f59e0b",
            "#8b5cf6",
            "#ec4899",
            "#14b8a6",
            "#f97316",
            "#6366f1",
            "#84cc16",
        ]
        return colors[project_id % len(colors)] if project_id else "#6b7280"

    # Apply filters and format time entries
    time_entries = []
    for e in result.get("time_entries", []):
        # Apply filters
        if project_id and e.get("projectId") != project_id:
            continue
        if task_id and e.get("taskId") != task_id:
            continue
        if tags and tags.lower() not in (e.get("notes") or "").lower():
            continue

        time_entries.append(
            {
                "id": e["id"],
                "title": e["title"],
                "start": e["start"],
                "end": e["end"],
                "editable": True,
                "allDay": False,
                "backgroundColor": get_project_color(e.get("projectId")),
                "borderColor": get_project_color(e.get("projectId")),
                "extendedProps": {**e, "item_type": "time_entry"},
            }
        )

    # Format tasks
    tasks = []
    for t in result.get("tasks", []):
        tasks.append(
            {
                "id": t["id"],
                "title": t["title"],
                "start": t["dueDate"],
                "end": t["dueDate"],
                "allDay": True,
                "editable": False,
                "backgroundColor": "#f59e0b",
                "borderColor": "#f59e0b",
                "extendedProps": {**t, "item_type": "task"},
            }
        )

    # Format calendar events
    events = []
    for ev in result.get("events", []):
        events.append(
            {
                "id": ev["id"],
                "title": ev["title"],
                "start": ev["start"],
                "end": ev["end"],
                "allDay": ev.get("allDay", False),
                "editable": True,
                "backgroundColor": ev.get("color", "#3b82f6"),
                "borderColor": ev.get("color", "#3b82f6"),
                "extendedProps": {**ev, "item_type": "event"},
            }
        )

    # Combine all items
    all_items = events + tasks + time_entries

    return jsonify(
        {
            "events": all_items,
            "summary": {"calendar_events": len(events), "tasks": len(tasks), "time_entries": len(time_entries)},
        }
    )


@api_bp.route("/api/calendar/export")
@login_required
def calendar_export():
    """Export calendar events to iCal or CSV format."""
    start = request.args.get("start")
    end = request.args.get("end")
    format_type = request.args.get("format", "ical").lower()
    project_id = request.args.get("project_id", type=int)

    if not (start and end):
        return jsonify({"error": "start and end are required"}), 400

    def parse_iso(s: str):
        try:
            ts = s.strip()
            if ts.endswith("Z"):
                ts = ts[:-1] + "+00:00"
            dt = datetime.fromisoformat(ts)
            if dt.tzinfo is not None:
                return utc_to_local(dt).replace(tzinfo=None)
            return dt
        except Exception:
            return None

    start_dt = parse_iso(start)
    end_dt = parse_iso(end)
    if not (start_dt and end_dt):
        return jsonify({"error": "Invalid date range"}), 400

    # Build query
    q = TimeEntry.query.filter(TimeEntry.user_id == current_user.id)
    q = q.filter(TimeEntry.start_time < end_dt, (TimeEntry.end_time.is_(None)) | (TimeEntry.end_time > start_dt))
    if project_id:
        q = q.filter(TimeEntry.project_id == project_id)

    items = q.order_by(TimeEntry.start_time.asc()).all()

    if format_type == "csv":
        import csv
        from io import StringIO

        output = StringIO()
        writer = csv.writer(output)
        writer.writerow(
            ["Date", "Start Time", "End Time", "Project", "Task", "Duration (hours)", "Notes", "Tags", "Billable"]
        )

        for entry in items:
            start_local = convert_app_datetime_to_user(entry.start_time, user=current_user)
            end_local = convert_app_datetime_to_user(entry.end_time, user=current_user) if entry.end_time else None
            writer.writerow(
                [
                    start_local.strftime("%Y-%m-%d") if start_local else "",
                    start_local.strftime("%H:%M") if start_local else "",
                    end_local.strftime("%H:%M") if end_local else "Active",
                    entry.project.name if entry.project else "",
                    entry.task.name if entry.task else "",
                    f"{entry.duration_hours:.2f}" if entry.duration_hours else "",
                    entry.notes or "",
                    entry.tags or "",
                    "Yes" if entry.billable else "No",
                ]
            )

        response = make_response(output.getvalue())
        response.headers["Content-Type"] = "text/csv"
        response.headers["Content-Disposition"] = (
            f'attachment; filename=calendar_export_{start_dt.strftime("%Y%m%d")}_to_{end_dt.strftime("%Y%m%d")}.csv'
        )
        return response

    elif format_type == "ical":
        # Generate iCal format
        ical_lines = [
            "BEGIN:VCALENDAR",
            "VERSION:2.0",
            "PRODID:-//TimeTracker//Calendar Export//EN",
            "CALSCALE:GREGORIAN",
            "METHOD:PUBLISH",
        ]

        for entry in items:
            if not entry.end_time:
                continue

            start_local = convert_app_datetime_to_user(entry.start_time, user=current_user)
            end_local = convert_app_datetime_to_user(entry.end_time, user=current_user)

            title = entry.project.name if entry.project else "Time Entry"
            if entry.task:
                title += f" - {entry.task.name}"

            description = []
            if entry.notes:
                description.append(f"Notes: {entry.notes}")
            if entry.tags:
                description.append(f"Tags: {entry.tags}")
            description.append(f'Billable: {"Yes" if entry.billable else "No"}')

            ical_lines.extend(
                [
                    "BEGIN:VEVENT",
                    f"UID:{entry.id}@timetracker",
                    f'DTSTAMP:{datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")}',
                    f'DTSTART:{start_local.strftime("%Y%m%dT%H%M%S") if start_local else entry.start_time.strftime("%Y%m%dT%H%M%S")}',
                    f'DTEND:{end_local.strftime("%Y%m%dT%H%M%S") if end_local else entry.end_time.strftime("%Y%m%dT%H%M%S")}',
                    f"SUMMARY:{title}",
                    f'DESCRIPTION:{" | ".join(description)}',
                    "END:VEVENT",
                ]
            )

        ical_lines.append("END:VCALENDAR")

        response = make_response("\r\n".join(ical_lines))
        response.headers["Content-Type"] = "text/calendar"
        response.headers["Content-Disposition"] = (
            f'attachment; filename=calendar_export_{start_dt.strftime("%Y%m%d")}_to_{end_dt.strftime("%Y%m%d")}.ics'
        )
        return response

    return jsonify({"error": 'Invalid format. Use "ical" or "csv"'}), 400


@api_bp.route("/api/projects")
@login_required
def get_projects():
    """Get active projects"""
    projects = Project.query.filter_by(status="active").order_by(Project.name).all()
    return jsonify({"projects": [project.to_dict() for project in projects]})


@api_bp.route("/api/projects/<int:project_id>/tasks")
@login_required
def get_project_tasks(project_id):
    """Get tasks for a specific project (excluding done and cancelled tasks)"""
    # Check if project exists and is active
    project = Project.query.filter_by(id=project_id, status="active").first()
    if not project:
        return jsonify({"error": "Project not found or inactive"}), 404

    # Get active tasks for the project (exclude done and cancelled)
    tasks = (
        Task.query.filter_by(project_id=project_id)
        .filter(Task.status.in_(["todo", "in_progress", "review"]))
        .order_by(Task.name)
        .all()
    )

    return jsonify(
        {
            "success": True,
            "tasks": [
                {
                    "id": task.id,
                    "name": task.name,
                    "description": task.description,
                    "status": task.status,
                    "priority": task.priority,
                }
                for task in tasks
            ],
        }
    )


# Fetch a single time entry (details for edit modal)
@api_bp.route("/api/entry/<int:entry_id>", methods=["GET"])
@login_required
def get_entry(entry_id):
    entry = TimeEntry.query.get_or_404(entry_id)
    if entry.user_id != current_user.id and not current_user.is_admin:
        return jsonify({"error": "Access denied"}), 403
    payload = entry.to_dict()
    payload["project_name"] = entry.project.name if entry.project else None
    return jsonify(payload)


@api_bp.route("/api/users")
@login_required
def get_users():
    """Get active users (admin only)"""
    if not current_user.is_admin:
        return jsonify({"error": "Access denied"}), 403

    users = User.query.filter_by(is_active=True).order_by(User.username).all()
    return jsonify({"users": [user.to_dict() for user in users]})


@api_bp.route("/api/stats")
@login_required
def get_stats():
    """Get user statistics"""
    # Get date range
    end_date = datetime.utcnow()
    start_date = end_date - timedelta(days=30)

    # Calculate statistics
    today_hours = TimeEntry.get_total_hours_for_period(
        start_date=end_date.date(), user_id=current_user.id if not current_user.is_admin else None
    )

    week_hours = TimeEntry.get_total_hours_for_period(
        start_date=end_date.date() - timedelta(days=7), user_id=current_user.id if not current_user.is_admin else None
    )

    month_hours = TimeEntry.get_total_hours_for_period(
        start_date=start_date.date(), user_id=current_user.id if not current_user.is_admin else None
    )

    return jsonify(
        {
            "today_hours": today_hours,
            "week_hours": week_hours,
            "month_hours": month_hours,
            "total_hours": current_user.total_hours,
        }
    )


@api_bp.route("/api/entry/<int:entry_id>", methods=["PUT"])
@login_required
def update_entry(entry_id):
    """Update a time entry"""
    entry = TimeEntry.query.get_or_404(entry_id)

    # Check permissions
    if entry.user_id != current_user.id and not current_user.is_admin:
        return jsonify({"error": "Access denied"}), 403

    data = request.get_json() or {}

    # Optional: project change (admin only)
    new_project_id = data.get("project_id")
    if new_project_id is not None and current_user.is_admin:
        if new_project_id != entry.project_id:
            project = Project.query.filter_by(id=new_project_id, status="active").first()
            if not project:
                return jsonify({"error": "Invalid project"}), 400
            entry.project_id = new_project_id

    # Optional: start/end time updates (admin only for safety)
    # Accept HTML datetime-local format: YYYY-MM-DDTHH:MM
    def parse_dt_local(dt_str):
        if not dt_str:
            return None
        try:
            if "T" in dt_str:
                date_part, time_part = dt_str.split("T", 1)
            else:
                date_part, time_part = dt_str.split(" ", 1)
            # Parse as UTC-aware then convert to local naive to match model storage
            parsed_utc = parse_local_datetime(date_part, time_part)
            parsed_local_aware = utc_to_local(parsed_utc)
            return parsed_local_aware.replace(tzinfo=None)
        except Exception:
            return None

    if current_user.is_admin:
        start_time_str = data.get("start_time")
        end_time_str = data.get("end_time")

        if start_time_str:
            parsed_start = parse_dt_local(start_time_str)
            if not parsed_start:
                return jsonify({"error": "Invalid start time format"}), 400
            entry.start_time = parsed_start

        if end_time_str is not None:
            if end_time_str == "" or end_time_str is False:
                entry.end_time = None
                entry.duration_seconds = None
            else:
                parsed_end = parse_dt_local(end_time_str)
                if not parsed_end:
                    return jsonify({"error": "Invalid end time format"}), 400
                if parsed_end <= (entry.start_time or parsed_end):
                    return jsonify({"error": "End time must be after start time"}), 400
                entry.end_time = parsed_end
                # Recalculate duration
                entry.calculate_duration()

    # Prevent multiple active timers for the same user when editing
    if entry.end_time is None:
        conflict = (
            TimeEntry.query.filter(TimeEntry.user_id == entry.user_id)
            .filter(TimeEntry.end_time.is_(None))
            .filter(TimeEntry.id != entry.id)
            .first()
        )
        if conflict:
            return jsonify({"error": "User already has an active timer"}), 400

    # Notes, tags, billable (both admin and owner can change)
    if "notes" in data:
        entry.notes = data["notes"].strip() if data["notes"] else None

    if "tags" in data:
        entry.tags = data["tags"].strip() if data["tags"] else None

    if "billable" in data:
        entry.billable = bool(data["billable"])

    # Prefer local time for updated_at per project preference
    entry.updated_at = local_now()

    if not safe_commit("api_update_entry", {"entry_id": entry_id}):
        return jsonify({"error": "Database error while updating entry"}), 500

    payload = entry.to_dict()
    payload["project_name"] = entry.project.name if entry.project else None
    return jsonify({"success": True, "entry": payload})


@api_bp.route("/api/entry/<int:entry_id>", methods=["DELETE"])
@login_required
def delete_entry(entry_id):
    """Delete a time entry"""
    entry = TimeEntry.query.get_or_404(entry_id)

    # Check permissions
    if entry.user_id != current_user.id and not current_user.is_admin:
        return jsonify({"error": "Access denied"}), 403

    # Don't allow deletion of active timers
    if entry.is_active:
        return jsonify({"error": "Cannot delete active timer"}), 400

    db.session.delete(entry)
    db.session.commit()

    return jsonify({"success": True})


# ================================
# Editor image uploads
# ================================

ALLOWED_IMAGE_EXTENSIONS = {"png", "jpg", "jpeg", "gif", "webp"}


def allowed_image_file(filename: str) -> bool:
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_IMAGE_EXTENSIONS


def get_editor_upload_folder() -> str:
    upload_folder = os.path.join(current_app.root_path, "static", "uploads", "editor")
    os.makedirs(upload_folder, exist_ok=True)
    return upload_folder


@api_bp.route("/api/uploads/images", methods=["POST"])
@login_required
def upload_editor_image():
    """Handle image uploads from the markdown editor."""
    if "image" not in request.files:
        return jsonify({"error": "No image provided"}), 400
    file = request.files["image"]
    if not file or file.filename == "":
        return jsonify({"error": "No image provided"}), 400
    if not allowed_image_file(file.filename):
        return jsonify({"error": "Invalid file type"}), 400

    filename = secure_filename(file.filename)
    ext = filename.rsplit(".", 1)[1].lower()
    unique_name = f"editor_{uuid.uuid4().hex[:12]}.{ext}"
    folder = get_editor_upload_folder()
    path = os.path.join(folder, unique_name)
    file.save(path)

    url = f"/uploads/editor/{unique_name}"
    return jsonify({"success": True, "url": url})


@api_bp.route("/uploads/editor/<path:filename>")
def serve_editor_image(filename):
    """Serve uploaded editor images from static/uploads/editor."""
    folder = get_editor_upload_folder()
    return send_from_directory(folder, filename)


# ================================
# Activity Feed API
# ================================


@api_bp.route("/api/activities")
@login_required
def get_activities():
    """Get recent activities with filtering"""
    from app.models import Activity
    from sqlalchemy import and_

    # Get query parameters
    limit = request.args.get("limit", 50, type=int)
    page = request.args.get("page", 1, type=int)
    user_id = request.args.get("user_id", type=int)
    entity_type = request.args.get("entity_type", "").strip()
    action = request.args.get("action", "").strip()
    start_date = request.args.get("start_date", "").strip()
    end_date = request.args.get("end_date", "").strip()

    # Build query
    query = Activity.query

    # Filter by user (admins can see all, users see only their own)
    if not current_user.is_admin:
        query = query.filter_by(user_id=current_user.id)
    elif user_id:
        query = query.filter_by(user_id=user_id)

    # Filter by entity type
    if entity_type:
        query = query.filter_by(entity_type=entity_type)

    # Filter by action
    if action:
        query = query.filter_by(action=action)

    # Filter by date range
    if start_date:
        try:
            start_dt = datetime.fromisoformat(start_date)
            query = query.filter(Activity.created_at >= start_dt)
        except ValueError:
            pass

    if end_date:
        try:
            end_dt = datetime.fromisoformat(end_date)
            query = query.filter(Activity.created_at <= end_dt)
        except ValueError:
            pass

    # Get total count
    total = query.count()

    # Apply ordering and pagination
    activities = query.order_by(Activity.created_at.desc()).paginate(page=page, per_page=limit, error_out=False)

    return jsonify(
        {
            "activities": [a.to_dict() for a in activities.items],
            "total": total,
            "pages": activities.pages,
            "current_page": activities.page,
            "has_next": activities.has_next,
            "has_prev": activities.has_prev,
        }
    )


@api_bp.route("/api/dashboard/stats")
@login_required
def dashboard_stats():
    """Get dashboard statistics for real-time updates"""
    from app.models import TimeEntry
    from datetime import datetime, timedelta

    today = datetime.utcnow().date()
    week_start = today - timedelta(days=today.weekday())
    month_start = today.replace(day=1)

    today_hours = TimeEntry.get_total_hours_for_period(start_date=today, user_id=current_user.id)

    week_hours = TimeEntry.get_total_hours_for_period(start_date=week_start, user_id=current_user.id)

    month_hours = TimeEntry.get_total_hours_for_period(start_date=month_start, user_id=current_user.id)

    return jsonify(
        {
            "success": True,
            "today_hours": float(today_hours),
            "week_hours": float(week_hours),
            "month_hours": float(month_hours),
        }
    )


@api_bp.route("/api/dashboard/sparklines")
@login_required
def dashboard_sparklines():
    """Get sparkline data for dashboard widgets"""
    from app.models import TimeEntry
    from datetime import datetime, timedelta
    from sqlalchemy import func

    # Get last 7 days of data
    seven_days_ago = datetime.utcnow() - timedelta(days=7)

    # Get daily totals for last 7 days
    daily_totals = (
        db.session.query(
            func.date(TimeEntry.start_time).label("date"), func.sum(TimeEntry.duration_seconds).label("total_seconds")
        )
        .filter(
            TimeEntry.user_id == current_user.id, TimeEntry.end_time.isnot(None), TimeEntry.start_time >= seven_days_ago
        )
        .group_by(func.date(TimeEntry.start_time))
        .order_by(func.date(TimeEntry.start_time))
        .all()
    )

    # Convert to hours and create array
    hours_data = []
    for i in range(7):
        date = datetime.utcnow().date() - timedelta(days=6 - i)
        matching = next((d for d in daily_totals if d.date == date), None)
        if matching:
            # total_seconds is already in seconds (Integer), convert to hours
            hours = (matching.total_seconds or 0) / 3600.0
        else:
            hours = 0
        hours_data.append(round(hours, 1))

    return jsonify(
        {
            "success": True,
            "today": hours_data,
            "week": hours_data,  # Same data for now
            "month": hours_data,  # Same data for now
        }
    )


@api_bp.route("/api/summary/today")
@login_required
def summary_today():
    """Get today's time tracking summary for daily summary notification"""
    from app.models import TimeEntry, Project
    from datetime import datetime, timedelta
    from sqlalchemy import func, distinct

    today = datetime.utcnow().date()

    # Get today's time entries for current user
    entries = TimeEntry.query.filter(
        TimeEntry.user_id == current_user.id, func.date(TimeEntry.start_time) == today, TimeEntry.end_time.isnot(None)
    ).all()

    # Calculate total hours
    total_hours = sum((entry.duration_hours or 0) for entry in entries)

    # Count unique projects
    project_ids = set(entry.project_id for entry in entries if entry.project_id)
    project_count = len(project_ids)

    return jsonify({"hours": round(total_hours, 2), "projects": project_count})


@api_bp.route("/api/activity/timeline")
@login_required
def activity_timeline():
    """Get activity timeline for dashboard"""
    from app.models import Activity
    from datetime import datetime, timedelta

    # Get activities from last 7 days
    seven_days_ago = datetime.utcnow() - timedelta(days=7)
    query = Activity.query.filter(Activity.created_at >= seven_days_ago)

    # Filter by user if not admin
    if not current_user.is_admin:
        query = query.filter_by(user_id=current_user.id)

    activities = query.order_by(Activity.created_at.desc()).limit(20).all()

    activities_data = []
    for activity in activities:
        activities_data.append(
            {
                "id": activity.id,
                "type": activity.entity_type or "default",
                "action": activity.action or "unknown",
                "description": activity.description or "Activity",
                "created_at": activity.created_at.isoformat() if activity.created_at else None,
            }
        )

    return jsonify({"success": True, "activities": activities_data})


@api_bp.route("/api/activities/stats")
@login_required
def get_activity_stats():
    """Get activity statistics"""
    from app.models import Activity
    from sqlalchemy import func

    # Get date range (default to last 7 days)
    days = request.args.get("days", 7, type=int)
    since = datetime.utcnow() - timedelta(days=days)

    # Build base query
    query = Activity.query.filter(Activity.created_at >= since)

    # Filter by user if not admin
    if not current_user.is_admin:
        query = query.filter_by(user_id=current_user.id)

    # Get counts by entity type
    entity_counts = db.session.query(Activity.entity_type, func.count(Activity.id).label("count")).filter(
        Activity.created_at >= since
    )

    if not current_user.is_admin:
        entity_counts = entity_counts.filter_by(user_id=current_user.id)

    entity_counts = entity_counts.group_by(Activity.entity_type).all()

    # Get counts by action
    action_counts = db.session.query(Activity.action, func.count(Activity.id).label("count")).filter(
        Activity.created_at >= since
    )

    if not current_user.is_admin:
        action_counts = action_counts.filter_by(user_id=current_user.id)

    action_counts = action_counts.group_by(Activity.action).all()

    # Get most active users (admins only)
    user_activity = []
    if current_user.is_admin:
        user_activity = (
            db.session.query(User.username, User.display_name, func.count(Activity.id).label("count"))
            .join(Activity, User.id == Activity.user_id)
            .filter(Activity.created_at >= since)
            .group_by(User.id, User.username, User.display_name)
            .order_by(func.count(Activity.id).desc())
            .limit(10)
            .all()
        )

    return jsonify(
        {
            "total_activities": query.count(),
            "entity_counts": {entity: count for entity, count in entity_counts},
            "action_counts": {action: count for action, count in action_counts},
            "user_activity": [{"username": u[0], "display_name": u[1], "count": u[2]} for u in user_activity],
            "period_days": days,
        }
    )


# WebSocket event handlers
@socketio.on("connect")
def handle_connect():
    """Handle WebSocket connection"""
    print(f"Client connected: {request.sid}")


@socketio.on("disconnect")
def handle_disconnect():
    """Handle WebSocket disconnection"""
    print(f"Client disconnected: {request.sid}")


@socketio.on("join_user_room")
def handle_join_user_room(data):
    """Join user-specific room for real-time updates"""
    user_id = data.get("user_id")
    if user_id and current_user.is_authenticated and current_user.id == user_id:
        socketio.join_room(f"user_{user_id}")
        print(f"User {user_id} joined room")


@socketio.on("leave_user_room")
def handle_leave_user_room(data):
    """Leave user-specific room"""
    user_id = data.get("user_id")
    if user_id:
        socketio.leave_room(f"user_{user_id}")
        print(f"User {user_id} left room")
