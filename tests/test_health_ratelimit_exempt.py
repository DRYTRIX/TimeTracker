"""Health/readiness probes must not be subject to the default rate limit.

Render (and similar platforms) probe /_health every few seconds from a fixed
IP. Without exemption those probes would return 429 and trigger unhealthy
restarts / 502s.
"""

import pytest
from flask_limiter.wrappers import LimitGroup

from app import limiter


def _force_strict_default(app, limit="5 per hour"):
    """Temporarily tighten the global default so exemption tests are meaningful."""
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
def test_health_check_exempt_from_default_rate_limit(app, client):
    """/_health must stay 200 even past a strict default limit."""
    assert app.config.get("RATELIMIT_DEFAULT")
    _force_strict_default(app, "5 per hour")

    for i in range(20):
        response = client.get("/_health")
        assert response.status_code == 200, f"request {i + 1} got {response.status_code}"
        assert response.get_json()["status"] == "healthy"


@pytest.mark.routes
def test_ready_check_exempt_from_default_rate_limit(app, client):
    """/_ready must also be exempt so readiness probes are not rate-limited."""
    _force_strict_default(app, "5 per hour")
    for i in range(20):
        response = client.get("/_ready")
        assert response.status_code == 200, f"request {i + 1} got {response.status_code}"


@pytest.mark.routes
def test_api_health_endpoints_exempt_from_default_rate_limit(app, client):
    """API health endpoints used by monitors/frontend probes stay available."""
    _force_strict_default(app, "5 per hour")
    for i in range(20):
        r1 = client.get("/api/health")
        r2 = client.get("/api/v1/health")
        assert r1.status_code == 200, f"/api/health request {i + 1} got {r1.status_code}"
        assert r2.status_code == 200, f"/api/v1/health request {i + 1} got {r2.status_code}"
