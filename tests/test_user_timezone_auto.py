"""Auto-detected user timezone: browser reports IANA zone, server follows unless pinned."""

from app import db


def test_auto_user_follows_reported_timezone(authenticated_client, user):
    user.timezone = None
    user.timezone_source = "auto"
    db.session.commit()

    resp = authenticated_client.post("/api/timezone", json={"timezone": "Asia/Bangkok"})
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["success"] is True
    assert body["changed"] is True
    db.session.refresh(user)
    assert user.timezone == "Asia/Bangkok"


def test_manual_user_is_not_overwritten(authenticated_client, user):
    user.timezone = "Europe/Vienna"
    user.timezone_source = "manual"
    db.session.commit()

    resp = authenticated_client.post("/api/timezone", json={"timezone": "Asia/Bangkok"})
    assert resp.status_code == 200
    assert resp.get_json().get("ignored") == "manual"
    db.session.refresh(user)
    assert user.timezone == "Europe/Vienna"


def test_invalid_timezone_is_rejected(authenticated_client, user):
    user.timezone = None
    user.timezone_source = "auto"
    db.session.commit()

    resp = authenticated_client.post("/api/timezone", json={"timezone": "Mars/Olympus_Mons"})
    assert resp.status_code == 400
    db.session.refresh(user)
    assert user.timezone is None


def test_missing_timezone_is_rejected(authenticated_client):
    resp = authenticated_client.post("/api/timezone", json={})
    assert resp.status_code == 400


def test_timezone_endpoint_requires_login(client):
    resp = client.post("/api/timezone", json={"timezone": "Asia/Bangkok"})
    assert resp.status_code in (302, 401)


def test_preferences_can_switch_source(authenticated_client, user):
    user.timezone_source = "manual"
    db.session.commit()

    resp = authenticated_client.patch("/api/preferences", json={"timezone_source": "auto"})
    assert resp.status_code == 200
    db.session.refresh(user)
    assert user.timezone_source == "auto"

    resp = authenticated_client.patch("/api/preferences", json={"timezone_source": "sometimes"})
    assert resp.status_code == 400


def test_settings_form_pins_manual_timezone(authenticated_client, user):
    user.timezone_source = "auto"
    db.session.commit()

    resp = authenticated_client.post(
        "/settings",
        data={"timezone": "Europe/Vienna"},
        follow_redirects=True,
    )
    assert resp.status_code == 200
    db.session.refresh(user)
    assert user.timezone == "Europe/Vienna"
    assert user.timezone_source == "manual"

    # Choosing Automatic clears the pin and lets the device lead again
    resp = authenticated_client.post("/settings", data={"timezone": "auto"}, follow_redirects=True)
    assert resp.status_code == 200
    db.session.refresh(user)
    assert user.timezone_source == "auto"
