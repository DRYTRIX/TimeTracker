"""Helpers to prevent open redirects via next= / Referer targets."""

from __future__ import annotations

from typing import Optional, Sequence
from urllib.parse import urlparse

from flask import request, url_for


def is_safe_relative_url(next_url: Optional[str]) -> bool:
    """
    Return True if next_url is a same-origin relative path (not protocol-relative).

    Rejects empty values, absolute URLs, protocol-relative URLs (//evil.com),
    and backslash tricks (/\evil.com).
    """
    if not next_url or not isinstance(next_url, str):
        return False
    candidate = next_url.strip()
    if not candidate.startswith("/") or candidate.startswith("//") or candidate.startswith("/\\"):
        return False
    # Disallow scheme-looking segments like /http: or /\\host
    if "://" in candidate.split("?", 1)[0].split("#", 1)[0]:
        return False
    return True


def is_safe_next_url(
    next_url: Optional[str],
    *,
    allowed_prefixes: Optional[Sequence[str]] = None,
) -> bool:
    """
    Validate a next URL.

    When allowed_prefixes is provided, the path must equal or start with one of
    those prefixes (with optional ?query or #fragment). Otherwise any safe
    relative path is accepted.
    """
    if not is_safe_relative_url(next_url):
        return False
    assert next_url is not None
    candidate = next_url.strip()
    if not allowed_prefixes:
        return True
    return any(
        candidate == prefix or candidate.startswith(prefix + "?") or candidate.startswith(prefix + "#")
        or candidate.startswith(prefix + "/")
        for prefix in allowed_prefixes
    )


def is_safe_referrer(referrer: Optional[str], *, require_same_host: bool = True) -> bool:
    """
    Validate a Referer / absolute URL redirect target.

    Relative paths are accepted when they pass is_safe_relative_url.
    Absolute URLs are accepted only when they share the current request host
    (and preferably scheme) when require_same_host is True.
    """
    if not referrer or not isinstance(referrer, str):
        return False
    candidate = referrer.strip()
    if is_safe_relative_url(candidate):
        return True

    try:
        parsed = urlparse(candidate)
    except Exception:
        return False

    if parsed.scheme not in ("http", "https") or not parsed.netloc:
        return False

    if not require_same_host:
        return True

    try:
        host_url = request.host_url  # e.g. http://localhost:8080/
        host_parsed = urlparse(host_url)
    except Exception:
        return False

    return parsed.netloc.lower() == host_parsed.netloc.lower()


def _rebuild_relative(candidate: str) -> str:
    """Rebuild a validated relative URL from parsed components (breaks taint)."""
    cleaned = candidate.strip().replace("\\", "/")
    parsed = urlparse(cleaned)
    path = parsed.path or "/"
    query = f"?{parsed.query}" if parsed.query else ""
    fragment = f"#{parsed.fragment}" if parsed.fragment else ""
    return f"{path}{query}{fragment}"


def _rebuild_same_host(candidate: str) -> str:
    """Rebuild a validated same-host absolute URL from parsed components."""
    cleaned = candidate.strip().replace("\\", "/")
    parsed = urlparse(cleaned)
    scheme = parsed.scheme.lower()
    netloc = parsed.netloc
    path = parsed.path or "/"
    query = f"?{parsed.query}" if parsed.query else ""
    fragment = f"#{parsed.fragment}" if parsed.fragment else ""
    return f"{scheme}://{netloc}{path}{query}{fragment}"


def safe_redirect_target(
    candidate: Optional[str],
    *,
    fallback: Optional[str] = None,
    fallback_endpoint: str = "main.dashboard",
    allowed_prefixes: Optional[Sequence[str]] = None,
    allow_absolute_same_host: bool = False,
) -> str:
    """
    Return a safe redirect target, or a fallback URL / endpoint.

    - Relative candidates use is_safe_next_url.
    - Absolute candidates are only allowed when allow_absolute_same_host is True
      and is_safe_referrer passes.
    - When no candidate is safe, ``fallback`` is returned if provided; otherwise
      ``url_for(fallback_endpoint)``.

    Validated targets are rebuilt from urlparse components so open-redirect
    taint does not flow to ``redirect()``.
    """
    if candidate:
        if allow_absolute_same_host and is_safe_referrer(candidate):
            return _rebuild_same_host(candidate)
        if is_safe_next_url(candidate, allowed_prefixes=allowed_prefixes):
            return _rebuild_relative(candidate)
    if fallback is not None:
        return fallback
    return url_for(fallback_endpoint)
