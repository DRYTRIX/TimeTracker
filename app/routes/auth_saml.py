"""SAML 2.0 SP routes (login, ACS, metadata).

See docs/design/SAML_SCIM.md. Uses python3-saml (onelogin.saml2) when installed.
"""

from __future__ import annotations

from flask import Blueprint, current_app, flash, redirect, request, session, url_for
from flask_babel import gettext as _
from flask_login import login_user

from app import csrf
from app.config import Config
from app.services.external_identity_service import provision_external_user
from app.utils.auth_method import auth_includes_saml

auth_saml_bp = Blueprint("auth_saml", __name__)


def _saml_enabled() -> bool:
    if current_app.config.get("SAML_ENABLED"):
        return True
    auth_method = current_app.config.get("AUTH_METHOD", "local")
    return auth_includes_saml(auth_method)


def _saml_settings() -> dict:
    """Build OneLogin python3-saml settings dict from app config."""
    base = (current_app.config.get("APP_URL") or request.url_root or "").rstrip("/")
    sp_entity = current_app.config.get("SAML_SP_ENTITY_ID") or f"{base}/auth/saml/metadata"
    acs_url = current_app.config.get("SAML_SP_ACS_URL") or f"{base}/auth/saml/acs"
    idp_entity = current_app.config.get("SAML_IDP_ENTITY_ID") or ""
    idp_sso = current_app.config.get("SAML_IDP_SSO_URL") or ""
    idp_x509 = current_app.config.get("SAML_IDP_X509_CERT") or ""

    return {
        "strict": True,
        "debug": bool(current_app.debug),
        "sp": {
            "entityId": sp_entity,
            "assertionConsumerService": {
                "url": acs_url,
                "binding": "urn:oasis:names:tc:SAML:2.0:bindings:HTTP-POST",
            },
            "NameIDFormat": "urn:oasis:names:tc:SAML:1.1:nameid-format:emailAddress",
            "x509cert": current_app.config.get("SAML_SP_X509_CERT") or "",
            "privateKey": current_app.config.get("SAML_SP_PRIVATE_KEY") or "",
        },
        "idp": {
            "entityId": idp_entity,
            "singleSignOnService": {
                "url": idp_sso,
                "binding": "urn:oasis:names:tc:SAML:2.0:bindings:HTTP-Redirect",
            },
            "x509cert": idp_x509,
        },
        "security": {
            "wantAssertionsSigned": current_app.config.get("SAML_WANT_ASSERTIONS_SIGNED", True),
            "wantMessagesSigned": False,
            "requestedAuthnContext": False,
            "logoutRequestSigned": False,
            "logoutResponseSigned": False,
            "metadataValidUntil": None,
            "metadataCacheDuration": None,
            "signMetadata": False,
            "digestAlgorithm": "http://www.w3.org/2001/04/xmlenc#sha256",
            "signatureAlgorithm": "http://www.w3.org/2001/04/xmldsig-more#rsa-sha256",
            "rejection_skew": int(current_app.config.get("SAML_CLOCK_SKEW_SECONDS") or 120),
        },
    }


def _prepare_saml_request() -> dict:
    url_data = request.host_url.rstrip("/")
    return {
        "https": "on" if request.scheme == "https" else "off",
        "http_host": request.host,
        "script_name": request.path,
        "server_port": request.environ.get("SERVER_PORT"),
        "get_data": request.args.copy(),
        "post_data": request.form.copy(),
    }


@auth_saml_bp.route("/auth/saml/login", methods=["GET"])
def saml_login():
    if not _saml_enabled():
        flash(_("SAML SSO is not enabled."), "error")
        return redirect(url_for("auth.login"))

    idp_sso = current_app.config.get("SAML_IDP_SSO_URL") or ""
    if not idp_sso:
        flash(_("SAML IdP is not configured."), "error")
        return redirect(url_for("auth.login"))

    try:
        from onelogin.saml2.auth import OneLogin_Saml2_Auth
    except ImportError:
        current_app.logger.error("python3-saml is not installed")
        flash(_("SAML support is not installed on this server."), "error")
        return redirect(url_for("auth.login"))

    req = _prepare_saml_request()
    auth = OneLogin_Saml2_Auth(req, _saml_settings())
    return_to = request.args.get("next") or url_for("main.dashboard", _external=True)
    return redirect(auth.login(return_to=return_to))


@auth_saml_bp.route("/auth/saml/acs", methods=["POST"])
@csrf.exempt
def saml_acs():
    if not _saml_enabled():
        flash(_("SAML SSO is not enabled."), "error")
        return redirect(url_for("auth.login"))

    try:
        from onelogin.saml2.auth import OneLogin_Saml2_Auth
    except ImportError:
        flash(_("SAML support is not installed on this server."), "error")
        return redirect(url_for("auth.login"))

    req = _prepare_saml_request()
    auth = OneLogin_Saml2_Auth(req, _saml_settings())
    auth.process_response()
    errors = auth.get_errors()
    if errors:
        current_app.logger.warning("SAML ACS errors: %s reason=%s", errors, auth.get_last_error_reason())
        flash(_("SAML authentication failed."), "error")
        return redirect(url_for("auth.login"))
    if not auth.is_authenticated():
        flash(_("SAML authentication failed."), "error")
        return redirect(url_for("auth.login"))

    attributes = auth.get_attributes() or {}
    nameid = auth.get_nameid() or ""
    issuer = (current_app.config.get("SAML_IDP_ENTITY_ID") or auth.get_issuers() or [""])[0] if hasattr(
        auth, "get_issuers"
    ) else (current_app.config.get("SAML_IDP_ENTITY_ID") or "")
    try:
        issuers = auth.get_issuers() or []
        if issuers:
            issuer = issuers[0]
    except Exception:
        pass
    issuer = issuer or current_app.config.get("SAML_IDP_ENTITY_ID") or "saml"

    def _attr(keys):
        for k in keys:
            vals = attributes.get(k)
            if isinstance(vals, list) and vals:
                return vals[0]
            if isinstance(vals, str) and vals:
                return vals
        return None

    email = (_attr(["email", "mail", "Email", "http://schemas.xmlsoap.org/ws/2005/05/identity/claims/emailaddress"]) or nameid or "").strip().lower() or None
    given = _attr(["givenName", "firstName", "http://schemas.xmlsoap.org/ws/2005/05/identity/claims/givenname"]) or ""
    family = _attr(["sn", "surname", "lastName", "http://schemas.xmlsoap.org/ws/2005/05/identity/claims/surname"]) or ""
    display = _attr(["displayName", "cn", "http://schemas.microsoft.com/identity/claims/displayname"]) or ""
    full_name = display or (" ".join(p for p in [given, family] if p).strip() or None)
    groups_raw = attributes.get("memberOf") or attributes.get("groups") or []
    if isinstance(groups_raw, str):
        groups = [groups_raw]
    else:
        groups = list(groups_raw or [])

    subject = nameid or email or ""
    admin_emails = current_app.config.get("SAML_ADMIN_EMAILS") or getattr(Config, "OIDC_ADMIN_EMAILS", []) or []
    admin_group = current_app.config.get("SAML_ADMIN_GROUP")

    provision = provision_external_user(
        provider="saml",
        subject=subject,
        issuer=issuer,
        email=email,
        full_name=full_name,
        groups=groups,
        admin_emails=admin_emails,
        admin_groups=[admin_group] if admin_group else None,
    )
    if not provision.user:
        flash(_(provision.error_flash or "Could not provision user from SAML."), "error")
        return redirect(url_for("auth.login"))

    user = provision.user
    if not user.is_active:
        flash(_("Account is disabled. Please contact an administrator."), "error")
        return redirect(url_for("auth.login"))

    if provision.created:
        flash(_("Welcome! Your account has been created."), "success")

    login_user(user, remember=True)
    session["auth_provider"] = "saml"
    return redirect(url_for("main.dashboard"))


@auth_saml_bp.route("/auth/saml/metadata", methods=["GET"])
def saml_metadata():
    if not _saml_enabled():
        return "SAML not enabled", 404
    try:
        from onelogin.saml2.auth import OneLogin_Saml2_Auth
        from onelogin.saml2.settings import OneLogin_Saml2_Settings
    except ImportError:
        return "python3-saml not installed", 501

    settings = OneLogin_Saml2_Settings(settings=_saml_settings(), sp_validation_only=True)
    metadata = settings.get_sp_metadata()
    errors = settings.validate_metadata(metadata)
    if errors:
        current_app.logger.warning("SAML metadata validation errors: %s", errors)
    return metadata, 200, {"Content-Type": "application/xml"}
