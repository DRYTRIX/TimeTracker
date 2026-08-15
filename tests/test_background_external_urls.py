"""Tests for background external URL generation (GitHub issue #730).

Production has no SERVER_NAME; scheduled emails call url_for(_external=True)
outside a request and used to raise RuntimeError. These tests clear SERVER_NAME
to reproduce that condition.
"""

from datetime import date
from unittest.mock import patch

import pytest
from flask import url_for

from app import db
from app.models import User
from app.models.working_time_violation import WorkingTimeViolation
from app.utils.email import send_working_time_limit_exceeded_email
from app.utils.urls import (
    external_url_context,
    get_app_base_url,
    remember_request_base_url,
    safe_external_url_for,
)


@pytest.fixture
def no_server_name(app):
    """Match production: no Flask SERVER_NAME for host matching."""
    previous = app.config.get("SERVER_NAME")
    previous_base = app.config.get("APP_BASE_URL")
    previous_detected = app.config.get("APP_BASE_URL_DETECTED")
    app.config["SERVER_NAME"] = None
    app.config["APP_BASE_URL"] = ""
    app.config.pop("APP_BASE_URL_DETECTED", None)
    yield app
    app.config["SERVER_NAME"] = previous
    app.config["APP_BASE_URL"] = previous_base or ""
    if previous_detected is None:
        app.config.pop("APP_BASE_URL_DETECTED", None)
    else:
        app.config["APP_BASE_URL_DETECTED"] = previous_detected


class TestGetAppBaseUrl:
    def test_prefers_app_base_url(self, no_server_name):
        app = no_server_name
        app.config["APP_BASE_URL"] = "https://time.example.com"
        app.config["APP_BASE_URL_DETECTED"] = "http://localhost:8080/"
        with app.app_context():
            assert get_app_base_url(app) == "https://time.example.com/"

    def test_uses_server_name_when_set(self, no_server_name):
        app = no_server_name
        app.config["SERVER_NAME"] = "time.example.com"
        app.config["PREFERRED_URL_SCHEME"] = "https"
        with app.app_context():
            assert get_app_base_url(app) == "https://time.example.com/"

    def test_uses_detected_when_nothing_configured(self, no_server_name):
        app = no_server_name
        app.config["APP_BASE_URL_DETECTED"] = "https://learned.example.com/"
        with app.app_context():
            assert get_app_base_url(app) == "https://learned.example.com/"

    def test_returns_none_when_unknown(self, no_server_name):
        app = no_server_name
        with app.app_context():
            assert get_app_base_url(app) is None


class TestRememberRequestBaseUrl:
    def test_learns_proxied_host(self, no_server_name, client):
        app = no_server_name
        # Trigger before_request via a real request with forwarded headers
        client.get(
            "/",
            headers={
                "Host": "localhost:8080",
                "X-Forwarded-Host": "time.example.com",
                "X-Forwarded-Proto": "https",
            },
        )
        detected = app.config.get("APP_BASE_URL_DETECTED")
        assert detected is not None
        assert "time.example.com" in detected
        assert detected.startswith("https://")

    def test_health_path_does_not_seed(self, no_server_name, client):
        app = no_server_name
        client.get("/health")
        # /health may 404; still must not seed from localhost health probes
        # Use a path that exists or force remember_request_base_url directly
        with app.test_request_context("http://127.0.0.1:8080/health"):
            remember_request_base_url()
        assert not app.config.get("APP_BASE_URL_DETECTED")

    def test_localhost_does_not_overwrite_good_host(self, no_server_name):
        app = no_server_name
        app.config["APP_BASE_URL_DETECTED"] = "https://time.example.com/"
        with app.test_request_context("http://localhost:8080/dashboard"):
            remember_request_base_url()
        assert app.config["APP_BASE_URL_DETECTED"] == "https://time.example.com/"

    def test_configured_app_base_url_skips_detection(self, no_server_name):
        app = no_server_name
        app.config["APP_BASE_URL"] = "https://configured.example.com"
        with app.test_request_context("https://other.example.com/dashboard"):
            remember_request_base_url()
        assert not app.config.get("APP_BASE_URL_DETECTED")


class TestExternalUrlContext:
    def test_url_for_raises_without_request_or_server_name(self):
        """Minimal Flask app reproduces the production RuntimeError from issue #730."""
        from flask import Flask

        minimal = Flask("url_probe")
        minimal.config["SERVER_NAME"] = None
        minimal.config["APPLICATION_ROOT"] = "/"
        minimal.config["PREFERRED_URL_SCHEME"] = "http"

        @minimal.route("/dashboard")
        def dashboard():
            return "ok"

        with minimal.app_context():
            with pytest.raises(RuntimeError, match="SERVER_NAME"):
                url_for("dashboard", _external=True)

    def test_url_for_works_without_server_name(self, no_server_name):
        app = no_server_name
        app.config["APP_BASE_URL"] = "https://time.example.com"

        with external_url_context(app):
            url = url_for("main.dashboard", _external=True)
            assert url.startswith("https://time.example.com/")

    def test_fallback_when_no_base_url(self, no_server_name):
        app = no_server_name
        with external_url_context(app):
            url = url_for("main.dashboard", _external=True)
            assert url.startswith("http://localhost:8080/")

    def test_safe_external_url_for(self, no_server_name):
        app = no_server_name
        app.config["APP_BASE_URL"] = "https://time.example.com"
        with external_url_context(app):
            assert "time.example.com" in safe_external_url_for("main.dashboard")
            assert safe_external_url_for("this.endpoint.does.not.exist") == ""


class TestIssue730WorkingTimeLimitEmail:
    """Regression: limit emails must send without SERVER_NAME (issue #730)."""

    def test_send_limit_email_builds_absolute_justify_url(self, no_server_name):
        app = no_server_name
        app.config["APP_BASE_URL"] = "https://time.example.com"

        with app.app_context():
            user = User(username="limit_mail_user", role="user", email="limit@example.com")
            user.set_password("testpass123")
            user.email_notifications = True
            db.session.add(user)
            db.session.commit()

            violation = WorkingTimeViolation(
                user_id=user.id,
                period_type=WorkingTimeViolation.PERIOD_DAILY,
                period_start=date(2026, 8, 14),
                period_end=date(2026, 8, 14),
                limit_hours=9.0,
                actual_hours=10.5,
                hours_over=1.5,
                status=WorkingTimeViolation.STATUS_PENDING,
            )
            db.session.add(violation)
            db.session.commit()
            violation_id = violation.id
            user_id = user.id

        captured = {}

        def _capture_send_email(subject, recipients, text_body, html_body=None, sender=None, attachments=None):
            captured["subject"] = subject
            captured["text_body"] = text_body
            captured["html_body"] = html_body

        with external_url_context(app):
            user = db.session.get(User, user_id)
            violation = db.session.get(WorkingTimeViolation, violation_id)
            with patch("app.utils.email.send_email", side_effect=_capture_send_email):
                send_working_time_limit_exceeded_email(user, violation)

        assert captured.get("text_body")
        assert "https://time.example.com/" in captured["text_body"]
        assert str(violation_id) in captured["text_body"]

    def test_check_working_time_limits_sends_without_server_name(self, no_server_name):
        app = no_server_name
        app.config["APP_BASE_URL"] = "https://time.example.com"

        with app.app_context():
            user = User(username="limit_sched_user", role="user", email="sched@example.com")
            user.set_password("testpass123")
            user.email_notifications = True
            db.session.add(user)
            db.session.commit()
            user_id = user.id

            violation = WorkingTimeViolation(
                user_id=user.id,
                period_type=WorkingTimeViolation.PERIOD_DAILY,
                period_start=date(2026, 8, 14),
                period_end=date(2026, 8, 14),
                limit_hours=9.0,
                actual_hours=10.0,
                hours_over=1.0,
                status=WorkingTimeViolation.STATUS_PENDING,
            )
            db.session.add(violation)
            db.session.commit()
            violation_id = violation.id

        sent = []

        def _fake_send(user, violation):
            # Must be able to build an external URL here (as the real sender does)
            url = url_for("workday.violation_justify", violation_id=violation.id, _external=True)
            sent.append(url)

        with patch(
            "app.services.workday_session_service.WorkdaySessionService.auto_close_stale_sessions",
            return_value=0,
        ), patch(
            "app.services.working_time_limit_service.WorkingTimeLimitService.check_user_limits",
            side_effect=lambda u: (
                [db.session.get(WorkingTimeViolation, violation_id)] if u.id == user_id else []
            ),
        ), patch(
            "app.utils.email.send_working_time_limit_exceeded_email",
            side_effect=_fake_send,
        ):
            from app.utils.scheduled_tasks import check_working_time_limits

            with external_url_context(app):
                from app.models import Settings

                settings = Settings.get_settings()
                settings.hour_limits_enabled = True
                settings.hour_limit_email_enabled = True
                db.session.commit()

                count = check_working_time_limits()

        assert count >= 1
        assert sent
        assert all(u.startswith("https://time.example.com/") for u in sent)
