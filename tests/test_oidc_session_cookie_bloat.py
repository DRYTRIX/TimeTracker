"""
Regression tests: prevent OIDC login loops due to oversized cookie session.

When the IdP issues a large id_token (often due to group claims), storing it in
Flask's cookie session can overflow cookie limits and cause the browser to drop
or truncate the session, leading to redirect loops back to /login.
"""

import pytest
from unittest.mock import patch


@pytest.mark.unit
@pytest.mark.security
def test_oidc_callback_does_not_store_id_token_in_cookie_session(app, client):
    # Arrange: a large token (bigger than typical cookie limits)
    huge_id_token = "x" * 12000

    token = {
        "id_token": huge_id_token,
        # Provide userinfo in token so the route doesn't need parse_id_token
        "userinfo": {
            "iss": "https://idp.example.com",
            "sub": "sub-123",
            "preferred_username": "oidc_bloat_test",
            "email": "oidc_bloat_test@example.com",
            "groups": ["administrators"],
        },
    }

    class DummyOidcClient:
        def authorize_access_token(self):
            return token

        def userinfo(self, token=None):
            # Return empty to force using token["userinfo"] (still fine)
            return {}

        def parse_id_token(self, token, nonce=None):
            return token.get("userinfo", {})

    # Minimal in-memory cache stub so we can assert storage happened server-side
    stored = {}

    class DummyCache:
        def get(self, key):
            return stored.get(key)

        def set(self, key, value, ttl=None):
            stored[key] = value

        def delete(self, key):
            stored.pop(key, None)

    with app.app_context():
        app.config["AUTH_METHOD"] = "oidc"
        app.config["PERMANENT_SESSION_LIFETIME"] = app.config.get("PERMANENT_SESSION_LIFETIME")

        with patch("app.routes.auth.oauth") as mock_oauth, patch("app.routes.auth.get_cache", return_value=DummyCache()):
            mock_oauth.create_client.return_value = DummyOidcClient()

            # Act: hit callback
            resp = client.get("/auth/oidc/callback", follow_redirects=False)

            # Assert: redirects (successful login flow)
            assert resp.status_code == 302

            # Session should NOT contain the full token
            with client.session_transaction() as sess:
                assert "oidc_id_token" not in sess
                assert "oidc_id_token_key" in sess
                key = sess["oidc_id_token_key"]

            # And the token should be stored server-side under the derived cache key
            assert stored.get(f"oidc:id_token:{key}") == huge_id_token

