"""SCIM 2.0 Users API (RFC 7643 / 7644).

See docs/design/SAML_SCIM.md. Blueprint is registered only when SCIM_ENABLED is true.
"""

from __future__ import annotations

import re

from flask import Blueprint, current_app, jsonify, request

from app import db
from app.models import AuditLog, Role, User
from app.utils.db import safe_commit

api_scim_bp = Blueprint("api_scim", __name__)

SCIM_LIST_RESPONSE = "urn:ietf:params:scim:api:messages:2.0:ListResponse"
SCIM_ERROR = "urn:ietf:params:scim:api:messages:2.0:Error"
SCIM_USER = "urn:ietf:params:scim:schemas:core:2.0:User"
SCIM_PATCH_OP = "urn:ietf:params:scim:api:messages:2.0:PatchOp"
SCIM_JSON = "application/scim+json"

_FILTER_USERNAME = re.compile(r'userName\s+eq\s+"([^"]+)"', re.I)
_FILTER_EXTERNAL = re.compile(r'externalId\s+eq\s+"([^"]+)"', re.I)


def _scim_auth_ok() -> bool:
    expected = (current_app.config.get("SCIM_BEARER_TOKEN") or "").strip()
    # Optional Settings override (hashed comparison not required for env token)
    if not expected:
        try:
            from app.models import Settings

            settings = Settings.get_settings()
            expected = (getattr(settings, "scim_bearer_token", None) or "").strip()
        except Exception:
            expected = ""
    if not expected:
        return False
    auth = request.headers.get("Authorization") or ""
    if not auth.lower().startswith("bearer "):
        return False
    token = auth[7:].strip()
    return token == expected


def _scim_unauthorized():
    return (
        jsonify({"schemas": [SCIM_ERROR], "detail": "Unauthorized", "status": "401"}),
        401,
        {"Content-Type": SCIM_JSON},
    )


def _scim_error(detail: str, status: int = 400):
    return (
        jsonify({"schemas": [SCIM_ERROR], "detail": detail, "status": str(status)}),
        status,
        {"Content-Type": SCIM_JSON},
    )


def _split_name(full_name: str | None) -> tuple[str, str, str]:
    full_name = (full_name or "").strip()
    if not full_name:
        return "", "", ""
    parts = full_name.split(None, 1)
    given = parts[0]
    family = parts[1] if len(parts) > 1 else ""
    return full_name, given, family


def _user_to_scim(user: User) -> dict:
    formatted, given, family = _split_name(user.full_name)
    return {
        "schemas": [SCIM_USER],
        "id": str(user.id),
        "externalId": user.scim_external_id,
        "userName": user.username,
        "name": {
            "formatted": formatted or user.username,
            "givenName": given,
            "familyName": family,
        },
        "displayName": formatted or user.username,
        "emails": ([{"value": user.email, "type": "work", "primary": True}] if user.email else []),
        "active": bool(user.is_active),
        "meta": {
            "resourceType": "User",
            "created": user.created_at.isoformat() + "Z" if user.created_at else None,
            "lastModified": (user.last_login or user.created_at).isoformat() + "Z"
            if (user.last_login or user.created_at)
            else None,
            "location": f"/scim/v2/Users/{user.id}",
        },
    }


def _parse_name_from_scim(data: dict) -> str | None:
    name = data.get("name") or {}
    if isinstance(name, dict):
        formatted = (name.get("formatted") or "").strip()
        if formatted:
            return formatted
        given = (name.get("givenName") or "").strip()
        family = (name.get("familyName") or "").strip()
        joined = " ".join(p for p in [given, family] if p).strip()
        return joined or None
    return None


def _parse_email_from_scim(data: dict) -> str | None:
    emails = data.get("emails") or []
    if not isinstance(emails, list):
        return None
    primary = None
    work = None
    first = None
    for e in emails:
        if not isinstance(e, dict):
            continue
        val = (e.get("value") or "").strip().lower()
        if not val:
            continue
        if first is None:
            first = val
        if e.get("primary"):
            primary = val
        if (e.get("type") or "").lower() == "work":
            work = val
    return primary or work or first


def _audit(action: str, user: User, description: str):
    try:
        AuditLog.log_change(
            user_id=None,
            action=action,
            entity_type="user",
            entity_id=user.id,
            entity_name=user.username,
            change_description=description,
            ip_address=request.remote_addr,
            user_agent=request.headers.get("User-Agent"),
            request_path=request.path,
        )
    except Exception:
        current_app.logger.debug("SCIM audit log failed", exc_info=True)


# ---------------------------------------------------------------------------
# Discovery
# ---------------------------------------------------------------------------


@api_scim_bp.route("/scim/v2/ServiceProviderConfig", methods=["GET"])
def service_provider_config():
    if not _scim_auth_ok():
        return _scim_unauthorized()
    body = {
        "schemas": ["urn:ietf:params:scim:schemas:core:2.0:ServiceProviderConfig"],
        "documentationUri": "https://github.com/",
        "patch": {"supported": True},
        "bulk": {"supported": False, "maxOperations": 0, "maxPayloadSize": 0},
        "filter": {"supported": True, "maxResults": 200},
        "changePassword": {"supported": False},
        "sort": {"supported": False},
        "etag": {"supported": False},
        "authenticationSchemes": [
            {
                "type": "oauthbearertoken",
                "name": "OAuth Bearer Token",
                "description": "Authentication via SCIM_BEARER_TOKEN",
                "specUri": "https://tools.ietf.org/html/rfc6750",
                "primary": True,
            }
        ],
    }
    return jsonify(body), 200, {"Content-Type": SCIM_JSON}


@api_scim_bp.route("/scim/v2/ResourceTypes", methods=["GET"])
def resource_types():
    if not _scim_auth_ok():
        return _scim_unauthorized()
    body = {
        "schemas": [SCIM_LIST_RESPONSE],
        "totalResults": 1,
        "Resources": [
            {
                "schemas": ["urn:ietf:params:scim:schemas:core:2.0:ResourceType"],
                "id": "User",
                "name": "User",
                "endpoint": "/scim/v2/Users",
                "description": "User Account",
                "schema": SCIM_USER,
                "schemaExtensions": [],
            }
        ],
    }
    return jsonify(body), 200, {"Content-Type": SCIM_JSON}


@api_scim_bp.route("/scim/v2/Schemas", methods=["GET"])
def schemas():
    if not _scim_auth_ok():
        return _scim_unauthorized()
    body = {
        "schemas": [SCIM_LIST_RESPONSE],
        "totalResults": 1,
        "Resources": [
            {
                "id": SCIM_USER,
                "name": "User",
                "description": "User Account",
                "attributes": [
                    {"name": "userName", "type": "string", "required": True, "uniqueness": "server"},
                    {"name": "externalId", "type": "string", "required": False},
                    {"name": "active", "type": "boolean", "required": False},
                    {
                        "name": "name",
                        "type": "complex",
                        "subAttributes": [
                            {"name": "formatted", "type": "string"},
                            {"name": "givenName", "type": "string"},
                            {"name": "familyName", "type": "string"},
                        ],
                    },
                    {
                        "name": "emails",
                        "type": "complex",
                        "multiValued": True,
                        "subAttributes": [
                            {"name": "value", "type": "string"},
                            {"name": "type", "type": "string"},
                            {"name": "primary", "type": "boolean"},
                        ],
                    },
                ],
            }
        ],
    }
    return jsonify(body), 200, {"Content-Type": SCIM_JSON}


# ---------------------------------------------------------------------------
# Users CRUD
# ---------------------------------------------------------------------------


@api_scim_bp.route("/scim/v2/Users", methods=["GET"])
def scim_list_users():
    if not _scim_auth_ok():
        return _scim_unauthorized()

    start_index = max(1, int(request.args.get("startIndex", 1) or 1))
    count = max(0, min(200, int(request.args.get("count", 100) or 100)))
    filter_expr = (request.args.get("filter") or "").strip()

    q = User.query
    if filter_expr:
        m = _FILTER_USERNAME.search(filter_expr)
        if m:
            q = q.filter(User.username == m.group(1))
        m = _FILTER_EXTERNAL.search(filter_expr)
        if m:
            q = q.filter(User.scim_external_id == m.group(1))

    total = q.count()
    if count == 0:
        resources = []
    else:
        resources = q.order_by(User.id.asc()).offset(start_index - 1).limit(count).all()

    body = {
        "schemas": [SCIM_LIST_RESPONSE],
        "totalResults": total,
        "startIndex": start_index,
        "itemsPerPage": len(resources),
        "Resources": [_user_to_scim(u) for u in resources],
    }
    return jsonify(body), 200, {"Content-Type": SCIM_JSON}


@api_scim_bp.route("/scim/v2/Users/<user_id>", methods=["GET"])
def scim_get_user(user_id: str):
    if not _scim_auth_ok():
        return _scim_unauthorized()
    try:
        uid = int(user_id)
    except (TypeError, ValueError):
        return _scim_error("User not found", 404)
    user = User.query.get(uid)
    if not user:
        return _scim_error("User not found", 404)
    return jsonify(_user_to_scim(user)), 200, {"Content-Type": SCIM_JSON}


@api_scim_bp.route("/scim/v2/Users", methods=["POST"])
def scim_create_user():
    if not _scim_auth_ok():
        return _scim_unauthorized()
    data = request.get_json(silent=True) or {}
    username = (data.get("userName") or "").strip().lower()
    if not username:
        return _scim_error("userName is required", 400)
    if User.query.filter_by(username=username).first():
        return _scim_error("userName already exists", 409)

    email = _parse_email_from_scim(data)
    full_name = _parse_name_from_scim(data)
    external_id = (data.get("externalId") or "").strip() or None
    active = data.get("active", True)
    if active is None:
        active = True

    user = User(username=username, email=email, full_name=full_name, role="user")
    user.is_active = bool(active)
    user.auth_provider = "scim"
    user.scim_external_id = external_id
    role_obj = Role.query.filter_by(name="user").first()
    if role_obj:
        user.roles.append(role_obj)
    db.session.add(user)
    if not safe_commit("scim_create_user", {"username": username}):
        return _scim_error("Failed to create user", 500)
    _audit("created", user, "SCIM user created")
    return jsonify(_user_to_scim(user)), 201, {"Content-Type": SCIM_JSON}


def _apply_user_fields(user: User, data: dict) -> None:
    if "userName" in data and data["userName"]:
        user.username = str(data["userName"]).strip().lower()
    if "externalId" in data:
        val = data.get("externalId")
        user.scim_external_id = (str(val).strip() if val else None)
    if "active" in data and data["active"] is not None:
        user.is_active = bool(data["active"])
    name = _parse_name_from_scim(data)
    if name is not None and ("name" in data):
        user.full_name = name
    if "emails" in data:
        email = _parse_email_from_scim(data)
        user.email = email


@api_scim_bp.route("/scim/v2/Users/<user_id>", methods=["PUT"])
def scim_replace_user(user_id: str):
    if not _scim_auth_ok():
        return _scim_unauthorized()
    try:
        uid = int(user_id)
    except (TypeError, ValueError):
        return _scim_error("User not found", 404)
    user = User.query.get(uid)
    if not user:
        return _scim_error("User not found", 404)
    data = request.get_json(silent=True) or {}
    _apply_user_fields(user, data)
    if not safe_commit("scim_replace_user", {"user_id": user.id}):
        return _scim_error("Failed to update user", 500)
    _audit("updated", user, "SCIM user replaced")
    return jsonify(_user_to_scim(user)), 200, {"Content-Type": SCIM_JSON}


@api_scim_bp.route("/scim/v2/Users/<user_id>", methods=["PATCH"])
def scim_patch_user(user_id: str):
    if not _scim_auth_ok():
        return _scim_unauthorized()
    try:
        uid = int(user_id)
    except (TypeError, ValueError):
        return _scim_error("User not found", 404)
    user = User.query.get(uid)
    if not user:
        return _scim_error("User not found", 404)

    data = request.get_json(silent=True) or {}
    ops = data.get("Operations") or data.get("operations") or []
    for op in ops:
        if not isinstance(op, dict):
            continue
        kind = (op.get("op") or "").lower()
        path = (op.get("path") or "").strip()
        value = op.get("value")

        if kind in ("replace", "add"):
            if path.lower() == "active" or (not path and isinstance(value, dict) and "active" in value):
                active_val = value if path.lower() == "active" else value.get("active")
                user.is_active = bool(active_val)
            elif path.lower() in ("name.formatted", "name.givenname", "name.familyname") or (
                not path and isinstance(value, dict) and "name" in value
            ):
                if path.lower() == "name.formatted":
                    user.full_name = str(value or "").strip() or user.full_name
                elif path.lower() == "name.givenname":
                    _, _, family = _split_name(user.full_name)
                    user.full_name = " ".join(p for p in [str(value or "").strip(), family] if p)
                elif path.lower() == "name.familyname":
                    formatted, given, _ = _split_name(user.full_name)
                    user.full_name = " ".join(p for p in [given, str(value or "").strip()] if p)
                else:
                    name = _parse_name_from_scim(value if isinstance(value, dict) else {"name": value})
                    if name:
                        user.full_name = name
            elif path.lower().startswith("emails") or (not path and isinstance(value, dict) and "emails" in value):
                if path.lower() == "emails" and isinstance(value, list):
                    email = _parse_email_from_scim({"emails": value})
                    user.email = email
                elif isinstance(value, dict) and "emails" in value:
                    user.email = _parse_email_from_scim(value)
                elif isinstance(value, str):
                    user.email = value.strip().lower() or None
            elif not path and isinstance(value, dict):
                _apply_user_fields(user, value)

    deactivated = not user.is_active
    if not safe_commit("scim_patch_user", {"user_id": user.id}):
        return _scim_error("Failed to patch user", 500)
    _audit("updated" if not deactivated else "updated", user, "SCIM user patched" + (" (deactivated)" if deactivated and not user.is_active else ""))
    return jsonify(_user_to_scim(user)), 200, {"Content-Type": SCIM_JSON}


@api_scim_bp.route("/scim/v2/Users/<user_id>", methods=["DELETE"])
def scim_delete_user(user_id: str):
    if not _scim_auth_ok():
        return _scim_unauthorized()
    try:
        uid = int(user_id)
    except (TypeError, ValueError):
        return _scim_error("User not found", 404)
    user = User.query.get(uid)
    if not user:
        return _scim_error("User not found", 404)
    user.is_active = False
    if not safe_commit("scim_deactivate_user", {"user_id": user.id}):
        return _scim_error("Failed to deactivate user", 500)
    _audit("updated", user, "SCIM user deactivated (DELETE)")
    return "", 204
