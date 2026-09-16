"""REST API v1 endpoints for workday sessions."""

from typing import Any, Dict, Optional, Tuple

from flask import g, request

from app.routes.api_v1 import api_v1_bp
from app.services.geofence_service import GeofenceService
from app.services.workday_session_service import WorkdaySessionService
from app.utils.api_auth import require_api_token
from app.utils.api_responses import error_response, success_response


def _parse_optional_float(value: Any) -> Optional[float]:
    if value is None or value == "":
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _parse_location(data: dict) -> Tuple[Optional[float], Optional[float], Optional[float]]:
    latitude = _parse_optional_float(data.get("latitude"))
    longitude = _parse_optional_float(data.get("longitude"))
    accuracy_m = _parse_optional_float(data.get("accuracy_m"))
    return latitude, longitude, accuracy_m


def _geofence_payload(enforcement: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "action": enforcement.get("action"),
        "status": enforcement.get("geofence_status"),
        "geofence_id": enforcement.get("geofence_id"),
        "distance_m": enforcement.get("distance_m"),
        "message": enforcement.get("message"),
        "violation": enforcement.get("violation"),
    }


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
    latitude, longitude, accuracy_m = _parse_location(data)

    enforcement = GeofenceService().enforce_policy(g.api_user, latitude, longitude)
    if enforcement.get("action") == "block":
        return error_response(
            message=enforcement.get("message") or "Clock-in blocked by geofence policy",
            status_code=403,
            error_code="geofence_blocked",
            details=_geofence_payload(enforcement),
        )

    result = WorkdaySessionService().start_workday(
        g.api_user.id,
        notes=notes,
        source=source,
        latitude=latitude,
        longitude=longitude,
        accuracy_m=accuracy_m,
        geofence_enforcement=enforcement,
    )
    if not result["success"]:
        return error_response(
            message=result.get("message", "Could not start workday"),
            status_code=400,
            error_code=result.get("error"),
        )
    response_data = {"session": result["session"].to_dict()}
    if enforcement.get("action") == "warn":
        response_data["geofence"] = _geofence_payload(enforcement)
    return success_response(
        data=response_data,
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

    latitude, longitude, accuracy_m = _parse_location(data)
    active_session = WorkdaySessionService().get_active_session(g.api_user.id)

    enforcement = GeofenceService().enforce_policy(
        g.api_user,
        latitude,
        longitude,
        session=active_session,
    )
    if enforcement.get("action") == "block":
        return error_response(
            message=enforcement.get("message") or "Clock-out blocked by geofence policy",
            status_code=403,
            error_code="geofence_blocked",
            details=_geofence_payload(enforcement),
        )

    result = WorkdaySessionService().end_workday(
        g.api_user.id,
        notes=notes,
        at_time=at_time,
        latitude=latitude,
        longitude=longitude,
        accuracy_m=accuracy_m,
        geofence_enforcement=enforcement,
    )
    if not result["success"]:
        return error_response(
            message=result.get("message", "Could not end workday"),
            status_code=400,
            error_code=result.get("error"),
        )
    response_data = {"session": result["session"].to_dict()}
    if enforcement.get("action") == "warn":
        response_data["geofence"] = _geofence_payload(enforcement)
    return success_response(
        data=response_data,
        message=result["message"],
    )


@api_v1_bp.route("/workday/auto-closed/<int:session_id>/resolve", methods=["POST"])
@require_api_token("write:time_entries")
def api_resolve_auto_closed_workday(session_id):
    from app.services.workday_session_service import parse_workday_end_time

    data = request.get_json(silent=True) or {}
    keep = data.get("keep") in (True, 1, "1")
    reason = (data.get("reason") or "").strip() or None
    at_time = None
    if not keep:
        end_raw = data.get("end_time") or data.get("at_time")
        if end_raw:
            at_time = parse_workday_end_time(str(end_raw))
            if at_time is None:
                return error_response(
                    message="Invalid leave time",
                    status_code=400,
                    error_code="invalid_end_time",
                )

    result = WorkdaySessionService().resolve_auto_closed_session(
        g.api_user.id,
        session_id,
        end_time=at_time,
        keep=keep,
        reason=reason,
    )
    if not result["success"]:
        return error_response(
            message=result.get("message", "Could not resolve auto-closed workday"),
            status_code=400,
            error_code=result.get("error"),
        )

    from app.utils.cache import get_cache

    try:
        get_cache().delete(f"dashboard:stats:{g.api_user.id}")
    except Exception:
        pass

    return success_response(
        data={
            "session": result["session"].to_dict(),
            "applied": result.get("applied", False),
            "pending_review": result.get("pending_review", False),
            "already_resolved": result.get("already_resolved", False),
        },
        message=result["message"],
    )
