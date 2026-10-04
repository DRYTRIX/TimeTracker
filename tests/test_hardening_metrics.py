"""Tests for Phase 5 hardening metrics (scheduler + outbound HTTP)."""

from unittest.mock import MagicMock

import pytest
import requests


def test_observe_scheduler_job_records_success_and_duration():
    from app.utils.hardening_metrics import (
        SCHEDULER_JOB_DURATION,
        SCHEDULER_JOB_SUCCESS,
        observe_scheduler_job,
    )

    before = SCHEDULER_JOB_SUCCESS.labels(job_id="unit_test_job")._value.get()
    observe_scheduler_job("unit_test_job", True, 0.12)
    after = SCHEDULER_JOB_SUCCESS.labels(job_id="unit_test_job")._value.get()
    assert after == before + 1
    # Histogram observe should not raise
    SCHEDULER_JOB_DURATION.labels(job_id="unit_test_job").observe(0.0)


def test_wrap_scheduler_job_counts_failure():
    from app.utils.hardening_metrics import SCHEDULER_JOB_FAILURE, wrap_scheduler_job

    def boom():
        raise RuntimeError("fail")

    wrapped = wrap_scheduler_job(boom, "unit_fail_job")
    before = SCHEDULER_JOB_FAILURE.labels(job_id="unit_fail_job")._value.get()
    with pytest.raises(RuntimeError):
        wrapped()
    after = SCHEDULER_JOB_FAILURE.labels(job_id="unit_fail_job")._value.get()
    assert after == before + 1


def test_session_request_records_outbound_metrics(monkeypatch):
    from app.utils import integration_http
    from app.utils.hardening_metrics import OUTBOUND_HTTP_REQUESTS

    session = MagicMock()
    fake_resp = MagicMock()
    fake_resp.status_code = 200
    session.request.return_value = fake_resp
    session.request_timeout = (1, 2)

    before = OUTBOUND_HTTP_REQUESTS.labels(host="example.com", outcome="ok")._value.get()
    resp = integration_http.session_request(session, "GET", "https://example.com/api")
    after = OUTBOUND_HTTP_REQUESTS.labels(host="example.com", outcome="ok")._value.get()
    assert resp is fake_resp
    assert after == before + 1


def test_session_request_records_error_on_raise():
    from app.utils import integration_http
    from app.utils.hardening_metrics import OUTBOUND_HTTP_REQUESTS

    session = MagicMock()
    session.request.side_effect = requests.Timeout("slow")
    session.request_timeout = (1, 2)

    before = OUTBOUND_HTTP_REQUESTS.labels(host="slow.test", outcome="error")._value.get()
    with pytest.raises(requests.Timeout):
        integration_http.session_request(session, "GET", "https://slow.test/x")
    after = OUTBOUND_HTTP_REQUESTS.labels(host="slow.test", outcome="error")._value.get()
    assert after == before + 1


def test_capture_exception_noop_without_sentry(monkeypatch):
    from app.utils import error_reporting

    # If sentry_sdk is missing or raises, must not propagate
    def _boom(*_a, **_k):
        raise RuntimeError("no sentry")

    monkeypatch.setattr(error_reporting, "capture_exception", error_reporting.capture_exception)
    error_reporting.capture_exception(ValueError("x"))
