import json
import os
import re
import uuid
from datetime import datetime, time, timedelta

from flask import Blueprint, current_app, jsonify, make_response, request, send_from_directory, session
from flask_babel import gettext as _
from flask_login import current_user, login_required
from sqlalchemy import func, or_
from sqlalchemy.exc import SQLAlchemyError
from werkzeug.utils import secure_filename

from app import db, socketio
from app.models import (
    Client,
    FocusSession,
    Project,
    RateOverride,
    RecurringBlock,
    SavedFilter,
    Settings,
    Task,
    TimeEntry,
    User,
)
from app.models.time_entry import local_now
from app.services.ai_suggestion_service import AISuggestionService
from app.services.global_search_service import run_global_search
from app.services.llm_service import AIServiceError, LLMService
from app.services.time_tracking_service import TimeTrackingService
from app.utils.api_deprecation import deprecated_session_api
from app.utils.db import safe_commit
from app.utils.scope_filter import apply_client_scope, apply_project_scope, user_can_access_project
from app.utils.timezone import convert_app_datetime_to_user, parse_local_datetime, utc_to_local

api_bp = Blueprint("api", __name__)


def _ai_error_response(exc: AIServiceError):
    return jsonify({"ok": False, "error": exc.message, "error_code": exc.code}), exc.status_code


@api_bp.route("/api/health")
@deprecated_session_api("/api/v1/health")
def health_check():
    """Health check endpoint for monitoring and error handling"""
    return jsonify({"status": "ok", "timestamp": datetime.utcnow().isoformat()})


@api_bp.route("/api/ai/context-preview")
@login_required
def ai_context_preview():
    """Return the compact context preview that would be sent to the configured AI provider."""
    try:
        service = LLMService()
        if not service.is_enabled():
            return jsonify({"ok": False, "error": "AI helper is disabled", "error_code": "ai_disabled"}), 503
        return jsonify(
            {"ok": True, "context": service.context_preview(current_user), "provider": service.config.public_dict()}
        )
    except AIServiceError as exc:
        return _ai_error_response(exc)


@api_bp.route("/api/ai/test", methods=["POST"])
@login_required
def ai_test_connection():
    """Test the configured AI provider. Admins/settings managers can use this from settings."""
    if not (current_user.is_admin or current_user.has_permission("manage_settings")):
        return jsonify({"ok": False, "error": "Admin permission required", "error_code": "forbidden"}), 403
    try:
        return jsonify(LLMService().test_connection())
    except AIServiceError as exc:
        return _ai_error_response(exc)


@api_bp.route("/api/ai/chat", methods=["POST"])
@login_required
def ai_chat():
    """Chat with the AI helper using server-built TimeTracker context."""
    data = request.get_json(silent=True) or {}
    try:
        result = LLMService().chat(current_user, data.get("prompt") or "", data.get("history") or [])
        return jsonify({"ok": True, **result})
    except AIServiceError as exc:
        return _ai_error_response(exc)


@api_bp.route("/api/ai/actions/confirm", methods=["POST"])
@login_required
def ai_confirm_action():
    """Execute a user-confirmed AI proposed action."""
    data = request.get_json(silent=True) or {}
    try:
        service = LLMService()
        if not service.is_enabled():
            return jsonify({"ok": False, "error": "AI helper is disabled", "error_code": "ai_disabled"}), 503
        result = service.confirm_action(current_user, data.get("action") or {})
        return jsonify(result)
    except AIServiceError as exc:
        return _ai_error_response(exc)


def _ai_confidence_label(value):
    """Map a numeric confidence (0..1) to a coarse label used by the suggestion UI."""
    try:
        score = float(value)
    except (TypeError, ValueError):
        return "low"
    if score >= 0.7:
        return "high"
    if score >= 0.4:
        return "medium"
    return "low"


def _ai_safe_int(value):
    try:
        return int(value) if value not in (None, "") else None
    except (TypeError, ValueError):
        return None


def _ai_parse_suggestion_array(content):
    """Best-effort extraction of a JSON array from an LLM reply that may include prose."""
    if not isinstance(content, str) or not content.strip():
        return []
    fenced = re.search(r"```(?:json)?\s*(\[.*?\])\s*```", content, re.DOTALL)
    candidate = fenced.group(1) if fenced else None
    if candidate is None:
        match = re.search(r"\[.*\]", content, re.DOTALL)
        candidate = match.group(0) if match else None
    if candidate is None:
        return []
    try:
        data = json.loads(candidate)
    except (ValueError, TypeError):
        return []
    if not isinstance(data, list):
        return []
    return [item for item in data if isinstance(item, dict)]


@api_bp.route("/api/ai/suggest")
@login_required
@deprecated_session_api("/api/v1/ai/suggest")
def ai_suggest():
    """Return AI-powered time entry suggestions (deterministic, optionally LLM-enhanced)."""
    q = (request.args.get("q") or "").strip()
    rich = (request.args.get("rich") or "").strip().lower() in {"1", "true", "yes", "on"}

    suggestions = []

    try:
        deterministic = AISuggestionService().get_time_entry_suggestions(current_user.id, limit=5)
    except Exception as exc:  # noqa: BLE001 - never let suggestion errors 500 the request
        current_app.logger.warning("AI deterministic suggestions failed: %s", exc)
        deterministic = []

    pairs = {(s.get("project_id"), s.get("task_id")) for s in deterministic if s.get("project_id")}
    last_entry_by_pair = {}
    for project_id, task_id in pairs:
        query = TimeEntry.query.filter(
            TimeEntry.user_id == current_user.id,
            TimeEntry.project_id == project_id,
            TimeEntry.end_time.isnot(None),
        )
        if task_id is None:
            query = query.filter(TimeEntry.task_id.is_(None))
        else:
            query = query.filter(TimeEntry.task_id == task_id)
        entry = query.order_by(TimeEntry.start_time.desc()).first()
        if entry is not None:
            last_entry_by_pair[(project_id, task_id)] = entry

    for item in deterministic:
        pid = item.get("project_id")
        tid = item.get("task_id")
        last = last_entry_by_pair.get((pid, tid))
        suggestions.append(
            {
                "project_id": pid,
                "project_name": item.get("project_name"),
                "task_id": tid,
                "task_name": item.get("task_name"),
                "notes": (last.notes if last and last.notes else "") or "",
                "tags": (last.tags if last and last.tags else "") or "",
                "billable": bool(last.billable) if last is not None else True,
                "confidence": _ai_confidence_label(item.get("confidence")),
                "source": "deterministic",
            }
        )

    if rich:
        try:
            llm = LLMService()
            if llm.is_enabled():
                prompt = (
                    "Based on the user's recent time entries and assigned tasks, suggest the top 3 most likely "
                    "next time entries. For each, return project_id, task_id (if any), notes, tags, billable. "
                    "Return ONLY a JSON array, no prose."
                )
                result = llm.chat(current_user, prompt)
                ai_items = _ai_parse_suggestion_array(result.get("reply") or "")
                for item in ai_items:
                    pid = _ai_safe_int(item.get("project_id"))
                    if pid is None or not user_can_access_project(current_user, pid):
                        continue
                    project = Project.query.get(pid)
                    if project is None:
                        continue
                    tid = _ai_safe_int(item.get("task_id"))
                    task = Task.query.get(tid) if tid else None
                    if task is not None and task.project_id != pid:
                        task = None
                        tid = None
                    suggestions.append(
                        {
                            "project_id": pid,
                            "project_name": project.name,
                            "task_id": tid,
                            "task_name": task.name if task else None,
                            "notes": (str(item.get("notes") or ""))[:1000],
                            "tags": (str(item.get("tags") or ""))[:500],
                            "billable": bool(item.get("billable", True)),
                            "confidence": "medium",
                            "source": "ai",
                        }
                    )
        except AIServiceError as exc:
            current_app.logger.info("AI rich suggestions unavailable: %s", exc.message)
        except Exception as exc:  # noqa: BLE001 - never fail the request because of AI errors
            current_app.logger.warning("AI rich suggestions failed: %s", exc)

    seen = set()
    unique = []
    for item in suggestions:
        key = (item.get("project_id"), item.get("task_id"))
        if key in seen:
            continue
        seen.add(key)
        unique.append(item)

    if q:
        ql = q.lower()

        def _matches(item):
            project_name = (item.get("project_name") or "").lower()
            notes = (item.get("notes") or "").lower()
            return ql in project_name or ql in notes

        unique = [item for item in unique if _matches(item)]

    return jsonify({"ok": True, "suggestions": unique[:5]})


def _effective_user_for_version_api():
    """Session user, or API token user (Bearer / X-API-Key). Used for version check routes."""
    if getattr(current_user, "is_authenticated", False):
        return current_user
    from app.utils.api_auth import authenticate_token, extract_token_from_request

    token = extract_token_from_request()
    if not token:
        return None
    user, _api_token, _err = authenticate_token(token, record_usage=False)
    return user


@api_bp.route("/api/version/check")
def api_version_check():
    """Admin only: compare installed version to latest GitHub release (cached)."""
    user = _effective_user_for_version_api()
    if user is None:
        return jsonify({"error": "unauthorized", "message": "Authentication required"}), 401
    if not user.is_admin:
        return jsonify({"error": "forbidden", "message": "Admin only"}), 403
    from app.services.version_service import VersionService

    return jsonify(VersionService.build_check_response(user))


@api_bp.route("/api/version/dismiss", methods=["POST"])
def api_version_dismiss():
    """Admin only: remember not to show update popup for this normalized release version."""
    user = _effective_user_for_version_api()
    if user is None:
        return jsonify({"error": "unauthorized", "message": "Authentication required"}), 401
    if not user.is_admin:
        return jsonify({"error": "forbidden", "message": "Admin only"}), 403
    data = request.get_json(silent=True) or {}
    raw = data.get("latest_version")
    if not isinstance(raw, str) or not raw.strip():
        return jsonify({"error": "latest_version is required"}), 400

    from app.utils.version_compare import normalize_version_tag

    norm = normalize_version_tag(raw)
    if not norm:
        current_app.logger.warning(
            "Version dismiss: invalid latest_version from admin user_id=%s: %r",
            user.id,
            raw,
        )
        return jsonify({"error": "invalid latest_version"}), 400
    user.dismissed_release_version = norm
    db.session.add(user)
    if not safe_commit():
        return jsonify({"error": "save_failed"}), 500
    return jsonify({"ok": True})


@api_bp.route("/api/timer/status")
@login_required
@deprecated_session_api("/api/v1/timer/status")
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


@api_bp.route("/api/tags")
@login_required
def get_recent_tags():
    """Return distinct tags from current user's time entries for autocomplete (e.g. Start Timer modal)."""
    limit = min(request.args.get("limit", 30, type=int), 100)
    entries = (
        TimeEntry.query.filter(
            TimeEntry.user_id == current_user.id,
            TimeEntry.tags.isnot(None),
            TimeEntry.tags != "",
        )
        .order_by(TimeEntry.updated_at.desc())
        .limit(500)
        .all()
    )
    tags_set = set()
    for e in entries:
        if e.tags:
            for part in e.tags.split(","):
                t = part.strip()
                if t:
                    tags_set.add(t)
                    if len(tags_set) >= limit:
                        break
        if len(tags_set) >= limit:
            break
    return jsonify({"tags": sorted(tags_set)})


@api_bp.route("/api/search")
@login_required
@deprecated_session_api("/api/v1/search")
def search():
    """Global search endpoint for projects, tasks, clients, and time entries.

    Query Parameters:
        q (str): Search query (minimum 2 characters)
        limit (int): Maximum number of results per category (default: 10, max: 50)
        types (str): Comma-separated list of types to search (project, task, client, entry)

    Returns:
        JSON with ``results``, ``query``, ``count``, ``partial`` (true if any search domain failed),
        and ``errors`` (map of domain key to message: ``projects``, ``tasks``, ``clients``, ``entries``).
        Domains that hit a database error are omitted from ``results``; other domains still return hits.
    """
    query = request.args.get("q", "").strip()
    limit = min(request.args.get("limit", 10, type=int), 50)  # Cap at 50
    types_filter = request.args.get("types", "").strip().lower()

    if not query or len(query) < 2:
        return jsonify({"results": [], "query": query, "count": 0, "partial": False, "errors": {}})

    results, errors = run_global_search(
        current_user,
        query,
        limit=limit,
        types_filter=types_filter,
    )
    return jsonify(
        {
            "results": results,
            "query": query,
            "count": len(results),
            "partial": bool(errors),
            "errors": errors,
        }
    )


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
@deprecated_session_api("/api/v1/tasks")
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
@deprecated_session_api("/api/v1/timer/start")
def api_start_timer():
    """Start timer via API"""
    data = request.get_json() or {}
    project_id = data.get("project_id")
    task_id = data.get("task_id")
    notes = (data.get("notes") or "").strip() or None

    if not project_id:
        return jsonify({"error": "Project ID is required"}), 400

    if not user_can_access_project(current_user, project_id):
        return jsonify({"error": "You do not have access to this project"}), 403

    service = TimeTrackingService()
    result = service.start_timer(
        user_id=current_user.id,
        project_id=project_id,
        task_id=task_id,
        notes=notes,
        template_id=None,
    )
    if not result.get("success"):
        return jsonify({"error": result.get("message", "Could not start timer")}), 400

    new_timer = result["timer"]
    project = new_timer.project or Project.query.get(project_id)
    tid = new_timer.task_id

    socketio.emit(
        "timer_started",
        {
            "user_id": current_user.id,
            "timer_id": new_timer.id,
            "project_name": project.name if project else "",
            "task_id": tid,
            "start_time": new_timer.start_time.isoformat(),
        },
    )

    try:
        from app.integrations.slack_connector import SlackConnector

        SlackConnector.notify_for_user(current_user, new_timer, event="start")
    except Exception as e:
        current_app.logger.debug("Slack notify failed: %s", e)

    return jsonify(
        {
            "success": True,
            "timer_id": new_timer.id,
            "project_name": project.name if project else "",
            "task_id": tid,
        }
    )


@api_bp.route("/api/timer/stop", methods=["POST"])
@login_required
@deprecated_session_api("/api/v1/timer/stop")
def api_stop_timer():
    """Stop timer via API"""
    active_timer = current_user.active_timer

    if not active_timer:
        return jsonify({"error": "No active timer to stop"}), 400

    service = TimeTrackingService()
    result = service.stop_timer(user_id=current_user.id, entry_id=active_timer.id)
    if not result.get("success"):
        return jsonify({"error": result.get("message", "Could not stop timer")}), 400

    entry = result["entry"]

    socketio.emit(
        "timer_stopped",
        {"user_id": current_user.id, "timer_id": entry.id, "duration": entry.duration_formatted},
    )

    try:
        from app.integrations.slack_connector import SlackConnector

        SlackConnector.notify_for_user(current_user, entry, event="stop")
    except Exception as e:
        current_app.logger.debug("Slack notify failed: %s", e)

    return jsonify({"success": True, "duration": entry.duration_formatted, "duration_hours": entry.duration_hours})


# --- Idle control: stop at specific time ---
@api_bp.route("/api/timer/stop_at", methods=["POST"])
@login_required
@deprecated_session_api("/api/v1/timer/stop")
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
@deprecated_session_api("/api/v1/timer/start")
def api_resume_timer():
    """Resume timer for last used project/task or provided project/task."""
    can_start, _ = TimeTrackingService().can_start_timer(current_user.id)
    if not can_start:
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

    service = TimeTrackingService()
    result = service.start_timer(
        user_id=current_user.id,
        project_id=project_id,
        task_id=task_id,
        notes=None,
        template_id=None,
    )
    if not result.get("success"):
        return jsonify({"error": result.get("message", "Could not start timer")}), 400

    new_timer = result["timer"]

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
@deprecated_session_api("/api/v1/time-entries")
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
        can_view_all = current_user.is_admin or current_user.has_permission("view_all_time_entries")
        if filt and (filt.user_id == current_user.id or (filt.is_shared and can_view_all)):
            payload = filt.payload or {}
            if "project_id" in payload:
                query = query.filter(TimeEntry.project_id == int(payload["project_id"]))
            if "user_id" in payload and can_view_all:
                query = query.filter(TimeEntry.user_id == int(payload["user_id"]))
            if "billable" in payload:
                query = query.filter(TimeEntry.billable == bool(payload["billable"]))
            if "tag" in payload and payload["tag"]:
                query = query.filter(TimeEntry.tags.ilike(f"%{payload['tag']}%"))

    # Filter by user (if has view_all_time_entries permission or own entries)
    can_view_all = current_user.is_admin or current_user.has_permission("view_all_time_entries")
    if user_id and can_view_all:
        query = query.filter(TimeEntry.user_id == user_id)
    elif not can_view_all:
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


# Module-level forecast cache: {project_id: (cached_at_epoch, payload_dict, kind)}
# kind is "deterministic" or "ai" so cached AI payloads aren't served for plain requests.
_FORECAST_CACHE: dict = {}
_FORECAST_CACHE_TTL_SEC = 600  # 10 minutes


def _forecast_cache_get(project_id: int, kind: str):
    try:
        entry = _FORECAST_CACHE.get(int(project_id))
    except (TypeError, ValueError):
        return None
    if not entry:
        return None
    cached_at, payload, cached_kind = entry
    if cached_kind != kind:
        return None
    if (datetime.utcnow().timestamp() - cached_at) > _FORECAST_CACHE_TTL_SEC:
        _FORECAST_CACHE.pop(int(project_id), None)
        return None
    return payload


def _forecast_cache_set(project_id: int, kind: str, payload: dict) -> None:
    try:
        _FORECAST_CACHE[int(project_id)] = (datetime.utcnow().timestamp(), payload, kind)
    except (TypeError, ValueError):
        return


def _forecast_cache_bust(project_id: int) -> None:
    try:
        _FORECAST_CACHE.pop(int(project_id), None)
    except (TypeError, ValueError):
        return


def _truthy_param(value) -> bool:
    if value is None:
        return False
    return str(value).strip().lower() in ("1", "true", "yes", "on")


@api_bp.route("/api/projects/<int:project_id>/forecast")
@login_required
def project_forecast(project_id):
    """Return deterministic (and optionally AI-narrated) forecast for a project.

    Query params:
        ai (bool, default false): include LLM-generated narrative/risks/recommendations.
        refresh (bool, default false): bust the in-memory cache for this project.
    """
    try:
        if not user_can_access_project(current_user, project_id):
            return jsonify({"ok": False, "error": "Access denied"}), 403

        include_ai = _truthy_param(request.args.get("ai"))
        refresh = _truthy_param(request.args.get("refresh"))

        if refresh:
            _forecast_cache_bust(project_id)

        cache_kind = "ai" if include_ai else "deterministic"
        if not refresh:
            cached = _forecast_cache_get(project_id, cache_kind)
            if cached is not None:
                return jsonify(cached)

        from app.services.forecast_service import ForecastService

        # Cheap probe so the component can hide the AI button when disabled.
        try:
            ai_enabled = LLMService().is_enabled()
        except Exception:
            ai_enabled = False

        if include_ai:
            ai_result = ForecastService.get_ai_forecast(project_id, current_user)
            forecast_dict = ai_result.get("deterministic") or ForecastService.get_deterministic_forecast(
                project_id, current_user
            )
            payload = {
                "ok": True,
                "project_id": int(project_id),
                "ai_enabled": bool(ai_enabled),
                "forecast": forecast_dict,
                "ai": {
                    "ok": bool(ai_result.get("ok")),
                    "narrative": ai_result.get("narrative"),
                    "risks": ai_result.get("risks") or [],
                    "recommendations": ai_result.get("recommendations") or [],
                    "error": ai_result.get("error"),
                    "error_code": ai_result.get("error_code"),
                },
            }
        else:
            forecast_dict = ForecastService.get_deterministic_forecast(project_id, current_user)
            payload = {
                "ok": True,
                "project_id": int(project_id),
                "ai_enabled": bool(ai_enabled),
                "forecast": forecast_dict,
            }

        _forecast_cache_set(project_id, cache_kind, payload)
        return jsonify(payload)
    except Exception as exc:
        current_app.logger.exception("project_forecast failed for project %s", project_id)
        return jsonify({"ok": False, "error": str(exc) or "internal_error"}), 500


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
@deprecated_session_api("/api/v1/time-entries")
def create_entry():
    """Create a finished time entry (used by calendar drag-create)."""
    from app.models import Client

    data = request.get_json() or {}
    project_id = data.get("project_id")
    client_id = data.get("client_id")
    task_id = data.get("task_id")
    start_time_str = data.get("start_time")
    end_time_str = data.get("end_time")
    notes = (data.get("notes") or "").strip() or None
    tags = (data.get("tags") or "").strip() or None
    billable = bool(data.get("billable", True))

    if not (start_time_str and end_time_str):
        return jsonify({"error": "start_time and end_time are required"}), 400

    if not project_id and not client_id:
        return jsonify({"error": "Either project_id or client_id is required"}), 400

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

    # Use service to create entry (handles validation)
    time_tracking_service = TimeTrackingService()
    result = time_tracking_service.create_manual_entry(
        user_id=current_user.id if not current_user.is_admin else (data.get("user_id") or current_user.id),
        project_id=project_id,
        client_id=client_id,
        start_time=start_dt,
        end_time=end_dt,
        task_id=task_id,
        notes=notes,
        tags=tags,
        billable=billable,
    )

    if not result.get("success"):
        return jsonify({"error": result.get("message", "Could not create time entry")}), 400

    entry = result.get("entry")

    # Log activity
    if entry:
        from app.models import Activity

        entity_name = entry.project.name if entry.project else (entry.client.name if entry.client else "Unknown")
        task_name = entry.task.name if entry.task else None
        duration_formatted = entry.duration_formatted if hasattr(entry, "duration_formatted") else "0:00"

        Activity.log(
            user_id=entry.user_id,
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
            ip_address=request.remote_addr,
            user_agent=request.headers.get("User-Agent"),
        )

    # Invalidate dashboard cache for the entry owner so new entry appears immediately
    try:
        from app.utils.cache import invalidate_dashboard_for_user

        invalidate_dashboard_for_user(entry.user_id)
        current_app.logger.debug("Invalidated dashboard cache for user %s after entry creation", entry.user_id)
    except Exception as e:
        current_app.logger.warning("Failed to invalidate dashboard cache: %s", e)

    payload = entry.to_dict()
    payload["project_name"] = entry.project.name if entry.project else None
    payload["client_name"] = entry.client.name if entry.client else None
    return jsonify({"success": True, "entry": payload}), 201


@api_bp.route("/api/entries/bulk", methods=["POST"])
@login_required
@deprecated_session_api("/api/v1/time-entries/bulk")
def bulk_entries_action():
    """Perform bulk actions on time entries: delete, set billable, set paid, add/remove tag."""
    from app.services.time_entry_bulk_service import apply_bulk_time_entry_actions

    data = request.get_json() or {}
    entry_ids = data.get("entry_ids") or []
    action = (data.get("action") or "").strip()
    value = data.get("value")

    if not entry_ids or not isinstance(entry_ids, list):
        return jsonify({"error": "entry_ids must be a non-empty list"}), 400
    try:
        ids_int = [int(eid) for eid in entry_ids]
    except (TypeError, ValueError):
        return jsonify({"error": "entry_ids must be integers"}), 400

    result = apply_bulk_time_entry_actions(
        ids_int, action, value, user_id=current_user.id, is_admin=current_user.is_admin
    )
    if not result.get("success"):
        return jsonify({"error": result.get("error", "Bulk operation failed")}), result.get("http_status", 400)
    return jsonify({"success": True, "affected": result.get("affected", 0)})


@api_bp.route("/api/calendar/events")
@login_required
def calendar_events():
    """Return calendar events, tasks, and time entries for the current user in a date range."""
    from app.models import CalendarEvent as CalendarEventModel

    start = request.args.get("start")
    end = request.args.get("end")
    include_tasks = request.args.get("include_tasks", "true").lower() == "true"
    include_time_entries = request.args.get("include_time_entries", "true").lower() == "true"
    include_holidays = request.args.get("include_holidays", "true").lower() == "true"
    include_time_off = request.args.get("include_time_off", "true").lower() == "true"
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

    # Helper function to convert ISO string from app timezone to user timezone and format for FullCalendar
    def convert_time_for_calendar(iso_str):
        """Convert ISO time string from app timezone to user timezone for FullCalendar."""
        if not iso_str:
            return None
        try:
            # Parse the ISO string (format: YYYY-MM-DDTHH:mm:ss, no timezone)
            dt = datetime.fromisoformat(iso_str)
            # Convert from app timezone to user's local timezone
            user_dt = convert_app_datetime_to_user(dt, user=current_user)
            # Convert to naive datetime (remove timezone info) for FullCalendar
            # FullCalendar with timeZone: 'local' expects times without timezone to be treated as local
            naive_dt = user_dt.replace(tzinfo=None) if user_dt.tzinfo else user_dt
            # Format as ISO string for FullCalendar
            return naive_dt.strftime("%Y-%m-%dT%H:%M:%S")
        except Exception:
            # If parsing fails, return original
            return iso_str

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
                "start": convert_time_for_calendar(e["start"]),
                "end": convert_time_for_calendar(e["end"]),
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
        # Only convert times for non-all-day events
        event_start = ev["start"]
        event_end = ev["end"]
        if not ev.get("allDay", False):
            event_start = convert_time_for_calendar(ev["start"])
            event_end = convert_time_for_calendar(ev["end"])

        events.append(
            {
                "id": ev["id"],
                "title": ev["title"],
                "start": event_start,
                "end": event_end,
                "allDay": ev.get("allDay", False),
                "editable": True,
                "backgroundColor": ev.get("color", "#3b82f6"),
                "borderColor": ev.get("color", "#3b82f6"),
                "extendedProps": {**ev, "item_type": "event"},
            }
        )

    # Combine all items
    all_items = events + tasks + time_entries

    from app.utils.calendar_overlay import (
        HOLIDAY_COLOR,
        TIME_OFF_COLOR,
        get_holidays_for_calendar,
        get_time_off_for_calendar,
    )

    overlay_start = start_dt.date()
    overlay_end = end_dt.date()
    if include_holidays:
        for item in get_holidays_for_calendar(overlay_start, overlay_end):
            all_items.append(
                {
                    "id": item["id"],
                    "title": item["title"],
                    "start": item["start"][:10],
                    "end": item["end"][:10],
                    "allDay": True,
                    "display": "background",
                    "backgroundColor": HOLIDAY_COLOR + "33",
                    "borderColor": HOLIDAY_COLOR,
                    "editable": False,
                    "extendedProps": {**item, "item_type": "holiday"},
                }
            )
    if include_time_off:
        for item in get_time_off_for_calendar(user_id, overlay_start, overlay_end):
            all_items.append(
                {
                    "id": item["id"],
                    "title": item["title"],
                    "start": item["start"][:10],
                    "end": item["end"][:10],
                    "allDay": True,
                    "display": "background",
                    "backgroundColor": (item.get("color") or TIME_OFF_COLOR) + "33",
                    "borderColor": item.get("color") or TIME_OFF_COLOR,
                    "editable": False,
                    "extendedProps": {**item, "item_type": "time_off"},
                }
            )

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
@deprecated_session_api("/api/v1/projects")
def get_projects():
    """Get active projects"""
    projects = Project.query.filter_by(status="active").order_by(Project.name).all()
    return jsonify({"projects": [project.to_dict() for project in projects]})


@api_bp.route("/api/projects/<int:project_id>/tasks")
@login_required
@deprecated_session_api("/api/v1/tasks")
def get_project_tasks(project_id):
    """Get tasks for a specific project"""
    # Check if project exists and is active
    project = Project.query.filter_by(id=project_id, status="active").first()
    if not project:
        return jsonify({"error": "Project not found or inactive"}), 404

    # Return ALL tasks for the project (including done/cancelled).
    # This is used by the manual time entry UI where users may need to log time
    # against any task status.
    tasks = Task.query.filter_by(project_id=project_id).order_by(Task.name).all()

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


@api_bp.route("/api/tasks/create", methods=["POST"])
@login_required
def create_task_inline():
    """Create a new task via AJAX with default values"""
    # Detect AJAX/JSON request
    try:
        is_classic_form = request.mimetype in ("application/x-www-form-urlencoded", "multipart/form-data")
    except Exception:
        is_classic_form = False

    try:
        wants_json = (
            request.headers.get("X-Requested-With") == "XMLHttpRequest"
            or request.is_json
            or (
                not is_classic_form
                and (request.accept_mimetypes["application/json"] > request.accept_mimetypes["text/html"])
            )
        )
    except Exception:
        wants_json = False

    if request.method == "POST":
        # Get data from JSON or form
        if request.is_json:
            data = request.get_json()
            name = data.get("name", "").strip()
            project_id = data.get("project_id")
            if project_id is not None:
                project_id = int(project_id)
        else:
            name = request.form.get("name", "").strip()
            project_id = request.form.get("project_id", type=int)

        # Validate required fields
        if not name or not project_id:
            if wants_json:
                return jsonify({"error": "name and project_id are required"}), 400
            from flask import flash, redirect, url_for

            flash(_("Task name and project are required"), "error")
            return redirect(url_for("tasks.list_tasks"))

        # Validate project exists and is active
        project = Project.query.filter_by(id=project_id, status="active").first()
        if not project:
            if wants_json:
                return jsonify({"error": "Project not found or inactive"}), 404
            from flask import flash, redirect, url_for

            flash(_("Selected project does not exist or is inactive"), "error")
            return redirect(url_for("tasks.list_tasks"))

        # Create task with defaults using TaskService
        from app.services import TaskService

        task_service = TaskService()
        result = task_service.create_task(
            name=name,
            project_id=project_id,
            created_by=current_user.id,
            assignee_id=current_user.id,  # Assign to current user
            priority="medium",  # Default priority
            due_date=None,  # No due date
            description=None,
            estimated_hours=None,
        )

        if not result["success"]:
            if wants_json:
                return jsonify({"error": result.get("message", "Failed to create task")}), 400
            from flask import flash, redirect, url_for

            flash(_(result["message"]), "error")
            return redirect(url_for("tasks.list_tasks"))

        task = result["task"]

        # Log task creation
        from app import log_event, track_event
        from app.models import Activity

        log_event(
            "task.created",
            user_id=current_user.id,
            task_id=task.id,
            project_id=project_id,
            priority="medium",
        )
        track_event(
            current_user.id, "task.created", {"task_id": task.id, "project_id": project_id, "priority": "medium"}
        )

        Activity.log(
            user_id=current_user.id,
            action="created",
            entity_type="task",
            entity_id=task.id,
            entity_name=task.name,
            description=f'Created task "{task.name}" in project "{project.name}"',
            extra_data={"project_id": project_id, "priority": "medium"},
            ip_address=request.remote_addr,
            user_agent=request.headers.get("User-Agent"),
        )

        if wants_json:
            return jsonify({"success": True, "id": task.id, "name": task.name, "task": task.to_dict()}), 201
        from flask import flash, redirect, url_for

        flash(_('Task "%(name)s" created successfully', name=name), "success")
        return redirect(url_for("tasks.view_task", task_id=task.id))

    # GET request - redirect to task list
    return redirect(url_for("tasks.list_tasks"))


# Fetch a single time entry (details for edit modal)
@api_bp.route("/api/entry/<int:entry_id>", methods=["GET"])
@login_required
@deprecated_session_api("/api/v1/time-entries")
def get_entry(entry_id):
    entry = TimeEntry.query.get_or_404(entry_id)
    if entry.user_id != current_user.id and not current_user.is_admin:
        return jsonify({"error": "Access denied"}), 403
    payload = entry.to_dict()
    payload["project_name"] = entry.project.name if entry.project else None
    return jsonify(payload)


@api_bp.route("/api/users")
@login_required
@deprecated_session_api("/api/v1/users")
def get_users():
    """Get active users (admin only). Uses a single aggregate query for total_hours to avoid N+1."""
    if not current_user.is_admin:
        return jsonify({"error": "Access denied"}), 403

    users = User.query.filter_by(is_active=True).order_by(User.username).all()
    if not users:
        return jsonify({"users": []})

    user_ids = [u.id for u in users]
    rows = (
        db.session.query(TimeEntry.user_id, db.func.sum(TimeEntry.duration_seconds))
        .filter(
            TimeEntry.user_id.in_(user_ids),
            TimeEntry.end_time.isnot(None),
        )
        .group_by(TimeEntry.user_id)
        .all()
    )
    total_hours_by_user = {uid: round((total_seconds or 0) / 3600, 2) for uid, total_seconds in rows}
    return jsonify({"users": [user.to_dict(total_hours_override=total_hours_by_user.get(user.id)) for user in users]})


@api_bp.route("/api/users/search")
@login_required
def search_users_for_mentions():
    """Lightweight active-user list for @mention autocomplete.

    Available to any authenticated user (unlike /api/users, which is admin
    only) and returns just the fields the mention UI needs. An optional ``q``
    query narrows the list by username or display name.
    """
    q = (request.args.get("q") or "").strip().lower()
    query = User.query.filter_by(is_active=True)
    if q:
        like = f"%{q}%"
        query = query.filter(
            db.or_(
                db.func.lower(User.username).like(like),
                db.func.lower(User.full_name).like(like),
            )
        )
    users = query.order_by(User.username).limit(500).all()
    return jsonify({"users": [{"id": u.id, "username": u.username, "display_name": u.display_name} for u in users]})


@api_bp.route("/api/stats")
@login_required
def get_stats():
    """Get user statistics"""
    from app.utils.overtime import calculate_period_overtime, get_week_start_for_date

    # Get date range
    end_date = datetime.utcnow()
    start_date = end_date - timedelta(days=30)
    today = end_date.date()
    week_start = get_week_start_for_date(today, current_user)
    user_id = current_user.id if not current_user.is_admin else None

    # Calculate statistics
    today_hours = TimeEntry.get_total_hours_for_period(start_date=today, user_id=user_id)

    week_hours = TimeEntry.get_total_hours_for_period(start_date=week_start, user_id=user_id)

    month_hours = TimeEntry.get_total_hours_for_period(start_date=start_date.date(), user_id=user_id)

    # Overtime for today, week, and YTD
    from app.utils.overtime import get_overtime_ytd

    today_overtime = calculate_period_overtime(current_user, today, today)
    week_overtime = calculate_period_overtime(current_user, week_start, today)
    overtime_ytd = get_overtime_ytd(current_user)
    standard_hours = float(getattr(current_user, "standard_hours_per_day", 8.0) or 8.0)

    return jsonify(
        {
            "today_hours": today_hours,
            "week_hours": week_hours,
            "month_hours": month_hours,
            "total_hours": current_user.total_hours,
            "standard_hours_per_day": standard_hours,
            "today_regular_hours": today_overtime["regular_hours"],
            "today_overtime_hours": today_overtime["overtime_hours"],
            "week_regular_hours": week_overtime["regular_hours"],
            "week_overtime_hours": week_overtime["overtime_hours"],
            "overtime_ytd_hours": overtime_ytd["overtime_hours"],
        }
    )


@api_bp.route("/api/stats/value-dashboard")
@login_required
def value_dashboard_stats():
    """Productivity/value aggregates for the dashboard widget (short-TTL Redis cache)."""
    from app.services.stats_service import StatsService

    return jsonify(StatsService.get_value_dashboard(current_user))


@api_bp.route("/api/reports/week-comparison")
@login_required
def week_comparison():
    """This week (Mon 00:00–now) vs same calendar weekdays last week; matches dashboard week hours."""
    now = datetime.now()
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    week_start = today_start - timedelta(days=today_start.weekday())
    today_date = today_start.date()
    week_start_date = week_start.date()
    last_week_start_date = week_start_date - timedelta(days=7)
    last_week_end_date = today_date - timedelta(days=7)

    last_start_dt = datetime.combine(last_week_start_date, time.min)
    last_end_exclusive = datetime.combine(last_week_end_date + timedelta(days=1), time.min)

    user_id = current_user.id

    def sum_hours_by_day(start_dt, end_dt, end_exclusive=False):
        q = db.session.query(
            func.date(TimeEntry.start_time).label("day"),
            func.sum(TimeEntry.duration_seconds),
        ).filter(
            TimeEntry.user_id == user_id,
            TimeEntry.end_time.isnot(None),
            TimeEntry.start_time >= start_dt,
        )
        if end_exclusive:
            q = q.filter(TimeEntry.start_time < end_dt)
        else:
            q = q.filter(TimeEntry.start_time <= end_dt)
        rows = q.group_by(func.date(TimeEntry.start_time)).all()
        out = {}
        for day_val, total_sec in rows:
            if day_val is None:
                continue
            if hasattr(day_val, "isoformat"):
                key = day_val.isoformat()
            else:
                key = str(day_val)
            out[key] = round((total_sec or 0) / 3600.0, 2)
        return out

    current_map = sum_hours_by_day(week_start, now, end_exclusive=False)
    last_map = sum_hours_by_day(last_start_dt, last_end_exclusive, end_exclusive=True)

    def dense_series(start_d, end_d, hmap):
        series = []
        total = 0.0
        d = start_d
        while d <= end_d:
            key = d.isoformat()
            h = float(hmap.get(key, 0.0))
            series.append({"day": key, "hours": h})
            total += h
            d += timedelta(days=1)
        return series, round(total, 2)

    current_by_day, current_total = dense_series(week_start_date, today_date, current_map)
    last_by_day, last_total = dense_series(last_week_start_date, last_week_end_date, last_map)

    if last_total > 0:
        change_percent = round((current_total - last_total) / last_total * 100.0, 1)
    else:
        change_percent = None

    return jsonify(
        {
            "current_week": {"total_hours": current_total, "by_day": current_by_day},
            "last_week": {"total_hours": last_total, "by_day": last_by_day},
            "change_percent": change_percent,
        }
    )


@api_bp.route("/api/entry/<int:entry_id>", methods=["PUT", "PATCH"])
@login_required
@deprecated_session_api("/api/v1/time-entries")
def update_entry(entry_id):
    """Update a time entry"""
    entry = TimeEntry.query.get_or_404(entry_id)

    # Check permissions
    if entry.user_id != current_user.id and not current_user.is_admin:
        return jsonify({"error": "Access denied"}), 403

    data = request.get_json() or {}
    reason = data.get("reason")  # Optional reason for the change

    can_edit_schedule = current_user.is_admin or (
        entry.user_id == current_user.id and current_user.has_permission("edit_own_time_entries")
    )

    # Optional: start/end time and assignment updates (admin or edit_own_time_entries on own entry)
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

    # Use service layer for update to get enhanced audit logging
    service = TimeTrackingService()

    # Convert data to service parameters
    result = service.update_entry(
        entry_id=entry_id,
        user_id=current_user.id,
        is_admin=current_user.is_admin,
        project_id=data.get("project_id") if can_edit_schedule else None,
        client_id=data.get("client_id") if can_edit_schedule else None,
        task_id=data.get("task_id") if can_edit_schedule else None,
        start_time=parse_dt_local(data.get("start_time")) if can_edit_schedule and data.get("start_time") else None,
        end_time=parse_dt_local(data.get("end_time")) if can_edit_schedule and data.get("end_time") else None,
        break_seconds=data.get("break_seconds") if can_edit_schedule else None,
        notes=data.get("notes"),
        tags=data.get("tags"),
        billable=data.get("billable"),
        paid=data.get("paid"),
        invoice_number=data.get("invoice_number"),
        reason=reason,
    )

    if not result.get("success"):
        return jsonify({"error": result.get("message", "Could not update entry")}), 400

    entry = result.get("entry")

    # Log activity
    if entry:
        from app.models import Activity

        entity_name = entry.project.name if entry.project else (entry.client.name if entry.client else "Unknown")
        task_name = entry.task.name if entry.task else None

        Activity.log(
            user_id=current_user.id,
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
            ip_address=request.remote_addr,
            user_agent=request.headers.get("User-Agent"),
        )

    # Invalidate dashboard cache for the entry owner so changes appear immediately
    try:
        from app.utils.cache import invalidate_dashboard_for_user

        invalidate_dashboard_for_user(entry.user_id)
        current_app.logger.debug("Invalidated dashboard cache for user %s after entry update", entry.user_id)
    except Exception as e:
        current_app.logger.warning("Failed to invalidate dashboard cache: %s", e)

    payload = entry.to_dict()
    payload["project_name"] = entry.project.name if entry.project else None
    return jsonify({"success": True, "entry": payload})


@api_bp.route("/api/entry/<int:entry_id>", methods=["DELETE"])
@login_required
def delete_entry(entry_id):
    """Delete a time entry"""
    data = request.get_json() or {}
    reason = data.get("reason")  # Optional reason for deletion

    # Use service layer for deletion to get enhanced audit logging
    service = TimeTrackingService()

    result = service.delete_entry(
        user_id=current_user.id,
        entry_id=entry_id,
        is_admin=current_user.is_admin,
        reason=reason,
    )

    if not result.get("success"):
        return jsonify({"error": result.get("message", "Could not delete entry")}), 400

    # Invalidate dashboard cache for the entry owner so changes appear immediately
    try:
        from app.utils.cache import invalidate_dashboard_for_user

        invalidate_dashboard_for_user(current_user.id)
        current_app.logger.debug("Invalidated dashboard cache for user %s after entry deletion", current_user.id)
    except Exception as e:
        current_app.logger.warning("Failed to invalidate dashboard cache: %s", e)

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


@api_bp.route("/api/uploads/images/bulk", methods=["POST"])
@login_required
def upload_editor_images_bulk():
    """Handle multiple image uploads from the markdown editor."""
    if "images" not in request.files:
        return jsonify({"error": "No images provided"}), 400

    files = request.files.getlist("images")
    if not files or all(f.filename == "" for f in files):
        return jsonify({"error": "No images provided"}), 400

    uploaded_urls = []
    errors = []

    for idx, file in enumerate(files):
        if file.filename == "":
            continue

        if not allowed_image_file(file.filename):
            errors.append(f"File {idx + 1} ({file.filename}): Invalid file type")
            continue

        try:
            filename = secure_filename(file.filename)
            ext = filename.rsplit(".", 1)[1].lower()
            unique_name = f"editor_{uuid.uuid4().hex[:12]}.{ext}"
            folder = get_editor_upload_folder()
            path = os.path.join(folder, unique_name)
            file.save(path)

            url = f"/uploads/editor/{unique_name}"
            uploaded_urls.append(url)
        except Exception as e:
            errors.append(f"File {idx + 1} ({file.filename}): {str(e)}")

    if not uploaded_urls and errors:
        return jsonify({"error": "All uploads failed", "details": errors}), 400

    response = {"success": True, "urls": uploaded_urls}
    if errors:
        response["warnings"] = errors

    return jsonify(response)


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
@deprecated_session_api("/api/v1/activities")
def get_activities():
    """Get recent activities with filtering"""
    from sqlalchemy import and_

    from app.models import Activity

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
    from datetime import datetime, timedelta

    from app.models import TimeEntry
    from app.utils.overtime import calculate_period_overtime, get_overtime_ytd, get_week_start_for_date

    today = datetime.utcnow().date()
    week_start = get_week_start_for_date(today, current_user)
    month_start = today.replace(day=1)

    today_hours = TimeEntry.get_total_hours_for_period(start_date=today, user_id=current_user.id)

    week_hours = TimeEntry.get_total_hours_for_period(start_date=week_start, user_id=current_user.id)

    month_hours = TimeEntry.get_total_hours_for_period(start_date=month_start, user_id=current_user.id)

    # Overtime for today, week, and YTD (for dashboard cards)
    today_overtime = calculate_period_overtime(current_user, today, today)
    week_overtime = calculate_period_overtime(current_user, week_start, today)
    overtime_ytd = get_overtime_ytd(current_user)
    standard_hours = float(getattr(current_user, "standard_hours_per_day", 8.0) or 8.0)

    return jsonify(
        {
            "success": True,
            "today_hours": float(today_hours),
            "week_hours": float(week_hours),
            "month_hours": float(month_hours),
            "standard_hours_per_day": standard_hours,
            "today_regular_hours": today_overtime["regular_hours"],
            "today_overtime_hours": today_overtime["overtime_hours"],
            "week_regular_hours": week_overtime["regular_hours"],
            "week_overtime_hours": week_overtime["overtime_hours"],
            "overtime_ytd_hours": overtime_ytd["overtime_hours"],
        }
    )


@api_bp.route("/api/dashboard/sparklines")
@login_required
def dashboard_sparklines():
    """Get sparkline data for dashboard widgets"""
    from datetime import datetime, timedelta

    from sqlalchemy import func

    from app.models import TimeEntry

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
    """Get today's time tracking summary (user's local calendar day, not UTC midnight)."""
    from app.services.notification_service import get_today_summary_for_user

    payload = get_today_summary_for_user(current_user)
    return jsonify(payload)


@api_bp.route("/api/notifications")
@login_required
def api_smart_notifications():
    """Smart in-app notification candidates (respects preferences, dismissals, caps)."""
    from app.services.notification_service import NotificationService

    return jsonify(NotificationService.build_for_user(current_user))


@api_bp.route("/api/notifications/dismiss", methods=["POST"])
@login_required
def api_smart_notifications_dismiss():
    """Record dismissal for a notification kind on a local calendar date."""
    from app.services.notification_service import NotificationService, user_local_today_bounds_utc

    data = request.get_json(silent=True) or {}
    kind = data.get("kind")
    local_date = data.get("local_date")
    if not kind or not isinstance(kind, str):
        return jsonify({"error": "kind is required"}), 400
    if not local_date or not isinstance(local_date, str):
        _, _, local_date = user_local_today_bounds_utc(current_user)
    ok = NotificationService.dismiss(current_user, kind.strip(), local_date.strip()[:10])
    if not ok:
        return jsonify({"error": "invalid kind or local_date"}), 400
    return jsonify({"success": True})


@api_bp.route("/api/activity/timeline")
@login_required
def activity_timeline():
    """Get activity timeline for dashboard"""
    from datetime import datetime, timedelta

    from app.models import Activity

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
    from sqlalchemy import func

    from app.models import Activity

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


@api_bp.route("/api/productivity/stats")
@login_required
def productivity_stats():
    """Aggregated personal productivity stats for the current user.

    Query params:
        period (int): days for focus/project breakdowns (default 30, max 90)
    """
    try:
        try:
            period = int(request.args.get("period", 30))
        except (TypeError, ValueError):
            period = 30
        period = max(1, min(period, 90))

        from app.services.productivity_service import ProductivityService

        cache_key = None
        cache_obj = None
        try:
            from app.utils.cache import get_cache as _get_app_cache

            cache_obj = _get_app_cache()
            cache_key = f"productivity:stats:{current_user.id}:{period}"
            cached = cache_obj.get(cache_key) if cache_obj is not None else None
            if cached is not None:
                return jsonify(cached)
        except Exception:
            cache_obj = None

        summary = ProductivityService.get_summary(current_user)
        daily_breakdown = ProductivityService.get_daily_breakdown(current_user, days=14)
        streak = ProductivityService.get_streak(current_user)
        focus = ProductivityService.get_focus_stats(current_user, days=period)
        projects = ProductivityService.get_project_breakdown(current_user, days=period)
        heatmap = ProductivityService.get_weekly_heatmap(current_user, weeks=12)
        insights = ProductivityService.get_insights(current_user, summary, daily_breakdown, streak, focus, projects)

        payload = {
            "ok": True,
            "period": period,
            "summary": summary,
            "daily_breakdown": daily_breakdown,
            "streak": streak,
            "focus": focus,
            "projects": projects,
            "heatmap": heatmap,
            "insights": insights,
        }

        # Don't cache when an active timer is running so the UI stays fresh.
        if cache_obj is not None and cache_key and not (summary or {}).get("active_timer"):
            try:
                cache_obj.set(cache_key, payload, ttl=300)
            except Exception:
                pass

        return jsonify(payload)
    except Exception as exc:
        current_app.logger.exception("productivity_stats failed")
        return jsonify({"ok": False, "error": str(exc) or "internal_error"}), 500


# ---------------------------------------------------------------- user theme
#
# Per-user custom theme endpoints. The actual logic (validation, CSS
# generation, persistence) lives in :class:`app.services.theme_service.ThemeService`
# so the routes stay thin and the theme picker component can also be
# rendered server-side without going through the API.


@api_bp.route("/api/user/theme", methods=["GET"])
@login_required
def get_user_theme():
    """Return the user's current theme + the list of available themes."""
    from app.services.theme_service import ThemeService

    service = ThemeService()
    current = {
        "theme_name": getattr(current_user, "theme_name", None) or "default",
        "accent_color": getattr(current_user, "theme_accent_color", None),
        "sidebar_style": getattr(current_user, "theme_sidebar_style", None) or "default",
        "font_size": getattr(current_user, "theme_font_size", None) or "base",
        "border_radius": getattr(current_user, "theme_border_radius", None) or "default",
    }
    return jsonify(
        {
            "ok": True,
            "current": current,
            "themes": service.get_all_themes(),
            "accent_presets": service.get_accent_presets(),
            "css": service.get_theme_css_vars(current_user),
        }
    )


@api_bp.route("/api/user/theme", methods=["POST"])
@login_required
def save_user_theme():
    """Persist the user's theme preferences and return the new CSS block.

    The returned ``css`` field is the regenerated ``<style id="tt-theme-vars">``
    block so the picker can swap it into the page for an instant live
    preview without a full reload.
    """
    from app.services.theme_service import ThemeService

    data = request.get_json(silent=True) or {}
    service = ThemeService()
    result = service.save_user_theme(
        current_user,
        theme_name=data.get("theme_name"),
        accent_color=data.get("accent_color"),
        sidebar_style=data.get("sidebar_style"),
        font_size=data.get("font_size"),
        border_radius=data.get("border_radius"),
    )
    if not result.get("ok"):
        return jsonify(result), 400
    return jsonify({"ok": True, "css": service.get_theme_css_vars(current_user)})


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


# Client portal real-time: join/leave client-specific room (auth via session)
def _get_client_id_from_session():
    """Resolve client_id for client portal from session. Returns None if not a portal session."""
    client_id = session.get("client_portal_id")
    if client_id is not None:
        return int(client_id) if client_id else None
    user_id = session.get("_user_id")
    if user_id is not None:
        try:
            uid = int(user_id) if isinstance(user_id, str) else user_id
            user = User.query.get(uid)
            if user and getattr(user, "client_portal_enabled", False) and getattr(user, "client_id", None):
                return user.client_id
        except (TypeError, ValueError):
            pass
    return None


@socketio.on("join_client_room")
def handle_join_client_room(data):
    """Join client portal room for real-time notifications. Client identity from session."""
    client_id = _get_client_id_from_session()
    if client_id is None:
        return
    room = f"client_portal_{client_id}"
    socketio.join_room(room)


@socketio.on("leave_client_room")
def handle_leave_client_room(data):
    """Leave client portal room."""
    client_id = _get_client_id_from_session()
    if client_id is not None:
        socketio.leave_room(f"client_portal_{client_id}")
