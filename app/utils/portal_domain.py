"""Resolve white-label client portal hosts to Client records."""

from __future__ import annotations

from typing import Optional

from flask import g, request


def normalize_host(host: Optional[str] = None) -> str:
    """Return a lowercase hostname without port."""
    raw = host if host is not None else (request.host or "")
    return (raw or "").split(":")[0].strip().lower()


def resolve_portal_client_for_host(host: Optional[str] = None):
    """
    Look up an active client by custom_domain when portal custom domains are enabled.

    Returns the Client or None. Does not require an authenticated portal session.
    """
    try:
        from app.models import Client, Settings

        settings = Settings.get_settings()
        if not getattr(settings, "portal_allowed_custom_domains", None):
            return None

        hostname = normalize_host(host)
        if not hostname:
            return None

        client = Client.query.filter(Client.custom_domain == hostname).first()
        if not client or not client.is_active or not client.has_portal_access:
            return None
        return client
    except Exception:
        return None


def bind_portal_client_to_g():
    """Store the resolved custom-domain client on flask.g as portal_client."""
    g.portal_client = resolve_portal_client_for_host()
    if g.portal_client is not None:
        g.portal_domain_client = g.portal_client
    return g.portal_client
