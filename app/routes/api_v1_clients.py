"""
API v1 - Clients sub-blueprint.
Routes under /api/v1/clients.
"""

from flask import Blueprint, jsonify, request, g
from app.models import Client
from app.utils.api_auth import require_api_token
from app.routes.api_v1_common import _require_module_enabled_for_api

api_v1_clients_bp = Blueprint("api_v1_clients", __name__, url_prefix="/api/v1")


@api_v1_clients_bp.route("/clients", methods=["GET"])
@require_api_token("read:clients")
def list_clients():
    """List all clients."""
    blocked = _require_module_enabled_for_api("clients")
    if blocked:
        return blocked
    from app.repositories import ClientRepository
    from app.utils.scope_filter import apply_client_scope_to_model

    page = request.args.get("page", 1, type=int)
    per_page = request.args.get("per_page", 50, type=int)
    client_repo = ClientRepository()
    query = client_repo.query().order_by(Client.name)
    scope = apply_client_scope_to_model(Client, g.api_user)
    if scope is not None:
        query = query.filter(scope)
    pagination = query.paginate(page=page, per_page=per_page, error_out=False)
    pagination_dict = {
        "page": pagination.page,
        "per_page": pagination.per_page,
        "total": pagination.total,
        "pages": pagination.pages,
        "has_next": pagination.has_next,
        "has_prev": pagination.has_prev,
        "next_page": pagination.page + 1 if pagination.has_next else None,
        "prev_page": pagination.page - 1 if pagination.has_prev else None,
    }
    return jsonify({"clients": [c.to_dict() for c in pagination.items], "pagination": pagination_dict})


@api_v1_clients_bp.route("/clients/<int:client_id>", methods=["GET"])
@require_api_token("read:clients")
def get_client(client_id):
    """Get a specific client."""
    blocked = _require_module_enabled_for_api("clients")
    if blocked:
        return blocked
    from sqlalchemy.orm import joinedload
    from app.utils.scope_filter import user_can_access_client

    client = Client.query.options(joinedload(Client.projects)).filter_by(id=client_id).first_or_404()
    if not user_can_access_client(g.api_user, client_id):
        return jsonify({"error": "Access denied", "message": "You do not have access to this client"}), 403
    return jsonify({"client": client.to_dict()})


@api_v1_clients_bp.route("/clients", methods=["POST"])
@require_api_token("write:clients")
def create_client():
    """Create a new client."""
    blocked = _require_module_enabled_for_api("clients")
    if blocked:
        return blocked
    from decimal import Decimal
    from app.services import ClientService

    data = request.get_json() or {}
    if not data.get("name"):
        return jsonify({"error": "Client name is required"}), 400
    client_service = ClientService()
    result = client_service.create_client(
        name=data["name"],
        created_by=g.api_user.id,
        email=data.get("email"),
        company=data.get("company"),
        phone=data.get("phone"),
        address=data.get("address"),
        default_hourly_rate=Decimal(str(data["default_hourly_rate"])) if data.get("default_hourly_rate") else None,
        custom_fields=data.get("custom_fields"),
    )
    if not result.get("success"):
        return jsonify({"error": result.get("message", "Could not create client")}), 400
    return jsonify({"message": "Client created successfully", "client": result["client"].to_dict()}), 201
