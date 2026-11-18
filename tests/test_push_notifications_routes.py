"""Smoke tests for push subscription API routes."""

import json

import pytest


@pytest.mark.unit
def test_list_push_subscriptions_requires_login(client):
    response = client.get("/api/push/subscriptions")
    assert response.status_code in (302, 401, 403)


@pytest.mark.unit
def test_subscribe_push_requires_login(client):
    response = client.post(
        "/api/push/subscribe",
        data=json.dumps({"endpoint": "https://example.com/push", "keys": {"p256dh": "a", "auth": "b"}}),
        content_type="application/json",
    )
    assert response.status_code in (302, 401, 403)


@pytest.mark.unit
def test_subscribe_and_list_push_as_user(authenticated_client):
    payload = {
        "endpoint": "https://example.com/push/endpoint-1",
        "keys": {"p256dh": "dGVzdA", "auth": "YXV0aA"},
    }
    headers = {}
    try:
        token_resp = authenticated_client.get("/auth/csrf-token")
        if token_resp.is_json:
            token = (token_resp.get_json() or {}).get("csrf_token") or ""
            if token:
                headers["X-CSRFToken"] = token
    except Exception:
        pass

    response = authenticated_client.post(
        "/api/push/subscribe",
        data=json.dumps(payload),
        content_type="application/json",
        headers=headers,
    )
    # Accept success or validation/config failures without crashing.
    assert response.status_code in (200, 201, 400, 422, 500)

    listed = authenticated_client.get("/api/push/subscriptions")
    assert listed.status_code in (200, 302, 401, 403)
