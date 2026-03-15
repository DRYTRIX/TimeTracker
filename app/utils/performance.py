"""
Optional performance instrumentation: slow-request logging and query-count profiling.

Enable via config:
- PERF_LOG_SLOW_REQUESTS_MS: log when request duration exceeds this many ms (0 = disabled)
- PERF_QUERY_PROFILE: when true, track DB query count per request and include in slow-request logs
"""

import logging
from flask import g, request
from sqlalchemy import event
from sqlalchemy.engine import Engine

logger = logging.getLogger("timetracker.perf")


def init_performance_logging(app):
    """
    Register slow-request logging and optional query-count profiling.
    No overhead when PERF_LOG_SLOW_REQUESTS_MS is 0 and PERF_QUERY_PROFILE is False.
    """
    slow_ms = app.config.get("PERF_LOG_SLOW_REQUESTS_MS", 0) or 0
    query_profile = app.config.get("PERF_QUERY_PROFILE", False)

    if query_profile:

        @app.before_request
        def _perf_set_query_count():
            g._perf_query_count = 0

        @event.listens_for(Engine, "before_cursor_execute")
        def _perf_count_query(conn, cursor, statement, parameters, context, executemany):
            if hasattr(g, "_perf_query_count"):
                g._perf_query_count += 1

    @app.after_request
    def _perf_log_slow_requests(response):
        if slow_ms <= 0:
            return response
        try:
            start = getattr(g, "_start_time", None)
            if start is None:
                return response
            duration_ms = (__import__("time").time() - start) * 1000
            if duration_ms < slow_ms:
                return response
            query_count = getattr(g, "_perf_query_count", getattr(g, "query_count", None))
            if query_count is not None:
                logger.warning(
                    "slow_request path=%s duration_ms=%.0f status=%s query_count=%s",
                    request.path, duration_ms, response.status_code, query_count,
                )
            else:
                logger.warning(
                    "slow_request path=%s duration_ms=%.0f status=%s",
                    request.path, duration_ms, response.status_code,
                )
        except Exception:
            pass
        return response
