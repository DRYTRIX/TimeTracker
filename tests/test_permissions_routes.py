"""Smoke tests for permission system routes"""

import pytest
from app import db
from app.models import User, Permission, Role


@pytest.mark.smoke
def test_roles_list_page(client, admin_user):
    """Test that roles list page loads for admin"""
    # Login as admin
    client.post("/login", data={"username": admin_user.username, "password": "password123"}, follow_redirects=True)

    # Access roles list page
    response = client.get("/admin/roles")
    assert response.status_code == 200
    assert b"Roles & Permissions" in response.data or b"Roles" in response.data


@pytest.mark.smoke
def test_create_role_page(client, admin_user):
    """Test that create role page loads for admin"""
    client.post("/login", data={"username": admin_user.username, "password": "password123"}, follow_redirects=True)

    response = client.get("/admin/roles/create")
    assert response.status_code == 200
    assert b"Create" in response.data or b"Role" in response.data


@pytest.mark.smoke
def test_permissions_list_page(client, admin_user):
    """Test that permissions list page loads for admin"""
    client.post("/login", data={"username": admin_user.username, "password": "password123"}, follow_redirects=True)

    response = client.get("/admin/permissions")
    assert response.status_code == 200
    assert b"Permission" in response.data


@pytest.mark.integration
def test_create_role_flow(app, client, admin_user):
    """Test creating a new role"""
    with app.app_context():
        # Create a test permission first
        permission = Permission(name="test_perm", category="test")
        db.session.add(permission)
        db.session.commit()
        perm_id = permission.id

    # Login as admin
    client.post("/login", data={"username": admin_user.username, "password": "password123"}, follow_redirects=True)

    # Create role
    response = client.post(
        "/admin/roles/create",
        data={"name": "test_role", "description": "Test role description", "permissions": [str(perm_id)]},
        follow_redirects=True,
    )

    assert response.status_code == 200

    # Verify role was created
    with app.app_context():
        role = Role.query.filter_by(name="test_role").first()
        assert role is not None
        assert role.description == "Test role description"
        assert len(role.permissions) == 1


@pytest.mark.integration
def test_view_role_page(app, client, admin_user):
    """Test viewing a role detail page"""
    with app.app_context():
        # Create a role
        role = Role(name="test_role", description="Test description")
        db.session.add(role)
        db.session.commit()
        role_id = role.id

    # Login as admin
    client.post("/login", data={"username": admin_user.username, "password": "password123"}, follow_redirects=True)

    # View role
    response = client.get(f"/admin/roles/{role_id}")
    assert response.status_code == 200
    assert b"test_role" in response.data


@pytest.mark.integration
def test_edit_role_flow(app, client, admin_user):
    """Test editing a role"""
    with app.app_context():
        # Create a role
        role = Role(name="test_role", description="Old description", is_system_role=False)
        db.session.add(role)
        db.session.commit()
        role_id = role.id

    # Login as admin
    client.post("/login", data={"username": admin_user.username, "password": "password123"}, follow_redirects=True)

    # Edit role
    response = client.post(
        f"/admin/roles/{role_id}/edit",
        data={"name": "updated_role", "description": "Updated description", "permissions": []},
        follow_redirects=True,
    )

    assert response.status_code == 200

    # Verify changes
    with app.app_context():
        role = Role.query.get(role_id)
        assert role.name == "updated_role"
        assert role.description == "Updated description"


@pytest.mark.integration
def test_delete_role_flow(app, client, admin_user):
    """Test deleting a role"""
    with app.app_context():
        # Create a role (non-system role without users)
        role = Role(name="deletable_role", is_system_role=False)
        db.session.add(role)
        db.session.commit()
        role_id = role.id

    # Login as admin
    client.post("/login", data={"username": admin_user.username, "password": "password123"}, follow_redirects=True)

    # Delete role
    response = client.post(f"/admin/roles/{role_id}/delete", follow_redirects=True)
    assert response.status_code == 200

    # Verify deletion
    with app.app_context():
        role = Role.query.get(role_id)
        assert role is None


@pytest.mark.integration
def test_cannot_delete_system_role(app, client, admin_user):
    """Test that system roles cannot be deleted"""
    with app.app_context():
        # Create a system role
        role = Role(name="system_role", is_system_role=True)
        db.session.add(role)
        db.session.commit()
        role_id = role.id

    # Login as admin
    client.post("/login", data={"username": admin_user.username, "password": "password123"}, follow_redirects=True)

    # Try to delete system role
    response = client.post(f"/admin/roles/{role_id}/delete", follow_redirects=True)
    assert response.status_code == 200

    # Verify it still exists
    with app.app_context():
        role = Role.query.get(role_id)
        assert role is not None


@pytest.mark.integration
def test_cannot_edit_system_role(app, client, admin_user):
    """Test that system roles cannot be edited"""
    with app.app_context():
        # Create a system role
        role = Role(name="system_role", is_system_role=True)
        db.session.add(role)
        db.session.commit()
        role_id = role.id

    # Login as admin
    client.post("/login", data={"username": admin_user.username, "password": "password123"}, follow_redirects=True)

    # Try to edit system role
    response = client.post(
        f"/admin/roles/{role_id}/edit",
        data={"name": "hacked_name", "description": "Hacked", "permissions": []},
        follow_redirects=True,
    )

    # Should redirect or show warning
    assert response.status_code == 200

    # Verify name didn't change
    with app.app_context():
        role = Role.query.get(role_id)
        assert role.name == "system_role"


@pytest.mark.integration
def test_manage_user_roles_page(app, client, admin_user):
    """Test managing user roles page"""
    with app.app_context():
        # Create a test user
        user = User(username="testuser", role="user")
        db.session.add(user)
        db.session.commit()
        user_id = user.id

    # Login as admin
    client.post("/login", data={"username": admin_user.username, "password": "password123"}, follow_redirects=True)

    # Access manage roles page
    response = client.get(f"/admin/users/{user_id}/roles")
    assert response.status_code == 200
    assert b"Manage Roles" in response.data or b"Assign Roles" in response.data


@pytest.mark.integration
def test_assign_roles_to_user(app, client, admin_user):
    """Test assigning roles to a user"""
    with app.app_context():
        # Create user and role
        user = User(username="testuser", role="user")
        role = Role(name="test_role")
        db.session.add_all([user, role])
        db.session.commit()
        user_id = user.id
        role_id = role.id

    # Login as admin
    client.post("/login", data={"username": admin_user.username, "password": "password123"}, follow_redirects=True)

    # Assign role to user
    response = client.post(f"/admin/users/{user_id}/roles", data={"roles": [str(role_id)]}, follow_redirects=True)

    assert response.status_code == 200

    # Verify assignment
    with app.app_context():
        user = User.query.get(user_id)
        assert len(user.roles) == 1
        assert user.roles[0].name == "test_role"


@pytest.mark.integration
def test_api_get_user_permissions(app, client, admin_user):
    """Test API endpoint to get user permissions"""
    with app.app_context():
        # Create user with role and permissions
        user = User(username="testuser", role="user")
        permission = Permission(name="test_perm", category="test")
        role = Role(name="test_role")
        db.session.add_all([user, permission, role])
        db.session.commit()

        role.add_permission(permission)
        user.add_role(role)
        db.session.commit()
        user_id = user.id

    # Login as admin
    client.post("/login", data={"username": admin_user.username, "password": "password123"}, follow_redirects=True)

    # Get user permissions via API
    response = client.get(f"/api/users/{user_id}/permissions")
    assert response.status_code == 200

    data = response.get_json()
    assert data["user_id"] == user_id
    assert len(data["roles"]) == 1
    assert len(data["permissions"]) == 1


@pytest.mark.integration
def test_api_get_role_permissions(app, client, admin_user):
    """Test API endpoint to get role permissions"""
    with app.app_context():
        # Create role with permissions
        permission = Permission(name="test_perm", category="test")
        role = Role(name="test_role", description="Test role")
        db.session.add_all([permission, role])
        db.session.commit()

        role.add_permission(permission)
        db.session.commit()
        role_id = role.id

    # Login as admin
    client.post("/login", data={"username": admin_user.username, "password": "password123"}, follow_redirects=True)

    # Get role permissions via API
    response = client.get(f"/api/roles/{role_id}/permissions")
    assert response.status_code == 200

    data = response.get_json()
    assert data["role_id"] == role_id
    assert data["name"] == "test_role"
    assert len(data["permissions"]) == 1


@pytest.mark.smoke
def test_non_admin_cannot_access_roles(authenticated_client):
    """Test that non-admin users cannot access roles management"""
    # Try to access roles list as authenticated regular user
    response = authenticated_client.get("/admin/roles", follow_redirects=True)
    # Should redirect to dashboard or show error
    assert response.status_code == 200
    # Verify not on roles page (should be redirected or see error)
    assert b"Roles & Permissions" not in response.data or b"Administrator access required" in response.data
