"""Auto-detected user timezone: browser reports IANA zone, server follows unless pinned."""

from flask import url_for

import pytest

from app import db


@pytest.fixture
def logged_in_user(client, user):
    client.post("/auth/login", data={"username": "testuser", "password": "password123"}, follow_redirects=True)
    return user


def test_auto_user_follows_reported_timezone(client, logged_in_user):
    logged_in_user.timezone = None
    logged_in_user.timezone_source = "auto"
    db.session.commit()

    resp = client.post("/user/api/timezone", json={"timezone": "Asia/Bangkok"})
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["success"] is True
    assert body["changed"] is True
    assert logged_in_user.timezone == "Asia/Bangkok"


def test_manual_user_is_not_overwritten(client, logged_in_user):
    logged_in_user.timezone = "Europe/Vienna"
    logged_in_user.timezone_source = "manual"
    db.session.commit()

    resp = client.post("/user/api/timezone", json={"timezone": "Asia/Bangkok"})
    assert resp.status_code == 200
    assert resp.get_json().get("ignored") == "manual"
    assert logged_in_user.timezone == "Europe/Vienna"


def test_invalid_timezone_is_rejected(client, logged_in_user):
    logged_in_user.timezone = None
    logged_in_user.timezone_source = "auto"
    db.session.commit()

    resp = client.post("/user/api/timezone", json={"timezone": "Mars/Olympus_Mons"})
    assert resp.status_code == 400
    assert logged_in_user.timezone is None


def test_missing_timezone_is_rejected(client, logged_in_user):
    resp = client.post("/user/api/timezone", json={})
    assert resp.status_code == 400


def test_timezone_endpoint_requires_login(client):
    resp = client.post("/user/api/timezone", json={"timezone": "Asia/Bangkok"})
    assert resp.status_code in (302, 401)


def test_preferences_can_switch_source(client, logged_in_user):
    logged_in_user.timezone_source = "manual"
    db.session.commit()

    resp = client.patch("/user/api/preferences", json={"timezone_source": "auto"})
    assert resp.status_code == 200
    assert logged_in_user.timezone_source == "auto"

    resp = client.patch("/user/api/preferences", json={"timezone_source": "sometimes"})
    assert resp.status_code == 400


def test_settings_form_pins_manual_timezone(client, logged_in_user):
    logged_in_user.timezone_source = "auto"
    db.session.commit()

    resp = client.post(
        url_for("user.settings"),
        data={"timezone": "Europe/Vienna"},
        follow_redirects=True,
    )
    assert resp.status_code == 200
    assert logged_in_user.timezone == "Europe/Vienna"
    assert logged_in_user.timezone_source == "manual"

    # Choosing Automatic clears the pin and lets the device lead again
    resp = client.post(url_for("user.settings"), data={"timezone": "auto"}, follow_redirects=True)
    assert logged_in_user.timezone_source == "auto"
