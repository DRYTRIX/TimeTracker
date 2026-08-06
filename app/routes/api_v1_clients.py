"""
API v1 - Clients sub-blueprint.
Routes under /api/v1/clients.
"""

from flask import Blueprint, current_app, g, jsonify, request
from flask_login import current_user

from app.models import Client
from app.routes.api_v1_common import _require_module_enabled_for_api
from app.utils.api_auth import authenticate_token, extract_token_from_request, require_api_token
from app.utils.api_responses import error_response, forbidden_response, validation_error_response

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
    per_page = min(request.args.get("per_page", 50, type=int), 100)
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
    from app.utils.scope_filter import user_can_access_client

    client = Client.query.filter_by(id=client_id).first_or_404()
    if not user_can_access_client(g.api_user, client_id):
        return forbidden_response("You do not have access to this client")
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
        return validation_error_response(
            errors={"name": ["Client name is required"]},
            message="Client name is required",
        )
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
        return error_response(result.get("message", "Could not create client"), status_code=400)
    return jsonify({"message": "Client created successfully", "client": result["client"].to_dict()}), 201


def _resolve_actor_for_invoice_unbilled():
    """
    API token (write:invoices) or logged-in web user (create_invoices / admin).
    Sets g.api_user for module checks. Returns (user, None) or (None, response_tuple).
    """
    token_string = extract_token_from_request()
    if token_string:
        user, api_token, error_msg = authenticate_token(token_string, record_usage=False)
        if not user or not api_token:
            message = error_msg or "The provided API token is invalid or expired"
            return None, (
                jsonify({"error": "Invalid token", "message": message, "error_code": "unauthorized"}),
                401,
            )
        if not api_token.has_scope("write:invoices"):
            return None, (
                jsonify(
                    {
                        "error": "Insufficient permissions",
                        "message": 'This endpoint requires scope "write:invoices"',
                        "error_code": "forbidden",
                    }
                ),
                403,
            )
        try:
            from app.utils.api_rate_limit import consume_api_token_rate_limit

            allowed, rl_info = consume_api_token_rate_limit(api_token.id)
            if not allowed:
                retry_after = int(rl_info.get("retry_after_seconds") or 60)
                resp = jsonify(
                    {
                        "error": "Rate limit exceeded",
                        "message": "Too many requests for this API token. Try again later.",
                        "error_code": "rate_limited",
                    }
                )
                resp.status_code = 429
                resp.headers["Retry-After"] = str(retry_after)
                return None, (resp, resp.status_code)
        except Exception as e:
            current_app.logger.warning("API token rate limit check failed (allowing request): %s", e)
        try:
            api_token.record_usage(request.remote_addr)
        except Exception as e:
            current_app.logger.warning("Failed to record API token usage: %s", e)
        g.api_user = user
        g.api_token = api_token
        return user, None

    if getattr(current_user, "is_authenticated", False):
        if not (current_user.is_admin or current_user.has_permission("create_invoices")):
            return None, (
                jsonify(
                    {
                        "error": "forbidden",
                        "message": "You do not have permission to create invoices.",
                        "error_code": "forbidden",
                    }
                ),
                403,
            )
        g.api_user = current_user
        return current_user, None

    return None, (
        jsonify(
            {
                "error": "Authentication required",
                "message": "API token or login session required.",
                "error_code": "unauthorized",
            }
        ),
        401,
    )


@api_v1_clients_bp.route("/clients/<int:client_id>/invoice-unbilled", methods=["POST"])
def post_client_invoice_unbilled(client_id):
    """Create a draft invoice from all unbilled billable time for this client (grouped by project)."""
    user, err = _resolve_actor_for_invoice_unbilled()
    if err:
        body, code = err
        return body, code

    for module_id in ("clients", "invoices"):
        blocked = _require_module_enabled_for_api(module_id)
        if blocked:
            return blocked

    from app.utils.scope_filter import user_can_access_client

    client = Client.query.get(client_id)
    if not client:
        return jsonify({"error": "not_found", "message": "Client not found"}), 404
    if not user_can_access_client(user, client_id):
        return forbidden_response("You do not have access to this client")

    from app.services import InvoiceService

    result = InvoiceService().create_client_unbilled_invoice(client_id, acting_user_id=user.id)
    if not result.get("success"):
        err = result.get("error", "unknown")
        if err == "not_found":
            return jsonify({"error": "not_found", "message": result.get("message", "Not found")}), 404
        return (
            jsonify(
                {
                    "error": err,
                    "message": result.get("message", "Cannot create invoice."),
                }
            ),
            400,
        )

    return (
        jsonify(
            {
                "invoice_id": result["invoice_id"],
                "invoice_number": result["invoice_number"],
                "total": result["total"],
                "item_count": result["item_count"],
            }
        ),
        200,
    )


@api_v1_clients_bp.route("/clients/<int:client_id>", methods=["PUT", "PATCH"])
@require_api_token("write:clients")
def update_client_api(client_id):
    """Update a client — restores the pre-5.9 token-API update and adds custom_fields.

    the v5.9+ per-resource API refactor dropped client update;
    needed for Peppol recipient ids (custom_fields.peppol_endpoint_id/scheme_id).
    """
    blocked = _require_module_enabled_for_api("clients")
    if blocked:
        return blocked
    from decimal import Decimal

    from app.services import ClientService

    data = request.get_json() or {}
    allowed = {}
    for field in ("name", "email", "company", "phone", "address"):
        if field in data:
            allowed[field] = data[field]
    if data.get("default_hourly_rate") is not None:
        allowed["default_hourly_rate"] = Decimal(str(data["default_hourly_rate"]))
    if data.get("custom_fields") is not None:
        allowed["custom_fields"] = data["custom_fields"]
    if not allowed:
        return validation_error_response(
            errors={"body": ["No updatable fields provided"]},
            message="No updatable fields provided",
        )
    result = ClientService().update_client(client_id, g.api_user.id, **allowed)
    if not result.get("success"):
        status = 404 if result.get("error") == "not_found" else 400
        return error_response(result.get("message", "Could not update client"), status_code=status)
    return jsonify({"message": "Client updated successfully", "client": result["client"].to_dict()})
