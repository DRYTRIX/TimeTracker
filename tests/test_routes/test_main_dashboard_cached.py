"""
Tests for main dashboard route with caching.
"""

import pytest

pytestmark = [pytest.mark.unit, pytest.mark.routes]

from unittest.mock import patch
from app.utils.cache import get_cache


# The dashboard route caches two values per user: aggregated stats and
# the time-by-project chart data. Keep these keys in sync with
# ``app/routes/main.py``.
def _dashboard_cache_keys(user_id):
    return (
        f"dashboard:stats:{user_id}",
        f"dashboard:chart:{user_id}",
    )


class TestDashboardCaching:
    """Tests for dashboard route caching"""

    def test_dashboard_uses_cache(self, authenticated_client, app, user, project):
        """Test that dashboard data is cached"""
        cache = get_cache()
        cache.clear()  # Clear cache before test

        # First request should populate cache
        with patch("app.routes.main.track_page_view"):
            response1 = authenticated_client.get("/dashboard")
            assert response1.status_code == 200

            stats_key, chart_key = _dashboard_cache_keys(user.id)
            cached_stats = cache.get(stats_key)
            cached_chart = cache.get(chart_key)
            assert cached_stats is not None
            assert cached_chart is not None
            # Stats payload exposes nested aggregations including today_hours.
            assert "time_tracking" in cached_stats
            assert "today_hours" in cached_stats["time_tracking"]

    def test_dashboard_cache_ttl(self, authenticated_client, app, user):
        """Test that dashboard cache entries are created"""
        cache = get_cache()
        cache.clear()

        with patch("app.routes.main.track_page_view"):
            authenticated_client.get("/dashboard")

            stats_key, chart_key = _dashboard_cache_keys(user.id)
            assert cache.exists(stats_key) is True
            assert cache.exists(chart_key) is True

    def test_dashboard_cache_invalidation(self, authenticated_client, app, user):
        """Test that dashboard cache can be invalidated"""
        cache = get_cache()
        cache.clear()

        with patch("app.routes.main.track_page_view"):
            authenticated_client.get("/dashboard")

            stats_key, chart_key = _dashboard_cache_keys(user.id)
            assert cache.exists(stats_key) is True

            # Invalidate cache
            cache.delete(stats_key)
            cache.delete(chart_key)
            assert cache.exists(stats_key) is False
            assert cache.exists(chart_key) is False

            # Next request should repopulate cache
            authenticated_client.get("/dashboard")
            assert cache.exists(stats_key) is True
            assert cache.exists(chart_key) is True
