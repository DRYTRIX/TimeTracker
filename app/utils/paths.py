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
