"""REST API v1 endpoints for workday sessions."""

from flask import g, request

from app.routes.api_v1 import api_v1_bp
from app.services.workday_session_service import WorkdaySessionService
from app.utils.api_auth import require_api_token
from app.utils.api_responses import error_response, success_response


@api_v1_bp.route("/workday/status", methods=["GET"])
@require_api_token("read:time_entries")
def api_workday_status():
    session = WorkdaySessionService().get_active_session(g.api_user.id)
    return success_response(
        data={
            "active": session is not None,
            "session": session.to_dict() if session else None,
        }
    )


@api_v1_bp.route("/workday/start", methods=["POST"])
@require_api_token("write:time_entries")
def api_workday_start():
    data = request.get_json(silent=True) or {}
    notes = (data.get("notes") or "").strip() or None
    source = (data.get("source") or "mobile").strip() or "mobile"

    result = WorkdaySessionService().start_workday(g.api_user.id, notes=notes, source=source)
    if not result["success"]:
        return error_response(
            message=result.get("message", "Could not start workday"),
            status_code=400,
            error_code=result.get("error"),
        )
    return success_response(
        data={"session": result["session"].to_dict()},
        message=result["message"],
    )


@api_v1_bp.route("/workday/end", methods=["POST"])
@require_api_token("write:time_entries")
def api_workday_end():
    from app.services.workday_session_service import parse_workday_end_time

    data = request.get_json(silent=True) or {}
    notes = (data.get("notes") or "").strip() or None
    end_raw = data.get("end_time") or data.get("at_time")
    at_time = None
    if end_raw:
        at_time = parse_workday_end_time(str(end_raw))
        if at_time is None:
            return error_response(
                message="Invalid leave time",
                status_code=400,
                error_code="invalid_end_time",
            )

    result = WorkdaySessionService().end_workday(g.api_user.id, notes=notes, at_time=at_time)
    if not result["success"]:
        return error_response(
            message=result.get("message", "Could not end workday"),
            status_code=400,
            error_code=result.get("error"),
        )
    return success_response(
        data={"session": result["session"].to_dict()},
        message=result["message"],
    )
