"""
Tests for enhanced API authentication with IP whitelisting and better error handling.
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, MagicMock
from flask import Flask, g
from app.models import ApiToken, User
from app.utils.api_auth import authenticate_token, require_api_token, extract_token_from_request
from app import db


class TestExtractToken:
    """Tests for token extraction from requests"""

    def test_extract_from_bearer_header(self):
        """Test extracting token from Bearer Authorization header"""
        from flask import Flask, request

        app = Flask(__name__)

        with app.test_request_context(headers={"Authorization": "Bearer tt_testtoken123"}):
            token = extract_token_from_request()
            assert token == "tt_testtoken123"

    def test_extract_from_token_header(self):
        """Test extracting token from Token Authorization header"""
        from flask import Flask, request

        app = Flask(__name__)

        with app.test_request_context(headers={"Authorization": "Token tt_testtoken123"}):
            token = extract_token_from_request()
            assert token == "tt_testtoken123"

    def test_extract_from_api_key_header(self):
        """Test extracting token from X-API-Key header"""
        from flask import Flask, request

        app = Flask(__name__)

        with app.test_request_context(headers={"X-API-Key": "tt_testtoken123"}):
            token = extract_token_from_request()
            assert token == "tt_testtoken123"

    def test_extract_none_when_missing(self):
        """Test that None is returned when no token is present"""
        from flask import Flask, request

        app = Flask(__name__)

        with app.test_request_context():
            token = extract_token_from_request()
            assert token is None


class TestAuthenticateToken:
    """Tests for token authentication with enhanced security"""

    @pytest.fixture
    def sample_user(self, app):
        """Create a sample user for testing"""
        user = User(username="testuser", is_active=True)
        db.session.add(user)
        db.session.commit()
        return user

    @pytest.fixture
    def sample_token(self, app, sample_user):
        """Create a sample API token"""
        token, plain_token = ApiToken.create_token(
            user_id=sample_user.id, name="Test Token", scopes="read:projects", expires_days=30
        )
        db.session.add(token)
        db.session.commit()
        return token, plain_token

    def test_authenticate_valid_token(self, app, sample_user, sample_token):
        """Test authentication with valid token"""
        token, plain_token = sample_token

        with app.test_request_context(remote_addr="127.0.0.1"):
            user, api_token, error = authenticate_token(plain_token)

            assert user is not None
            assert api_token is not None
            assert error is None
            assert user.id == sample_user.id
            assert api_token.id == token.id

    def test_authenticate_expired_token(self, app, sample_user):
        """Test authentication with expired token"""
        token, plain_token = ApiToken.create_token(
            user_id=sample_user.id, name="Expired Token", expires_days=-1  # Expired
        )
        token.expires_at = datetime.utcnow() - timedelta(days=1)
        db.session.add(token)
        db.session.commit()

        with app.test_request_context(remote_addr="127.0.0.1"):
            user, api_token, error = authenticate_token(plain_token)

            assert user is None
            assert api_token is None
            assert error == "Token has expired"

    def test_authenticate_revoked_token(self, app, sample_user, sample_token):
        """Test authentication with revoked token"""
        token, plain_token = sample_token
        token.is_active = False
        db.session.commit()

        with app.test_request_context(remote_addr="127.0.0.1"):
            user, api_token, error = authenticate_token(plain_token)

            assert user is None
            assert api_token is None
            assert error == "Token has been revoked"

    def test_authenticate_with_ip_whitelist_allowed(self, app, sample_user):
        """Test authentication with IP whitelist - allowed IP"""
        token, plain_token = ApiToken.create_token(
            user_id=sample_user.id, name="Whitelisted Token", scopes="read:projects"
        )
        token.ip_whitelist = "127.0.0.1,192.168.1.0/24"
        db.session.add(token)
        db.session.commit()

        with app.test_request_context(remote_addr="127.0.0.1"):
            user, api_token, error = authenticate_token(plain_token)

            assert user is not None
            assert api_token is not None
            assert error is None

    def test_authenticate_with_ip_whitelist_denied(self, app, sample_user):
        """Test authentication with IP whitelist - denied IP"""
        token, plain_token = ApiToken.create_token(
            user_id=sample_user.id, name="Whitelisted Token", scopes="read:projects"
        )
        token.ip_whitelist = "192.168.1.0/24"
        db.session.add(token)
        db.session.commit()

        with app.test_request_context(remote_addr="10.0.0.1"):
            user, api_token, error = authenticate_token(plain_token)

            assert user is None
            assert api_token is None
            assert error == "Access denied from this IP address"

    def test_authenticate_with_cidr_block(self, app, sample_user):
        """Test authentication with CIDR block in whitelist"""
        token, plain_token = ApiToken.create_token(user_id=sample_user.id, name="CIDR Token", scopes="read:projects")
        token.ip_whitelist = "192.168.1.0/24"
        db.session.add(token)
        db.session.commit()

        with app.test_request_context(remote_addr="192.168.1.100"):
            user, api_token, error = authenticate_token(plain_token)

            assert user is not None
            assert api_token is not None
            assert error is None

    def test_authenticate_invalid_token_format(self, app):
        """Test authentication with invalid token format"""
        with app.test_request_context(remote_addr="127.0.0.1"):
            user, api_token, error = authenticate_token("invalid_token")

            assert user is None
            assert api_token is None
            assert error == "Invalid token format"

    def test_authenticate_nonexistent_token(self, app):
        """Test authentication with non-existent token"""
        fake_token = "tt_" + "x" * 32

        with app.test_request_context(remote_addr="127.0.0.1"):
            user, api_token, error = authenticate_token(fake_token)

            assert user is None
            assert api_token is None
            assert error == "Token not found"

    def test_authenticate_inactive_user(self, app, sample_token):
        """Test authentication with inactive user"""
        token, plain_token = sample_token
        token.user.is_active = False
        db.session.commit()

        with app.test_request_context(remote_addr="127.0.0.1"):
            user, api_token, error = authenticate_token(plain_token)

            assert user is None
            assert api_token is None
            assert error == "User account is inactive"


class TestRequireApiToken:
    """Tests for require_api_token decorator"""

    @pytest.fixture
    def app_with_routes(self, app):
        """Create Flask app with test routes"""

        @app.route("/test/protected")
        @require_api_token("read:projects")
        def protected_route():
            return {"message": "success", "user_id": g.api_user.id}

        @app.route("/test/protected_no_scope")
        @require_api_token()
        def protected_route_no_scope():
            return {"message": "success"}

        return app

    def test_protected_route_with_valid_token(self, app_with_routes, sample_user, sample_token):
        """Test accessing protected route with valid token"""
        token, plain_token = sample_token

        with app_with_routes.test_client() as client:
            response = client.get("/test/protected", headers={"Authorization": f"Bearer {plain_token}"})

            assert response.status_code == 200
            data = response.get_json()
            assert data["message"] == "success"
            assert data["user_id"] == sample_user.id

    def test_protected_route_without_token(self, app_with_routes):
        """Test accessing protected route without token"""
        with app_with_routes.test_client() as client:
            response = client.get("/test/protected")

            assert response.status_code == 401
            data = response.get_json()
            assert "error" in data
            assert "Authentication required" in data["error"]

    def test_protected_route_with_insufficient_scope(self, app_with_routes, sample_user):
        """Test accessing protected route with insufficient scope"""
        token, plain_token = ApiToken.create_token(
            user_id=sample_user.id, name="Limited Token", scopes="read:time_entries"  # Different scope
        )
        db.session.add(token)
        db.session.commit()

        with app_with_routes.test_client() as client:
            response = client.get("/test/protected", headers={"Authorization": f"Bearer {plain_token}"})

            assert response.status_code == 403
            data = response.get_json()
            assert "error" in data
            assert "Insufficient permissions" in data["error"]

    def test_protected_route_with_wildcard_scope(self, app_with_routes, sample_user):
        """Test accessing protected route with wildcard scope"""
        token, plain_token = ApiToken.create_token(
            user_id=sample_user.id, name="Admin Token", scopes="read:*"  # Wildcard scope
        )
        db.session.add(token)
        db.session.commit()

        with app_with_routes.test_client() as client:
            response = client.get("/test/protected", headers={"Authorization": f"Bearer {plain_token}"})

            assert response.status_code == 200
            data = response.get_json()
            assert data["message"] == "success"
