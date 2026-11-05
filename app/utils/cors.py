"""CORS / Socket.IO origin allowlist helpers."""

from __future__ import annotations

from typing import List, Optional
from urllib.parse import urlparse


def _origin_from_base_url(base_url: Optional[str]) -> Optional[str]:
    if not base_url:
        return None
    parsed = urlparse(base_url.strip())
    if not parsed.scheme or not parsed.netloc:
        return None
    return f"{parsed.scheme}://{parsed.netloc}".rstrip("/")


def get_cors_allowed_origins(app=None) -> List[str]:
    """
    Return browser origins allowed for /api/v1 CORS and Socket.IO.

    Sources (deduped):
    - ``CORS_ALLOWED_ORIGINS`` config (explicit allowlist)
    - ``APP_BASE_URL`` / detected base URL origin
    - ``SERVER_NAME`` + ``PREFERRED_URL_SCHEME`` when set

    Never returns ``*``. Empty list means cross-origin browser calls are denied.
    """
    if app is None:
        from flask import current_app

        app = current_app._get_current_object()

    origins: List[str] = []
    seen = set()

    def _add(origin: Optional[str]) -> None:
        if not origin:
            return
        cleaned = origin.strip().rstrip("/")
        if not cleaned or cleaned == "*" or cleaned in seen:
            return
        seen.add(cleaned)
        origins.append(cleaned)

    for origin in app.config.get("CORS_ALLOWED_ORIGINS") or []:
        _add(origin)

    _add(_origin_from_base_url(app.config.get("APP_BASE_URL") or ""))

    try:
        from app.utils.urls import get_app_base_url

        _add(_origin_from_base_url(get_app_base_url(app)))
    except Exception:
        pass

    server_name = (app.config.get("SERVER_NAME") or "").strip()
    if server_name:
        scheme = (app.config.get("PREFERRED_URL_SCHEME") or "http").strip() or "http"
        _add(f"{scheme}://{server_name}")

    _add(_origin_from_base_url(app.config.get("APP_BASE_URL_DETECTED") or ""))

    return origins


def cors_origin_allowed(origin: Optional[str], app=None, environ=None) -> bool:
    """Return True if the request Origin is on the allowlist or same-host.

    Same-host (scheme+Host / X-Forwarded-*) is always allowed so first-party
    Socket.IO keeps working before APP_BASE_URL is configured. Arbitrary
    cross-origin browsers must appear in ``CORS_ALLOWED_ORIGINS`` / base URL.
    """
    if not origin:
        return False
    candidate = origin.strip().rstrip("/")
    if not candidate or candidate == "*":
        return False

    allowed = {o.lower() for o in get_cors_allowed_origins(app)}
    if candidate.lower() in allowed:
        return True

    # Same-origin fallback (mirrors python-engineio default when allowlist is None)
    if environ:
        hosts = []
        if environ.get("wsgi.url_scheme") and environ.get("HTTP_HOST"):
            hosts.append(f"{environ['wsgi.url_scheme']}://{environ['HTTP_HOST']}")
        if environ.get("HTTP_X_FORWARDED_PROTO") or environ.get("HTTP_X_FORWARDED_HOST"):
            scheme = environ.get("HTTP_X_FORWARDED_PROTO", environ.get("wsgi.url_scheme", "http")).split(",")[0].strip()
            host = environ.get("HTTP_X_FORWARDED_HOST", environ.get("HTTP_HOST", "")).split(",")[0].strip()
            if scheme and host:
                hosts.append(f"{scheme}://{host}")
        if candidate.lower() in {h.rstrip("/").lower() for h in hosts}:
            return True

    # Flask request context same-host check for HTTP CORS
    try:
        from flask import has_request_context, request

        if has_request_context() and request.host_url:
            req_origin = request.host_url.rstrip("/")
            if candidate.lower() == req_origin.lower():
                return True
    except Exception:
        pass

    return False


def socketio_cors_allowed_origin(origin, environ=None) -> bool:
    """Callable for ``socketio.init_app(..., cors_allowed_origins=...)``."""
    return cors_origin_allowed(origin, environ=environ)
