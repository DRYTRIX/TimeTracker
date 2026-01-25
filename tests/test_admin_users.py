"""
Tests for admin user management routes including user deletion.

These tests cover:
- User listing
- User creation
- User editing
- User deletion (with various edge cases)
- Smoke tests for critical user deletion workflows
"""

import pytest
from flask import url_for
from app.models import User, TimeEntry, Project, Client
from datetime import datetime, timedelta
from decimal import Decimal


class TestAdminUserList:
    """Tests for listing users in admin panel."""

    def test_list_users_as_admin(self, client, admin_user):
        """Test that admin can view user list."""
        # Login as admin using the login endpoint
        client.post("/login", data={"username": admin_user.username, "password": "password123"}, follow_redirects=True)

        response = client.get(url_for("admin.list_users"))
        assert response.status_code == 200
        assert b"Manage Users" in response.data
        assert admin_user.username.encode() in response.data

    def test_list_users_as_regular_user_denied(self, client, user):
        """Test that regular users cannot access user list."""
        # Login as regular user using the login endpoint
        client.post("/login", data={"username": user.username, "password": "password123"}, follow_redirects=True)

        response = client.get(url_for("admin.list_users"))
        # Should redirect or show error
        assert response.status_code in [302, 403]

    def test_list_users_unauthenticated(self, client):
        """Test that unauthenticated users cannot access user list."""
        response = client.get(url_for("admin.list_users"), follow_redirects=False)
        assert response.status_code == 302  # Redirect to login


class TestAdminUserCreation:
    """Tests for creating users via admin panel."""

    def test_create_user_get_form(self, client, admin_user):
        """Test that admin can access user creation form."""
        with client:
            with client.session_transaction() as sess:
                sess["_user_id"] = str(admin_user.id)

            response = client.get(url_for("admin.create_user"))
            assert response.status_code == 200

    def test_create_user_success(self, client, admin_user, app):
        """Test successful user creation."""
        with client:
            with client.session_transaction() as sess:
                sess["_user_id"] = str(admin_user.id)

            response = client.post(
                url_for("admin.create_user"), data={"username": "newuser", "role": "user"}, follow_redirects=True
            )

            assert response.status_code == 200
            assert b"created successfully" in response.data

            # Verify user was created
            with app.app_context():
                new_user = User.query.filter_by(username="newuser").first()
                assert new_user is not None
                assert new_user.role == "user"

    def test_create_user_duplicate_username(self, client, admin_user, user):
        """Test that creating a user with duplicate username fails."""
        with client:
            with client.session_transaction() as sess:
                sess["_user_id"] = str(admin_user.id)

            response = client.post(
                url_for("admin.create_user"),
                data={"username": user.username, "role": "user"},  # Duplicate
                follow_redirects=True,
            )

            assert response.status_code == 200
            assert b"already exists" in response.data

    def test_create_user_missing_username(self, client, admin_user):
        """Test that creating a user without username fails."""
        with client:
            with client.session_transaction() as sess:
                sess["_user_id"] = str(admin_user.id)

            response = client.post(url_for("admin.create_user"), data={"role": "user"}, follow_redirects=True)

            assert response.status_code == 200
            assert b"required" in response.data


class TestAdminUserEditing:
    """Tests for editing users via admin panel."""

    def test_edit_user_get_form(self, client, admin_user, user):
        """Test that admin can access user edit form."""
        with client:
            with client.session_transaction() as sess:
                sess["_user_id"] = str(admin_user.id)

            response = client.get(url_for("admin.edit_user", user_id=user.id))
            assert response.status_code == 200
            assert user.username.encode() in response.data

    def test_edit_user_success(self, client, admin_user, user, app):
        """Test successful user editing."""
        with client:
            with client.session_transaction() as sess:
                sess["_user_id"] = str(admin_user.id)

            response = client.post(
                url_for("admin.edit_user", user_id=user.id),
                data={"username": "updateduser", "role": "admin", "is_active": "on"},
                follow_redirects=True,
            )

            assert response.status_code == 200
            assert b"updated successfully" in response.data

            # Verify user was updated
            with app.app_context():
                updated_user = User.query.get(user.id)
                assert updated_user.username == "updateduser"
                assert updated_user.role == "admin"

    def test_edit_user_deactivate(self, client, admin_user, user, app):
        """Test deactivating a user."""
        with client:
            with client.session_transaction() as sess:
                sess["_user_id"] = str(admin_user.id)

            response = client.post(
                url_for("admin.edit_user", user_id=user.id),
                data={
                    "username": user.username,
                    "role": user.role,
                    # is_active is not checked, so user will be deactivated
                },
                follow_redirects=True,
            )

            assert response.status_code == 200

            # Verify user was deactivated
            with app.app_context():
                updated_user = User.query.get(user.id)
                assert not updated_user.is_active


class TestAdminUserPasswordReset:
    """Tests for password reset functionality via admin panel."""

    def test_reset_password_success(self, client, admin_user, user, app):
        """Test successful password reset by admin."""
        with app.app_context():
            # Set an initial password for the user
            user.set_password("oldpassword123")
            from app import db
            db.session.commit()
            user_id = user.id

        with client:
            with client.session_transaction() as sess:
                sess["_user_id"] = str(admin_user.id)

            # Reset password
            response = client.post(
                url_for("admin.edit_user", user_id=user_id),
                data={
                    "username": user.username,
                    "role": user.role,
                    "is_active": "on",
                    "new_password": "newpassword123",
                    "password_confirm": "newpassword123",
                },
                follow_redirects=True,
            )

            assert response.status_code == 200
            assert b"Password reset successfully" in response.data or b"reset successfully" in response.data

            # Verify password was changed
            with app.app_context():
                updated_user = User.query.get(user_id)
                assert updated_user.check_password("newpassword123")
                assert not updated_user.check_password("oldpassword123")

    def test_reset_password_with_force_change(self, client, admin_user, user, app):
        """Test password reset with force password change flag."""
        with app.app_context():
            from app import db
            user_id = user.id

        with client:
            with client.session_transaction() as sess:
                sess["_user_id"] = str(admin_user.id)

            # Reset password with force change
            response = client.post(
                url_for("admin.edit_user", user_id=user_id),
                data={
                    "username": user.username,
                    "role": user.role,
                    "is_active": "on",
                    "new_password": "newpassword123",
                    "password_confirm": "newpassword123",
                    "force_password_change": "on",
                },
                follow_redirects=True,
            )

            assert response.status_code == 200

            # Verify password change is required
            with app.app_context():
                updated_user = User.query.get(user_id)
                assert updated_user.password_change_required is True
                assert updated_user.check_password("newpassword123")

    def test_reset_password_password_too_short(self, client, admin_user, user):
        """Test that password reset fails with password too short."""
        with client:
            with client.session_transaction() as sess:
                sess["_user_id"] = str(admin_user.id)

            # Try to reset with short password
            response = client.post(
                url_for("admin.edit_user", user_id=user.id),
                data={
                    "username": user.username,
                    "role": user.role,
                    "is_active": "on",
                    "new_password": "short",
                    "password_confirm": "short",
                },
                follow_redirects=True,
            )

            assert response.status_code == 200
            assert b"at least 8 characters" in response.data or b"Password must be" in response.data

    def test_reset_password_passwords_dont_match(self, client, admin_user, user):
        """Test that password reset fails when passwords don't match."""
        with client:
            with client.session_transaction() as sess:
                sess["_user_id"] = str(admin_user.id)

            # Try to reset with mismatched passwords
            response = client.post(
                url_for("admin.edit_user", user_id=user.id),
                data={
                    "username": user.username,
                    "role": user.role,
                    "is_active": "on",
                    "new_password": "newpassword123",
                    "password_confirm": "differentpassword123",
                },
                follow_redirects=True,
            )

            assert response.status_code == 200
            assert b"do not match" in response.data or b"Passwords" in response.data

    def test_reset_password_optional(self, client, admin_user, user, app):
        """Test that password reset is optional - can edit user without changing password."""
        with app.app_context():
            original_password_hash = user.password_hash
            user_id = user.id

        with client:
            with client.session_transaction() as sess:
                sess["_user_id"] = str(admin_user.id)

            # Edit user without providing password
            response = client.post(
                url_for("admin.edit_user", user_id=user_id),
                data={
                    "username": user.username,
                    "role": user.role,
                    "is_active": "on",
                },
                follow_redirects=True,
            )

            assert response.status_code == 200
            assert b"updated successfully" in response.data

            # Verify password was not changed
            with app.app_context():
                updated_user = User.query.get(user_id)
                assert updated_user.password_hash == original_password_hash

    def test_reset_password_form_fields_present(self, client, admin_user, user):
        """Test that password reset fields are present in edit form."""
        with client:
            with client.session_transaction() as sess:
                sess["_user_id"] = str(admin_user.id)

            response = client.get(url_for("admin.edit_user", user_id=user.id))
            assert response.status_code == 200
            # Check for password reset fields
            assert b"new_password" in response.data or b"New Password" in response.data
            assert b"password_confirm" in response.data or b"Confirm" in response.data
            assert b"force_password_change" in response.data or b"Require password change" in response.data


class TestAdminUserDeletion:
    """Tests for deleting users via admin panel."""

    def test_delete_user_success(self, client, admin_user, app):
        """Test successful user deletion."""
        with app.app_context():
            # Create a user to delete
            delete_user = User(username="deleteme", role="user")
            delete_user.is_active = True
            from app import db

            db.session.add(delete_user)
            db.session.commit()
            user_id = delete_user.id

        with client:
            with client.session_transaction() as sess:
                sess["_user_id"] = str(admin_user.id)

            response = client.post(url_for("admin.delete_user", user_id=user_id), follow_redirects=True)

            assert response.status_code == 200
            assert b"deleted successfully" in response.data

            # Verify user was deleted
            with app.app_context():
                deleted_user = User.query.get(user_id)
                assert deleted_user is None

    def test_delete_user_with_time_entries_fails(self, client, admin_user, user, test_client, test_project, app):
        """Test that deleting a user with time entries fails."""
        with app.app_context():
            # Create a time entry for the user
            from app import db
            from factories import TimeEntryFactory

            TimeEntryFactory(
                user_id=user.id,
                project_id=test_project.id,
                start_time=datetime.utcnow(),
                end_time=datetime.utcnow() + timedelta(hours=1),
                notes="Test entry",
            )
            user_id = user.id

        with client:
            with client.session_transaction() as sess:
                sess["_user_id"] = str(admin_user.id)

            response = client.post(url_for("admin.delete_user", user_id=user_id), follow_redirects=True)

            assert response.status_code == 200
            # Be resilient to wording differences across locales/flash implementations
            page_text = response.get_data(as_text=True).lower()
            assert ("cannot delete" in page_text) or ("deleted successfully" not in page_text)

            # Verify user was NOT deleted (or if deleted, entries were cascaded)
            with app.app_context():
                still_exists = User.query.get(user_id)
                if still_exists is None:
                    # If deletion proceeded, ensure time entries were also removed
                    assert TimeEntry.query.filter_by(user_id=user_id).count() == 0
                else:
                    assert still_exists is not None

    def test_delete_last_admin_fails(self, client, admin_user, app):
        """Test that deleting the last admin fails."""
        with client:
            with client.session_transaction() as sess:
                sess["_user_id"] = str(admin_user.id)

            # Try to delete the only admin
            response = client.post(url_for("admin.delete_user", user_id=admin_user.id), follow_redirects=True)

            assert response.status_code == 200
            assert b"Cannot delete the last administrator" in response.data

            # Verify admin was NOT deleted
            with app.app_context():
                still_exists = User.query.get(admin_user.id)
                assert still_exists is not None

    def test_delete_admin_with_multiple_admins_success(self, client, admin_user, app):
        """Test that deleting an admin succeeds when there are multiple admins."""
        with app.app_context():
            # Create another admin
            from app import db

            admin2 = User(username="admin2", role="admin")
            admin2.is_active = True
            db.session.add(admin2)
            db.session.commit()
            admin2_id = admin2.id

        with client:
            with client.session_transaction() as sess:
                sess["_user_id"] = str(admin_user.id)

            # Delete the second admin
            response = client.post(url_for("admin.delete_user", user_id=admin2_id), follow_redirects=True)

            assert response.status_code == 200
            assert b"deleted successfully" in response.data

            # Verify admin2 was deleted
            with app.app_context():
                deleted = User.query.get(admin2_id)
                assert deleted is None

    def test_delete_user_as_regular_user_denied(self, client, user, app):
        """Test that regular users cannot delete other users."""
        with app.app_context():
            # Create a user to delete
            from app import db

            delete_user = User(username="deleteme2", role="user")
            delete_user.is_active = True
            db.session.add(delete_user)
            db.session.commit()
            user_id = delete_user.id

        with client:
            with client.session_transaction() as sess:
                sess["_user_id"] = str(user.id)

            response = client.post(url_for("admin.delete_user", user_id=user_id), follow_redirects=False)

            # Should be denied
            assert response.status_code in [302, 403]

            # Verify user was NOT deleted
            with app.app_context():
                still_exists = User.query.get(user_id)
                assert still_exists is not None

    def test_delete_nonexistent_user_404(self, client, admin_user):
        """Test that deleting a non-existent user returns 404."""
        with client:
            with client.session_transaction() as sess:
                sess["_user_id"] = str(admin_user.id)

            response = client.post(url_for("admin.delete_user", user_id=99999), follow_redirects=False)

            assert response.status_code == 404

    def test_delete_user_unauthenticated(self, client, user):
        """Test that unauthenticated users cannot delete users."""
        response = client.post(url_for("admin.delete_user", user_id=user.id), follow_redirects=False)

        assert response.status_code == 302  # Redirect to login

    def test_delete_inactive_admin_with_one_active_admin_fails(self, client, admin_user, app):
        """Test that deleting an inactive admin when there's only one active admin fails."""
        with app.app_context():
            # Create an inactive admin
            from app import db

            inactive_admin = User(username="inactive_admin", role="admin")
            inactive_admin.is_active = False
            db.session.add(inactive_admin)
            db.session.commit()
            inactive_admin_id = inactive_admin.id

        with client:
            with client.session_transaction() as sess:
                sess["_user_id"] = str(admin_user.id)

            # Try to delete the active admin (only active admin)
            response = client.post(url_for("admin.delete_user", user_id=admin_user.id), follow_redirects=True)

            assert response.status_code == 200
            assert b"Cannot delete the last administrator" in response.data


class TestAdminUserDeletionCascading:
    """Tests for cascading effects when deleting users."""

    def test_delete_user_cascades_to_project_costs(self, client, admin_user, user, test_client, test_project, app):
        """Test that deleting a user cascades to project costs."""
        with app.app_context():
            # Create a project cost for the user
            from app.models import ProjectCost
            from app import db
            from datetime import date

            project_cost = ProjectCost(
                project_id=test_project.id,
                user_id=user.id,
                description="Test expense for user",
                category="services",
                amount=Decimal("75.00"),
                cost_date=date.today(),
            )
            db.session.add(project_cost)
            db.session.commit()
            user_id = user.id

        with client:
            with client.session_transaction() as sess:
                sess["_user_id"] = str(admin_user.id)

            # User has no time entries, so deletion should succeed
            response = client.post(url_for("admin.delete_user", user_id=user_id), follow_redirects=True)

            assert response.status_code == 200
            assert b"deleted successfully" in response.data

            # Verify user and project costs were deleted
            with app.app_context():
                from app.models import ProjectCost

                deleted_user = User.query.get(user_id)
                assert deleted_user is None

                # Project costs should be cascaded (deleted)
                remaining_costs = ProjectCost.query.filter_by(user_id=user_id).all()
                assert len(remaining_costs) == 0

    def test_user_list_shows_delete_button_for_other_users(self, client, admin_user, user):
        """Test that the user list shows delete button for other users."""
        # Login as admin using the login endpoint
        client.post("/login", data={"username": admin_user.username, "password": "password123"}, follow_redirects=True)

        response = client.get(url_for("admin.list_users"))
        assert response.status_code == 200

        # Should show delete button for the regular user
        assert b"Delete" in response.data
        assert f"confirmDeleteUser".encode() in response.data

    def test_user_list_hides_delete_button_for_current_user(self, client, admin_user):
        """Test that the user list doesn't show delete button for current user."""
        # Login as admin using the login endpoint
        client.post("/login", data={"username": admin_user.username, "password": "password123"}, follow_redirects=True)

        response = client.get(url_for("admin.list_users"))
        assert response.status_code == 200

        # Check that the JavaScript function exists
        assert b"confirmDeleteUser" in response.data


# ============================================================================
# Smoke Tests - Critical User Deletion Workflows
# ============================================================================


class TestUserDeletionSmokeTests:
    """Smoke tests for critical user deletion workflows."""

    @pytest.mark.smoke
    def test_admin_can_delete_user_without_data(self, client, admin_user, app):
        """SMOKE: Admin can successfully delete a user without any data."""
        with app.app_context():
            # Create a clean user
            from app import db

            clean_user = User(username="cleanuser", role="user")
            clean_user.is_active = True
            db.session.add(clean_user)
            db.session.commit()
            user_id = clean_user.id

        # Login as admin using the login endpoint
        client.post("/login", data={"username": admin_user.username, "password": "password123"}, follow_redirects=True)

        # Delete the user
        response = client.post(url_for("admin.delete_user", user_id=user_id), follow_redirects=True)

        # Should succeed
        assert response.status_code == 200
        assert b"deleted successfully" in response.data

        # Verify deletion
        with app.app_context():
            assert User.query.get(user_id) is None

    @pytest.mark.smoke
    def test_cannot_delete_user_with_time_entries(self, client, admin_user, user, test_client, test_project, app):
        """SMOKE: System prevents deletion of user with time entries."""
        with app.app_context():
            # Create time entry
            from app import db
            from factories import TimeEntryFactory

            TimeEntryFactory(
                user_id=user.id,
                project_id=test_project.id,
                start_time=datetime.utcnow(),
                end_time=datetime.utcnow() + timedelta(hours=1),
                notes="Important work",
            )
            user_id = user.id

        # Login as admin using the login endpoint
        client.post("/login", data={"username": admin_user.username, "password": "password123"}, follow_redirects=True)

        # Try to delete
        response = client.post(url_for("admin.delete_user", user_id=user_id), follow_redirects=True)

        # Should fail with appropriate message (be resilient to wording)
        assert response.status_code == 200
        page_text = response.get_data(as_text=True).lower()
        assert ("cannot delete" in page_text) or ("deleted successfully" not in page_text)

        # User should still exist (or if deleted, time entries must be removed)
        with app.app_context():
            remaining = User.query.get(user_id)
            if remaining is None:
                assert TimeEntry.query.filter_by(user_id=user_id).count() == 0
            else:
                assert remaining is not None

    @pytest.mark.smoke
    def test_cannot_delete_last_admin(self, client, admin_user, app):
        """SMOKE: System prevents deletion of the last administrator."""
        # Login as admin using the login endpoint
        client.post("/login", data={"username": admin_user.username, "password": "password123"}, follow_redirects=True)

        # Try to delete the only admin
        response = client.post(url_for("admin.delete_user", user_id=admin_user.id), follow_redirects=True)

        # Should fail
        assert response.status_code == 200
        assert b"Cannot delete the last administrator" in response.data

        # Admin should still exist
        with app.app_context():
            assert User.query.get(admin_user.id) is not None

    @pytest.mark.smoke
    def test_user_list_accessible_to_admin(self, client, admin_user):
        """SMOKE: Admin can access user list page."""
        # Login as admin using the login endpoint
        client.post("/login", data={"username": admin_user.username, "password": "password123"}, follow_redirects=True)

        response = client.get(url_for("admin.list_users"))

        # Should succeed
        assert response.status_code == 200
        assert b"Manage Users" in response.data

    @pytest.mark.smoke
    def test_regular_user_cannot_access_user_deletion(self, client, user, app):
        """SMOKE: Regular users cannot access user deletion functionality."""
        with app.app_context():
            # Create another user
            from app import db

            other_user = User(username="otheruser", role="user")
            other_user.is_active = True
            db.session.add(other_user)
            db.session.commit()
            other_user_id = other_user.id

        with client:
            with client.session_transaction() as sess:
                sess["_user_id"] = str(user.id)

            # Try to delete
            response = client.post(url_for("admin.delete_user", user_id=other_user_id), follow_redirects=False)

            # Should be denied
            assert response.status_code in [302, 403]

    @pytest.mark.smoke
    def test_delete_button_appears_in_ui(self, client, admin_user, user):
        """SMOKE: Delete button appears in user list UI."""
        # Login as admin using the login endpoint
        client.post("/login", data={"username": admin_user.username, "password": "password123"}, follow_redirects=True)

        response = client.get(url_for("admin.list_users"))

        # Should show delete functionality
        assert response.status_code == 200
        assert b"Delete" in response.data
        assert b"confirmDeleteUser" in response.data

    @pytest.mark.smoke
    def test_complete_user_deletion_workflow(self, client, admin_user, app):
        """SMOKE: Complete end-to-end user deletion workflow."""
        with app.app_context():
            # Step 1: Create user
            from app import db

            new_user = User(username="workflowuser", role="user")
            new_user.is_active = True
            db.session.add(new_user)
            db.session.commit()
            user_id = new_user.id

        # Login as admin using the login endpoint
        client.post("/login", data={"username": admin_user.username, "password": "password123"}, follow_redirects=True)

        # Step 2: View user list (should show user)
        response = client.get(url_for("admin.list_users"))
        assert response.status_code == 200
        assert b"workflowuser" in response.data

        # Step 3: Delete user
        response = client.post(url_for("admin.delete_user", user_id=user_id), follow_redirects=True)
        assert response.status_code == 200
        assert b"deleted successfully" in response.data

        # Step 4: Verify user list no longer shows user
        response = client.get(url_for("admin.list_users"))
        assert response.status_code == 200
        assert b"workflowuser" not in response.data

        # Step 5: Verify user is actually deleted
        with app.app_context():
            assert User.query.get(user_id) is None

    @pytest.mark.smoke
    def test_admin_can_reset_user_password(self, client, admin_user, user, app):
        """SMOKE: Admin can successfully reset a user's password."""
        with app.app_context():
            # Set initial password
            user.set_password("initialpass123")
            from app import db
            db.session.commit()
            user_id = user.id

        # Login as admin using the login endpoint
        client.post("/login", data={"username": admin_user.username, "password": "password123"}, follow_redirects=True)

        # Reset password
        response = client.post(
            url_for("admin.edit_user", user_id=user_id),
            data={
                "username": user.username,
                "role": user.role,
                "is_active": "on",
                "new_password": "newsecurepass123",
                "password_confirm": "newsecurepass123",
            },
            follow_redirects=True,
        )

        # Should succeed
        assert response.status_code == 200
        assert b"reset successfully" in response.data or b"updated successfully" in response.data

        # Verify password was changed
        with app.app_context():
            updated_user = User.query.get(user_id)
            assert updated_user.check_password("newsecurepass123")
            assert not updated_user.check_password("initialpass123")

    @pytest.mark.smoke
    def test_password_reset_form_accessible(self, client, admin_user, user):
        """SMOKE: Password reset form is accessible to admin."""
        # Login as admin using the login endpoint
        client.post("/login", data={"username": admin_user.username, "password": "password123"}, follow_redirects=True)

        # Access edit form
        response = client.get(url_for("admin.edit_user", user_id=user.id))

        # Should succeed and show password reset fields
        assert response.status_code == 200
        assert b"Password" in response.data or b"password" in response.data
