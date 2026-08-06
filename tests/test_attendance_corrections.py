"""Tests for attendance correction visibility and socket.io room handlers (#709)."""

import importlib.util
import os
from unittest.mock import patch

import pytest
from flask import session
from flask_login import login_user

from app import db
from app.models import User
from app.models.attendance_compliance import (
    AttendanceCorrection,
    AttendanceCorrectionStatus,
    AttendanceWorkPeriod,
    DailyAttendanceRecord,
)
from app.models.time_entry import local_now
from app.services.attendance_compliance_service import AttendanceComplianceService
from app.utils.timezone import convert_app_datetime_to_user, parse_user_local_datetime_from_string


def _load_legacy_api_routes():
    api_module_path = os.path.join(
        os.path.dirname(__file__), "..", "app", "routes", "api.py"
    )
    spec = importlib.util.spec_from_file_location("legacy_api_routes", api_module_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _login(client, username):
    client.post(
        "/login",
        data={"username": username, "password": "password123"},
        follow_redirects=True,
    )


def _cleanup_attendance(user_id):
    AttendanceCorrection.query.filter_by(requested_by=user_id).delete()
    AttendanceWorkPeriod.query.filter_by(user_id=user_id).delete()
    DailyAttendanceRecord.query.filter_by(user_id=user_id).delete()


def _closed_work_period(app, user_id):
    with app.app_context():
        svc = AttendanceComplianceService()
        start = svc.clock_in(user_id, source="manual")
        assert start["success"] is True
        period = start["period"]
        end = local_now().replace(hour=17, minute=0, second=0, microsecond=0)
        period.end_time = end
        period.calculate_duration()
        period.attendance_day.recalculate_totals()
        db.session.commit()
        return {
            "period_id": period.id,
            "attendance_day_id": period.attendance_day_id,
            "start_time": period.start_time,
            "end_time": period.end_time,
        }


@pytest.mark.unit
def test_join_user_room_calls_flask_socketio_join_room(app, user):
    """Regression for #709: join_room must be imported from flask_socketio, not called on SocketIO."""
    legacy_api = _load_legacy_api_routes()
    with app.test_request_context():
        user = db.session.merge(user)
        login_user(user)
        with patch.object(legacy_api, "join_room") as mock_join:
            legacy_api.handle_join_user_room({"user_id": user.id})
            mock_join.assert_called_once_with(f"user_{user.id}")


@pytest.mark.unit
def test_join_client_room_calls_flask_socketio_join_room(app, test_client):
    """Client portal room join must use flask_socketio.join_room."""
    legacy_api = _load_legacy_api_routes()
    with app.test_request_context():
        session["client_portal_id"] = test_client.id
        with patch.object(legacy_api, "join_room") as mock_join:
            legacy_api.handle_join_client_room({})
            mock_join.assert_called_once_with(f"client_portal_{test_client.id}")


@pytest.mark.routes
def test_correction_request_visible_on_history_and_admin(client, app, user, admin_user):
    user_id = user.id
    ctx = _closed_work_period(app, user_id)
    start_local = convert_app_datetime_to_user(ctx["start_time"]).strftime("%Y-%m-%dT%H:%M")
    end_local = convert_app_datetime_to_user(ctx["end_time"]).strftime("%Y-%m-%dT%H:%M")

    try:
        _login(client, user.username)
        response = client.post(
            "/workday/corrections/request",
            data={
                "entity_type": "AttendanceWorkPeriod",
                "attendance_day_id": ctx["attendance_day_id"],
                "entity_id": ctx["period_id"],
                "start_time": start_local,
                "end_time": end_local,
                "reason": "Forgot to adjust leave time",
            },
            follow_redirects=True,
        )
        assert response.status_code == 200

        with app.app_context():
            correction = AttendanceCorrection.query.filter_by(requested_by=user_id).first()
            assert correction is not None
            assert correction.status == AttendanceCorrectionStatus.PENDING

        history = client.get("/workday/history")
        assert history.status_code == 200
        history_body = history.data.decode("utf-8", errors="replace")
        assert "My correction requests" in history_body or "Forgot to adjust leave time" in history_body

        _login(client, admin_user.username)
        with app.app_context():
            pending = AttendanceComplianceService().list_pending_corrections()
            assert any(c.reason == "Forgot to adjust leave time" for c in pending)
    finally:
        with app.app_context():
            _cleanup_attendance(user_id)
            db.session.commit()


@pytest.mark.routes
def test_correction_timezone_roundtrip(client, app, user):
    user_id = user.id
    with app.app_context():
        db_user = db.session.get(User, user_id)
        db_user.timezone = "America/New_York"
        db.session.commit()

    ctx = _closed_work_period(app, user_id)
    with app.app_context():
        db_user = db.session.get(User, user_id)
        start_local = convert_app_datetime_to_user(ctx["start_time"], user=db_user).strftime("%Y-%m-%dT%H:%M")
        end_local = convert_app_datetime_to_user(ctx["end_time"], user=db_user).strftime("%Y-%m-%dT%H:%M")

    try:
        _login(client, user.username)
        response = client.post(
            "/workday/corrections/request",
            data={
                "entity_type": "AttendanceWorkPeriod",
                "attendance_day_id": ctx["attendance_day_id"],
                "entity_id": ctx["period_id"],
                "start_time": start_local,
                "end_time": end_local,
                "reason": "Timezone round-trip test",
            },
            follow_redirects=True,
        )
        assert response.status_code == 200

        with app.app_context():
            db_user = db.session.get(User, user_id)
            correction = AttendanceCorrection.query.filter_by(requested_by=user_id).first()
            assert correction is not None
            corrected = correction.corrected_values
            parsed_start = parse_user_local_datetime_from_string(start_local, user=db_user)
            parsed_end = parse_user_local_datetime_from_string(end_local, user=db_user)
            assert corrected["start_time"] == parsed_start.isoformat()
            assert corrected["end_time"] == parsed_end.isoformat()
            assert parsed_start.replace(second=0, microsecond=0) == ctx["start_time"].replace(
                second=0, microsecond=0
            )
            assert parsed_end == ctx["end_time"]
    finally:
        with app.app_context():
            db_user = db.session.get(User, user_id)
            db_user.timezone = None
            _cleanup_attendance(user_id)
            db.session.commit()
