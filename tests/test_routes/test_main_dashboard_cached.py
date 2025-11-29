"""
Tests for main dashboard route with caching.
"""

import pytest
from unittest.mock import patch, MagicMock
from app.utils.cache import get_cache


class TestDashboardCaching:
    """Tests for dashboard route caching"""

    def test_dashboard_uses_cache(self, authenticated_client, app, user, project):
        """Test that dashboard data is cached"""
        from app.utils.cache import get_cache

        cache = get_cache()
        cache.clear()  # Clear cache before test

        # First request should populate cache
        with patch("app.routes.main.track_page_view"):
            response1 = authenticated_client.get("/dashboard")
            assert response1.status_code == 200

            # Check cache was set
            cache_key = f"dashboard:{user.id}"
            cached_data = cache.get(cache_key)
            assert cached_data is not None
            assert "active_projects" in cached_data
            assert "today_hours" in cached_data

    def test_dashboard_cache_ttl(self, authenticated_client, app, user):
        """Test that dashboard cache has appropriate TTL"""
        from app.utils.cache import get_cache
        import time

        cache = get_cache()
        cache.clear()

        with patch("app.routes.main.track_page_view"):
            authenticated_client.get("/dashboard")

            cache_key = f"dashboard:{user.id}"
            # Cache should exist
            assert cache.exists(cache_key) is True

    def test_dashboard_cache_invalidation(self, authenticated_client, app, user):
        """Test that dashboard cache can be invalidated"""
        from app.utils.cache import get_cache

        cache = get_cache()
        cache.clear()

        with patch("app.routes.main.track_page_view"):
            # First request
            authenticated_client.get("/dashboard")

            cache_key = f"dashboard:{user.id}"
            assert cache.exists(cache_key) is True

            # Invalidate cache
            cache.delete(cache_key)
            assert cache.exists(cache_key) is False

            # Next request should repopulate cache
            authenticated_client.get("/dashboard")
            assert cache.exists(cache_key) is True
