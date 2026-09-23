"""REST API v1 endpoints for audit logs."""

from flask import jsonify, request

from app.models import AuditLog
from app.routes.api_v1 import api_v1_bp
from app.utils.api_auth import require_api_token


@api_v1_bp.route("/audit-logs", methods=["GET"])
@require_api_token("admin:all")
def list_audit_logs():
    """List audit logs (admin)"""
    entity_type = request.args.get("entity_type")
    user_id = request.args.get("user_id", type=int)
    action = request.args.get("action")
    limit = request.args.get("limit", type=int) or 100
    q = AuditLog.query
    if entity_type:
        q = q.filter(AuditLog.entity_type == entity_type)
    if user_id:
        q = q.filter(AuditLog.user_id == user_id)
    if action:
        q = q.filter(AuditLog.action == action)
    logs = q.order_by(AuditLog.created_at.desc()).limit(limit).all()
    return jsonify({"audit_logs": [l.to_dict() for l in logs]})
