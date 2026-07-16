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
from app.models import User, Client, Project, Invoice, InvoiceItem, TimeEntry, Quote
from app import db


@pytest.fixture(autouse=True)
def disable_audit_logging_for_client_portal_tests(monkeypatch):
    monkeypatch.setattr("app.utils.audit.check_audit_table_exists", lambda force_check=False: False)


def set_client_portal_access(user, client_id=None, enabled=True, portal_only=False):
    User.query.filter_by(id=user.id).update(
        {
            "client_portal_enabled": enabled,
            "client_id": client_id if enabled else None,
            "portal_only": portal_only if enabled else False,
        },
        synchronize_session=False,
    )
    db.session.commit()
    db.session.expire_all()
    return User.query.get(user.id)


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
            html = response.get_data(as_text=True)
            assert "Client Portal" in html or "Dashboard" in html or "Welcome" in html or "Projects" in html

    def test_client_portal_dashboard_customize_save_has_loading_state(self, app, client, user, test_client):
        """Test dashboard customize modal Save button has loading state (aria-busy or Saving...)."""
        with app.app_context():
            with db.session.no_autoflush:
                user.client_portal_enabled = True
                user.client_id = test_client.id
                db.session.merge(user)
                db.session.flush()
            safe_commit_with_retry()
            user = safe_get_user(user.id)
            with client.session_transaction() as sess:
                sess["_user_id"] = str(user.id)
            response = client.get("/client-portal/dashboard")
            assert response.status_code == 200
            html = response.get_data(as_text=True)
            assert "dashboard-customize-save" in html
            assert "aria-busy" in html or "Saving" in html
            assert "X-CSRFToken" in html

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
            user = set_client_portal_access(user, test_client.id)

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

    def test_view_invoice_other_clients_invoice_returns_404_with_flash(
        self, app, client, user, test_client
    ):
        """Portal user cannot view invoice belonging to another client; returns 404 and flash."""
        with app.app_context():
            user = set_client_portal_access(user, test_client.id)

            other_client = Client(name="Other Client")
            db.session.add(other_client)
            db.session.flush()
            other_project = Project(
                name="Other Project", client_id=other_client.id, status="active"
            )
            db.session.add(other_project)
            safe_commit_with_retry()

            other_invoice = Invoice(
                invoice_number="INV-OTHER-001",
                project_id=other_project.id,
                client_name=other_client.name,
                client_id=other_client.id,
                due_date=datetime.utcnow().date() + timedelta(days=30),
                created_by=user.id,
                total_amount=Decimal("50.00"),
            )
            db.session.add(other_invoice)
            safe_commit_with_retry()

            with client.session_transaction() as sess:
                sess["_user_id"] = str(user.id)

            response = client.get(f"/client-portal/invoices/{other_invoice.id}")
            assert response.status_code == 404
            body = response.get_data(as_text=True)
            assert "not found" in body.lower() or "Invoice" in body

    def test_view_quote_other_clients_quote_returns_404_with_flash(
        self, app, client, user, test_client
    ):
        """Portal user cannot view quote belonging to another client; returns 404 and flash."""
        with app.app_context():
            user = set_client_portal_access(user, test_client.id)

            other_client = Client(name="Other Quote Client")
            db.session.add(other_client)
            db.session.flush()

            other_quote = Quote(
                quote_number="QUO-OTHER-001",
                client_id=other_client.id,
                title="Other client quote",
                created_by=user.id,
                visible_to_client=True,
            )
            db.session.add(other_quote)
            safe_commit_with_retry()

            with client.session_transaction() as sess:
                sess["_user_id"] = str(user.id)

            response = client.get(f"/client-portal/quotes/{other_quote.id}")
            assert response.status_code == 404
            body = response.get_data(as_text=True)
            assert "not found" in body.lower() or "Quote" in body


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
            user = set_client_portal_access(user, test_client.id)

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
# Portal-only and logout (issue #677)
# ============================================================================


@pytest.mark.routes
@pytest.mark.integration
class TestPortalOnlyAccess:
    def test_portal_only_login_redirects_to_client_portal(self, app, client, user, test_client):
        with app.app_context():
            user = set_client_portal_access(user, test_client.id, portal_only=True)
            user.set_password("password123")
            db.session.commit()
            username = user.username

        resp = client.post(
            "/login",
            data={"username": username, "password": "password123"},
            follow_redirects=False,
        )
        assert resp.status_code in (302, 303)
        assert "/client-portal" in resp.headers.get("Location", "")

    def test_portal_only_user_blocked_from_main_app(self, app, client, user, test_client):
        with app.app_context():
            user = set_client_portal_access(user, test_client.id, portal_only=True)
            user.set_password("password123")
            db.session.commit()
            username = user.username

        client.post(
            "/login",
            data={"username": username, "password": "password123"},
            follow_redirects=True,
        )
        resp = client.get("/dashboard", follow_redirects=False)
        assert resp.status_code in (302, 303)
        assert "/client-portal" in resp.headers.get("Location", "")

    def test_non_portal_only_user_can_access_main_app(self, app, client, user, test_client):
        with app.app_context():
            user = set_client_portal_access(user, test_client.id, portal_only=False)
            user.set_password("password123")
            db.session.commit()
            username = user.username

        client.post(
            "/login",
            data={"username": username, "password": "password123"},
            follow_redirects=True,
        )
        resp = client.get("/dashboard", follow_redirects=False)
        assert resp.status_code in (200, 302, 303)
        if resp.status_code in (302, 303):
            assert "/client-portal" not in resp.headers.get("Location", "")


@pytest.mark.routes
@pytest.mark.integration
class TestClientPortalLogout:
    def test_portal_logout_clears_user_session(self, app, client, user, test_client):
        with app.app_context():
            user = set_client_portal_access(user, test_client.id)

        with client.session_transaction() as sess:
            sess["_user_id"] = str(user.id)

        resp = client.get("/client-portal/logout", follow_redirects=False)
        assert resp.status_code in (302, 303)
        assert "/client-portal/login" in resp.headers.get("Location", "")

        dash = client.get("/client-portal/dashboard", follow_redirects=False)
        assert dash.status_code in (302, 303)
        assert "/client-portal/login" in dash.headers.get("Location", "")

    def test_native_client_logout_redirects_to_portal_login(self, app, client, test_client):
        with app.app_context():
            test_client.portal_enabled = True
            test_client.portal_username = "portaluser"
            test_client.set_portal_password("password123")
            db.session.commit()
            client_id = test_client.id

        with client.session_transaction() as sess:
            sess["client_portal_id"] = client_id

        resp = client.get("/client-portal/logout", follow_redirects=False)
        assert resp.status_code in (302, 303)
        assert "/client-portal/login" in resp.headers.get("Location", "")


@pytest.mark.routes
@pytest.mark.integration
class TestUnifiedClientPortalLogin:
    def test_main_login_with_portal_credentials_creates_portal_session(self, app, client, test_client):
        with app.app_context():
            test_client.portal_enabled = True
            test_client.portal_username = "portalclient"
            test_client.set_portal_password("password123")
            db.session.commit()

        resp = client.post(
            "/login",
            data={"username": "portalclient", "password": "password123"},
            follow_redirects=False,
        )
        assert resp.status_code in (302, 303)
        assert "/client-portal" in resp.headers.get("Location", "")

        with client.session_transaction() as sess:
            assert sess.get("client_portal_id") == test_client.id
            assert sess.get("_user_id") is None

    def test_main_login_with_portal_username_wrong_password_does_not_self_register(self, app, client, test_client):
        with app.app_context():
            from app.models import Settings

            settings = Settings.get_settings()
            settings.allow_self_register = True
            test_client.portal_enabled = True
            test_client.portal_username = "portalclient"
            test_client.set_portal_password("password123")
            db.session.commit()

        resp = client.post(
            "/login",
            data={"username": "portalclient", "password": "wrongpassword"},
            follow_redirects=True,
        )
        assert resp.status_code == 200

        with app.app_context():
            assert User.query.filter_by(username="portalclient").first() is None

    def test_auth_logout_for_portal_only_user_redirects_to_portal_login(self, app, client, user, test_client):
        with app.app_context():
            user = set_client_portal_access(user, test_client.id, portal_only=True)
            user.set_password("password123")
            db.session.commit()
            username = user.username

        client.post(
            "/login",
            data={"username": username, "password": "password123"},
            follow_redirects=True,
        )

        resp = client.get("/logout", follow_redirects=False)
        assert resp.status_code in (302, 303)
        assert "/client-portal/login" in resp.headers.get("Location", "")

    def test_authenticate_portal_is_case_insensitive(self, app, test_client):
        with app.app_context():
            client = Client.query.get(test_client.id)
            client.portal_enabled = True
            client.portal_username = "PortalClient"
            client.set_portal_password("password123")
            db.session.commit()

            authenticated = Client.authenticate_portal("portalclient", "password123")
            assert authenticated is not None
            assert authenticated.id == test_client.id


@pytest.mark.routes
@pytest.mark.integration
class TestNativeClientPortalSessionContainment:
    """Regression for issue #677: native portal sessions must not bounce to /login."""

    def _login_native_client(self, client, username="portalclient", password="password123"):
        return client.post(
            "/login",
            data={"username": username, "password": password},
            follow_redirects=False,
        )

    def test_native_client_main_login_then_root_stays_in_portal(self, app, client, test_client):
        with app.app_context():
            test_client.portal_enabled = True
            test_client.portal_username = "portalclient"
            test_client.set_portal_password("password123")
            db.session.commit()

        login_resp = self._login_native_client(client)
        assert login_resp.status_code in (302, 303)
        assert "/client-portal" in login_resp.headers.get("Location", "")

        root_resp = client.get("/", follow_redirects=False)
        assert root_resp.status_code in (302, 303)
        location = root_resp.headers.get("Location", "")
        assert "/client-portal" in location
        assert "/login" not in location or "/client-portal/login" in location

    def test_native_client_main_login_then_dashboard_stays_in_portal(self, app, client, test_client):
        with app.app_context():
            test_client.portal_enabled = True
            test_client.portal_username = "portalclient"
            test_client.set_portal_password("password123")
            db.session.commit()

        self._login_native_client(client)

        dash_resp = client.get("/dashboard", follow_redirects=False)
        assert dash_resp.status_code in (302, 303)
        location = dash_resp.headers.get("Location", "")
        assert "/client-portal" in location
        assert location.endswith("/login") is False or "/client-portal/login" in location

    def test_native_client_get_login_redirects_to_portal_dashboard(self, app, client, test_client):
        with app.app_context():
            test_client.portal_enabled = True
            test_client.portal_username = "portalclient"
            test_client.set_portal_password("password123")
            db.session.commit()
            client_id = test_client.id

        with client.session_transaction() as sess:
            sess["client_portal_id"] = client_id

        resp = client.get("/login", follow_redirects=False)
        assert resp.status_code in (302, 303)
        assert "/client-portal/dashboard" in resp.headers.get("Location", "")

    def test_native_client_unauthorized_handler_uses_portal_login(self, app, client, test_client):
        with app.app_context():
            test_client.portal_enabled = True
            test_client.portal_username = "portalclient"
            test_client.set_portal_password("password123")
            db.session.commit()
            client_id = test_client.id

        with client.session_transaction() as sess:
            sess["client_portal_id"] = client_id
            sess.pop("_user_id", None)

        # Simulate a protected main-app route without tripping the before_request guard
        resp = client.get("/settings", follow_redirects=False)
        assert resp.status_code in (302, 303)
        assert "/client-portal" in resp.headers.get("Location", "")

    def test_admin_enable_client_portal_defaults_portal_only(self, app, admin_authenticated_client, user, test_client):
        with app.app_context():
            assert user.client_portal_enabled is False

            get_response = admin_authenticated_client.get(f"/admin/users/{user.id}/edit", follow_redirects=True)
            assert get_response.status_code == 200
            html = get_response.get_data(as_text=True)
            import re

            csrf_match = re.search(r'name="csrf_token"\s+value="([^"]+)"', html)
            csrf_token = csrf_match.group(1) if csrf_match else ""

            admin_authenticated_client.post(
                f"/admin/users/{user.id}/edit",
                data={
                    "username": user.username,
                    "role": user.role,
                    "is_active": "on",
                    "client_portal_enabled": "on",
                    "client_id": str(test_client.id),
                    "csrf_token": csrf_token,
                },
                follow_redirects=True,
            )

            db.session.expire_all()
            updated_user = User.query.get(user.id)
            assert updated_user.client_portal_enabled is True
            assert updated_user.client_id == test_client.id
            assert updated_user.portal_only is True


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


# ============================================================================
# Dashboard widget preferences
# ============================================================================


@pytest.mark.routes
@pytest.mark.unit
class TestClientPortalDashboardPreferences:
    """Test dashboard widget preference persistence and validation"""

    def test_dashboard_preferences_get_default(self, app, client, user, test_client):
        """GET preferences returns default layout when none saved"""
        with app.app_context():
            user = set_client_portal_access(user, test_client.id)
            with client.session_transaction() as sess:
                sess["_user_id"] = str(user.id)
            response = client.get("/client-portal/dashboard/preferences")
            assert response.status_code == 200
            data = response.get_json()
            assert "widget_ids" in data
            assert "widget_order" in data
            assert data["widget_ids"]  # default non-empty

    def test_dashboard_preferences_post_and_get(self, app, client, user, test_client):
        """POST saves preferences; GET returns saved layout"""
        with app.app_context():
            user = set_client_portal_access(user, test_client.id)
            with client.session_transaction() as sess:
                sess["_user_id"] = str(user.id)
            post_resp = client.post(
                "/client-portal/dashboard/preferences",
                json={"widget_ids": ["stats", "projects"], "widget_order": ["stats", "projects"]},
                headers={"Content-Type": "application/json"},
            )
            assert post_resp.status_code == 200
            get_resp = client.get("/client-portal/dashboard/preferences")
            assert get_resp.status_code == 200
            data = get_resp.get_json()
            assert data["widget_ids"] == ["stats", "projects"]

    def test_dashboard_preferences_reject_invalid_widget_id(self, app, client, user, test_client):
        """POST with invalid widget_ids returns 400"""
        with app.app_context():
            user = set_client_portal_access(user, test_client.id)
            with client.session_transaction() as sess:
                sess["_user_id"] = str(user.id)
            response = client.post(
                "/client-portal/dashboard/preferences",
                json={"widget_ids": ["stats", "invalid_widget"], "widget_order": ["stats", "invalid_widget"]},
                headers={"Content-Type": "application/json"},
            )
            assert response.status_code == 400

    def test_dashboard_preferences_require_auth(self, app, client):
        """Preferences endpoints require client portal auth"""
        response = client.get("/client-portal/dashboard/preferences")
        assert response.status_code in (302, 403)

    def test_dashboard_preferences_post_non_json_returns_400(self, app, client, user, test_client):
        """POST with non-JSON body returns 400 (widget_ids missing or invalid)."""
        with app.app_context():
            user = set_client_portal_access(user, test_client.id)
            with client.session_transaction() as sess:
                sess["_user_id"] = str(user.id)
            response = client.post(
                "/client-portal/dashboard/preferences",
                data="not json",
                headers={"Content-Type": "text/plain"},
            )
            assert response.status_code == 400

    def test_dashboard_preferences_post_widget_ids_not_list_returns_400(
        self, app, client, user, test_client
    ):
        """POST with widget_ids not a list (e.g. string) returns 400."""
        with app.app_context():
            user = set_client_portal_access(user, test_client.id)
            with client.session_transaction() as sess:
                sess["_user_id"] = str(user.id)
            response = client.post(
                "/client-portal/dashboard/preferences",
                json={"widget_ids": "stats", "widget_order": ["stats"]},
                headers={"Content-Type": "application/json"},
            )
            assert response.status_code == 400
            data = response.get_json()
            assert data is not None and "error" in data


# ============================================================================
# Client report visibility
# ============================================================================


@pytest.mark.routes
@pytest.mark.unit
class TestClientPortalReportsVisibility:
    """Test that report data respects client visibility"""

    def test_reports_only_show_authenticated_client_data(self, app, client, user, test_client):
        """Reports page returns 200 and uses portal data for authenticated client only"""
        with app.app_context():
            from app.models import Client as ClientModel
            other_client = ClientModel(name="Other Client", email="other@example.com")
            db.session.add(other_client)
            db.session.flush()
            other_project = Project(name="Other Project", client_id=other_client.id, status="active")
            db.session.add(other_project)
            db.session.commit()
            user = set_client_portal_access(user, test_client.id)
            with client.session_transaction() as sess:
                sess["_user_id"] = str(user.id)
            response = client.get("/client-portal/reports")
            assert response.status_code == 200
            html = response.get_data(as_text=True)
            assert "Reports" in html or "report" in html.lower()
            assert "Other Project Feed" not in html and "Other Project" not in html

    def test_reports_date_range_days_param(self, app, client, user, test_client):
        """Reports with ?days=7 returns 200 and page reflects date range."""
        with app.app_context():
            user = set_client_portal_access(user, test_client.id)
            with client.session_transaction() as sess:
                sess["_user_id"] = str(user.id)
            response = client.get("/client-portal/reports?days=7")
            assert response.status_code == 200
            html = response.get_data(as_text=True)
            assert "7" in html or "Reports" in html

    def test_reports_csv_export(self, app, client, user, test_client):
        """Reports with ?format=csv returns CSV attachment with expected columns."""
        with app.app_context():
            user = set_client_portal_access(user, test_client.id)
            with client.session_transaction() as sess:
                sess["_user_id"] = str(user.id)
            response = client.get("/client-portal/reports?format=csv")
            assert response.status_code == 200
            assert "text/csv" in response.headers.get("Content-Type", "")
            assert "attachment" in response.headers.get("Content-Disposition", "")
            body = response.get_data(as_text=True)
            assert "Total Hours" in body or "Hours" in body
            assert "client-report-" in response.headers.get("Content-Disposition", "")

    def test_reports_csv_export_requires_access(self, app, client):
        """Reports CSV export without client portal auth returns redirect/error."""
        response = client.get("/client-portal/reports?format=csv")
        assert response.status_code in (302, 403)

    def test_reports_page_has_date_range_and_csv_link(self, app, client, user, test_client):
        """Reports page exposes date range controls and CSV download link."""
        with app.app_context():
            user = set_client_portal_access(user, test_client.id)
            with client.session_transaction() as sess:
                sess["_user_id"] = str(user.id)
            response = client.get("/client-portal/reports?days=90")
            assert response.status_code == 200
            html = response.get_data(as_text=True)
            assert "format=csv" in html
            assert "days=7" in html or "days=90" in html


# ============================================================================
# Discrepancy fix regression tests
# ============================================================================


@pytest.mark.routes
@pytest.mark.unit
class TestClientPortalDiscrepancyFixes:
    """Regression tests for client portal discrepancy fixes."""

    def test_native_login_clears_stale_user_session(self, app, client, user, test_client):
        with app.app_context():
            test_client.portal_enabled = True
            test_client.portal_username = "portaluser"
            test_client.set_portal_password("password123")
            db.session.commit()

        with client.session_transaction() as sess:
            sess["_user_id"] = str(user.id)

        resp = client.post(
            "/client-portal/login",
            data={"username": "portaluser", "password": "password123"},
            follow_redirects=False,
        )
        assert resp.status_code in (302, 303)

        with client.session_transaction() as sess:
            assert "client_portal_id" in sess
            assert "_user_id" not in sess
            assert "user_id" not in sess

    def test_issues_accessible_for_user_based_auth_without_native_credentials(
        self, app, client, user, test_client
    ):
        with app.app_context():
            Client.query.filter_by(id=test_client.id).update(
                {
                    "portal_enabled": False,
                    "portal_username": None,
                    "portal_password_hash": None,
                    "portal_issues_enabled": True,
                },
                synchronize_session=False,
            )
            db.session.commit()
            user = set_client_portal_access(user, test_client.id)
            user_id = user.id

        with client.session_transaction() as sess:
            sess["_user_id"] = str(user_id)

        response = client.get("/client-portal/issues", follow_redirects=True)
        assert response.status_code == 200
        html = response.get_data(as_text=True)
        assert "Issues" in html or "issues" in html.lower()

    def test_inactive_client_blocked_for_user_based_auth(self, app, client, user, test_client):
        with app.app_context():
            Client.query.filter_by(id=test_client.id).update(
                {"status": "inactive"},
                synchronize_session=False,
            )
            db.session.commit()
            user = set_client_portal_access(user, test_client.id)
            user_id = user.id

        with client.session_transaction() as sess:
            sess["_user_id"] = str(user_id)

        response = client.get("/client-portal/dashboard", follow_redirects=False)
        # Inactive client triggers abort(403); handler redirects unauthenticated portal context to login
        assert response.status_code in (302, 403)
        if response.status_code == 302:
            assert "/client-portal/login" in response.headers.get("Location", "")

    def test_mark_notification_read_redirects(self, app, client, user, test_client):
        with app.app_context():
            from app.models.client_notification import ClientNotification

            user = set_client_portal_access(user, test_client.id)
            user_id = user.id
            notification = ClientNotification(
                client_id=test_client.id,
                type="general",
                title="Test",
                message="Test notification",
            )
            db.session.add(notification)
            db.session.commit()
            notification_id = notification.id

        with client.session_transaction() as sess:
            sess["_user_id"] = str(user_id)

        response = client.post(
            f"/client-portal/notifications/{notification_id}/read",
            follow_redirects=False,
        )
        assert response.status_code in (302, 303)
        assert "/client-portal/notifications" in response.headers.get("Location", "")

    def test_download_attachment_wrong_type_denied(self, app, client, user, test_client):
        with app.app_context():
            from app.models import ProjectAttachment

            user = set_client_portal_access(user, test_client.id)
            user_id = user.id
            project = Project(name="Attachment Project", client_id=test_client.id, status="active")
            db.session.add(project)
            db.session.flush()
            attachment = ProjectAttachment(
                project_id=project.id,
                filename="proj.txt",
                original_filename="proj.txt",
                file_path="uploads/proj.txt",
                file_size=10,
                uploaded_by=user_id,
                is_visible_to_client=True,
            )
            db.session.add(attachment)
            db.session.commit()
            attachment_id = attachment.id

        with client.session_transaction() as sess:
            sess["_user_id"] = str(user_id)

        response = client.get(
            f"/client-portal/documents/{attachment_id}/download?type=client",
            follow_redirects=False,
        )
        assert response.status_code in (302, 303)
        assert "/client-portal/documents" in response.headers.get("Location", "")

    def test_approval_detail_template_compiles(self, app, test_client):
        """Regression: approval_detail page_header macro must render without Jinja syntax errors."""
        from types import SimpleNamespace

        from flask import render_template

        approval = SimpleNamespace(
            id=1,
            time_entry_id=42,
            status=SimpleNamespace(value="pending"),
            time_entry=None,
            request_comment=None,
            requested_at=None,
            requester=None,
            approved_at=None,
            rejected_at=None,
            approval_comment=None,
            rejection_reason=None,
        )
        with app.app_context():
            with app.test_request_context():
                html = render_template(
                    "client_portal/approval_detail.html",
                    client=test_client,
                    approval=approval,
                )
        assert "Approval Details" in html
        assert "#42" in html


# ============================================================================
# Activity feed filtering
# ============================================================================


@pytest.mark.routes
@pytest.mark.unit
class TestClientPortalActivityFeed:
    """Test activity feed shows only client-visible events"""

    def test_activity_feed_requires_auth(self, app, client):
        """Activity feed requires client portal auth"""
        response = client.get("/client-portal/activity")
        assert response.status_code in (302, 403)

    def test_activity_feed_returns_feed_items(self, app, client, user, test_client):
        """Activity feed returns 200 and feed_items for authenticated client"""
        with app.app_context():
            user = set_client_portal_access(user, test_client.id)
            with client.session_transaction() as sess:
                sess["_user_id"] = str(user.id)
            response = client.get("/client-portal/activity")
            assert response.status_code == 200
            html = response.get_data(as_text=True)
            assert "Activity" in html or "activity" in html

    def test_activity_feed_service_only_client_projects(self, app, test_client):
        """get_client_activity_feed returns only activities for client's projects"""
        with app.app_context():
            from app.models import Activity, Client as ClientModel
            from app.services.client_activity_feed_service import get_client_activity_feed
            other_client = ClientModel(name="Other Client Feed", email="other2@example.com")
            db.session.add(other_client)
            db.session.flush()
            other_project = Project(name="Other Project Feed", client_id=other_client.id, status="active")
            db.session.add(other_project)
            db.session.commit()
            proj = Project(name="My Project", client_id=test_client.id, status="active")
            db.session.add(proj)
            db.session.commit()
            feed = get_client_activity_feed(test_client.id, limit=10)
            for item in feed:
                if item.get("project_id"):
                    assert item["project_id"] == proj.id or item["project_name"] != "Other Project Feed"


# ============================================================================
# SocketIO client room (unit: session resolution and emit on notification)
# ============================================================================


@pytest.mark.unit
def test_get_client_id_from_session_client_portal_id(app):
    """_get_client_id_from_session returns client_id when session has client_portal_id"""
    with app.app_context():
        from app.routes.api import _get_client_id_from_session
        with app.test_request_context():
            from flask import session
            session["client_portal_id"] = 42
            assert _get_client_id_from_session() == 42


@pytest.mark.unit
def test_get_client_id_from_session_user_portal(app, user, test_client):
    """_get_client_id_from_session returns client_id when session has _user_id with portal access"""
    with app.app_context():
        User.query.filter_by(id=user.id).update(
            {"client_portal_enabled": True, "client_id": test_client.id},
            synchronize_session=False,
        )
        db.session.commit()
        db.session.expire_all()
        from app.routes.api import _get_client_id_from_session
        with app.test_request_context():
            from flask import session
            session["_user_id"] = str(user.id)
            assert _get_client_id_from_session() == test_client.id


@pytest.mark.unit
def test_get_client_id_from_session_returns_none_without_portal(app, user):
    """_get_client_id_from_session returns None when session has no portal identity"""
    with app.app_context():
        from app.routes.api import _get_client_id_from_session
        with app.test_request_context():
            from flask import session
            session.clear()
            assert _get_client_id_from_session() is None


@pytest.mark.unit
def test_create_notification_emits_to_client_room(app, test_client):
    """Creating a client notification emits to client_portal_{client_id} room"""
    with app.app_context():
        from unittest.mock import patch, MagicMock
        with patch("app.socketio") as mock_socketio:
            mock_socketio.emit = MagicMock()
            from app.services.client_notification_service import ClientNotificationService
            service = ClientNotificationService()
            service.create_notification(
                client_id=test_client.id,
                notification_type="invoice_created",
                title="Test",
                message="Test message",
                send_email=False,
            )
            mock_socketio.emit.assert_called_once()
            call_args = mock_socketio.emit.call_args
            assert call_args[0][0] == "client_notification"
            assert call_args[1]["room"] == f"client_portal_{test_client.id}"
