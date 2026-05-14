"""API v1 AI helper endpoints."""

from flask import Blueprint, g, jsonify, request

from app.services.llm_service import AIServiceError, LLMService
from app.utils.api_auth import require_api_token

api_v1_ai_bp = Blueprint("api_v1_ai", __name__, url_prefix="/api/v1")


def _ai_error_response(exc: AIServiceError):
    return (
        jsonify({"success": False, "error": exc.message, "message": exc.message, "error_code": exc.code}),
        exc.status_code,
    )


def _ai_disabled_response():
    msg = "AI helper is disabled"
    return (
        jsonify({"success": False, "error": msg, "message": msg, "error_code": "ai_disabled"}),
        503,
    )


@api_v1_ai_bp.route("/ai/context-preview", methods=["GET"])
@require_api_token("read:ai")
def ai_context_preview():
    try:
        service = LLMService()
        if not service.is_enabled():
            return _ai_disabled_response()
        return jsonify(
            {"success": True, "context": service.context_preview(g.api_user), "provider": service.config.public_dict()}
        )
    except AIServiceError as exc:
        return _ai_error_response(exc)


@api_v1_ai_bp.route("/ai/chat", methods=["POST"])
@require_api_token("write:ai")
def ai_chat():
    data = request.get_json(silent=True) or {}
    try:
        result = LLMService().chat(g.api_user, data.get("prompt") or "", data.get("history") or [])
        return jsonify({"success": True, **result})
    except AIServiceError as exc:
        return _ai_error_response(exc)


@api_v1_ai_bp.route("/ai/actions/confirm", methods=["POST"])
@require_api_token("write:ai")
def ai_confirm_action():
    data = request.get_json(silent=True) or {}
    try:
        service = LLMService()
        if not service.is_enabled():
            return _ai_disabled_response()
        result = service.confirm_action(g.api_user, data.get("action") or {})
        return jsonify({"success": True, **result})
    except AIServiceError as exc:
        return _ai_error_response(exc)
