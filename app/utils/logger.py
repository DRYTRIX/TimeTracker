"""
Enhanced logging utilities.
"""

from typing import Any, Dict, Optional
import logging
from flask import current_app, request, g
from app.utils.performance import get_performance_metrics


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger instance.

    Args:
        name: Logger name (usually __name__)

    Returns:
        Logger instance
    """
    return logging.getLogger(name)


def log_request(logger: logging.Logger, level: int = logging.INFO, extra: Optional[Dict[str, Any]] = None) -> None:
    """
    Log request information.

    Args:
        logger: Logger instance
        level: Log level
        extra: Additional context
    """
    if not request:
        return

    context = {
        "method": request.method,
        "path": request.path,
        "remote_addr": request.remote_addr,
        "user_agent": request.headers.get("User-Agent"),
        "request_id": getattr(g, "request_id", None),
    }

    if extra:
        context.update(extra)

    logger.log(level, f"{request.method} {request.path}", extra=context)


def log_error(logger: logging.Logger, error: Exception, context: Optional[Dict[str, Any]] = None) -> None:
    """
    Log an error with context.

    Args:
        logger: Logger instance
        error: Exception to log
        context: Additional context
    """
    error_context = {
        "error_type": type(error).__name__,
        "error_message": str(error),
        "request_id": getattr(g, "request_id", None),
        "path": request.path if request else None,
        "method": request.method if request else None,
    }

    if context:
        error_context.update(context)

    logger.error(f"Error: {error}", exc_info=True, extra=error_context)


def log_business_event(logger: logging.Logger, event: str, user_id: Optional[int] = None, **kwargs) -> None:
    """
    Log a business event.

    Args:
        logger: Logger instance
        event: Event name
        user_id: User ID
        **kwargs: Additional event data
    """
    event_data = {
        "event": event,
        "user_id": user_id,
        "request_id": getattr(g, "request_id", None),
        "path": request.path if request else None,
    }
    event_data.update(kwargs)

    logger.info(f"Business event: {event}", extra=event_data)


def log_performance(logger: logging.Logger, operation: str, duration: float, **kwargs) -> None:
    """
    Log performance metrics.

    Args:
        logger: Logger instance
        operation: Operation name
        duration: Duration in seconds
        **kwargs: Additional metrics
    """
    metrics = {"operation": operation, "duration": duration, "request_id": getattr(g, "request_id", None)}
    metrics.update(kwargs)

    logger.info(f"Performance: {operation} took {duration:.4f}s", extra=metrics)
