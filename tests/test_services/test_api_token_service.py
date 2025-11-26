"""
Tests for ApiTokenService.
"""

import pytest
from app.services import ApiTokenService
from app.models import ApiToken, User
from app import db


@pytest.mark.unit
def test_create_token_success(app, test_user):
    """Test successful token creation"""
    service = ApiTokenService()
    
    result = service.create_token(
        user_id=test_user.id,
        name="Test Token",
        description="Test description",
        scopes="read:projects,write:time_entries",
        expires_days=30
    )
    
    assert result['success'] is True
    assert result['token'] is not None
    assert result['api_token'] is not None
    assert result['api_token'].name == "Test Token"
    assert result['api_token'].user_id == test_user.id


@pytest.mark.unit
def test_create_token_invalid_user(app):
    """Test token creation with invalid user"""
    service = ApiTokenService()
    
    result = service.create_token(
        user_id=99999,  # Non-existent user
        name="Test Token",
        scopes="read:projects"
    )
    
    assert result['success'] is False
    assert result['error'] == 'invalid_user'


@pytest.mark.unit
def test_validate_scopes_valid(app):
    """Test scope validation with valid scopes"""
    service = ApiTokenService()
    
    result = service.validate_scopes("read:projects,write:time_entries")
    assert result['valid'] is True
    assert len(result['invalid']) == 0


@pytest.mark.unit
def test_validate_scopes_invalid(app):
    """Test scope validation with invalid scopes"""
    service = ApiTokenService()
    
    result = service.validate_scopes("read:projects,invalid:scope")
    assert result['valid'] is False
    assert 'invalid:scope' in result['invalid']


@pytest.mark.unit
def test_rotate_token(app, test_user):
    """Test token rotation"""
    service = ApiTokenService()
    
    # Create initial token
    create_result = service.create_token(
        user_id=test_user.id,
        name="Original Token",
        scopes="read:projects"
    )
    
    assert create_result['success'] is True
    original_token_id = create_result['api_token'].id
    
    # Rotate token
    rotate_result = service.rotate_token(
        token_id=original_token_id,
        user_id=test_user.id
    )
    
    assert rotate_result['success'] is True
    assert rotate_result['new_token'] is not None
    assert rotate_result['old_token'].is_active is False
    assert rotate_result['api_token'].id != original_token_id

