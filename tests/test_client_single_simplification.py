"""
Tests for Client Single-Client Simplification (Issue #467).

When only one active client exists, the client selection field is pre-filled
and grayed out across manual time logging, project creation, and similar forms.
"""

import pytest
from app import db
from app.models import Client
from flask import url_for


@pytest.mark.integration
@pytest.mark.routes
def test_manual_entry_shows_single_client_prefilled(authenticated_client, app, user, test_client):
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
def test_manual_entry_shows_select_when_multiple_clients(authenticated_client, app, user, test_client):
    """When multiple clients exist, manual entry form shows normal client select."""
    with app.app_context():
        # Add a second client
        second = Client(
            name="Second Client",
            email="second@example.com",
            status="active",
        )
        db.session.add(second)
        db.session.commit()

        active_count = Client.query.filter_by(status="active").count()
        assert active_count >= 2

        response = authenticated_client.get(url_for("timer.manual_entry"))
        assert response.status_code == 200
        html = response.get_data(as_text=True)

        # Should have normal select, not single-client hidden + disabled
        assert '<select' in html
        assert 'id="client_id"' in html or 'name="client_id"' in html
        assert "Select a client" in html or "client" in html.lower()
