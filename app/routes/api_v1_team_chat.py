"""API v1 - Team chat channels and messages."""

from flask import Blueprint, g, jsonify, request

from app.services.team_chat_service import TeamChatService
from app.utils.api_auth import require_api_token
from app.utils.api_responses import error_response, not_found_response, validation_error_response

api_v1_team_chat_bp = Blueprint("api_v1_team_chat", __name__, url_prefix="/api/v1")
_chat = TeamChatService()


@api_v1_team_chat_bp.route("/team-chat/channels", methods=["GET"])
@require_api_token("read:projects")
def list_channels():
    channels = _chat.list_channels_for_user(g.api_user.id)
    return jsonify({"channels": [_chat.serialize_channel(c) for c in channels]})


@api_v1_team_chat_bp.route("/team-chat/channels", methods=["POST"])
@require_api_token("write:projects")
def create_channel():
    data = request.get_json() or {}
    name = (data.get("name") or "").strip()
    if not name:
        return validation_error_response({"name": ["Required"]})
    channel = _chat.create_channel(
        name=name,
        created_by=g.api_user.id,
        description=(data.get("description") or None),
        channel_type=data.get("channel_type") or "public",
        project_id=data.get("project_id"),
        member_ids=data.get("member_ids") or [],
    )
    return jsonify({"channel": _chat.serialize_channel(channel)}), 201


@api_v1_team_chat_bp.route("/team-chat/channels/<int:channel_id>/messages", methods=["GET"])
@require_api_token("read:projects")
def list_messages(channel_id):
    channel = _chat.get_channel(channel_id)
    if not channel:
        return not_found_response("Channel not found")
    if not _chat.user_can_access_channel(channel_id, g.api_user.id, is_admin=g.api_user.is_admin):
        return error_response("Access denied", error_code="forbidden", status_code=403)

    before_id = request.args.get("before_id", type=int)
    limit = request.args.get("limit", 50, type=int)
    messages = _chat.list_messages(channel_id, before_id=before_id, limit=limit or 50)
    _chat.mark_messages_read(messages, g.api_user.id)
    return jsonify({"messages": [_chat.serialize_message(m) for m in messages]})


@api_v1_team_chat_bp.route("/team-chat/channels/<int:channel_id>/messages", methods=["POST"])
@require_api_token("write:projects")
def post_message(channel_id):
    channel = _chat.get_channel(channel_id)
    if not channel:
        return not_found_response("Channel not found")
    if not _chat.user_can_access_channel(channel_id, g.api_user.id, is_admin=g.api_user.is_admin):
        return error_response("Access denied", error_code="forbidden", status_code=403)

    data = request.get_json() or {}
    text = (data.get("message") or "").strip()
    if not text and not data.get("attachment_url"):
        return validation_error_response({"message": ["Message cannot be empty"]})

    message = _chat.post_message(
        channel_id,
        g.api_user.id,
        message=text,
        message_type=data.get("message_type") or ("file" if data.get("attachment_url") else "text"),
        reply_to_id=data.get("reply_to_id"),
        attachment_url=data.get("attachment_url"),
        attachment_filename=data.get("attachment_filename"),
        attachment_size=data.get("attachment_size"),
    )
    if message.mentions:
        _chat.notify_mentions(channel, g.api_user.display_name, message.mentions)
    return jsonify({"message": _chat.serialize_message(message)}), 201
