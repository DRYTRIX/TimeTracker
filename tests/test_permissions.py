"""Tests for the advanced permission system"""

import pytest
from app import db
from app.models import User, Permission, Role


@pytest.mark.unit
@pytest.mark.models
def test_permission_creation(app):
    """Test permission creation"""
    with app.app_context():
        permission = Permission(name="test_permission", description="Test permission", category="testing")
        db.session.add(permission)
        db.session.commit()

        assert permission.id is not None
        assert permission.name == "test_permission"
        assert permission.description == "Test permission"
        assert permission.category == "testing"


@pytest.mark.unit
@pytest.mark.models
def test_role_creation(app):
    """Test role creation"""
    with app.app_context():
        role = Role(name="test_role", description="Test role", is_system_role=False)
        db.session.add(role)
        db.session.commit()

        assert role.id is not None
        assert role.name == "test_role"
        assert role.description == "Test role"
        assert role.is_system_role is False


@pytest.mark.unit
@pytest.mark.models
def test_role_permission_assignment(app):
    """Test assigning permissions to a role"""
    with app.app_context():
        # Create permission
        permission1 = Permission(name="perm1", category="test")
        permission2 = Permission(name="perm2", category="test")
        db.session.add_all([permission1, permission2])

        # Create role
        role = Role(name="test_role")
        db.session.add(role)
        db.session.commit()

        # Assign permissions
        role.add_permission(permission1)
        role.add_permission(permission2)
        db.session.commit()

        assert len(role.permissions) == 2
        assert role.has_permission("perm1")
        assert role.has_permission("perm2")
        assert not role.has_permission("perm3")


@pytest.mark.unit
@pytest.mark.models
def test_role_permission_removal(app):
    """Test removing permissions from a role"""
    with app.app_context():
        permission = Permission(name="perm1", category="test")
        db.session.add(permission)

        role = Role(name="test_role")
        db.session.add(role)
        db.session.commit()

        # Add and remove permission
        role.add_permission(permission)
        db.session.commit()
        assert role.has_permission("perm1")

        role.remove_permission(permission)
        db.session.commit()
        assert not role.has_permission("perm1")


@pytest.mark.unit
@pytest.mark.models
def test_user_role_assignment(app):
    """Test assigning roles to users"""
    with app.app_context():
        user = User(username="testuser", role="user")
        db.session.add(user)

        role = Role(name="test_role")
        db.session.add(role)
        db.session.commit()

        # Assign role to user
        user.add_role(role)
        db.session.commit()

        assert len(user.roles) == 1
        assert role in user.roles


@pytest.mark.unit
@pytest.mark.models
def test_user_permission_check(app):
    """Test checking if user has specific permissions"""
    with app.app_context():
        # Create user
        user = User(username="testuser", role="user")
        db.session.add(user)

        # Create permissions
        perm1 = Permission(name="perm1", category="test")
        perm2 = Permission(name="perm2", category="test")
        perm3 = Permission(name="perm3", category="test")
        db.session.add_all([perm1, perm2, perm3])

        # Create role with permissions
        role = Role(name="test_role")
        db.session.add(role)
        db.session.commit()

        role.add_permission(perm1)
        role.add_permission(perm2)
        db.session.commit()

        # Assign role to user
        user.add_role(role)
        db.session.commit()

        # Test permission checks
        assert user.has_permission("perm1")
        assert user.has_permission("perm2")
        assert not user.has_permission("perm3")


@pytest.mark.unit
@pytest.mark.models
def test_user_has_any_permission(app):
    """Test checking if user has any of specified permissions"""
    with app.app_context():
        user = User(username="testuser", role="user")
        db.session.add(user)

        perm1 = Permission(name="perm1", category="test")
        perm2 = Permission(name="perm2", category="test")
        db.session.add_all([perm1, perm2])

        role = Role(name="test_role")
        db.session.add(role)
        db.session.commit()

        role.add_permission(perm1)
        user.add_role(role)
        db.session.commit()

        # User has perm1 but not perm2
        assert user.has_any_permission("perm1", "perm2")
        assert user.has_any_permission("perm1")
        assert not user.has_any_permission("perm2", "perm3")


@pytest.mark.unit
@pytest.mark.models
def test_user_has_all_permissions(app):
    """Test checking if user has all specified permissions"""
    with app.app_context():
        user = User(username="testuser", role="user")
        db.session.add(user)

        perm1 = Permission(name="perm1", category="test")
        perm2 = Permission(name="perm2", category="test")
        perm3 = Permission(name="perm3", category="test")
        db.session.add_all([perm1, perm2, perm3])

        role = Role(name="test_role")
        db.session.add(role)
        db.session.commit()

        role.add_permission(perm1)
        role.add_permission(perm2)
        user.add_role(role)
        db.session.commit()

        # User has perm1 and perm2, but not perm3
        assert user.has_all_permissions("perm1", "perm2")
        assert user.has_all_permissions("perm1")
        assert not user.has_all_permissions("perm1", "perm2", "perm3")


@pytest.mark.unit
@pytest.mark.models
def test_user_get_all_permissions(app):
    """Test getting all permissions for a user"""
    with app.app_context():
        user = User(username="testuser", role="user")
        db.session.add(user)

        # Create permissions and two roles
        perm1 = Permission(name="perm1", category="test")
        perm2 = Permission(name="perm2", category="test")
        perm3 = Permission(name="perm3", category="test")
        db.session.add_all([perm1, perm2, perm3])

        role1 = Role(name="role1")
        role2 = Role(name="role2")
        db.session.add_all([role1, role2])
        db.session.commit()

        # Assign permissions to roles
        role1.add_permission(perm1)
        role1.add_permission(perm2)
        role2.add_permission(perm2)  # Duplicate permission in both roles
        role2.add_permission(perm3)

        # Assign both roles to user
        user.add_role(role1)
        user.add_role(role2)
        db.session.commit()

        # Get all permissions (should be deduplicated)
        all_permissions = user.get_all_permissions()
        permission_names = [p.name for p in all_permissions]

        assert len(all_permissions) == 3
        assert "perm1" in permission_names
        assert "perm2" in permission_names
        assert "perm3" in permission_names


@pytest.mark.unit
@pytest.mark.models
def test_legacy_admin_user_permissions(app):
    """Test that legacy admin users (without roles) still have all permissions"""
    with app.app_context():
        # Create a legacy admin user (with role='admin' but no roles assigned)
        admin = User(username="admin", role="admin")
        db.session.add(admin)
        db.session.commit()

        # Legacy admin should be recognized as admin
        assert admin.is_admin is True

        # Legacy admin should have permission to anything (backward compatibility)
        assert admin.has_permission("any_permission")


@pytest.mark.unit
@pytest.mark.models
def test_admin_role_user(app):
    """Test that users with admin role have admin status"""
    with app.app_context():
        user = User(username="testuser", role="user")
        db.session.add(user)

        # Create admin role
        admin_role = Role(name="admin")
        db.session.add(admin_role)
        db.session.commit()

        # User is not admin initially
        assert not user.is_admin

        # Assign admin role
        user.add_role(admin_role)
        db.session.commit()

        # User should now be admin
        assert user.is_admin


@pytest.mark.unit
@pytest.mark.models
def test_super_admin_role_user(app):
    """Test that users with super_admin role have admin status"""
    with app.app_context():
        user = User(username="testuser", role="user")
        db.session.add(user)

        # Create super_admin role
        super_admin_role = Role(name="super_admin")
        db.session.add(super_admin_role)
        db.session.commit()

        # Assign super_admin role
        user.add_role(super_admin_role)
        db.session.commit()

        # User should be admin
        assert user.is_admin


@pytest.mark.unit
@pytest.mark.models
def test_role_get_permission_names(app):
    """Test getting permission names from a role"""
    with app.app_context():
        perm1 = Permission(name="perm1", category="test")
        perm2 = Permission(name="perm2", category="test")
        db.session.add_all([perm1, perm2])

        role = Role(name="test_role")
        db.session.add(role)
        db.session.commit()

        role.add_permission(perm1)
        role.add_permission(perm2)
        db.session.commit()

        permission_names = role.get_permission_names()
        assert len(permission_names) == 2
        assert "perm1" in permission_names
        assert "perm2" in permission_names


@pytest.mark.unit
@pytest.mark.models
def test_user_get_role_names(app):
    """Test getting role names from a user"""
    with app.app_context():
        user = User(username="testuser", role="user")
        db.session.add(user)

        role1 = Role(name="role1")
        role2 = Role(name="role2")
        db.session.add_all([role1, role2])
        db.session.commit()

        user.add_role(role1)
        user.add_role(role2)
        db.session.commit()

        role_names = user.get_role_names()
        assert len(role_names) == 2
        assert "role1" in role_names
        assert "role2" in role_names


@pytest.mark.unit
@pytest.mark.models
def test_permission_to_dict(app):
    """Test permission serialization to dictionary"""
    with app.app_context():
        permission = Permission(name="test_permission", description="Test description", category="testing")
        db.session.add(permission)
        db.session.commit()

        perm_dict = permission.to_dict()
        assert perm_dict["id"] == permission.id
        assert perm_dict["name"] == "test_permission"
        assert perm_dict["description"] == "Test description"
        assert perm_dict["category"] == "testing"


@pytest.mark.unit
@pytest.mark.models
def test_role_to_dict(app):
    """Test role serialization to dictionary"""
    with app.app_context():
        role = Role(name="test_role", description="Test description", is_system_role=True)
        db.session.add(role)
        db.session.commit()

        role_dict = role.to_dict()
        assert role_dict["id"] == role.id
        assert role_dict["name"] == "test_role"
        assert role_dict["description"] == "Test description"
        assert role_dict["is_system_role"] is True


@pytest.mark.unit
@pytest.mark.models
def test_role_to_dict_with_permissions(app):
    """Test role serialization with permissions included"""
    with app.app_context():
        perm = Permission(name="test_perm", category="test")
        db.session.add(perm)

        role = Role(name="test_role")
        db.session.add(role)
        db.session.commit()

        role.add_permission(perm)
        db.session.commit()

        role_dict = role.to_dict(include_permissions=True)
        assert "permissions" in role_dict
        assert "permission_count" in role_dict
        assert role_dict["permission_count"] == 1
        assert len(role_dict["permissions"]) == 1
