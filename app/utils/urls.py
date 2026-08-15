"""Helpers for building absolute URLs outside an HTTP request (scheduled jobs, emails).

Flask's ``url_for(..., _external=True)`` needs either an active request or
``SERVER_NAME``. Setting ``SERVER_NAME`` globally makes Flask host-match every
incoming request and 404 Host headers that differ (common behind reverse
proxies). Instead we push a synthetic request context built from a known base
URL for background work.
"""

from __future__ import annotations

import logging
import re
from contextlib import contextmanager
from typing import Iterator, Optional
from urllib.parse import urlparse

from flask import current_app, has_request_context, request, url_for
from werkzeug.routing import BuildError

logger = logging.getLogger(__name__)

_FALLBACK_BASE_URL = "http://localhost:8080/"
_WARNED_MISSING_BASE = False

# Paths that should not seed APP_BASE_URL_DETECTED (container health probes, etc.)
_HEALTH_PATH_PREFIXES = (
    "/health",
    "/_health",
    "/ready",
    "/live",
    "/ping",
    "/status",
    "/api/health",
)


def _normalize_base_url(url: str) -> str:
    url = (url or "").strip()
    if not url:
        return ""
    if not re.match(r"^https?://", url, re.IGNORECASE):
        url = "https://" + url
    return url.rstrip("/") + "/"


def _is_local_or_ip_host(hostname: Optional[str]) -> bool:
    if not hostname:
        return True
    host = hostname.lower().split("%", 1)[0]
    if host in ("localhost", "127.0.0.1", "::1", "0.0.0.0"):
        return True
    # Bare IPv4
    if re.fullmatch(r"\d{1,3}(?:\.\d{1,3}){3}", host):
        return True
    return False


def _is_health_path(path: str) -> bool:
    path = (path or "/").split("?", 1)[0]
    if not path.startswith("/"):
        path = "/" + path
    lower = path.lower()
    return any(lower == p or lower.startswith(p + "/") for p in _HEALTH_PATH_PREFIXES)


def get_app_base_url(app=None) -> Optional[str]:
    """Resolve the public base URL for this instance.

    Order: Settings ``app_base_url`` (if set), then ``APP_BASE_URL`` config,
    then ``SERVER_NAME`` + ``PREFERRED_URL_SCHEME`` if an operator set them,
    then auto-detected value from a real request, else ``None``.
    """
    if app is None:
        app = current_app._get_current_object()

    try:
        from app.models import Settings

        settings = Settings.get_settings()
        from_settings = _normalize_base_url(getattr(settings, "app_base_url", "") or "")
        if from_settings:
            return from_settings
    except Exception:
        # DB may be unavailable during early boot or in some tests
        pass

    configured = _normalize_base_url(app.config.get("APP_BASE_URL") or "")
    if configured:
        return configured

    server_name = (app.config.get("SERVER_NAME") or "").strip()
    if server_name:
        scheme = (app.config.get("PREFERRED_URL_SCHEME") or "http").strip() or "http"
        return _normalize_base_url(f"{scheme}://{server_name}")

    detected = _normalize_base_url(app.config.get("APP_BASE_URL_DETECTED") or "")
    if detected:
        return detected

    return None


def remember_request_base_url() -> None:
    """Record ``request.url_root`` for later use by background jobs.

    Ignores health-check paths. A localhost / bare-IP host only wins when
    nothing better is stored, so container probes cannot poison the value.
    Never overwrites an explicitly configured ``APP_BASE_URL``.
    """
    if not has_request_context():
        return

    app = current_app._get_current_object()
    if _normalize_base_url(app.config.get("APP_BASE_URL") or ""):
        return

    try:
        from app.models import Settings

        if _normalize_base_url(getattr(Settings.get_settings(), "app_base_url", "") or ""):
            return
    except Exception:
        pass

    try:
        path = request.path or "/"
        if _is_health_path(path):
            return

        root = _normalize_base_url(request.url_root or "")
        if not root:
            return

        parsed = urlparse(root)
        host_is_weak = _is_local_or_ip_host(parsed.hostname)
        existing = _normalize_base_url(app.config.get("APP_BASE_URL_DETECTED") or "")

        if host_is_weak and existing:
            existing_host = urlparse(existing).hostname
            if existing_host and not _is_local_or_ip_host(existing_host):
                return

        if existing == root:
            return

        app.config["APP_BASE_URL_DETECTED"] = root
    except Exception:
        # Never break a real request for URL bookkeeping
        pass


@contextmanager
def external_url_context(app) -> Iterator[None]:
    """App + synthetic request context so ``url_for(_external=True)`` works off-request.

    Falls back to ``http://localhost:8080/`` with a one-time warning when no base
    URL is known, so scheduled jobs still complete instead of crashing.
    """
    global _WARNED_MISSING_BASE

    with app.app_context():
        base = get_app_base_url(app)
        if not base:
            if not _WARNED_MISSING_BASE:
                logger.warning(
                    "APP_BASE_URL is not set and no public host has been learned from "
                    "incoming requests yet. Email and notification links from background "
                    "jobs may point at localhost. Set APP_BASE_URL (e.g. "
                    "https://time.example.com) so links are correct."
                )
                _WARNED_MISSING_BASE = True
            base = _FALLBACK_BASE_URL

        with app.test_request_context(base_url=base, path="/"):
            yield


def safe_external_url_for(endpoint: str, **values) -> str:
    """Like ``url_for(..., _external=True)`` but returns ``""`` on failure."""
    try:
        return url_for(endpoint, _external=True, **values)
    except (BuildError, RuntimeError) as exc:
        try:
            current_app.logger.warning(
                "Could not build external URL for %s: %s", endpoint, exc
            )
        except RuntimeError:
            logger.warning("Could not build external URL for %s: %s", endpoint, exc)
        return ""
