"""SCIM 2.0 API scaffolding (Users list stub).

See docs/design/SAML_SCIM.md. Blueprint is registered only when SCIM_ENABLED is true.
"""

from __future__ import annotations

from flask import Blueprint, current_app, jsonify, request

api_scim_bp = Blueprint("api_scim", __name__)

SCIM_LIST_RESPONSE = "urn:ietf:params:scim:api:messages:2.0:ListResponse"
SCIM_JSON = "application/scim+json"


def _scim_auth_ok() -> bool:
    """Placeholder bearer auth until full SCIM token management exists."""
    expected = (current_app.config.get("SCIM_BEARER_TOKEN") or "").strip()
    if not expected:
        return False
    auth = request.headers.get("Authorization") or ""
    if not auth.lower().startswith("bearer "):
        return False
    token = auth[7:].strip()
    return token == expected


def _scim_unauthorized():
    return jsonify({"schemas": ["urn:ietf:params:scim:api:messages:2.0:Error"], "detail": "Unauthorized"}), 401


@api_scim_bp.route("/scim/v2/Users", methods=["GET"])
def scim_list_users():
    """Return an empty SCIM ListResponse (provisioning not implemented yet)."""
    if not _scim_auth_ok():
        return _scim_unauthorized()

    start_index = max(1, int(request.args.get("startIndex", 1)))
    count = max(0, int(request.args.get("count", 100)))

    body = {
        "schemas": [SCIM_LIST_RESPONSE],
        "totalResults": 0,
        "startIndex": start_index,
        "itemsPerPage": 0,
        "Resources": [],
    }
    if count == 0:
        body["itemsPerPage"] = 0
    return jsonify(body), 200, {"Content-Type": SCIM_JSON}
