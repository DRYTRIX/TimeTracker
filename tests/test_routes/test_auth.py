"""
Web auth route tests: login page, success redirect, wrong password.
"""

import pytest

pytestmark = [pytest.mark.routes, pytest.mark.integration]


def test_login_page_returns_200(client):
    """GET /login returns 200 and shows login form."""
    resp = client.get("/login")
    assert resp.status_code == 200
    data = resp.get_data(as_text=True)
    assert "login" in data.lower() or "username" in data.lower() or "sign" in data.lower()


def test_login_success_redirects(client, user):
    """POST /login with valid credentials redirects or ends on dashboard."""
    resp = client.post(
        "/login",
        data={"username": user.username, "password": "password123"},
        follow_redirects=True,
    )
    # Either we got a redirect (302/303) and followed to dashboard, or direct 200 dashboard
    assert resp.status_code == 200
    data = resp.get_data(as_text=True)
    # Should not still be on login form (no "Invalid" or "password" error for success path)
    # and should show dashboard or main app content
    assert "dashboard" in data.lower() or "welcome" in data.lower() or "timer" in data.lower() or "project" in data.lower()


def test_login_wrong_password_returns_200_with_message(client, user):
    """POST /login with wrong password returns 200 and error message, no redirect to dashboard."""
    resp = client.post(
        "/login",
        data={"username": user.username, "password": "wrongpassword"},
        follow_redirects=True,
    )
    assert resp.status_code == 200
    data = resp.get_data(as_text=True)
    # Should still be on login page (login form or error message present)
    assert "login" in data.lower() or "invalid" in data.lower() or "password" in data.lower() or "username" in data.lower()
    # Should not be dashboard
    assert "dashboard" not in data.lower() or "login" in data.lower()
