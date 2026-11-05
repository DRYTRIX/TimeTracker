"""Path helpers that keep filesystem access inside a realpath jail."""

from __future__ import annotations

import os
from typing import Optional


class PathEscapeError(ValueError):
    """Raised when a candidate path escapes the allowed base directory."""


def safe_path_under(base_dir: str, *parts: str) -> str:
    """
    Join ``parts`` under ``base_dir`` and ensure the result stays inside it.

    Resolves symlinks via ``os.path.realpath``. Raises ``PathEscapeError`` if
    the candidate escapes ``base_dir``.
    """
    if not base_dir:
        raise PathEscapeError("base directory is required")
    base = os.path.realpath(base_dir)
    if not parts:
        return base
    candidate = os.path.realpath(os.path.join(base, *parts))
    if candidate != base and not candidate.startswith(base + os.sep):
        raise PathEscapeError("path escapes base directory")
    return candidate


def safe_path_under_or_none(base_dir: str, *parts: str) -> Optional[str]:
    """Like ``safe_path_under`` but returns None instead of raising."""
    try:
        return safe_path_under(base_dir, *parts)
    except (PathEscapeError, OSError, TypeError, ValueError):
        return None


def resolve_stored_upload_path(app_root_path: str, stored_relative: str, *, under: str = "..") -> str:
    """
    Resolve a DB-stored relative upload path inside a realpath jail.

    ``stored_relative`` is typically ``uploads/...`` relative to the project root
    (parent of the Flask app package). Absolute paths and ``..`` segments are rejected.
    """
    if not stored_relative or not isinstance(stored_relative, str):
        raise PathEscapeError("path is required")
    candidate = stored_relative.strip()
    if not candidate or os.path.isabs(candidate) or candidate.startswith(("~", "\\\\")):
        raise PathEscapeError("absolute paths are not allowed")
    parts = [p for p in candidate.replace("\\", "/").split("/") if p and p != "."]
    if not parts or any(p == ".." for p in parts):
        raise PathEscapeError("path escapes base directory")
    base = os.path.realpath(os.path.join(app_root_path, under)) if under else os.path.realpath(app_root_path)
    return safe_path_under(base, *parts)
