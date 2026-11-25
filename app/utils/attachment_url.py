"""Validate chat/message attachment_url values to block path traversal."""

from __future__ import annotations

import os
from typing import Optional
from urllib.parse import urlparse


def sanitize_attachment_url(url: Optional[str], *, max_length: int = 2000) -> Optional[str]:
    """Return a safe attachment URL/path or None if rejected.

    Allowed:
    - ``https://`` / ``http://`` absolute URLs (no credentials/userinfo)
    - Relative paths under ``uploads/`` or ``static/uploads/`` without ``..``

    Rejected: ``file:``, absolute filesystem paths, ``..``, empty, overly long.
    """
    if url is None:
        return None
    if not isinstance(url, str):
        return None
    candidate = url.strip()
    if not candidate or len(candidate) > max_length:
        return None

    lowered = candidate.lower()
    if lowered.startswith("file:") or lowered.startswith("\\\\") or "\x00" in candidate:
        return None

    parsed = urlparse(candidate)
    if parsed.scheme in ("http", "https"):
        if parsed.username or parsed.password:
            return None
        if not parsed.hostname:
            return None
        return candidate

    if parsed.scheme:
        return None

    path = candidate.split("?", 1)[0].split("#", 1)[0].replace("\\", "/")
    if os.path.isabs(path) or path.startswith("~"):
        return None
    parts = [p for p in path.split("/") if p and p != "."]
    if not parts or any(p == ".." for p in parts):
        return None
    normalized = "/".join(parts)
    if not (
        normalized.startswith("uploads/")
        or normalized.startswith("static/uploads/")
        or normalized.startswith("api/")
        or normalized.startswith("team-chat/")
    ):
        return None
    return normalized
