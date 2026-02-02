"""
Tests for OIDC logout behavior
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from flask import session, url_for
from app.models import User
from app import db


@pytest.fixture
def oidc_user(app):
    """Create a test user with OIDC linkage."""
    with app.app_context():
        user = User(username="oidc_test_user", email="oidc@example.com", full_name="OIDC Test User")
        # Set OIDC attributes after creation
        user.oidc_issuer = "https://idp.example.com"
        user.oidc_sub = "test-sub-123"
        db.session.add(user)
        db.session.commit()
        yield user
        db.session.delete(user)
        db.session.commit()


@pytest.fixture
def oidc_authenticated_client(client, oidc_user):
    """Client with an authenticated OIDC user."""
    with client:
        with client.session_transaction() as sess:
            sess["_user_id"] = str(oidc_user.id)
            # Legacy compatibility: older versions stored the full token in-session.
            sess["oidc_id_token"] = "mock_id_token_12345"
        yield client


# ============================================================================
# Unit Tests: OIDC Logout Behavior
# ============================================================================


@pytest.mark.unit
@pytest.mark.security
def test_logout_without_post_logout_uri_config(oidc_authenticated_client, app):
    """
    Test that when OIDC_POST_LOGOUT_REDIRECT_URI is not set,
    logout performs local logout only and redirects to login page.

    This fixes the issue where Authelia (and other providers without
    RP-Initiated Logout support) would receive incorrect redirect requests.
    """
    with app.app_context():
        # Ensure OIDC_POST_LOGOUT_REDIRECT_URI is not set
        app.config["AUTH_METHOD"] = "oidc"
        if hasattr(app.config, "OIDC_POST_LOGOUT_REDIRECT_URI"):
            delattr(app.config, "OIDC_POST_LOGOUT_REDIRECT_URI")

        # Mock oauth client to prevent actual OIDC calls
        with patch("app.routes.auth.oauth") as mock_oauth:
            mock_client = MagicMock()
            mock_oauth.create_client.return_value = mock_client

            # Perform logout
            response = oidc_authenticated_client.get("/logout", follow_redirects=False)

            # Should redirect to local login page, NOT to IdP
            assert response.status_code == 302
            assert response.location.endswith("/login")

            # OAuth client should not have been created since no post_logout URI
            mock_oauth.create_client.assert_not_called()


@pytest.mark.unit
@pytest.mark.security
def test_logout_with_post_logout_uri_config(oidc_authenticated_client, app):
    """
    Test that when OIDC_POST_LOGOUT_REDIRECT_URI is set,
    logout attempts RP-Initiated Logout at the provider.
    """
    with app.app_context():
        app.config["AUTH_METHOD"] = "oidc"
        # Mock oauth client and Config
        with patch("app.routes.auth.oauth") as mock_oauth, patch("app.routes.auth.Config") as mock_config:
            # Configure OIDC with post-logout redirect
            mock_config.AUTH_METHOD = "oidc"
            mock_config.OIDC_POST_LOGOUT_REDIRECT_URI = "https://app.example.com/"

            mock_client = MagicMock()
            mock_metadata = {"end_session_endpoint": "https://idp.example.com/logout"}
            mock_client.load_server_metadata.return_value = mock_metadata
            mock_oauth.create_client.return_value = mock_client

            # Perform logout
            response = oidc_authenticated_client.get("/logout", follow_redirects=False)

            # Should redirect to IdP logout endpoint
            assert response.status_code == 302
            assert "idp.example.com/logout" in response.location
            assert "post_logout_redirect_uri" in response.location
            assert "id_token_hint" in response.location


@pytest.mark.unit
@pytest.mark.security
def test_logout_oidc_provider_has_revocation_endpoint_only(oidc_authenticated_client, app):
    """
    Test logout when provider has revocation_endpoint but no end_session_endpoint.
    Should use revocation_endpoint as fallback when post_logout URI is configured.
    """
    with app.app_context():
        app.config["AUTH_METHOD"] = "oidc"
        with patch("app.routes.auth.oauth") as mock_oauth, patch("app.routes.auth.Config") as mock_config:
            mock_config.AUTH_METHOD = "oidc"
            mock_config.OIDC_POST_LOGOUT_REDIRECT_URI = "https://app.example.com/"

            mock_client = MagicMock()
            mock_metadata = {"revocation_endpoint": "https://idp.example.com/revoke"}
            mock_client.load_server_metadata.return_value = mock_metadata
            mock_oauth.create_client.return_value = mock_client

            response = oidc_authenticated_client.get("/logout", follow_redirects=False)

            # Should redirect to revocation endpoint
            assert response.status_code == 302
            assert "idp.example.com/revoke" in response.location


@pytest.mark.unit
@pytest.mark.security
def test_logout_local_auth_method(authenticated_client, app):
    """Test that local auth method doesn't try OIDC logout."""
    with app.app_context():
        app.config["AUTH_METHOD"] = "local"

        with patch("app.routes.auth.oauth") as mock_oauth:
            response = authenticated_client.get("/logout", follow_redirects=False)

            # Should redirect to login
            assert response.status_code == 302
            assert response.location.endswith("/login")

            # Should not attempt OIDC operations
            mock_oauth.create_client.assert_not_called()


@pytest.mark.unit
@pytest.mark.security
def test_logout_clears_oidc_id_token_from_session(oidc_authenticated_client, app):
    """Test that logout removes the OIDC ID token from session."""
    with app.app_context():
        app.config["AUTH_METHOD"] = "oidc"

        with patch("app.routes.auth.oauth"):
            # Verify ID token is in session before logout
            with oidc_authenticated_client.session_transaction() as sess:
                assert "oidc_id_token" in sess
                assert "oidc_id_token_key" not in sess

            # Perform logout
            oidc_authenticated_client.get("/logout", follow_redirects=True)

            # Verify ID token is removed from session
            with oidc_authenticated_client.session_transaction() as sess:
                assert "oidc_id_token" not in sess
                assert "oidc_id_token_key" not in sess


@pytest.mark.unit
@pytest.mark.security
def test_logout_uses_cached_oidc_id_token_hint_when_present(oidc_authenticated_client, app):
    """If oidc_id_token_key is present, logout should use cached token as id_token_hint."""
    with app.app_context():
        app.config["AUTH_METHOD"] = "oidc"

        # Put a small key in session (new behavior)
        with oidc_authenticated_client.session_transaction() as sess:
            sess["oidc_id_token_key"] = "k_test_1"

        fake_cache_store = {"oidc:id_token:k_test_1": "cached_id_token_67890"}

        class FakeCache:
            def get(self, key):
                return fake_cache_store.get(key)

            def delete(self, key):
                fake_cache_store.pop(key, None)

        with patch("app.routes.auth.get_cache", return_value=FakeCache()), patch("app.routes.auth.oauth") as mock_oauth, patch(
            "app.routes.auth.Config"
        ) as mock_config:
            mock_config.AUTH_METHOD = "oidc"
            mock_config.OIDC_POST_LOGOUT_REDIRECT_URI = "https://app.example.com/"
            mock_client = MagicMock()
            mock_client.load_server_metadata.return_value = {"end_session_endpoint": "https://idp.example.com/logout"}
            mock_oauth.create_client.return_value = mock_client

            response = oidc_authenticated_client.get("/logout", follow_redirects=False)

            assert response.status_code == 302
            assert "idp.example.com/logout" in response.location
            assert "id_token_hint=cached_id_token_67890" in response.location
            # Ensure cache entry was cleaned up
            assert "oidc:id_token:k_test_1" not in fake_cache_store


@pytest.mark.unit
@pytest.mark.security
def test_logout_with_both_auth_method_no_post_logout_uri(oidc_authenticated_client, app):
    """
    Test logout with AUTH_METHOD=both and no post_logout URI.
    Should perform local logout only.
    """
    with app.app_context():
        app.config["AUTH_METHOD"] = "both"
        if hasattr(app.config, "OIDC_POST_LOGOUT_REDIRECT_URI"):
            delattr(app.config, "OIDC_POST_LOGOUT_REDIRECT_URI")

        with patch("app.routes.auth.oauth") as mock_oauth:
            response = oidc_authenticated_client.get("/logout", follow_redirects=False)

            # Should redirect to login without OIDC logout
            assert response.status_code == 302
            assert response.location.endswith("/login")
            mock_oauth.create_client.assert_not_called()


@pytest.mark.unit
@pytest.mark.security
def test_logout_provider_metadata_load_fails_gracefully(oidc_authenticated_client, app):
    """Test that logout handles provider metadata loading failures gracefully."""
    with app.app_context():
        with patch("app.routes.auth.oauth") as mock_oauth, patch("app.routes.auth.Config") as mock_config:
            mock_config.AUTH_METHOD = "oidc"
            mock_config.OIDC_POST_LOGOUT_REDIRECT_URI = "https://app.example.com/"

            mock_client = MagicMock()
            # Simulate metadata loading failure
            mock_client.load_server_metadata.side_effect = Exception("Metadata unavailable")
            mock_oauth.create_client.return_value = mock_client

            # Should fall back to local logout
            response = oidc_authenticated_client.get("/logout", follow_redirects=False)

            assert response.status_code == 302
            assert response.location.endswith("/login")


# ============================================================================
# Smoke Tests: OIDC Logout
# ============================================================================


@pytest.mark.smoke
def test_logout_endpoint_exists(client):
    """Smoke test: Ensure logout endpoint is accessible."""
    # Should redirect to login (not 404)
    response = client.get("/logout", follow_redirects=False)
    assert response.status_code in [302, 401]  # Redirect or unauthorized, not 404


@pytest.mark.smoke
def test_logout_configuration_keys_valid(app):
    """Smoke test: Verify OIDC configuration keys are properly defined."""
    with app.app_context():
        from app.config import Config

        # These should be accessible without errors
        auth_method = getattr(Config, "AUTH_METHOD", None)
        assert auth_method in ["local", "oidc", "both", None]

        # OIDC_POST_LOGOUT_REDIRECT_URI should be optional
        post_logout = getattr(Config, "OIDC_POST_LOGOUT_REDIRECT_URI", None)
        # It's fine if it's None or a string
        assert post_logout is None or isinstance(post_logout, str)
