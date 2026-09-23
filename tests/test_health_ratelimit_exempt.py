"""Health/readiness probes must not be subject to the default rate limit.

Render (and similar platforms) probe /_health every few seconds from a fixed
IP. With RATELIMIT_DEFAULT of "50 per hour", those probes would otherwise
return 429 after ~4 minutes and trigger unhealthy restarts / 502s.
"""

import pytest


@pytest.mark.routes
def test_health_check_exempt_from_default_rate_limit(app, client):
    """/_health must stay 200 even past the default 50-per-hour limit."""
    assert "50 per hour" in (app.config.get("RATELIMIT_DEFAULT") or "")

    for i in range(55):
        response = client.get("/_health")
        assert response.status_code == 200, f"request {i + 1} got {response.status_code}"
        assert response.get_json()["status"] == "healthy"


@pytest.mark.routes
def test_ready_check_exempt_from_default_rate_limit(client):
    """/_ready must also be exempt so readiness probes are not rate-limited."""
    for i in range(55):
        response = client.get("/_ready")
        assert response.status_code == 200, f"request {i + 1} got {response.status_code}"


@pytest.mark.routes
def test_api_health_endpoints_exempt_from_default_rate_limit(client):
    """API health endpoints used by monitors/frontend probes stay available."""
    for i in range(55):
        r1 = client.get("/api/health")
        r2 = client.get("/api/v1/health")
        assert r1.status_code == 200, f"/api/health request {i + 1} got {r1.status_code}"
        assert r2.status_code == 200, f"/api/v1/health request {i + 1} got {r2.status_code}"
