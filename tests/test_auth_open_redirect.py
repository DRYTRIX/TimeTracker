"""Auth login must not open-redirect via next=."""

import pytest

pytestmark = [pytest.mark.security, pytest.mark.routes]


def test_login_rejects_protocol_relative_next(client, user):
    resp = client.post(
        "/login?next=//evil.com",
        data={"username": user.username, "password": "password123"},
        follow_redirects=False,
    )
    assert resp.status_code in (302, 303)
    location = resp.headers.get("Location", "")
    assert "evil.com" not in location
    assert "/dashboard" in location or location.endswith("/")


def test_login_accepts_safe_next_dashboard(client, user):
    resp = client.post(
        "/login?next=/dashboard",
        data={"username": user.username, "password": "password123"},
        follow_redirects=False,
    )
    assert resp.status_code in (302, 303)
    location = resp.headers.get("Location", "")
    assert "evil.com" not in location
    assert "/dashboard" in location
