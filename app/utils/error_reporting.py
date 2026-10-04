"""
Optional Sentry reporting helpers.

Sentry may be uninitialized (no DSN); all helpers no-op safely in that case.
"""

from __future__ import annotations

import logging
import sys
from typing import Any, Optional, Union


def capture_exception(exc: Optional[BaseException] = None) -> None:
    """Best-effort Sentry capture; never raises."""
    try:
        import sentry_sdk

        sentry_sdk.capture_exception(exc)
    except Exception:
        pass


def log_and_capture(
    logger: Union[logging.Logger, Any],
    msg: str,
    *args: Any,
    exc: Optional[BaseException] = None,
    level: str = "warning",
    **kwargs: Any,
) -> None:
    """
    Log a message (with exc_info when an exception is present) and capture to Sentry.

    Prefer this for high-value swallowed errors instead of blanket wrapping.
    Extra positional args are forwarded to the logger like standard logging.
    """
    log_fn = getattr(logger, level, None) or logger.warning
    active = exc if exc is not None else sys.exc_info()[1]

    try:
        if active is not None and "exc_info" not in kwargs:
            kwargs["exc_info"] = True
        log_fn(msg, *args, **kwargs)
    except Exception:
        pass

    if active is not None:
        capture_exception(active)
