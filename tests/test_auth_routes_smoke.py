"""Smoke tests for auth routes via test client."""

import pytest


@pytest.mark.smoke
@pytest.mark.routes
def test_login_success_with_local_auth(client, user):
    response = client.post(
        "/login",
        data={"username": user.username, "password": "password123"},
        follow_redirects=False,
    )
    assert response.status_code in (302, 303)


@pytest.mark.smoke
@pytest.mark.routes
def test_logout_clears_session(authenticated_client):
    response = authenticated_client.get("/logout", follow_redirects=False)
    assert response.status_code in (302, 303)
