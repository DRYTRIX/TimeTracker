"""
PostHog Monitoring Utilities

Track errors, performance metrics, and application health through PostHog.
"""

from typing import Optional, Dict, Any
import time
import os
from functools import wraps
from contextlib import contextmanager


def is_monitoring_enabled() -> bool:
    """Check if PostHog monitoring is enabled."""
    return bool(os.getenv("POSTHOG_API_KEY", ""))


# ============================================================================
# Error Tracking
# ============================================================================


def track_error(
    user_id: Any, error_type: str, error_message: str, context: Optional[Dict] = None, severity: str = "error"
) -> None:
    """
    Track application errors in PostHog.

    Args:
        user_id: User ID (or 'anonymous' for unauthenticated)
        error_type: Type of error (e.g., 'validation', 'database', 'api', '404')
        error_message: Error message (sanitized, no PII)
        context: Additional context (page, action, etc.)
        severity: Error severity ('error', 'warning', 'critical')

    Example:
        try:
            generate_report()
        except ValueError as e:
            track_error(
                current_user.id,
                "validation",
                "Invalid date range for report",
                {"report_type": "summary"}
            )
            raise
    """
    if not is_monitoring_enabled():
        return

    from app import track_event
    from flask import request

    error_properties = {
        "error_type": error_type,
        "error_message": error_message[:500],  # Limit message length
        "severity": severity,
        "timestamp": time.time(),
    }

    # Add context
    if context:
        error_properties["error_context"] = context

    # Add request context if available
    try:
        if request:
            error_properties.update(
                {
                    "$current_url": request.url,
                    "$pathname": request.path,
                    "method": request.method,
                }
            )
    except Exception:
        pass

    track_event(user_id, "error_occurred", error_properties)


def track_http_error(user_id: Any, status_code: int, error_message: str, context: Optional[Dict] = None) -> None:
    """
    Track HTTP errors (404, 500, etc.).

    Args:
        user_id: User ID
        status_code: HTTP status code
        error_message: Error message
        context: Additional context
    """
    track_error(
        user_id,
        f"http_{status_code}",
        error_message,
        {"status_code": status_code, **(context or {})},
        severity="warning" if status_code < 500 else "error",
    )


def track_validation_error(user_id: Any, field: str, error_message: str, context: Optional[Dict] = None) -> None:
    """
    Track form validation errors.

    Args:
        user_id: User ID
        field: Field that failed validation
        error_message: Validation error message
        context: Additional context
    """
    track_error(user_id, "validation", error_message, {"field": field, **(context or {})}, severity="warning")


# ============================================================================
# Performance Tracking
# ============================================================================


def track_performance(
    user_id: Any,
    metric_name: str,
    duration_ms: float,
    context: Optional[Dict] = None,
    threshold_ms: Optional[float] = None,
) -> None:
    """
    Track performance metrics in PostHog.

    Args:
        user_id: User ID
        metric_name: Name of the metric (e.g., 'report_generation', 'export_csv')
        duration_ms: Duration in milliseconds
        context: Additional context
        threshold_ms: If provided, also track if duration exceeded threshold

    Example:
        start = time.time()
        generate_report()
        duration = (time.time() - start) * 1000
        track_performance(
            current_user.id,
            "report_generation",
            duration,
            {"report_type": "summary", "entries_count": 100}
        )
    """
    if not is_monitoring_enabled():
        return

    from app import track_event

    performance_properties = {
        "metric_name": metric_name,
        "duration_ms": duration_ms,
        "duration_seconds": duration_ms / 1000,
        **(context or {}),
    }

    # Check if threshold exceeded
    if threshold_ms is not None:
        performance_properties["threshold_exceeded"] = duration_ms > threshold_ms
        performance_properties["threshold_ms"] = threshold_ms

    track_event(user_id, "performance_metric", performance_properties)


@contextmanager
def measure_performance(
    user_id: Any, metric_name: str, context: Optional[Dict] = None, threshold_ms: Optional[float] = None
):
    """
    Context manager to measure performance of a code block.

    Usage:
        with measure_performance(current_user.id, "report_generation", {"type": "summary"}):
            generate_report()
    """
    start = time.time()
    try:
        yield
    finally:
        duration_ms = (time.time() - start) * 1000
        track_performance(user_id, metric_name, duration_ms, context, threshold_ms)


def performance_tracked(metric_name: str, threshold_ms: Optional[float] = None):
    """
    Decorator to track performance of a function.

    Usage:
        @performance_tracked("report_generation", threshold_ms=5000)
        def generate_report():
            # ... generate report
            pass
    """

    def decorator(f):
        @wraps(f)
        def wrapped(*args, **kwargs):
            from flask_login import current_user

            user_id = current_user.id if current_user.is_authenticated else "anonymous"

            start = time.time()
            try:
                result = f(*args, **kwargs)
                return result
            finally:
                duration_ms = (time.time() - start) * 1000
                track_performance(user_id, metric_name, duration_ms, {"function": f.__name__}, threshold_ms)

        return wrapped

    return decorator


# ============================================================================
# Database Performance Tracking
# ============================================================================


def track_query_performance(user_id: Any, query_type: str, duration_ms: float, context: Optional[Dict] = None) -> None:
    """
    Track database query performance.

    Args:
        user_id: User ID
        query_type: Type of query (e.g., 'select', 'insert', 'update', 'complex_join')
        duration_ms: Query duration in milliseconds
        context: Additional context (table, filters, etc.)
    """
    track_performance(
        user_id,
        f"db_query.{query_type}",
        duration_ms,
        {"query_type": query_type, **(context or {})},
        threshold_ms=1000,  # Warn if query takes > 1 second
    )


# ============================================================================
# API Performance Tracking
# ============================================================================


def track_api_call(
    user_id: Any, endpoint: str, method: str, status_code: int, duration_ms: float, context: Optional[Dict] = None
) -> None:
    """
    Track API call performance and status.

    Args:
        user_id: User ID
        endpoint: API endpoint
        method: HTTP method
        status_code: Response status code
        duration_ms: Request duration in milliseconds
        context: Additional context
    """
    from app import track_event

    track_event(
        user_id,
        "api_call",
        {
            "endpoint": endpoint,
            "method": method,
            "status_code": status_code,
            "duration_ms": duration_ms,
            "success": 200 <= status_code < 400,
            **(context or {}),
        },
    )


# ============================================================================
# Page Load Tracking
# ============================================================================


def track_page_load(user_id: Any, page_name: str, duration_ms: float, context: Optional[Dict] = None) -> None:
    """
    Track page load performance.

    Args:
        user_id: User ID
        page_name: Name of the page
        duration_ms: Load duration in milliseconds
        context: Additional context
    """
    track_performance(
        user_id,
        f"page_load.{page_name}",
        duration_ms,
        {"page_name": page_name, **(context or {})},
        threshold_ms=3000,  # Warn if page takes > 3 seconds
    )


# ============================================================================
# Export/Report Performance
# ============================================================================


def track_export_performance(
    user_id: Any, export_type: str, row_count: int, duration_ms: float, file_size_bytes: Optional[int] = None
) -> None:
    """
    Track export generation performance.

    Args:
        user_id: User ID
        export_type: Type of export (csv, excel, pdf)
        row_count: Number of rows exported
        duration_ms: Generation duration in milliseconds
        file_size_bytes: Generated file size in bytes
    """
    context = {
        "export_type": export_type,
        "row_count": row_count,
        "rows_per_second": int(row_count / (duration_ms / 1000)) if duration_ms > 0 else 0,
    }

    if file_size_bytes:
        context["file_size_bytes"] = file_size_bytes
        context["file_size_kb"] = round(file_size_bytes / 1024, 2)

    track_performance(
        user_id, f"export.{export_type}", duration_ms, context, threshold_ms=10000  # Warn if export takes > 10 seconds
    )


# ============================================================================
# Health Monitoring
# ============================================================================


def track_health_check(status: str, checks: Dict[str, bool], response_time_ms: float) -> None:
    """
    Track health check results.

    Args:
        status: Overall health status ('healthy', 'degraded', 'unhealthy')
        checks: Dict of individual health checks and their results
        response_time_ms: Health check response time
    """
    if not is_monitoring_enabled():
        return

    from app import track_event

    track_event(
        "system",
        "health_check",
        {
            "status": status,
            "checks": checks,
            "all_healthy": all(checks.values()),
            "response_time_ms": response_time_ms,
            "failed_checks": [k for k, v in checks.items() if not v],
        },
    )


# ============================================================================
# Resource Usage Tracking
# ============================================================================


def track_resource_usage(
    user_id: Any, resource_type: str, usage_amount: float, unit: str, context: Optional[Dict] = None
) -> None:
    """
    Track resource usage (memory, CPU, disk, etc.).

    Args:
        user_id: User ID or 'system'
        resource_type: Type of resource (memory, cpu, disk, api_calls)
        usage_amount: Amount used
        unit: Unit of measurement (mb, percent, count)
        context: Additional context
    """
    from app import track_event

    track_event(
        user_id,
        "resource_usage",
        {"resource_type": resource_type, "usage_amount": usage_amount, "unit": unit, **(context or {})},
    )


# ============================================================================
# Slow Operation Detection
# ============================================================================


def track_slow_operation(
    user_id: Any, operation_name: str, expected_ms: float, actual_ms: float, context: Optional[Dict] = None
) -> None:
    """
    Track operations that exceed expected duration.

    Args:
        user_id: User ID
        operation_name: Name of the operation
        expected_ms: Expected duration in milliseconds
        actual_ms: Actual duration in milliseconds
        context: Additional context
    """
    track_error(
        user_id,
        "slow_operation",
        f"{operation_name} took {actual_ms}ms (expected {expected_ms}ms)",
        {
            "operation": operation_name,
            "expected_ms": expected_ms,
            "actual_ms": actual_ms,
            "slowdown_factor": actual_ms / expected_ms if expected_ms > 0 else 0,
            **(context or {}),
        },
        severity="warning",
    )
