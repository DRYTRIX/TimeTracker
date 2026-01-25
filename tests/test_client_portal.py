"""
Comprehensive tests for Client Portal feature.

This module tests:
- User model client portal fields and properties
- Client portal routes and access control
- Client portal data retrieval
- Admin interface for enabling/disabling portal access
"""

import pytest
from datetime import datetime, timedelta
from decimal import Decimal
from sqlalchemy.exc import PendingRollbackError
from app.models import User, Client, Project, Invoice, InvoiceItem, TimeEntry
from app import db


def safe_commit_with_retry(max_retries=3):
    """Safely commit with retry logic for database locks
    
    This is needed because audit logging can cause database locks during parallel
    test execution. If commit fails, we rollback and retry.
    
    Note: If the commit fails due to audit logging, the transaction is rolled back,
    so the data changes are lost. This function will retry the commit, but if it
    continues to fail, the data may not be saved. The caller should verify the data
    was actually saved.
    """
    import time
    for attempt in range(max_retries):
        try:
            db.session.commit()
            return True
        except Exception as e:
            # If commit fails, rollback and retry after a short delay
            try:
                db.session.rollback()
            except Exception:
                pass
            
            # Wait a bit before retrying (exponential backoff)
            if attempt < max_retries - 1:
                time.sleep(0.1 * (2 ** attempt))
            else:
                # On final attempt, just rollback and return False
                # The caller should verify if data was actually saved
                return False
    return False


def safe_get_user(user_id):
    """Safely get a user, handling rollback errors from database locks
    
    This is needed because audit logging can cause database locks during parallel
    test execution, which leaves the session in a rolled-back state.
    """
    try:
        return User.query.get(user_id)
    except PendingRollbackError:
        # If session was rolled back due to database lock, rollback and retry
        try:
            db.session.rollback()
        except Exception:
            # If rollback fails, create a new session context
            pass
        return User.query.get(user_id)


# ============================================================================
# Model Tests
# ============================================================================


@pytest.mark.models
@pytest.mark.unit
class TestClientPortalUserModel:
    """Test User model client portal functionality"""

    def test_user_client_portal_enabled_field(self, app, user):
        """Test client_portal_enabled field defaults to False"""
        with app.app_context():
            assert user.client_portal_enabled is False

    def test_user_client_id_field(self, app, user):
        """Test client_id field defaults to None"""
        with app.app_context():
            assert user.client_id is None

    def test_is_client_portal_user_property(self, app, user, test_client):
        """Test is_client_portal_user property"""
        with app.app_context():
            # Initially False
            assert user.is_client_portal_user is False

            # Enable portal but no client assigned
            user.client_portal_enabled = True
            assert user.is_client_portal_user is False

            # Assign client
            user.client_id = test_client.id
            assert user.is_client_portal_user is True

    def test_get_client_portal_data(self, app, user, test_client):
        """Test get_client_portal_data method"""
        with app.app_context():
            # No portal access
            assert user.get_client_portal_data() is None

            # Enable portal and assign client
            user.client_portal_enabled = True
            user.client_id = test_client.id
            db.session.commit()

            # Should return data structure
            data = user.get_client_portal_data()
            assert data is not None
            assert "client" in data
            assert "projects" in data
            assert "invoices" in data
            assert "time_entries" in data
            assert data["client"].id == test_client.id

    def test_get_client_portal_data_with_projects(self, app, user, test_client):
        """Test get_client_portal_data includes projects"""
        with app.app_context():
            user.client_portal_enabled = True
            user.client_id = test_client.id

            # Create projects
            project1 = Project(name="Project 1", client_id=test_client.id, status="active")
            project2 = Project(name="Project 2", client_id=test_client.id, status="active")
            project3 = Project(name="Project 3", client_id=test_client.id, status="inactive")
            db.session.add_all([project1, project2, project3])
            db.session.commit()

            data = user.get_client_portal_data()
            assert len(data["projects"]) == 2  # Only active projects
            assert project1 in data["projects"]
            assert project2 in data["projects"]
            assert project3 not in data["projects"]

    def test_get_client_portal_data_with_invoices(self, app, user, test_client):
        """Test get_client_portal_data includes invoices"""
        with app.app_context():
            user_id = user.id
            # Use no_autoflush to prevent audit logging from interfering
            with db.session.no_autoflush:
                user.client_portal_enabled = True
                user.client_id = test_client.id
                db.session.merge(user)
                db.session.flush()

            # Commit outside no_autoflush block
            # Use safe_commit_with_retry to handle database locks from audit logging
            commit_success = safe_commit_with_retry()
            
            # Verify user was actually updated (commit might have failed)
            user = safe_get_user(user_id)
            if not commit_success or not user.client_portal_enabled or user.client_id != test_client.id:
                # Re-apply changes if commit failed
                user.client_portal_enabled = True
                user.client_id = test_client.id
                db.session.merge(user)
                safe_commit_with_retry()
                user = safe_get_user(user_id)

            project = Project(name="Test Project", client_id=test_client.id)
            db.session.add(project)
            db.session.flush()  # Flush to get project.id without committing
            project_id = project.id

            # Create invoices
            invoice1 = Invoice(
                invoice_number="INV-001",
                project_id=project_id,
                client_name=test_client.name,
                client_id=test_client.id,
                due_date=datetime.utcnow().date() + timedelta(days=30),
                created_by=user.id,
                total_amount=Decimal("100.00"),
            )
            invoice2 = Invoice(
                invoice_number="INV-002",
                project_id=project_id,
                client_name=test_client.name,
                client_id=test_client.id,
                due_date=datetime.utcnow().date() + timedelta(days=30),
                created_by=user.id,
                total_amount=Decimal("200.00"),
            )
            db.session.add_all([invoice1, invoice2])
            # Use safe_commit_with_retry to handle database locks
            safe_commit_with_retry()

            # Get fresh user to avoid session attachment issues
            user = safe_get_user(user.id)
            data = user.get_client_portal_data()
            assert len(data["invoices"]) == 2
            assert invoice1 in data["invoices"]
            assert invoice2 in data["invoices"]

    def test_get_client_portal_data_with_time_entries(self, app, user, test_client):
        """Test get_client_portal_data includes time entries"""
        with app.app_context():
            user_id = user.id
            # Use no_autoflush to prevent audit logging from interfering
            with db.session.no_autoflush:
                user.client_portal_enabled = True
                user.client_id = test_client.id
                db.session.merge(user)
                db.session.flush()

            # Commit outside no_autoflush block
            # Use safe_commit_with_retry to handle database locks from audit logging
            commit_success = safe_commit_with_retry()
            
            # Verify user was actually updated (commit might have failed)
            user = safe_get_user(user_id)
            if not commit_success or not user.client_portal_enabled or user.client_id != test_client.id:
                # Re-apply changes if commit failed
                user.client_portal_enabled = True
                user.client_id = test_client.id
                db.session.merge(user)
                safe_commit_with_retry()
                user = safe_get_user(user_id)

            project = Project(name="Test Project", client_id=test_client.id)
            db.session.add(project)
            safe_commit_with_retry()

            # Create time entries
            entry1 = TimeEntry(
                user_id=user.id,
                project_id=project.id,
                start_time=datetime.utcnow() - timedelta(hours=2),
                end_time=datetime.utcnow(),
                duration_seconds=7200,
            )
            entry2 = TimeEntry(
                user_id=user.id,
                project_id=project.id,
                start_time=datetime.utcnow() - timedelta(hours=1),
                end_time=datetime.utcnow(),
                duration_seconds=3600,
            )
            db.session.add_all([entry1, entry2])
            # Use safe_commit_with_retry to handle database locks
            safe_commit_with_retry()

            # Get fresh user to avoid session attachment issues
            user = safe_get_user(user.id)
            data = user.get_client_portal_data()
            assert len(data["time_entries"]) == 2
            assert entry1 in data["time_entries"]
            assert entry2 in data["time_entries"]


# ============================================================================
# Route Tests
# ============================================================================


@pytest.mark.routes
@pytest.mark.unit
class TestClientPortalRoutes:
    """Test client portal routes"""

    def test_client_portal_dashboard_requires_access(self, app, client, user):
        """Test dashboard requires client portal access - redirects to client portal login when user has no portal access"""
        with app.app_context():
            # Login user without portal access
            with client.session_transaction() as sess:
                sess["_user_id"] = str(user.id)

            response = client.get("/client-portal/dashboard")
            assert response.status_code == 302
            # Client portal 403 handler redirects authenticated non-portal users to client portal login
            assert "client-portal" in (response.location or "") and "login" in (response.location or "")

    def test_client_portal_dashboard_with_access(self, app, client, user, test_client):
        """Test dashboard accessible with portal access"""
        with app.app_context():
            # Use no_autoflush to prevent audit logging from interfering
            with db.session.no_autoflush:
                user.client_portal_enabled = True
                user.client_id = test_client.id
                db.session.merge(user)
                db.session.flush()

            # Commit outside no_autoflush block
            # Use safe_commit_with_retry to handle database locks from audit logging
            safe_commit_with_retry()

            # Query for user fresh in current session to avoid session attachment issues
            # This handles PendingRollbackError if session was rolled back due to audit log lock
            user = safe_get_user(user.id)

            with client.session_transaction() as sess:
                sess["_user_id"] = str(user.id)

            response = client.get("/client-portal/dashboard")
            assert response.status_code == 200
            assert b"Client Portal" in response.data

    def test_client_portal_projects_route(self, app, client, user, test_client):
        """Test projects route"""
        with app.app_context():
            # Use no_autoflush to prevent audit logging from interfering
            with db.session.no_autoflush:
                user.client_portal_enabled = True
                user.client_id = test_client.id
                db.session.merge(user)
                db.session.flush()

            # Commit outside no_autoflush block
            # Use safe_commit_with_retry to handle database locks from audit logging
            safe_commit_with_retry()

            # Query for user fresh in current session to avoid session attachment issues
            # This handles PendingRollbackError if session was rolled back due to audit log lock
            user = safe_get_user(user.id)

            with client.session_transaction() as sess:
                sess["_user_id"] = str(user.id)

            response = client.get("/client-portal/projects")
            assert response.status_code == 200

    def test_client_portal_invoices_route(self, app, client, user, test_client):
        """Test invoices route"""
        with app.app_context():
            # Use no_autoflush to prevent audit logging from interfering
            with db.session.no_autoflush:
                user.client_portal_enabled = True
                user.client_id = test_client.id
                db.session.merge(user)
                db.session.flush()

            # Commit outside no_autoflush block
            # Use safe_commit_with_retry to handle database locks from audit logging
            safe_commit_with_retry()

            # Query for user fresh in current session to avoid session attachment issues
            # This handles PendingRollbackError if session was rolled back due to audit log lock
            user = safe_get_user(user.id)

            with client.session_transaction() as sess:
                sess["_user_id"] = str(user.id)

            response = client.get("/client-portal/invoices")
            assert response.status_code == 200

    def test_client_portal_time_entries_route(self, app, client, user, test_client):
        """Test time entries route"""
        with app.app_context():
            # Use no_autoflush to prevent audit logging from interfering
            with db.session.no_autoflush:
                user.client_portal_enabled = True
                user.client_id = test_client.id
                db.session.merge(user)
                db.session.flush()

            # Commit outside no_autoflush block
            # Use safe_commit_with_retry to handle database locks from audit logging
            safe_commit_with_retry()

            # Query for user fresh in current session to avoid session attachment issues
            # This handles PendingRollbackError if session was rolled back due to audit log lock
            user = safe_get_user(user.id)

            with client.session_transaction() as sess:
                sess["_user_id"] = str(user.id)

            response = client.get("/client-portal/time-entries")
            assert response.status_code == 200

    def test_view_invoice_belongs_to_client(self, app, client, user, test_client):
        """Test viewing invoice requires it belongs to user's client"""
        with app.app_context():
            # Use no_autoflush to prevent audit logging from interfering
            with db.session.no_autoflush:
                user.client_portal_enabled = True
                user.client_id = test_client.id
                db.session.merge(user)
                db.session.flush()

            # Commit outside no_autoflush block
            # Use safe_commit_with_retry to handle database locks from audit logging
            safe_commit_with_retry()

            # Query for user fresh in current session to avoid session attachment issues
            # This handles PendingRollbackError if session was rolled back due to audit log lock
            user = safe_get_user(user.id)

            # Create another client
            other_client = Client(name="Other Client")
            db.session.add(other_client)

            project = Project(name="Test Project", client_id=test_client.id)
            db.session.add(project)
            # Use safe_commit_with_retry to handle database locks from audit logging
            safe_commit_with_retry()

            # Create invoice for user's client
            invoice = Invoice(
                invoice_number="INV-001",
                project_id=project.id,
                client_name=test_client.name,
                client_id=test_client.id,
                due_date=datetime.utcnow().date() + timedelta(days=30),
                created_by=user.id,
                total_amount=Decimal("100.00"),
            )
            db.session.add(invoice)
            # Use safe_commit_with_retry to handle database locks from audit logging
            safe_commit_with_retry()

            with client.session_transaction() as sess:
                sess["_user_id"] = str(user.id)

            # Should be able to view invoice
            response = client.get(f"/client-portal/invoices/{invoice.id}")
            assert response.status_code == 200


# ============================================================================
# Admin Interface Tests
# ============================================================================


@pytest.mark.routes
@pytest.mark.unit
class TestAdminClientPortalManagement:
    """Test admin interface for managing client portal access"""

    def test_admin_can_enable_client_portal(self, app, admin_authenticated_client, user, test_client):
        """Test admin can enable client portal for user"""
        with app.app_context():
            # Get the edit form page first to get CSRF token
            get_response = admin_authenticated_client.get(f"/admin/users/{user.id}/edit", follow_redirects=True)
            assert get_response.status_code == 200

            # Extract CSRF token from the form if available
            html = get_response.get_data(as_text=True)
            import re
            import time

            csrf_match = re.search(r'name="csrf_token"\s+value="([^"]+)"', html)
            csrf_token = csrf_match.group(1) if csrf_match else ""

            response = admin_authenticated_client.post(
                f"/admin/users/{user.id}/edit",
                data={
                    "username": user.username,
                    "role": user.role,
                    "is_active": "on" if user.is_active else "",
                    "client_portal_enabled": "on",
                    "client_id": str(test_client.id),
                    "csrf_token": csrf_token,
                },
                follow_redirects=True,
            )
            # Should redirect to users list (or show form with error if commit failed)
            assert response.status_code == 200
            
            # Check for error messages in response (commit failure)
            response_text = response.get_data(as_text=True)
            if "Could not update user due to a database error" in response_text:
                # If commit failed, the test should fail, not skip
                # But we'll still check the database in case the error message is misleading
                pass

            # Verify user was updated - retry in case of database lock delays
            # The route uses safe_commit which might fail due to audit logging locks
            max_retries = 5
            for attempt in range(max_retries):
                # Expire any cached objects to force fresh query
                db.session.expire_all()
                updated_user = safe_get_user(user.id)
                if updated_user.client_portal_enabled is True and updated_user.client_id == test_client.id:
                    break
                if attempt < max_retries - 1:
                    time.sleep(0.1 * (2 ** attempt))
                else:
                    # Final attempt - verify the assertion
                    assert updated_user.client_portal_enabled is True, f"User client_portal_enabled is {updated_user.client_portal_enabled}, expected True"
                    assert updated_user.client_id == test_client.id, f"User client_id is {updated_user.client_id}, expected {test_client.id}"

    def test_admin_can_disable_client_portal(self, app, admin_authenticated_client, user, test_client):
        """Test admin can disable client portal for user"""
        with app.app_context():
            # Enable portal first - use no_autoflush to prevent audit logging from interfering
            with db.session.no_autoflush:
                user.client_portal_enabled = True
                user.client_id = test_client.id
                # Use merge to handle objects from different sessions
                merged_user = db.session.merge(user)
                db.session.flush()

            # Commit outside no_autoflush block
            # Use safe_commit_with_retry to handle database locks from audit logging
            safe_commit_with_retry()

            # Query for user fresh in current session to avoid session attachment issues
            # This handles PendingRollbackError if session was rolled back due to audit log lock
            user = safe_get_user(user.id)

            # Get the edit form page first to get CSRF token
            get_response = admin_authenticated_client.get(f"/admin/users/{user.id}/edit", follow_redirects=True)
            assert get_response.status_code == 200

            # Extract CSRF token from the form if available
            html = get_response.get_data(as_text=True)
            import re

            csrf_match = re.search(r'name="csrf_token"\s+value="([^"]+)"', html)
            csrf_token = csrf_match.group(1) if csrf_match else ""

            response = admin_authenticated_client.post(
                f"/admin/users/{user.id}/edit",
                data={
                    "username": user.username,
                    "role": user.role,
                    "is_active": "on" if user.is_active else "",
                    "client_portal_enabled": "",  # Not checked
                    "client_id": "",
                    "csrf_token": csrf_token,
                },
                follow_redirects=True,
            )
            
            # Check for error messages in response (commit failure)
            response_text = response.get_data(as_text=True)
            if "Could not update user due to a database error" in response_text:
                # If commit failed, the test should fail, not skip
                # But we'll still check the database in case the error message is misleading
                pass

            # Verify user was updated - retry in case of database lock delays
            # The route uses safe_commit which might fail due to audit logging locks
            import time
            max_retries = 5
            for attempt in range(max_retries):
                # Expire any cached objects to force fresh query
                db.session.expire_all()
                updated_user = safe_get_user(user.id)
                if updated_user.client_portal_enabled is False and updated_user.client_id is None:
                    break
                if attempt < max_retries - 1:
                    time.sleep(0.1 * (2 ** attempt))
                else:
                    # Final attempt - verify the assertion
                    assert updated_user.client_portal_enabled is False, f"User client_portal_enabled is {updated_user.client_portal_enabled}, expected False"
                    assert updated_user.client_id is None, f"User client_id is {updated_user.client_id}, expected None"


# ============================================================================
# Smoke Tests
# ============================================================================


@pytest.mark.smoke
@pytest.mark.unit
def test_client_portal_smoke(app, user, test_client):
    """Smoke test for client portal basic functionality"""
    with app.app_context():
        # Enable portal
        user.client_portal_enabled = True
        user.client_id = test_client.id
        db.session.commit()

        # Verify properties
        assert user.is_client_portal_user is True

        # Get portal data
        data = user.get_client_portal_data()
        assert data is not None
        assert data["client"] == test_client
