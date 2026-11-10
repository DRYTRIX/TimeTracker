"""Shared chat slash-command handlers for Slack / Teams timer bots."""

from __future__ import annotations

from typing import Any


def handle_timer_command(user, text: str) -> dict[str, Any]:
    """Dispatch ``start|stop|status|today`` for a linked TimeTracker user.

    Args:
        user: Authenticated :class:`~app.models.user.User` (must have ``id``).
        text: Raw command text (without leading slash), e.g. ``\"start My Project\"``.

    Returns:
        ``{\"text\": str}`` reply payload suitable for Slack ephemeral or Teams message.
    """
    raw_text = (text or "").strip()
    parts = raw_text.split(None, 1)
    subcommand = (parts[0] or "").lower() if parts else ""
    argument = parts[1] if len(parts) > 1 else ""

    if subcommand == "start":
        return _cmd_start(user, argument)
    if subcommand == "stop":
        return _cmd_stop(user)
    if subcommand == "status":
        return _cmd_status(user)
    if subcommand == "today":
        return _cmd_today(user)
    return {
        "text": (
            "Available commands:\n"
            "• `start <project>` — start a timer\n"
            "• `stop` — stop the active timer\n"
            "• `status` — show the current timer\n"
            "• `today` — today's hours summary"
        )
    }


def _cmd_start(user, argument: str) -> dict[str, Any]:
    from app.models import Project
    from app.services.time_tracking_service import TimeTrackingService

    argument = (argument or "").strip()
    if not argument:
        return {"text": "Usage: `start <project name or ID>`"}

    project = None
    try:
        project = Project.query.get(int(argument))
    except (TypeError, ValueError):
        project = None
    if not project:
        project = Project.query.filter(Project.name.ilike(f"%{argument}%")).first()
    if not project:
        return {"text": f"Project not found: `{argument}`"}

    result = TimeTrackingService().start_timer(user_id=user.id, project_id=project.id)
    if result.get("success"):
        return {"text": f"Timer started for *{project.name}*."}
    return {"text": f"Could not start timer: {result.get('message') or 'unknown error'}"}


def _cmd_stop(user) -> dict[str, Any]:
    from app.services.time_tracking_service import TimeTrackingService

    result = TimeTrackingService().stop_timer(user_id=user.id)
    if result.get("success"):
        entry = result.get("entry")
        duration = getattr(entry, "duration_formatted", "")
        return {"text": f"Timer stopped (duration {duration})."}
    return {"text": f"Could not stop timer: {result.get('message') or 'no active timer'}"}


def _cmd_status(user) -> dict[str, Any]:
    active = getattr(user, "active_timer", None)
    if not active:
        return {"text": "No active timer."}
    project_name = active.project.name if getattr(active, "project", None) else "—"
    return {"text": f"Active timer on *{project_name}* (running {active.duration_formatted})."}


def _cmd_today(user) -> dict[str, Any]:
    try:
        from app.services.notification_service import get_today_summary_for_user

        summary = get_today_summary_for_user(user)
    except Exception:
        import logging

        logging.getLogger(__name__).exception("Could not fetch today's summary for user_id=%s", getattr(user, "id", None))
        return {"text": "Could not fetch today's summary."}
    hours = summary.get("hours", 0)
    projects = summary.get("projects", 0)
    return {"text": f"Today: *{hours}h* across *{projects}* project(s)."}
