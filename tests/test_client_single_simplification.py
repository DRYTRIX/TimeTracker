"""
Tests for Client Single-Client Simplification (Issue #467).

When only one active client exists, the client selection field is pre-filled
and grayed out across manual time logging, project creation, and similar forms.
"""

import re

import pytest
from app import db
from app.models import Client
from flask import url_for


def _project_select_attrs(html: str) -> str:
    """Return the opening <select ...> tag for #project_id."""
    match = re.search(
        r'<select\b[^>]*\bid=["\']project_id["\'][^>]*>',
        html,
        flags=re.IGNORECASE,
    )
    if not match:
        match = re.search(
            r'<select\b[^>]*\bname=["\']project_id["\'][^>]*>',
            html,
            flags=re.IGNORECASE,
        )
    assert match, "Expected a project_id <select> on the manual entry form"
    return match.group(0)


@pytest.mark.integration
@pytest.mark.routes
def test_manual_entry_shows_single_client_prefilled(
    authenticated_client, app, user, test_client, project
):
    """When only one client exists, manual entry form shows pre-filled grayed-out client."""
    with app.app_context():
        # Ensure exactly one active client (test_client from fixture)
        active_count = Client.query.filter_by(status="active").count()
        assert active_count == 1, "Expected exactly 1 active client for this test"

        response = authenticated_client.get(url_for("timer.manual_entry"))
        assert response.status_code == 200
        html = response.get_data(as_text=True)

        # Should have hidden input for client_id (single-client mode)
        assert 'name="client_id"' in html
        assert f'value="{test_client.id}"' in html
        # Should have disabled readonly display
        assert "disabled" in html
        assert "readonly" in html
        assert test_client.name in html


@pytest.mark.integration
@pytest.mark.routes
def test_manual_entry_single_client_project_not_disabled(
    authenticated_client, app, user, test_client, project
):
    """Issue #789: with one client locked, the project picker must still be usable."""
    with app.app_context():
        active_count = Client.query.filter_by(status="active").count()
        assert active_count == 1, "Expected exactly 1 active client for this test"

        response = authenticated_client.get(url_for("timer.manual_entry"))
        assert response.status_code == 200
        html = response.get_data(as_text=True)

        # Client remains locked (#467 / #753)
        assert "readonly" in html
        assert f'value="{test_client.id}"' in html

        project_tag = _project_select_attrs(html)
        assert "disabled" not in project_tag, (
            "Project select must not be disabled when the sole client is auto-selected (#789)"
        )


@pytest.mark.integration
@pytest.mark.routes
def test_manual_entry_shows_select_when_multiple_clients(
    authenticated_client, app, user, test_client
):
    """When multiple clients exist, manual entry form shows normal client select."""
    with app.app_context():
        # Add a second client the test user can see (own-clients scope uses created_by)
        second = Client(
            name="Second Client",
            email="second@example.com",
            created_by=user.id,
        )
        second.status = "active"
        db.session.add(second)
        db.session.commit()

        active_count = Client.query.filter_by(status="active").count()
        assert active_count >= 2

        response = authenticated_client.get(url_for("timer.manual_entry"))
        assert response.status_code == 200
        html = response.get_data(as_text=True)

        # Main client control is a real <select>, not the single-client hidden lock
        assert re.search(
            r'<select\b[^>]*\bid=["\']client_id["\']',
            html,
            flags=re.IGNORECASE,
        ), "Expected a selectable client_id <select> when multiple clients are visible"
        assert not re.search(
            r'<input[^>]*\bid=["\']client_id["\'][^>]*data-auto-client',
            html,
            flags=re.IGNORECASE,
        ), "Single-client auto-lock must not apply when multiple clients are visible"

        # Issue #789: with no client chosen yet, project stays gated
        project_tag = _project_select_attrs(html)
        assert "disabled" in project_tag
