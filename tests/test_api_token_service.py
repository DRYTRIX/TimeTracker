"""Tests for ApiTokenService (create, validate scopes, rotate, revoke)."""

import pytest

from app import db
from app.models import ApiToken
from app.services.api_token_service import ApiTokenService

pytestmark = [pytest.mark.unit]


@pytest.mark.unit
def test_create_token_success(app, test_user):
    service = ApiTokenService()

    result = service.create_token(
        user_id=test_user.id,
        name="Test Token",
        description="Test description",
        scopes="read:projects,write:time_entries",
        expires_days=30,
    )

    assert result["success"] is True
    assert result["token"] is not None
    assert result["token"].startswith("tt_")
    assert result["api_token"] is not None
    assert result["api_token"].name == "Test Token"
    assert result["api_token"].user_id == test_user.id
    assert result["api_token"].verify_token(result["token"])


@pytest.mark.unit
def test_create_token_invalid_user(app):
    service = ApiTokenService()

    result = service.create_token(user_id=99999, name="Test Token", scopes="read:projects")

    assert result["success"] is False
    assert result["error"] == "invalid_user"


@pytest.mark.unit
def test_create_token_invalid_scopes(app, test_user):
    service = ApiTokenService()

    result = service.create_token(
        user_id=test_user.id,
        name="Bad scopes",
        scopes="read:projects,invalid:scope",
    )

    assert result["success"] is False
    assert result["error"] == "invalid_scopes"
    assert "invalid:scope" in result["invalid_scopes"]


@pytest.mark.unit
def test_validate_scopes_valid(app):
    service = ApiTokenService()

    result = service.validate_scopes("read:projects,write:time_entries")
    assert result["valid"] is True
    assert result["invalid"] == []


@pytest.mark.unit
def test_validate_scopes_invalid(app):
    service = ApiTokenService()

    result = service.validate_scopes("read:projects,invalid:scope")
    assert result["valid"] is False
    assert "invalid:scope" in result["invalid"]


@pytest.mark.unit
def test_rotate_token(app, test_user):
    service = ApiTokenService()

    create_result = service.create_token(user_id=test_user.id, name="Original Token", scopes="read:projects")
    assert create_result["success"] is True
    original_token_id = create_result["api_token"].id

    rotate_result = service.rotate_token(token_id=original_token_id, user_id=test_user.id)

    assert rotate_result["success"] is True
    assert rotate_result["new_token"] is not None
    assert rotate_result["old_token"].is_active is False
    assert rotate_result["api_token"].id != original_token_id


@pytest.mark.unit
def test_revoke_token_success(app, test_user):
    service = ApiTokenService()
    create_result = service.create_token(user_id=test_user.id, name="To Revoke", scopes="read:projects")
    token_id = create_result["api_token"].id

    revoke_result = service.revoke_token(token_id=token_id, user_id=test_user.id)

    assert revoke_result["success"] is True
    stored = ApiToken.query.get(token_id)
    assert stored is not None
    assert stored.is_active is False


@pytest.mark.unit
def test_revoke_token_permission_denied(app, test_user):
    from app.models import User

    service = ApiTokenService()
    create_result = service.create_token(user_id=test_user.id, name="Owner only", scopes="read:projects")
    token_id = create_result["api_token"].id

    other = User(username="otheruser", role="user", email="otheruser@example.com")
    other.set_password("password123")
    other.is_active = True
    db.session.add(other)
    db.session.commit()

    result = service.revoke_token(token_id=token_id, user_id=other.id)

    assert result["success"] is False
    assert result["error"] == "permission_denied"


@pytest.mark.unit
def test_plain_token_invalid_after_revoke(app, test_user):
    service = ApiTokenService()
    create_result = service.create_token(user_id=test_user.id, name="Verify", scopes="read:projects")
    plain = create_result["token"]
    api_token = create_result["api_token"]

    assert api_token.verify_token(plain) is True
    assert api_token.is_valid() is True

    service.revoke_token(token_id=api_token.id, user_id=test_user.id)
    db.session.refresh(api_token)

    assert api_token.verify_token(plain) is True
    assert api_token.is_valid() is False
    assert api_token.verify_token("tt_not-a-real-token") is False
