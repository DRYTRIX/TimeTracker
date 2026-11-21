"""OAuth 2.0 authorization server (authorization_code + PKCE, refresh, revoke).

Hand-rolled against existing OAuthApplication / OAuthAuthorizationCode /
OAuthAccessToken models. See docs/design/OAUTH2_API_APPS.md.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
from datetime import datetime
from urllib.parse import urlencode

from flask import Blueprint, current_app, jsonify, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from app import csrf, db, limiter
from app.models import OAuthAccessToken, OAuthApplication, OAuthAuthorizationCode
from app.utils.db import safe_commit
from app.utils.permissions import admin_or_permission_required
from app.utils.safe_redirect import match_registered_redirect

oauth_server_bp = Blueprint("oauth_server", __name__)


def _pkce_s256_challenge(verifier: str) -> str:
    digest = hashlib.sha256(verifier.encode("ascii")).digest()
    return base64.urlsafe_b64encode(digest).rstrip(b"=").decode("ascii")


def _verify_pkce(verifier: str, challenge: str, method: str | None) -> bool:
    method = (method or "S256").upper()
    if method != "S256":
        return False
    if not verifier or not challenge:
        return False
    computed = _pkce_s256_challenge(verifier)
    return hmac.compare_digest(computed, challenge)


def _intersect_scopes(requested: str, allowed: list[str]) -> str:
    req = [s.strip() for s in (requested or "").split() if s.strip()]
    if not req and allowed:
        return ",".join(allowed)
    if not allowed:
        return ",".join(req)
    allowed_set = set(allowed)
    granted = [s for s in req if s in allowed_set]
    return ",".join(granted)


def _authenticate_client() -> tuple[OAuthApplication | None, str | None]:
    """Resolve confidential/public client from Basic auth or form body."""
    client_id = None
    client_secret = None

    auth = request.headers.get("Authorization") or ""
    if auth.lower().startswith("basic "):
        try:
            decoded = base64.b64decode(auth[6:].strip()).decode("utf-8")
            client_id, _, client_secret = decoded.partition(":")
        except Exception:
            return None, "invalid_client"

    client_id = client_id or request.form.get("client_id") or (request.get_json(silent=True) or {}).get("client_id")
    client_secret = (
        client_secret or request.form.get("client_secret") or (request.get_json(silent=True) or {}).get("client_secret")
    )

    if not client_id:
        return None, "invalid_client"

    app_rec = OAuthApplication.query.filter_by(client_id=client_id, is_active=True).first()
    if not app_rec:
        return None, "invalid_client"

    if app_rec.is_confidential:
        if not client_secret or not app_rec.client_secret_hash:
            return None, "invalid_client"
        if not hmac.compare_digest(app_rec.client_secret_hash, OAuthApplication.hash_secret(client_secret)):
            return None, "invalid_client"

    return app_rec, None


def _form_or_json(key: str, default=None):
    if key in request.form:
        return request.form.get(key, default)
    data = request.get_json(silent=True) or {}
    return data.get(key, default)


# ---------------------------------------------------------------------------
# Authorization endpoint
# ---------------------------------------------------------------------------


@oauth_server_bp.route("/oauth/authorize", methods=["GET", "POST"])
@login_required
@limiter.limit("30 per minute")
def authorize():
    if request.method == "GET":
        client_id = request.args.get("client_id", "")
        redirect_uri = request.args.get("redirect_uri", "")
        response_type = request.args.get("response_type", "")
        scope = request.args.get("scope", "")
        state = request.args.get("state", "")
        code_challenge = request.args.get("code_challenge", "")
        code_challenge_method = request.args.get("code_challenge_method", "S256")

        app_rec = OAuthApplication.query.filter_by(client_id=client_id, is_active=True).first()
        if not app_rec:
            return render_template("oauth/authorize.html", error="Unknown or inactive client."), 400
        if response_type != "code":
            return render_template("oauth/authorize.html", error="Unsupported response_type."), 400
        if redirect_uri not in app_rec.redirect_uri_list():
            return render_template("oauth/authorize.html", error="redirect_uri mismatch."), 400
        if not code_challenge:
            return render_template("oauth/authorize.html", error="PKCE code_challenge is required."), 400
        if (code_challenge_method or "S256").upper() != "S256":
            return render_template("oauth/authorize.html", error="Only S256 PKCE is supported."), 400

        granted_scope = _intersect_scopes(scope, app_rec.scope_list())
        return render_template(
            "oauth/authorize.html",
            application=app_rec,
            client_id=client_id,
            redirect_uri=redirect_uri,
            scope=granted_scope,
            scope_list=[s for s in granted_scope.split(",") if s],
            state=state,
            code_challenge=code_challenge,
            code_challenge_method=code_challenge_method or "S256",
            error=None,
        )

    # POST — consent
    decision = (request.form.get("decision") or "").strip().lower()
    client_id = request.form.get("client_id", "")
    redirect_uri = request.form.get("redirect_uri", "")
    scope = request.form.get("scope", "")
    state = request.form.get("state", "")
    code_challenge = request.form.get("code_challenge", "")
    code_challenge_method = request.form.get("code_challenge_method", "S256")

    app_rec = OAuthApplication.query.filter_by(client_id=client_id, is_active=True).first()
    matched_redirect = match_registered_redirect(redirect_uri, app_rec.redirect_uri_list()) if app_rec else None
    if not app_rec or not matched_redirect:
        return render_template("oauth/authorize.html", error="Invalid authorization request."), 400

    if decision != "approve":
        params = {"error": "access_denied"}
        if state:
            params["state"] = state
        sep = "&" if "?" in matched_redirect else "?"
        # codeql[py/url-redirection]: matched_redirect is allowlisted registered URI
        return redirect(f"{matched_redirect}{sep}{urlencode(params)}")

    # Consent form may pass comma-separated scopes
    scope_for_intersect = scope.replace(",", " ")
    granted = _intersect_scopes(scope_for_intersect, app_rec.scope_list())
    if not granted and scope:
        granted = ",".join(s.strip() for s in scope.replace(" ", ",").split(",") if s.strip() in app_rec.scope_list())

    code_rec, plain_code = OAuthAuthorizationCode.create_code(
        application_id=app_rec.id,
        user_id=current_user.id,
        redirect_uri=matched_redirect,
        scope=granted,
        code_challenge=code_challenge,
        code_challenge_method=code_challenge_method or "S256",
    )
    db.session.add(code_rec)
    safe_commit("oauth_consent_granted", {"app_id": app_rec.id, "user_id": current_user.id})

    params = {"code": plain_code}
    if state:
        params["state"] = state
    sep = "&" if "?" in matched_redirect else "?"
    # codeql[py/url-redirection]: matched_redirect is allowlisted registered URI
    return redirect(f"{matched_redirect}{sep}{urlencode(params)}")


# ---------------------------------------------------------------------------
# Token endpoint
# ---------------------------------------------------------------------------


@oauth_server_bp.route("/oauth/token", methods=["POST"])
@csrf.exempt
@limiter.limit("60 per minute")
def token():
    app_rec, err = _authenticate_client()
    if err or not app_rec:
        return jsonify({"error": "invalid_client"}), 401

    grant_type = (_form_or_json("grant_type") or "").strip()

    if grant_type == "authorization_code":
        return _token_authorization_code(app_rec)
    if grant_type == "refresh_token":
        return _token_refresh(app_rec)

    return jsonify({"error": "unsupported_grant_type"}), 400


def _token_authorization_code(app_rec: OAuthApplication):
    code = (_form_or_json("code") or "").strip()
    redirect_uri = (_form_or_json("redirect_uri") or "").strip()
    code_verifier = (_form_or_json("code_verifier") or "").strip()

    if not code or not redirect_uri:
        return jsonify({"error": "invalid_request"}), 400

    code_rec = OAuthAuthorizationCode.query.filter_by(
        code_hash=OAuthAuthorizationCode.hash_code(code),
        application_id=app_rec.id,
    ).first()
    if not code_rec or not code_rec.is_valid():
        return jsonify({"error": "invalid_grant"}), 400
    if code_rec.redirect_uri != redirect_uri:
        return jsonify({"error": "invalid_grant"}), 400
    if not _verify_pkce(code_verifier, code_rec.code_challenge or "", code_rec.code_challenge_method):
        return jsonify({"error": "invalid_grant", "error_description": "PKCE verification failed"}), 400

    code_rec.used_at = datetime.utcnow()
    access_rec, plain_access, plain_refresh = OAuthAccessToken.create_token(
        application_id=app_rec.id,
        user_id=code_rec.user_id,
        scopes=code_rec.scope or "",
    )
    db.session.add(access_rec)
    safe_commit("oauth_token_issued", {"app_id": app_rec.id, "user_id": code_rec.user_id})

    body = {
        "access_token": plain_access,
        "token_type": "Bearer",
        "expires_in": max(0, int((access_rec.expires_at - datetime.utcnow()).total_seconds())),
        "scope": (access_rec.scopes or "").replace(",", " "),
    }
    if plain_refresh:
        body["refresh_token"] = plain_refresh
    return jsonify(body)


def _token_refresh(app_rec: OAuthApplication):
    refresh = (_form_or_json("refresh_token") or "").strip()
    if not refresh:
        return jsonify({"error": "invalid_request"}), 400

    refresh_hashes = OAuthAccessToken.lookup_hashes(refresh)
    existing = OAuthAccessToken.query.filter(
        OAuthAccessToken.refresh_token_hash.in_(refresh_hashes),
        OAuthAccessToken.application_id == app_rec.id,
    ).first()
    if not existing or existing.revoked_at is not None:
        return jsonify({"error": "invalid_grant"}), 400
    if existing.refresh_expires_at and existing.refresh_expires_at < datetime.utcnow():
        return jsonify({"error": "invalid_grant"}), 400

    # Rotate: revoke old access token, issue new pair
    existing.revoke()
    access_rec, plain_access, plain_refresh = OAuthAccessToken.create_token(
        application_id=app_rec.id,
        user_id=existing.user_id,
        scopes=existing.scopes or "",
    )
    db.session.add(access_rec)
    safe_commit("oauth_token_refreshed", {"app_id": app_rec.id, "user_id": existing.user_id})

    body = {
        "access_token": plain_access,
        "token_type": "Bearer",
        "expires_in": max(0, int((access_rec.expires_at - datetime.utcnow()).total_seconds())),
        "scope": (access_rec.scopes or "").replace(",", " "),
    }
    if plain_refresh:
        body["refresh_token"] = plain_refresh
    return jsonify(body)


# ---------------------------------------------------------------------------
# Revoke
# ---------------------------------------------------------------------------


@oauth_server_bp.route("/oauth/revoke", methods=["POST"])
@csrf.exempt
@limiter.limit("60 per minute")
def revoke():
    app_rec, err = _authenticate_client()
    # RFC 7009: also allow bearer token without client auth for public clients
    token_value = (_form_or_json("token") or "").strip()
    if not token_value:
        return jsonify({"error": "invalid_request"}), 400

    revoked = False
    token_hashes = OAuthAccessToken.lookup_hashes(token_value)
    if token_value.startswith("tto_"):
        rec = OAuthAccessToken.query.filter(OAuthAccessToken.token_hash.in_(token_hashes)).first()
        if rec and (app_rec is None or rec.application_id == app_rec.id):
            rec.revoke()
            revoked = True
    elif token_value.startswith("ttr_"):
        rec = OAuthAccessToken.query.filter(OAuthAccessToken.refresh_token_hash.in_(token_hashes)).first()
        if rec and (app_rec is None or rec.application_id == app_rec.id):
            rec.revoke()
            revoked = True

    if revoked:
        safe_commit("oauth_token_revoked", {})
    # RFC 7009: always 200
    return "", 200


# ---------------------------------------------------------------------------
# Metadata
# ---------------------------------------------------------------------------


# MCP OAuth scope presets (also documented in docs/integrations/MCP.md)
MCP_USER_SCOPES = (
    "read:users,read:projects,read:tasks,read:time_entries,write:time_entries,"
    "read:time_approvals,write:time_approvals"
)
MCP_ADMIN_SCOPES = (
    "read:users,read:projects,write:projects,read:tasks,write:tasks,"
    "read:time_entries,write:time_entries,read:clients,write:clients,"
    "read:invoices,write:invoices,read:quotes,write:quotes,"
    "read:expenses,write:expenses,read:reports,read:time_approvals,write:time_approvals"
)
MCP_ADMIN_READONLY_SCOPES = (
    "read:users,read:projects,read:tasks,read:time_entries,read:clients,"
    "read:invoices,read:quotes,read:expenses,read:reports,read:time_approvals"
)

# Limited DCR redirect URI allowlist (hostname / scheme prefixes)
_MCP_DCR_REDIRECT_ALLOW_PREFIXES = (
    "http://127.0.0.1",
    "http://localhost",
    "https://localhost",
    "https://claude.ai/",
    "https://claude.com/",
    "https://cursor.com/",
    "https://www.cursor.com/",
    "cursor://",
    "vscode://",
    "vscode-insiders://",
)


def _issuer_base() -> str:
    return (
        current_app.config.get("APP_URL")
        or current_app.config.get("APP_BASE_URL")
        or request.url_root
    ).rstrip("/")


def _redirect_uri_allowed_for_dcr(uri: str) -> bool:
    u = (uri or "").strip()
    if not u:
        return False
    return any(u.startswith(prefix) for prefix in _MCP_DCR_REDIRECT_ALLOW_PREFIXES)


def _dcr_owner_user_id() -> int | None:
    """Pick an admin to own dynamically registered public MCP clients."""
    from app.models import User

    admin = User.query.filter_by(is_active=True, role="admin").order_by(User.id.asc()).first()
    if admin:
        return admin.id
    for user in User.query.filter_by(is_active=True).order_by(User.id.asc()).limit(50):
        if user.is_admin:
            return user.id
    first = User.query.filter_by(is_active=True).order_by(User.id.asc()).first()
    return first.id if first else None


@oauth_server_bp.route("/.well-known/oauth-authorization-server", methods=["GET"])
def well_known():
    issuer = _issuer_base()
    return jsonify(
        {
            "issuer": issuer,
            "authorization_endpoint": url_for("oauth_server.authorize", _external=True),
            "token_endpoint": url_for("oauth_server.token", _external=True),
            "revocation_endpoint": url_for("oauth_server.revoke", _external=True),
            "registration_endpoint": url_for("oauth_server.dynamic_client_register", _external=True),
            "response_types_supported": ["code"],
            "grant_types_supported": ["authorization_code", "refresh_token"],
            "code_challenge_methods_supported": ["S256"],
            "token_endpoint_auth_methods_supported": ["client_secret_basic", "client_secret_post", "none"],
            "scopes_supported": sorted(
                set(
                    s.strip()
                    for chunk in (MCP_USER_SCOPES, MCP_ADMIN_SCOPES, MCP_ADMIN_READONLY_SCOPES)
                    for s in chunk.split(",")
                    if s.strip()
                )
            ),
        }
    )


@oauth_server_bp.route("/.well-known/oauth-protected-resource", methods=["GET"])
def well_known_protected_resource():
    """RFC 9728 protected resource metadata for MCP / API clients."""
    issuer = _issuer_base()
    mcp_resource = current_app.config.get("MCP_RESOURCE_URL") or f"{issuer}/mcp"
    return jsonify(
        {
            "resource": mcp_resource,
            "authorization_servers": [issuer],
            "bearer_methods_supported": ["header"],
            "scopes_supported": sorted(
                set(
                    s.strip()
                    for chunk in (MCP_USER_SCOPES, MCP_ADMIN_SCOPES, MCP_ADMIN_READONLY_SCOPES)
                    for s in chunk.split(",")
                    if s.strip()
                )
            ),
            "resource_documentation": f"{issuer}/docs/integrations/MCP.md",
        }
    )


@oauth_server_bp.route("/oauth/register", methods=["POST"])
@csrf.exempt
@limiter.limit("30 per hour")
def dynamic_client_register():
    """Limited RFC 7591 dynamic client registration for public MCP clients."""
    data = request.get_json(silent=True) or {}
    redirect_uris = data.get("redirect_uris") or []
    if not isinstance(redirect_uris, list) or not redirect_uris:
        return jsonify({"error": "invalid_client_metadata", "error_description": "redirect_uris required"}), 400
    if not all(isinstance(u, str) and _redirect_uri_allowed_for_dcr(u) for u in redirect_uris):
        return (
            jsonify(
                {
                    "error": "invalid_redirect_uri",
                    "error_description": "One or more redirect_uris are not allowed for dynamic registration",
                }
            ),
            400,
        )

    token_endpoint_auth_method = (data.get("token_endpoint_auth_method") or "none").strip()
    if token_endpoint_auth_method != "none":
        return (
            jsonify(
                {
                    "error": "invalid_client_metadata",
                    "error_description": "Only public clients (token_endpoint_auth_method=none) are supported",
                }
            ),
            400,
        )

    owner_id = _dcr_owner_user_id()
    if not owner_id:
        return jsonify({"error": "server_error", "error_description": "No user available to own the client"}), 500

    preset = (data.get("scope_preset") or data.get("timetracker_scope_preset") or "user").strip().lower()
    if preset in ("admin_readonly", "admin-readonly", "readonly"):
        allowed = MCP_ADMIN_READONLY_SCOPES
    elif preset == "admin":
        allowed = MCP_ADMIN_SCOPES
    else:
        allowed = MCP_USER_SCOPES

    requested_scope = (data.get("scope") or "").replace(",", " ")
    if requested_scope.strip():
        allowed_set = set(s.strip() for s in allowed.split(",") if s.strip())
        granted = [s for s in requested_scope.split() if s in allowed_set]
        allowed_scopes = ",".join(granted) if granted else allowed
    else:
        allowed_scopes = allowed

    client_name = (data.get("client_name") or "MCP Client").strip()[:200] or "MCP Client"
    app_rec, _plain = OAuthApplication.create_application(
        owner_user_id=owner_id,
        name=client_name,
        redirect_uris=redirect_uris,
        description=(data.get("client_uri") or data.get("software_id") or "Dynamically registered MCP client")[:500],
        allowed_scopes=allowed_scopes,
        is_confidential=False,
    )
    app_rec.grant_types = ["authorization_code", "refresh_token"]
    db.session.add(app_rec)
    if not safe_commit("oauth_dcr.created", {"name": client_name}):
        return jsonify({"error": "server_error", "error_description": "Could not register client"}), 500

    return (
        jsonify(
            {
                "client_id": app_rec.client_id,
                "client_id_issued_at": int(app_rec.created_at.timestamp()) if app_rec.created_at else None,
                "client_name": app_rec.name,
                "redirect_uris": app_rec.redirect_uri_list(),
                "grant_types": app_rec.grant_types,
                "response_types": ["code"],
                "token_endpoint_auth_method": "none",
                "scope": " ".join(app_rec.scope_list()),
            }
        ),
        201,
    )


# ---------------------------------------------------------------------------
# Admin UI: /admin/oauth-apps
# ---------------------------------------------------------------------------


@oauth_server_bp.route("/admin/oauth-apps", methods=["GET"])
@login_required
@admin_or_permission_required("access_admin")
def admin_list_apps():
    apps = OAuthApplication.query.order_by(OAuthApplication.created_at.desc()).all()
    return render_template("admin/oauth_apps.html", apps=apps, new_secret=None, new_app=None)


@oauth_server_bp.route("/admin/oauth-apps", methods=["POST"])
@login_required
@admin_or_permission_required("access_admin")
def admin_create_app():
    name = (request.form.get("name") or "").strip()
    description = (request.form.get("description") or "").strip()
    redirect_uris_raw = (request.form.get("redirect_uris") or "").strip()
    allowed_scopes = (
        request.form.get("allowed_scopes") or "read:projects,read:time_entries,write:time_entries"
    ).strip()
    is_confidential = request.form.get("is_confidential") == "1"

    if not name:
        apps = OAuthApplication.query.order_by(OAuthApplication.created_at.desc()).all()
        return render_template("admin/oauth_apps.html", apps=apps, error="Name is required."), 400

    redirect_uris = [u.strip() for u in redirect_uris_raw.replace(",", "\n").splitlines() if u.strip()]
    app_rec, plain_secret = OAuthApplication.create_application(
        owner_user_id=current_user.id,
        name=name,
        redirect_uris=redirect_uris,
        description=description,
        allowed_scopes=allowed_scopes,
        is_confidential=is_confidential,
    )
    db.session.add(app_rec)
    safe_commit("oauth_app.created", {"name": name})
    apps = OAuthApplication.query.order_by(OAuthApplication.created_at.desc()).all()
    return render_template(
        "admin/oauth_apps.html",
        apps=apps,
        new_secret=plain_secret,
        new_app=app_rec,
    )


@oauth_server_bp.route("/admin/oauth-apps/<int:app_id>/rotate", methods=["POST"])
@login_required
@admin_or_permission_required("access_admin")
def admin_rotate_secret(app_id: int):
    app_rec = OAuthApplication.query.get_or_404(app_id)
    plain = OAuthApplication.generate_client_secret()
    app_rec.client_secret_hash = OAuthApplication.hash_secret(plain)
    app_rec.is_confidential = True
    app_rec.updated_at = datetime.utcnow()
    safe_commit("oauth_app.secret_rotated", {"app_id": app_id})
    apps = OAuthApplication.query.order_by(OAuthApplication.created_at.desc()).all()
    return render_template("admin/oauth_apps.html", apps=apps, new_secret=plain, new_app=app_rec)


@oauth_server_bp.route("/admin/oauth-apps/<int:app_id>/delete", methods=["POST"])
@login_required
@admin_or_permission_required("access_admin")
def admin_delete_app(app_id: int):
    app_rec = OAuthApplication.query.get_or_404(app_id)
    db.session.delete(app_rec)
    safe_commit("oauth_app.deleted", {"app_id": app_id})
    return redirect(url_for("oauth_server.admin_list_apps"))


# ---------------------------------------------------------------------------
# Minimal API: /api/v1/oauth/applications
# ---------------------------------------------------------------------------


@oauth_server_bp.route("/api/v1/oauth/applications", methods=["GET"])
@csrf.exempt
def api_list_applications():
    from flask import g

    from app.utils.api_auth import authenticate_token, extract_token_from_request

    token_string = extract_token_from_request()
    user, api_token, err = authenticate_token(token_string or "", record_usage=True)
    if not user or not api_token:
        return jsonify({"error": "unauthorized", "message": err or "Authentication required"}), 401
    if not api_token.has_scope("admin:all"):
        return jsonify({"error": "forbidden", "message": 'Requires scope "admin:all"'}), 403
    g.api_user = user
    g.api_token = api_token
    apps = OAuthApplication.query.order_by(OAuthApplication.created_at.desc()).all()
    return jsonify({"applications": [a.to_dict() for a in apps]})


@oauth_server_bp.route("/api/v1/oauth/applications", methods=["POST"])
@csrf.exempt
def api_create_application():
    from flask import g

    from app.utils.api_auth import authenticate_token, extract_token_from_request

    token_string = extract_token_from_request()
    user, api_token, err = authenticate_token(token_string or "", record_usage=True)
    if not user or not api_token:
        return jsonify({"error": "unauthorized", "message": err or "Authentication required"}), 401
    if not api_token.has_scope("admin:all"):
        return jsonify({"error": "forbidden", "message": 'Requires scope "admin:all"'}), 403
    g.api_user = user
    g.api_token = api_token

    data = request.get_json(silent=True) or {}
    name = (data.get("name") or "").strip()
    if not name:
        return jsonify({"error": "name is required"}), 400
    redirect_uris = data.get("redirect_uris") or []
    if isinstance(redirect_uris, str):
        redirect_uris = [u.strip() for u in redirect_uris.split(",") if u.strip()]
    scopes = data.get("allowed_scopes") or "read:projects,read:time_entries,write:time_entries"
    if isinstance(scopes, list):
        scopes = ",".join(scopes)
    app_rec, plain_secret = OAuthApplication.create_application(
        owner_user_id=user.id,
        name=name,
        redirect_uris=redirect_uris,
        description=data.get("description") or "",
        allowed_scopes=scopes,
        is_confidential=bool(data.get("is_confidential", True)),
    )
    db.session.add(app_rec)
    safe_commit("oauth_app.created_api", {"name": name})
    payload = app_rec.to_dict()
    payload["client_secret"] = plain_secret
    return jsonify(payload), 201
