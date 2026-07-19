"""Helpers for native client portal sessions (session['client_portal_id'])."""

from __future__ import annotations

from flask import request, session, url_for
from flask.helpers import redirect

_NATIVE_CLIENT_ALLOWED_ENDPOINTS = frozenset(
    {
        "auth.login",
        "auth.logout",
        "static",
        "setup.initial_setup",
        "main.health_check",
        "main.readiness_check",
    }
)


def get_active_native_client_portal_id():
    """Return session client_portal_id when it refers to an active portal client."""
    client_id = session.get("client_portal_id")
    if not client_id:
        return None

    try:
        from app.models import Client

        client = Client.query.get(client_id)
    except Exception:
        return None

    if not client or not client.is_active or not client.has_portal_access:
        return None
    return client.id


def is_native_client_portal_endpoint_allowed(endpoint: str | None, path: str | None) -> bool:
    """Whether a native client portal session may access this route without redirect."""
    endpoint = endpoint or ""
    path = path or ""

    if endpoint.startswith("client_portal."):
        return True
    if endpoint in _NATIVE_CLIENT_ALLOWED_ENDPOINTS:
        return True
    if path.startswith("/static/") or path.startswith("/client-portal"):
        return True
    return False


def redirect_native_client_to_portal():
    """Redirect an authenticated native client session to the portal dashboard."""
    return redirect(url_for("client_portal.dashboard"))


def should_redirect_native_client_portal_session() -> bool:
    """True when the current request should be kept inside the client portal UI."""
    if not get_active_native_client_portal_id():
        return False
    return not is_native_client_portal_endpoint_allowed(request.endpoint, request.path)
