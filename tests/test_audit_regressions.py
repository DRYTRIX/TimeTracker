"""Regression smoke tests for issues fixed after the 2026-10-04 instance audit.

Each case GETs a previously-500 route as an admin and expects a non-500 response.
"""

import pytest

from app import db
from app.models import User


AUDIT_GET_ROUTES = [
    "/activity",
    "/expenses",
    "/expenses/scan-receipt",
    "/inventory/reservations",
    "/quotes/templates",
    "/quotes/templates/create",
    "/settings/profile",
    "/chat",
    "/workflows/create",
    "/workflows/templates/create",
    "/admin/geofences",
    "/admin/payroll-templates",
    "/admin/gamification",
]


@pytest.fixture
def oidc_detail_user(app, admin_user):
    """Ensure a local user exists for the OIDC user detail page."""
    with app.app_context():
        user = User.query.filter_by(username="audit_oidc_user").first()
        if user is None:
            user = User(username="audit_oidc_user", role="user", email="audit_oidc@example.com")
            user.is_active = True
            user.set_password("password123")
            db.session.add(user)
            db.session.commit()
        return user.id


@pytest.mark.smoke
@pytest.mark.parametrize("path", AUDIT_GET_ROUTES)
def test_audit_fixed_pages_do_not_500(admin_authenticated_client, path):
    response = admin_authenticated_client.get(path, follow_redirects=True)
    assert response.status_code < 500, f"{path} returned {response.status_code}"


@pytest.mark.smoke
def test_audit_oidc_user_detail_does_not_500(admin_authenticated_client, oidc_detail_user):
    response = admin_authenticated_client.get(
        f"/admin/oidc/user/{oidc_detail_user}",
        follow_redirects=True,
    )
    assert response.status_code < 500, f"oidc user detail returned {response.status_code}"


@pytest.mark.smoke
def test_audit_activity_stats_api_does_not_500(admin_authenticated_client):
    response = admin_authenticated_client.get("/api/activities/stats")
    assert response.status_code < 500, f"/api/activities/stats returned {response.status_code}"


@pytest.mark.smoke
def test_audit_unpaid_hours_by_salesman_does_not_500(admin_authenticated_client):
    response = admin_authenticated_client.get("/api/unpaid-hours/by-salesman")
    assert response.status_code < 500, f"/api/unpaid-hours/by-salesman returned {response.status_code}"


@pytest.mark.smoke
def test_audit_missing_client_note_returns_404_not_500(admin_authenticated_client):
    response = admin_authenticated_client.get("/api/client-notes/999999")
    assert response.status_code == 404
    assert response.status_code < 500
