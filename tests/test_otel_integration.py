"""OpenTelemetry tracing, metrics hooks, and OTLP log correlation tests."""

import uuid
from unittest.mock import MagicMock, patch

import pytest


@pytest.fixture
def otel_app(app_config, monkeypatch, tmp_path):
    """Flask app with in-memory OTel export (no network)."""
    monkeypatch.setenv("OTEL_ENABLE_IN_TESTS", "1")
    # Avoid host env OTLP credentials making _export_allowed always true.
    monkeypatch.delenv("OTEL_EXPORTER_OTLP_ENDPOINT", raising=False)
    monkeypatch.delenv("OTEL_EXPORTER_OTLP_TOKEN", raising=False)
    monkeypatch.delenv("ENABLE_TELEMETRY", raising=False)

    from app.telemetry.otel_setup import reset_for_testing

    reset_for_testing()

    unique_db_path = tmp_path / f"otel_{uuid.uuid4().hex}.sqlite"
    config = dict(app_config)
    config["SQLALCHEMY_DATABASE_URI"] = f"sqlite:///{unique_db_path}"

    from app import create_app, db

    application = create_app(config)
    with application.app_context():
        import app.models  # noqa: F401 — register metadata

        db.create_all()
    return application


@pytest.fixture
def otel_client(otel_app):
    return otel_app.test_client()


@pytest.fixture
def otel_app_metrics_opted_in(app_config, monkeypatch, tmp_path):
    """In-memory OTel app with telemetry opt-in so metric recording proceeds."""
    monkeypatch.setenv("OTEL_ENABLE_IN_TESTS", "1")
    monkeypatch.setenv("ENABLE_TELEMETRY", "true")
    monkeypatch.delenv("OTEL_EXPORTER_OTLP_ENDPOINT", raising=False)
    monkeypatch.delenv("OTEL_EXPORTER_OTLP_TOKEN", raising=False)

    from app.telemetry.otel_setup import invalidate_export_allowed_cache, reset_for_testing

    reset_for_testing()
    invalidate_export_allowed_cache()

    unique_db_path = tmp_path / f"otel_m_{uuid.uuid4().hex}.sqlite"
    config = dict(app_config)
    config["SQLALCHEMY_DATABASE_URI"] = f"sqlite:///{unique_db_path}"

    from app import create_app, db

    application = create_app(config)
    with application.app_context():
        import app.models  # noqa: F401

        db.create_all()
    return application


def _collect_metrics(reader):
    """Return list of (scope_name, metric_name, attributes_dict, data_point) tuples."""
    out = []
    data = reader.get_metrics_data()
    if data is None:
        return out
    for rm in data.resource_metrics:
        for sm in rm.scope_metrics:
            scope = sm.scope.name
            for metric in sm.metrics:
                for pt in metric.data.data_points:
                    out.append((scope, metric.name, dict(pt.attributes), pt))
    return out


def test_health_request_emits_span(otel_client):
    resp = otel_client.get("/_health")
    assert resp.status_code == 200
    from app.telemetry.otel_setup import get_test_span_exporter

    exp = get_test_span_exporter()
    assert exp is not None
    spans = exp.get_finished_spans()
    assert len(spans) >= 1


def test_otlp_log_payload_has_trace_and_event_category():
    from app.telemetry.service import _build_otlp_logs_payload

    fake_tid = "a" * 32
    fake_sid = "b" * 16
    with patch("app.telemetry.otel_setup.is_otel_tracing_active", return_value=True):
        with patch(
            "app.telemetry.otel_setup.get_trace_context_for_logs",
            return_value={"trace_id": fake_tid, "span_id": fake_sid},
        ):
            payload = _build_otlp_logs_payload("auth.login", "1", True, {}, "1.0.0")
    rec = payload["resourceLogs"][0]["scopeLogs"][0]["logRecords"][0]["attributes"]
    keys_to_val = {a["key"]: a["value"] for a in rec}
    assert keys_to_val.get("event_category") == {"stringValue": "auth"}
    assert keys_to_val.get("trace_id") == {"stringValue": fake_tid}
    assert keys_to_val.get("span_id") == {"stringValue": fake_sid}


def test_record_background_job_noop_without_metrics():
    from app.telemetry.otel_setup import record_background_job_outcome, reset_for_testing

    reset_for_testing()
    record_background_job_outcome("check_overdue_invoices", True)


def test_http_server_metrics_record_does_not_raise_when_otel_inactive(otel_app):
    from app.telemetry.otel_setup import record_http_server_metrics, reset_for_testing

    reset_for_testing()
    record_http_server_metrics("GET", "/_health", 200, 0.01)


def test_http_metrics_not_recorded_when_opted_out(otel_app, monkeypatch):
    """Without telemetry opt-in, record_* must not emit series."""
    monkeypatch.delenv("ENABLE_TELEMETRY", raising=False)
    from app.telemetry import otel_setup
    from app.telemetry.otel_setup import (
        get_test_metric_reader,
        invalidate_export_allowed_cache,
        record_http_server_metrics,
    )

    # Ensure baked (non-env) credentials path for the gate.
    otel_setup._otlp_credentials_from_env = False
    invalidate_export_allowed_cache()

    reader = get_test_metric_reader()
    assert reader is not None
    record_http_server_metrics("GET", "/_health", 200, 0.01)
    collected = _collect_metrics(reader)
    http_names = {name for _, name, _, _ in collected if name.startswith("http.server")}
    assert http_names == set()


def test_http_metrics_recorded_when_opted_in(otel_app_metrics_opted_in):
    from app.telemetry.otel_setup import (
        _HTTP_DURATION_BOUNDARIES,
        get_test_metric_reader,
        record_http_server_metrics,
    )

    reader = get_test_metric_reader()
    assert reader is not None
    record_http_server_metrics("GET", "/_health", 200, 0.12)
    collected = _collect_metrics(reader)

    duration_pts = [(attrs, pt) for scope, name, attrs, pt in collected if name == "http.server.duration"]
    request_pts = [(attrs, pt) for scope, name, attrs, pt in collected if name == "http.server.requests"]
    assert len(duration_pts) == 1
    assert len(request_pts) == 1

    dur_attrs, dur_pt = duration_pts[0]
    req_attrs, _ = request_pts[0]

    # Histogram: method + status_class only (no route).
    assert dur_attrs.get("http.method") == "GET"
    assert dur_attrs.get("status_class") == "2xx"
    assert "http.route" not in dur_attrs
    assert "app_version" not in dur_attrs
    assert list(dur_pt.explicit_bounds) == list(_HTTP_DURATION_BOUNDARIES)

    # Counter: keeps route + status_class.
    assert req_attrs.get("http.route") == "/_health"
    assert req_attrs.get("status_class") == "2xx"
    assert "app_version" not in req_attrs


def test_http_errors_have_no_route(otel_app_metrics_opted_in):
    from app.telemetry.otel_setup import get_test_metric_reader, record_http_server_metrics

    reader = get_test_metric_reader()
    record_http_server_metrics("POST", "/login", 404, 0.02)
    collected = _collect_metrics(reader)
    error_pts = [attrs for _, name, attrs, _ in collected if name == "http.server.errors"]
    assert len(error_pts) == 1
    assert error_pts[0].get("status_class") == "4xx"
    assert "http.route" not in error_pts[0]
    assert "app_version" not in error_pts[0]


def test_flask_instrumentation_metrics_dropped(otel_app_metrics_opted_in):
    """FlaskInstrumentor metrics must be dropped via View; traces still work."""
    from app.telemetry.otel_setup import get_test_metric_reader, get_test_span_exporter

    client = otel_app_metrics_opted_in.test_client()
    resp = client.get("/_health")
    assert resp.status_code == 200

    # Traces still emitted.
    spans = get_test_span_exporter().get_finished_spans()
    assert len(spans) >= 1

    reader = get_test_metric_reader()
    collected = _collect_metrics(reader)
    flask_scopes = {scope for scope, _, _, _ in collected if scope.startswith("opentelemetry.instrumentation")}
    assert flask_scopes == set()


def test_export_allowed_true_with_env_credentials(monkeypatch):
    from app.telemetry import otel_setup

    monkeypatch.setenv("OTEL_EXPORTER_OTLP_ENDPOINT", "https://example.com/otlp")
    monkeypatch.setenv("OTEL_EXPORTER_OTLP_TOKEN", "secret-token")
    monkeypatch.delenv("ENABLE_TELEMETRY", raising=False)

    with patch("app.telemetry.service._build_otlp_auth_header", return_value="Basic x"):
        with patch(
            "app.config.analytics_defaults.get_analytics_config",
            return_value={"otel_exporter_otlp_endpoint": "", "otel_exporter_otlp_token": ""},
        ):
            conn = otel_setup.resolve_otlp_connection()

    assert conn is not None
    assert otel_setup._otlp_credentials_from_env is True
    otel_setup.invalidate_export_allowed_cache()
    assert otel_setup._export_allowed() is True


def test_export_allowed_false_without_optin_baked_creds(monkeypatch):
    from app.telemetry import otel_setup

    monkeypatch.delenv("OTEL_EXPORTER_OTLP_ENDPOINT", raising=False)
    monkeypatch.delenv("OTEL_EXPORTER_OTLP_TOKEN", raising=False)
    monkeypatch.delenv("ENABLE_TELEMETRY", raising=False)

    with patch(
        "app.config.analytics_defaults.get_analytics_config",
        return_value={
            "otel_exporter_otlp_endpoint": "https://baked.example/otlp",
            "otel_exporter_otlp_token": "baked-token",
        },
    ):
        with patch("app.telemetry.service._build_otlp_auth_header", return_value="Basic y"):
            conn = otel_setup.resolve_otlp_connection()

    assert conn is not None
    assert otel_setup._otlp_credentials_from_env is False
    otel_setup.invalidate_export_allowed_cache()
    with patch("app.utils.telemetry.is_telemetry_enabled", return_value=False):
        assert otel_setup._export_allowed() is False


def test_env_credentials_take_precedence_over_baked(monkeypatch):
    from app.telemetry import otel_setup

    monkeypatch.setenv("OTEL_EXPORTER_OTLP_ENDPOINT", "https://env.example/otlp")
    monkeypatch.setenv("OTEL_EXPORTER_OTLP_TOKEN", "env-token")

    with patch(
        "app.config.analytics_defaults.get_analytics_config",
        return_value={
            "otel_exporter_otlp_endpoint": "https://baked.example/otlp",
            "otel_exporter_otlp_token": "baked-token",
        },
    ):
        with patch("app.telemetry.service._build_otlp_auth_header", side_effect=lambda t: f"Auth {t}"):
            base, headers = otel_setup.resolve_otlp_connection()

    assert base == "https://env.example/otlp"
    assert headers["Authorization"] == "Auth env-token"
    assert otel_setup._otlp_credentials_from_env is True


def test_optin_metric_exporter_skips_when_disallowed():
    from opentelemetry.sdk.metrics.export import MetricExportResult

    from app.telemetry.otel_setup import _OptInMetricExporter, invalidate_export_allowed_cache

    inner = MagicMock()
    inner.export.return_value = MetricExportResult.SUCCESS
    inner._preferred_temporality = None
    inner._preferred_aggregation = None
    wrapper = _OptInMetricExporter(inner)

    invalidate_export_allowed_cache()
    with patch("app.telemetry.otel_setup._export_allowed", return_value=False):
        result = wrapper.export(MagicMock())
    assert result == MetricExportResult.SUCCESS
    inner.export.assert_not_called()

    invalidate_export_allowed_cache()
    with patch("app.telemetry.otel_setup._export_allowed", return_value=True):
        wrapper.export(MagicMock())
    inner.export.assert_called_once()


def test_optin_span_exporter_skips_when_disallowed():
    from opentelemetry.sdk.trace.export import SpanExportResult

    from app.telemetry.otel_setup import _OptInSpanExporter, invalidate_export_allowed_cache

    inner = MagicMock()
    inner.export.return_value = SpanExportResult.SUCCESS
    wrapper = _OptInSpanExporter(inner)

    invalidate_export_allowed_cache()
    with patch("app.telemetry.otel_setup._export_allowed", return_value=False):
        result = wrapper.export([])
    assert result == SpanExportResult.SUCCESS
    inner.export.assert_not_called()
