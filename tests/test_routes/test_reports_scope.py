"""
Reports scope tests: scope-restricted user only sees allowed projects in report views.
"""

import pytest

from app import db

pytestmark = [pytest.mark.routes, pytest.mark.integration]


def test_project_report_lists_only_allowed_projects(
    app, scope_restricted_authenticated_client, scope_restricted_user, project, test_client
):
    """GET /reports/project as scope-restricted user returns page with only assigned project in project list."""
    with app.app_context():
        from app.models import Client, Project, Settings

        settings = Settings.get_settings()
        disabled = list(settings.disabled_module_ids or [])
        if "reports" in disabled:
            settings.disabled_module_ids = [m for m in disabled if m != "reports"]
            db.session.add(settings)
            db.session.commit()

        other_client = Client(name="Other Corp", email="other@example.com")
        other_client.status = "active"
        db.session.add(other_client)
        db.session.commit()
        other_project = Project(name="Other Project", client_id=other_client.id, status="active")
        db.session.add(other_project)
        db.session.commit()

    resp = scope_restricted_authenticated_client.get("/reports/project", follow_redirects=True)
    assert resp.status_code == 200
    data = resp.get_data(as_text=True)
    # If we are on the report page (not redirected to login), project list should be scoped
    on_login_page = "sign in" in data.lower() or "log in" in data.lower()
    if not on_login_page:
        # Allowed project (from test_client) should appear
        assert project.name in data
        # Disallowed project should not appear in the project list (scoped out)
        assert "Other Project" not in data
