"""Background polling endpoints must not burn the global rate-limit budget (Issue #767).

An idle dashboard polls /timer/status every 30s and /api/timer/status every 60s.
With the previous default of 50/hour per IP, that alone caused 429s within minutes.
"""

import pytest
from flask_limiter.wrappers import LimitGroup

from app import db, limiter
from app.models import User


def _force_strict_default(app, limit="5 per hour"):
    app.config["RATELIMIT_DEFAULT"] = limit
    limiter._default_limits = [p.strip() for p in limit.replace(",", ";").split(";") if p.strip()]
    limiter.limit_manager.set_default_limits(
        [
            LimitGroup(
                limit_provider=limit,
                key_function=limiter._key_func,
            )
        ]
    )
    try:
        limiter.reset()
    except Exception:
        pass


@pytest.mark.routes
def test_timer_status_polling_exempt_from_default_rate_limit(app, authenticated_client):
    """Authenticated /timer/status stays 200 past a strict global default."""
    _force_strict_default(app, "5 per hour")
    for i in range(20):
        response = authenticated_client.get(
            "/timer/status",
            headers={"Accept": "application/json"},
        )
        assert response.status_code == 200, f"request {i + 1} got {response.status_code}"


@pytest.mark.routes
def test_api_timer_status_polling_exempt_from_default_rate_limit(app, authenticated_client):
    """Authenticated /api/timer/status stays 200 past a strict global default."""
    _force_strict_default(app, "5 per hour")
    for i in range(20):
        response = authenticated_client.get(
            "/api/timer/status",
            headers={"Accept": "application/json"},
        )
        assert response.status_code == 200, f"request {i + 1} got {response.status_code}"


@pytest.mark.routes
def test_api_notifications_exempt_from_default_rate_limit(app, authenticated_client):
    """Idle.js polls /api/notifications; must not be rate-limited by the default."""
    _force_strict_default(app, "5 per hour")
    for i in range(20):
        response = authenticated_client.get(
            "/api/notifications",
            headers={"Accept": "application/json"},
        )
        assert response.status_code == 200, f"request {i + 1} got {response.status_code}"


@pytest.mark.routes
def test_service_worker_exempt_from_default_rate_limit(app, client):
    """PWA service-worker updates must not return 429 under a strict default."""
    _force_strict_default(app, "5 per hour")
    for i in range(20):
        response = client.get("/service-worker.js")
        assert response.status_code == 200, f"request {i + 1} got {response.status_code}"


@pytest.mark.routes
def test_rate_limit_json_429_for_accept_json(app, client):
    """Fetch/XHR clients prefer JSON; 429 must not be an HTML error page."""
    _force_strict_default(app, "3 per hour")

    last = None
    for _ in range(10):
        last = client.get("/about", headers={"Accept": "application/json"})
        if last.status_code == 429:
            break

    assert last is not None
    assert last.status_code == 429
    assert last.is_json, f"expected JSON 429, got content-type={last.content_type!r}"
    body = last.get_json()
    assert body.get("error_code") == "rate_limited"
    assert body.get("success") is False


@pytest.mark.routes
def test_rate_limit_keyed_per_authenticated_user(app, client, user):
    """Two logged-in users behind the same IP get separate rate-limit buckets."""
    _force_strict_default(app, "3 per hour")

    other = User(username="otheruser767", role="user", email="other767@example.com")
    other.set_password("password123")
    db.session.add(other)
    db.session.commit()

    # Exhaust user1's budget on a non-exempt page (same client IP throughout)
    client.post("/login", data={"username": user.username, "password": "password123"}, follow_redirects=True)
    for _ in range(10):
        if client.get("/about").status_code == 429:
            break
    else:
        pytest.fail("expected user1 to hit the rate limit on /about")

    # Switch to other user without clearing limiter storage — separate key => still 200
    client.get("/logout", follow_redirects=True)
    client.post(
        "/login",
        data={"username": other.username, "password": "password123"},
        follow_redirects=True,
    )
    r = client.get("/about")
    assert r.status_code == 200, f"other user should have a fresh bucket, got {r.status_code}"
