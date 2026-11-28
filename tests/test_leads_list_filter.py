"""Regression tests for leads list status filter (#996)."""

import pytest

from app import db
from app.models import Lead, Settings

pytestmark = [pytest.mark.unit, pytest.mark.routes]


@pytest.fixture
def leads_module_enabled(app):
    """Ensure the leads module is enabled for the test."""
    settings = Settings.get_settings()
    disabled = list(settings.disabled_module_ids or [])
    if "leads" in disabled:
        settings.disabled_module_ids = [m for m in disabled if m != "leads"]
        db.session.add(settings)
        db.session.commit()


@pytest.fixture
def sample_leads(app, admin_user):
    """Create active, converted, and lost leads."""
    active = Lead(first_name="Active", last_name="Lead", created_by=admin_user.id, status="new")
    converted = Lead(
        first_name="Converted", last_name="Lead", created_by=admin_user.id, status="converted"
    )
    lost = Lead(first_name="Lost", last_name="Lead", created_by=admin_user.id, status="lost")
    db.session.add_all([active, converted, lost])
    db.session.commit()
    return {"active": active, "converted": converted, "lost": lost}


def test_leads_list_default_excludes_converted_and_lost(
    client, admin_user, leads_module_enabled, sample_leads
):
    with client.session_transaction() as sess:
        sess["_user_id"] = str(admin_user.id)

    response = client.get("/leads")
    assert response.status_code == 200
    html = response.get_data(as_text=True)
    assert "Active Lead" in html
    assert "Converted Lead" not in html
    assert "Lost Lead" not in html


def test_leads_list_status_all_includes_converted_and_lost(
    client, admin_user, leads_module_enabled, sample_leads
):
    with client.session_transaction() as sess:
        sess["_user_id"] = str(admin_user.id)

    response = client.get("/leads?status=all")
    assert response.status_code == 200
    html = response.get_data(as_text=True)
    assert "Active Lead" in html
    assert "Converted Lead" in html
    assert "Lost Lead" in html


def test_leads_list_status_converted_only(
    client, admin_user, leads_module_enabled, sample_leads
):
    with client.session_transaction() as sess:
        sess["_user_id"] = str(admin_user.id)

    response = client.get("/leads?status=converted")
    assert response.status_code == 200
    html = response.get_data(as_text=True)
    assert "Converted Lead" in html
    assert "Active Lead" not in html
    assert "Lost Lead" not in html
