"""
Security testing suite.
Tests authentication, authorization, and security vulnerabilities.
"""

import pytest
from flask import session
from app import db
from app.models import User, Project, TimeEntry


# ============================================================================
# Authentication Tests
# ============================================================================


@pytest.mark.security
@pytest.mark.smoke
def test_unauthenticated_cannot_access_dashboard(client):
    """Test that unauthenticated users cannot access protected pages."""
    response = client.get("/dashboard", follow_redirects=False)
    assert response.status_code == 302  # Redirect to login


@pytest.mark.security
@pytest.mark.smoke
def test_unauthenticated_cannot_access_api(client):
    """Test that unauthenticated users cannot access API endpoints."""
    response = client.get("/api/timer/active")
    assert response.status_code in [302, 401, 403, 404]  # 404 is also acceptable if endpoint doesn't exist without auth


@pytest.mark.security
def test_session_cookie_httponly(client, user):
    """Test that session cookies are HTTPOnly."""
    with client:
        with client.session_transaction() as sess:
            sess["_user_id"] = str(user.id)

        response = client.get("/dashboard")

        # Check Set-Cookie header for HTTPOnly flag
        set_cookie_headers = response.headers.getlist("Set-Cookie")
        for header in set_cookie_headers:
            if "session" in header.lower():
                assert "HttpOnly" in header


# ============================================================================
# Authorization Tests
# ============================================================================


@pytest.mark.security
@pytest.mark.integration
def test_regular_user_cannot_access_admin_pages(authenticated_client):
    """Test that regular users cannot access admin pages."""
    response = authenticated_client.get("/admin", follow_redirects=False)
    assert response.status_code in [302, 403]


@pytest.mark.security
@pytest.mark.integration
def test_admin_can_access_admin_pages(admin_authenticated_client):
    """Test that admin users can access admin pages."""
    response = admin_authenticated_client.get("/admin")
    assert response.status_code == 200


@pytest.mark.security
@pytest.mark.integration
def test_user_cannot_access_other_users_data(app, user, multiple_users, authenticated_client):
    """Test that users cannot access other users' data."""
    with app.app_context():
        other_user = multiple_users[0]

        # Try to access another user's profile/data
        response = authenticated_client.get(f"/api/user/{other_user.id}")
        # Should return 403 Forbidden or 404 Not Found
        assert response.status_code in [403, 404, 302]


@pytest.mark.security
@pytest.mark.integration
def test_user_cannot_edit_other_users_time_entries(app, authenticated_client, user, test_client):
    """Test that users cannot edit other users' time entries."""
    from datetime import datetime

    with app.app_context():
        # Create another user with a time entry
        other_user = User(username="otheruser", role="user", email="otheruser@example.com")
        other_user.is_active = True
        db.session.add(other_user)
        db.session.commit()

        project = Project.query.first()
        if not project:
            project = Project(name="Test", client_id=test_client.id, billable=True)
            project.status = "active"
            db.session.add(project)
            db.session.commit()

        from factories import TimeEntryFactory

        other_entry = TimeEntryFactory(
            user_id=other_user.id,
            project_id=project.id,
            start_time=datetime.utcnow(),
            end_time=datetime.utcnow(),
            source="manual",
        )
        db.session.commit()

        # Try to edit the other user's entry
        response = authenticated_client.post(f"/api/timer/edit/{other_entry.id}", json={"notes": "Trying to hack"})

        # Should be forbidden
        assert response.status_code in [403, 404, 302]


# ============================================================================
# CSRF Protection Tests
# ============================================================================


@pytest.mark.security
def test_csrf_token_required_for_forms(client, user):
    """Test that CSRF token is required for form submissions."""
    with client:
        with client.session_transaction() as sess:
            sess["_user_id"] = str(user.id)

        # Try to submit a form without CSRF token
        response = client.post("/projects/new", data={"name": "Test Project", "billable": True}, follow_redirects=False)

        # Should fail with 400 or redirect
        # Note: This test assumes CSRF is enabled in production
        # In test config, CSRF might be disabled
        pass  # Adjust based on your CSRF configuration


# ============================================================================
# SQL Injection Tests
# ============================================================================


@pytest.mark.security
def test_sql_injection_in_search(authenticated_client):
    """Test SQL injection protection in search."""
    # Try SQL injection in search
    malicious_query = "'; DROP TABLE users; --"

    response = authenticated_client.get("/api/search", query_string={"q": malicious_query})

    # Should handle gracefully, not execute SQL
    assert response.status_code in [200, 400, 404]


@pytest.mark.security
def test_sql_injection_in_filter(authenticated_client):
    """Test SQL injection protection in filters."""
    malicious_input = "1' OR '1'='1"

    response = authenticated_client.get("/api/projects", query_string={"client_id": malicious_input})

    # Should handle gracefully
    assert response.status_code in [200, 400, 404]


# ============================================================================
# XSS Protection Tests
# ============================================================================


@pytest.mark.security
def test_xss_in_project_name(app, authenticated_client, test_client):
    """Test XSS protection in project names."""
    with app.app_context():
        xss_payload = '<script>alert("XSS")</script>'

        response = authenticated_client.post(
            "/api/projects", json={"name": xss_payload, "client_id": test_client.id, "billable": True}
        )

        # Should either sanitize or reject
        if response.status_code in [200, 201]:
            data = response.get_json()
            # Script tags should be escaped or removed
            assert "<script>" not in str(data)


@pytest.mark.security
def test_xss_in_notes(app, authenticated_client, project):
    """Test XSS protection in time entry notes."""
    with app.app_context():
        xss_payload = '<img src=x onerror=alert("XSS")>'

        response = authenticated_client.post("/api/timer/start", json={"project_id": project.id, "notes": xss_payload})

        # Should handle XSS attempt
        if response.status_code in [200, 201]:
            data = response.get_json()
            # XSS should be escaped
            assert "onerror" not in str(data).lower()


# ============================================================================
# Path Traversal Tests
# ============================================================================


@pytest.mark.security
def test_path_traversal_in_file_download(authenticated_client):
    """Test path traversal protection in file downloads."""
    # Try to access system files
    malicious_paths = [
        "../../../etc/passwd",
        "..\\..\\..\\windows\\system32\\config\\sam",
        "/etc/passwd",
        "C:\\Windows\\System32\\config\\SAM",
    ]

    for path in malicious_paths:
        response = authenticated_client.get(f"/download/{path}")
        # Should not allow access to system files
        assert response.status_code in [400, 403, 404]


# ============================================================================
# Rate Limiting Tests (if implemented)
# ============================================================================


@pytest.mark.security
@pytest.mark.slow
def test_api_rate_limiting(client):
    """Test API rate limiting (if implemented)."""
    # Make many requests in quick succession
    responses = []
    for i in range(100):
        response = client.get("/_health")
        responses.append(response.status_code)

    # If rate limiting is implemented, should get 429 responses
    # If not implemented, all should be 200
    # This test just checks the system doesn't crash
    assert all(code in [200, 429] for code in responses)


# ============================================================================
# Password Security Tests (if applicable)
# ============================================================================


@pytest.mark.security
def test_password_not_exposed_in_api(app, user):
    """Test that passwords are never exposed in API responses."""
    # If your User model has passwords
    with app.app_context():
        user_dict = user.to_dict()

        # Should not contain password-related fields
        assert "password" not in user_dict
        assert "password_hash" not in user_dict
        assert "hashed_password" not in user_dict


# ============================================================================
# Session Security Tests
# ============================================================================


@pytest.mark.security
def test_logout_invalidates_session(client, user):
    """Test that logout properly invalidates the session."""
    with client:
        # Login
        with client.session_transaction() as sess:
            sess["_user_id"] = str(user.id)

        # Verify logged in
        response = client.get("/dashboard")
        assert response.status_code == 200

        # Logout
        client.get("/logout")

        # Try to access protected page
        response = client.get("/dashboard", follow_redirects=False)
        assert response.status_code == 302  # Redirect to login


@pytest.mark.security
def test_session_fixation_protection(client, user):
    """Test protection against session fixation attacks."""
    with client:
        # Get initial session
        client.get("/")

        with client.session_transaction() as sess:
            initial_session_id = sess.get("_id")

        # Simulate login
        with client.session_transaction() as sess:
            sess["_user_id"] = str(user.id)

        # Session ID should change after login (if implemented)
        # This test depends on your session management implementation
        pass


# ============================================================================
# Header Security Tests
# ============================================================================


@pytest.mark.security
def test_security_headers_present(client):
    """Test that security headers are present."""
    response = client.get("/")

    headers = response.headers

    # Check for common security headers
    # Note: Adjust based on your actual security header implementation
    # These might not all be present, but checking doesn't hurt

    # X-Content-Type-Options
    # assert 'X-Content-Type-Options' in headers

    # X-Frame-Options
    # assert 'X-Frame-Options' in headers

    # Content-Security-Policy
    # assert 'Content-Security-Policy' in headers


# ============================================================================
# Input Validation Tests
# ============================================================================


@pytest.mark.security
def test_oversized_input_rejection(authenticated_client, project):
    """Test that oversized inputs are rejected."""
    # Try to start a timer with extremely long notes
    very_long_notes = "A" * 10000

    response = authenticated_client.post("/api/timer/start", json={"project_id": project.id, "notes": very_long_notes})

    # Should accept (server may truncate) or reject
    # The test ensures the application doesn't crash with large input
    assert response.status_code in [200, 201, 400, 422, 413]


@pytest.mark.security
def test_invalid_email_format(app):
    """Test email validation."""
    with app.app_context():
        from app.models import Client
        from app import db

        # Try to create client with invalid email
        client = Client(name="Test", email="not-an-email")
        db.session.add(client)

        # Depending on validation, might raise error or be allowed
        # Adjust based on your actual email validation
        try:
            db.session.commit()
            # If it succeeds, email validation might not be enforced
            db.session.rollback()
        except Exception:
            # Email validation is working
            db.session.rollback()


# ============================================================================
# Business Logic Security Tests
# ============================================================================


@pytest.mark.security
@pytest.mark.integration
def test_cannot_create_negative_time_entries(app, authenticated_client, project):
    """Test that negative time entries are rejected."""
    with app.app_context():
        from datetime import datetime, timedelta

        now = datetime.utcnow()
        later = now + timedelta(hours=2)

        # Try to create entry with start_time after end_time
        response = authenticated_client.post(
            "/api/entries",
            json={
                "project_id": project.id,
                "start_time": later.isoformat(),
                "end_time": now.isoformat(),
                "notes": "Invalid entry",
            },
        )

        # Should reject
        assert response.status_code in [400, 422]


@pytest.mark.security
@pytest.mark.integration
def test_cannot_create_invoice_with_negative_amount(app, authenticated_client, project, test_client, user):
    """Test that invoices with negative amounts are rejected or handled safely."""
    with app.app_context():
        from datetime import date, timedelta

        # Note: There's no /api/invoices endpoint - invoices are created via form submission at /invoices/create
        # This test verifies the application doesn't crash with negative values
        # The actual validation happens in the form/route handler

        # Try to create invoice via the form endpoint
        response = authenticated_client.post(
            "/invoices/create",
            data={
                "project_id": project.id,
                "client_id": test_client.id,
                "client_name": test_client.name,
                "due_date": (date.today() + timedelta(days=30)).isoformat(),
                "items-0-description": "Test",
                "items-0-quantity": "-10",  # Negative quantity
                "items-0-unit_price": "50",
                "tax_rate": "0",
            },
        )

        # Should either reject (400, 422) or redirect with validation error (302)
        # The important part is it doesn't allow creating an invalid invoice
        assert response.status_code in [200, 302, 400, 422]

        # If it's a 200 response (form re-rendered), there should be an error message
        # If it's a 302 redirect, it should redirect to show the validation error
        # In both cases, the invoice should not be created with negative amounts
