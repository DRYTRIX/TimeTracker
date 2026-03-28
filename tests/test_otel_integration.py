"""OpenTelemetry tracing, metrics hooks, and OTLP log correlation tests."""

import uuid
from unittest.mock import patch

import pytest


@pytest.fixture
def otel_app(app_config, monkeypatch, tmp_path):
    """Flask app with in-memory OTel export (no network)."""
    monkeypatch.setenv("OTEL_ENABLE_IN_TESTS", "1")

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
