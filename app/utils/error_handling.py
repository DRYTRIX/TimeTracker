"""
Safe error-handling utilities for logging and file operations.
Use these where failures must not break the main flow (e.g. cache, cleanup, telemetry).
"""

import logging
import os
import re
from typing import Any, Optional, Tuple

_valid_log_levels = ("debug", "info", "warning", "error", "critical")
_LOG_CRLF_RE = re.compile(r"[\r\n]+")

# Generic client-facing message — never embed exception text in HTTP responses.
DEFAULT_CLIENT_ERROR = "An unexpected error occurred"


def sanitize_log_value(value: Any, *, max_len: int = 500) -> str:
    """Neutralize CR/LF (log injection) and truncate untrusted values for logging."""
    if value is None:
        return ""
    text = str(value)
    text = _LOG_CRLF_RE.sub(" ", text)
    if len(text) > max_len:
        text = text[: max_len - 3] + "..."
    return text


def client_error_payload(
    message: str = DEFAULT_CLIENT_ERROR,
    *,
    key: str = "error",
) -> dict:
    """Return a JSON-serializable error dict safe to send to clients."""
    return {key: message}


def client_error_response(
    message: str = DEFAULT_CLIENT_ERROR,
    status: int = 500,
    *,
    key: str = "error",
) -> Tuple[Any, int]:
    """
    Build a (jsonify_body, status) pair without leaking exception details.

    Usage::

        except Exception:
            current_app.logger.exception("…")
            return client_error_response()
    """
    from flask import jsonify

    return jsonify(client_error_payload(message, key=key)), status


def safe_log(
    logger: logging.Logger,
    level: str,
    msg: str,
    *args: Any,
    exc_info: bool = False,
    **kwargs: Any,
) -> None:
    """
    Call logger.<level>(msg, *args, **kwargs) without ever raising.
    Use when logging must not break the request (e.g. after cache invalidation, telemetry).
    """
    if level not in _valid_log_levels:
        level = "debug"
    try:
        method = getattr(logger, level, None)
        if method and callable(method):
            method(msg, *args, exc_info=exc_info, **kwargs)
    except Exception:
        pass


def safe_file_remove(path: str, logger: Optional[logging.Logger] = None) -> bool:
    """
    Remove a file at path. On failure log at warning and return False.
    Returns True if the file was removed or did not exist.
    """
    if not path:
        return True
    try:
        if os.path.isfile(path):
            os.remove(path)
        return True
    except OSError as e:
        if logger:
            logger.warning("Failed to remove file %s: %s", path, e)
        return False
    except Exception as e:
        if logger:
            logger.warning("Unexpected error removing file %s: %s", path, e)
        return False
