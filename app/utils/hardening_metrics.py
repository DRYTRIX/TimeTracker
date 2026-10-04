"""
Prometheus metrics for scheduler jobs and outbound integration HTTP.

Kept separate from the HTTP request counters in app/__init__.py so
background/outbound instrumentation stays light and self-contained.
"""

from __future__ import annotations

import logging
from functools import wraps
from time import perf_counter
from typing import Any, Callable, Optional
from urllib.parse import urlparse

from prometheus_client import Counter, Histogram

logger = logging.getLogger(__name__)

SCHEDULER_JOB_SUCCESS = Counter(
    "tt_scheduler_job_success_total",
    "Scheduled jobs completed without raising",
    ["job_id"],
)
SCHEDULER_JOB_FAILURE = Counter(
    "tt_scheduler_job_failure_total",
    "Scheduled jobs that raised an exception",
    ["job_id"],
)
SCHEDULER_JOB_DURATION = Histogram(
    "tt_scheduler_job_duration_seconds",
    "Scheduled job wall-clock duration",
    ["job_id"],
    buckets=(0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 15.0, 60.0, 300.0),
)

OUTBOUND_HTTP_REQUESTS = Counter(
    "tt_outbound_http_requests_total",
    "Outbound integration HTTP requests",
    ["host", "outcome"],
)
OUTBOUND_HTTP_LATENCY = Histogram(
    "tt_outbound_http_latency_seconds",
    "Outbound integration HTTP latency",
    ["host"],
    buckets=(0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0, 30.0),
)


def _safe_job_id(job_id: Optional[str]) -> str:
    return (job_id or "unknown")[:128]


def _host_label(url: str) -> str:
    try:
        host = (urlparse(url).hostname or "unknown").lower()
        return host[:128] or "unknown"
    except Exception:
        return "unknown"


def observe_scheduler_job(job_id: str, success: bool, duration_s: float) -> None:
    """Record scheduler job success/failure and duration."""
    try:
        label = _safe_job_id(job_id)
        SCHEDULER_JOB_DURATION.labels(job_id=label).observe(max(0.0, float(duration_s)))
        if success:
            SCHEDULER_JOB_SUCCESS.labels(job_id=label).inc()
        else:
            SCHEDULER_JOB_FAILURE.labels(job_id=label).inc()
    except Exception:
        logger.debug("Failed to record scheduler job metrics", exc_info=True)


def wrap_scheduler_job(func: Callable[..., Any], job_id: str) -> Callable[..., Any]:
    """Wrap a scheduled job callable to record Prometheus metrics."""

    @wraps(func)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        start = perf_counter()
        success = False
        try:
            result = func(*args, **kwargs)
            success = True
            return result
        finally:
            observe_scheduler_job(job_id, success, perf_counter() - start)

    return wrapper


def observe_outbound_http(host: str, outcome: str, duration_s: float) -> None:
    """Record outbound HTTP latency and outcome (ok / http_error / error)."""
    try:
        label = (host or "unknown")[:128]
        outcome_label = (outcome or "error")[:32]
        OUTBOUND_HTTP_LATENCY.labels(host=label).observe(max(0.0, float(duration_s)))
        OUTBOUND_HTTP_REQUESTS.labels(host=label, outcome=outcome_label).inc()
    except Exception:
        logger.debug("Failed to record outbound HTTP metrics", exc_info=True)


def host_from_url(url: str) -> str:
    """Public helper for callers that already have a URL."""
    return _host_label(url)
