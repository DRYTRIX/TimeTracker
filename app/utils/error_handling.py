"""
Safe error-handling utilities for logging and file operations.
Use these where failures must not break the main flow (e.g. cache, cleanup, telemetry).
"""

import logging
import os
from typing import Any, Optional

_valid_log_levels = ("debug", "info", "warning", "error", "critical")


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
