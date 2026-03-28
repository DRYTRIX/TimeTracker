"""
OpenTelemetry traces and OTLP metrics for TimeTracker.

Initialization is gated on OTLP credentials (same sources as manual log export).
Feature flags: ENABLE_TRACING, ENABLE_METRICS (default true when unset).

Tests: set OTEL_ENABLE_IN_TESTS=1 for in-memory tracing without network export.
"""

from __future__ import annotations

import atexit
import logging
import os
from contextlib import contextmanager
from typing import Any, Dict, Iterator, Optional, Tuple

logger = logging.getLogger(__name__)

_initialized = False
_tracing_enabled = False
_metrics_enabled = False
_flask_app: Any = None

# Metrics instruments (populated in init)
_http_duration: Any = None
_http_requests: Any = None
_http_errors: Any = None
_invoice_created: Any = None
_invoice_duration: Any = None
_report_generated: Any = None
_export_duration: Any = None
_bg_job_success: Any = None
_bg_job_failure: Any = None
_webhook_success: Any = None
_webhook_failure: Any = None

# Test-only span exporter (set when OTEL_ENABLE_IN_TESTS=1)
_test_span_exporter: Any = None


def _env_bool(name: str, default: bool = True) -> bool:
    raw = os.getenv(name)
    if raw is None or raw.strip() == "":
        return default
    return raw.strip().lower() in ("1", "true", "yes", "on")


def _deployment_environment() -> str:
    return (os.getenv("DEPLOYMENT_ENV") or os.getenv("FLASK_ENV") or "production").strip()


def _app_version() -> str:
    try:
        from app.config.analytics_defaults import get_analytics_config

        return str(get_analytics_config().get("app_version") or "unknown")
    except Exception:
        return "unknown"


def _metric_attrs() -> Dict[str, str]:
    return {"environment": _deployment_environment(), "app_version": _app_version()}


def resolve_otlp_connection() -> Optional[Tuple[str, Dict[str, str]]]:
    """
    Return (base_url, headers) for OTLP/HTTP exporters, or None if not configured.
    Base URL has no trailing slash; traces/metrics append /v1/traces and /v1/metrics.
    """
    from app.config.analytics_defaults import get_analytics_config
    from app.telemetry.service import _build_otlp_auth_header

    cfg = get_analytics_config()
    endpoint = (cfg.get("otel_exporter_otlp_endpoint") or os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT") or "").strip()
    token = (cfg.get("otel_exporter_otlp_token") or os.getenv("OTEL_EXPORTER_OTLP_TOKEN") or "").strip()
    if not endpoint or not token:
        return None
    base = endpoint.rstrip("/")
    if base.endswith("/v1/logs"):
        base = base[: -len("/v1/logs")]
    elif base.endswith("/logs") and "/v1/" in base:
        # tolerate .../otlp/v1/logs
        idx = base.rfind("/v1/logs")
        if idx != -1:
            base = base[:idx]
    headers = {"Authorization": _build_otlp_auth_header(token)}
    return base, headers


def install_id_attr() -> Dict[str, str]:
    try:
        from app.utils.installation import get_installation_config

        iid = get_installation_config().get_install_id()
        if iid:
            return {"install_id": str(iid)}
    except Exception:
        pass
    return {}


def trace_user_attrs(user_id: Any) -> Dict[str, str]:
    """user_id on spans only when detailed analytics opt-in; never for metrics."""
    try:
        from app.telemetry.service import is_detailed_analytics_enabled

        if user_id is not None and is_detailed_analytics_enabled():
            return {"user_id": str(user_id)}
    except Exception:
        pass
    return {}


def _flatten_attrs(attrs: Dict[str, Any]) -> Dict[str, Any]:
    out: Dict[str, Any] = {}
    for k, v in attrs.items():
        if v is None:
            continue
        if isinstance(v, (str, int, float, bool)):
            out[k] = v
        else:
            out[k] = str(v)
    return out


@contextmanager
def business_span(name: str, *, user_id: Any = None, **attributes: Any) -> Iterator[None]:
    """Child business span with install_id and optional user_id (opt-in only)."""
    from opentelemetry import trace

    merged = {**install_id_attr(), **attributes}
    merged.update(trace_user_attrs(user_id))
    tracer = trace.get_tracer("timetracker.business")
    with tracer.start_as_current_span(name, attributes=_flatten_attrs(merged)):
        yield


def get_trace_context_for_logs() -> Dict[str, Optional[str]]:
    """Hex trace_id / span_id for log correlation (empty if no valid span)."""
    try:
        from opentelemetry import trace
        from opentelemetry.trace import SpanContext

        span = trace.get_current_span()
        ctx: SpanContext = span.get_span_context()
        if ctx is None or not getattr(ctx, "is_valid", False):
            return {}
        return {
            "trace_id": format(ctx.trace_id, "032x"),
            "span_id": format(ctx.span_id, "016x"),
        }
    except Exception:
        return {}


def is_otel_tracing_active() -> bool:
    return _tracing_enabled


def is_otel_metrics_active() -> bool:
    return _metrics_enabled


def record_http_server_metrics(method: str, route: str, status_code: int, duration_s: float) -> None:
    if not _metrics_enabled or _http_duration is None:
        return
    try:
        base = _metric_attrs()
        attrs = {
            **base,
            "http.method": method or "UNKNOWN",
            "http.route": route or "unknown",
        }
        _http_duration.record(float(duration_s), attrs)
        _http_requests.add(1, attrs)
        if status_code >= 500:
            _http_errors.add(1, {**attrs, "status_class": "5xx"})
        elif status_code >= 400:
            _http_errors.add(1, {**attrs, "status_class": "4xx"})
    except Exception:
        pass


def record_invoice_created() -> None:
    if not _metrics_enabled or _invoice_created is None:
        return
    try:
        _invoice_created.add(1, _metric_attrs())
    except Exception:
        pass


def record_invoice_duration_seconds(seconds: float, operation: str) -> None:
    """
    timetracker.invoice.duration — use operation='pdf' for PDF generation latency,
    operation='create' for create/commit path duration.
    """
    if not _metrics_enabled or _invoice_duration is None:
        return
    try:
        attrs = {**_metric_attrs(), "operation": operation}
        _invoice_duration.record(float(seconds), attrs)
    except Exception:
        pass


def record_report_generated() -> None:
    if not _metrics_enabled or _report_generated is None:
        return
    try:
        _report_generated.add(1, _metric_attrs())
    except Exception:
        pass


def record_export_duration_seconds(seconds: float, export_kind: str) -> None:
    if not _metrics_enabled or _export_duration is None:
        return
    try:
        attrs = {**_metric_attrs(), "export_kind": export_kind}
        _export_duration.record(float(seconds), attrs)
    except Exception:
        pass


def record_background_job_outcome(job_id: str, success: bool) -> None:
    if not _metrics_enabled:
        return
    try:
        attrs = {**_metric_attrs(), "job_id": str(job_id)[:128]}
        if success and _bg_job_success is not None:
            _bg_job_success.add(1, attrs)
        elif not success and _bg_job_failure is not None:
            _bg_job_failure.add(1, attrs)
    except Exception:
        pass


def record_webhook_delivery(event_type: str, success: bool) -> None:
    if not _metrics_enabled:
        return
    try:
        et = (event_type or "unknown")[:128]
        attrs = {**_metric_attrs(), "event_type": et}
        if success and _webhook_success is not None:
            _webhook_success.add(1, attrs)
        elif not success and _webhook_failure is not None:
            _webhook_failure.add(1, attrs)
    except Exception:
        pass


def inject_traceparent_headers(response: Any) -> Any:
    if not _tracing_enabled:
        return response
    try:
        from opentelemetry import propagate

        carrier: Dict[str, str] = {}
        propagate.inject(carrier)
        if carrier.get("traceparent"):
            response.headers["traceparent"] = carrier["traceparent"]
        if carrier.get("tracestate"):
            response.headers["tracestate"] = carrier["tracestate"]
    except Exception:
        pass
    return response


def _active_timers_callback(options: Any) -> Any:
    from opentelemetry.metrics import Observation

    app = _flask_app
    if app is None:
        yield Observation(0, _metric_attrs())
        return
    try:
        with app.app_context():
            from app.models.time_entry import TimeEntry

            n = TimeEntry.query.filter(TimeEntry.end_time.is_(None)).count()
            yield Observation(int(n), _metric_attrs())
    except Exception:
        yield Observation(0, _metric_attrs())


def _shutdown_providers() -> None:
    try:
        from opentelemetry import metrics as metrics_api
        from opentelemetry import trace as trace_api
        from opentelemetry.sdk.metrics import MeterProvider
        from opentelemetry.sdk.trace import TracerProvider

        tp = trace_api.get_tracer_provider()
        if isinstance(tp, TracerProvider):
            tp.shutdown()
        mp = metrics_api.get_meter_provider()
        if isinstance(mp, MeterProvider):
            mp.shutdown()
    except Exception:
        pass


def get_test_span_exporter() -> Any:
    """Only populated when OTEL_ENABLE_IN_TESTS=1 during init."""
    return _test_span_exporter


def reset_for_testing() -> None:
    """Tear down OTel globals so a new Flask app can call init_opentelemetry (pytest only)."""
    global _initialized, _tracing_enabled, _metrics_enabled, _flask_app
    global _http_duration, _http_requests, _http_errors
    global _invoice_created, _invoice_duration, _report_generated, _export_duration
    global _bg_job_success, _bg_job_failure, _webhook_success, _webhook_failure
    global _test_span_exporter

    if not _initialized:
        return
    try:
        if _tracing_enabled:
            from opentelemetry.instrumentation.flask import FlaskInstrumentor
            from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor

            FlaskInstrumentor().uninstrument()
            SQLAlchemyInstrumentor().uninstrument()
    except Exception:
        pass
    # Do not call _shutdown_providers() here: pytest teardown + atexit would double-shutdown
    # MeterProvider and spam SDK warnings. Process exit still runs atexit-registered shutdown.
    _initialized = False
    _tracing_enabled = False
    _metrics_enabled = False
    _flask_app = None
    _http_duration = None
    _http_requests = None
    _http_errors = None
    _invoice_created = None
    _invoice_duration = None
    _report_generated = None
    _export_duration = None
    _bg_job_success = None
    _bg_job_failure = None
    _webhook_success = None
    _webhook_failure = None
    _test_span_exporter = None


def init_opentelemetry(app: Any) -> bool:
    """
    Configure OTLP tracing/metrics and instrument Flask + SQLAlchemy.
    Returns True if any telemetry subsystem was configured.
    """
    global _initialized, _tracing_enabled, _metrics_enabled, _flask_app
    global _http_duration, _http_requests, _http_errors
    global _invoice_created, _invoice_duration, _report_generated, _export_duration
    global _bg_job_success, _bg_job_failure, _webhook_success, _webhook_failure
    global _test_span_exporter

    if _initialized:
        return _tracing_enabled or _metrics_enabled

    _flask_app = app
    bootstrap = os.getenv("TT_BOOTSTRAP_MODE", "").strip().lower()
    if bootstrap == "migrate":
        _initialized = True
        return False

    enable_trace_flag = _env_bool("ENABLE_TRACING", True)
    enable_metrics_flag = _env_bool("ENABLE_METRICS", True)

    testing = bool(app.config.get("TESTING"))
    testing_memory = testing and _env_bool("OTEL_ENABLE_IN_TESTS", False)

    conn = resolve_otlp_connection()
    if not conn and not testing_memory:
        _initialized = True
        return False

    if (
        conn
        and not testing_memory
        and not enable_trace_flag
        and not enable_metrics_flag
    ):
        _initialized = True
        return False

    base, headers = conn if conn else ("http://localhost:4318", {})

    from opentelemetry import metrics as metrics_api
    from opentelemetry import trace as trace_api
    from opentelemetry.instrumentation.flask import FlaskInstrumentor
    from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor
    from opentelemetry.propagate import set_global_textmap
    from opentelemetry.sdk.resources import Resource
    from opentelemetry.trace.propagation.tracecontext import TraceContextTextMapPropagator

    resource_attrs = {
        "service.name": "timetracker",
        "service.version": _app_version(),
        "deployment.environment": _deployment_environment(),
    }
    resource = Resource.create(resource_attrs)

    set_global_textmap(TraceContextTextMapPropagator())

    trace_endpoint = f"{base.rstrip('/')}/v1/traces"
    metrics_endpoint = f"{base.rstrip('/')}/v1/metrics"

    if testing_memory:
        from opentelemetry.sdk.metrics import MeterProvider
        from opentelemetry.sdk.metrics.export import InMemoryMetricReader
        from opentelemetry.sdk.trace import TracerProvider
        from opentelemetry.sdk.trace.export import SimpleSpanProcessor
        from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter

        if enable_trace_flag:
            _test_span_exporter = InMemorySpanExporter()
            tp = TracerProvider(resource=resource)
            tp.add_span_processor(SimpleSpanProcessor(_test_span_exporter))
            trace_api.set_tracer_provider(tp)
            _tracing_enabled = True
        else:
            trace_api.set_tracer_provider(TracerProvider(resource=resource))
            _tracing_enabled = False

        if enable_metrics_flag:
            reader = InMemoryMetricReader()
            mp = MeterProvider(resource=resource, metric_readers=[reader])
            metrics_api.set_meter_provider(mp)
            _metrics_enabled = True
        else:
            _discard_reader = InMemoryMetricReader()
            metrics_api.set_meter_provider(
                MeterProvider(resource=resource, metric_readers=[_discard_reader])
            )
            _metrics_enabled = False
    else:
        from opentelemetry.exporter.otlp.proto.http.metric_exporter import OTLPMetricExporter
        from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
        from opentelemetry.sdk.metrics import MeterProvider
        from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
        from opentelemetry.sdk.trace import TracerProvider
        from opentelemetry.sdk.trace.export import BatchSpanProcessor

        if enable_trace_flag:
            span_exp = OTLPSpanExporter(endpoint=trace_endpoint, headers=headers)
            tp = TracerProvider(resource=resource)
            tp.add_span_processor(BatchSpanProcessor(span_exp))
            trace_api.set_tracer_provider(tp)
            _tracing_enabled = True
        else:
            trace_api.set_tracer_provider(TracerProvider(resource=resource))
            _tracing_enabled = False

        if enable_metrics_flag:
            interval_ms = int(os.getenv("OTEL_METRICS_EXPORT_INTERVAL_MS", "60000"))
            metric_exp = OTLPMetricExporter(endpoint=metrics_endpoint, headers=headers)
            reader = PeriodicExportingMetricReader(metric_exp, export_interval_millis=interval_ms)
            mp = MeterProvider(resource=resource, metric_readers=[reader])
            metrics_api.set_meter_provider(mp)
            _metrics_enabled = True
        else:
            from opentelemetry.sdk.metrics.export import InMemoryMetricReader

            _discard_reader2 = InMemoryMetricReader()
            metrics_api.set_meter_provider(
                MeterProvider(resource=resource, metric_readers=[_discard_reader2])
            )
            _metrics_enabled = False

    if _metrics_enabled:
        meter = metrics_api.get_meter("timetracker", _app_version())

        _http_duration = meter.create_histogram(
            name="http.server.duration",
            description="HTTP server request duration in seconds",
            unit="s",
        )
        _http_requests = meter.create_counter(
            name="http.server.requests",
            description="HTTP server request count",
            unit="1",
        )
        _http_errors = meter.create_counter(
            name="http.server.errors",
            description="HTTP server responses with 4xx/5xx status",
            unit="1",
        )
        _invoice_created = meter.create_counter(
            name="timetracker.invoice.created",
            description="Invoices created",
            unit="1",
        )
        _invoice_duration = meter.create_histogram(
            name="timetracker.invoice.duration",
            description="Invoice-related durations (operation label: pdf | create)",
            unit="s",
        )
        _report_generated = meter.create_counter(
            name="timetracker.report.generated",
            description="Reports generated",
            unit="1",
        )
        _export_duration = meter.create_histogram(
            name="timetracker.export.duration",
            description="Export operation duration",
            unit="s",
        )
        _bg_job_success = meter.create_counter(
            name="background_job.success",
            description="Scheduled job completed successfully",
            unit="1",
        )
        _bg_job_failure = meter.create_counter(
            name="background_job.failure",
            description="Scheduled job failed",
            unit="1",
        )
        _webhook_success = meter.create_counter(
            name="webhook.delivery.success",
            description="Outbound webhook delivery success",
            unit="1",
        )
        _webhook_failure = meter.create_counter(
            name="webhook.delivery.failure",
            description="Outbound webhook delivery failure",
            unit="1",
        )

        meter.create_observable_gauge(
            name="timetracker.active_timers",
            callbacks=[_active_timers_callback],
            description="Count of time entries with no end_time (active timers)",
            unit="1",
        )

    if _tracing_enabled:
        FlaskInstrumentor().instrument_app(app)

    if _tracing_enabled:
        try:
            from app import db

            if db.engine is not None:
                SQLAlchemyInstrumentor().instrument(engine=db.engine)
        except Exception as e:
            logger.warning("SQLAlchemy OpenTelemetry instrumentation skipped: %s", e)

    atexit.register(_shutdown_providers)
    _initialized = True
    logger.info(
        "OpenTelemetry initialized tracing=%s metrics=%s",
        _tracing_enabled,
        _metrics_enabled,
    )
    return True
