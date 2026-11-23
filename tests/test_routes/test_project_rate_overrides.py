"""Web UI routes for project rate overrides."""

from datetime import date
from decimal import Decimal

import pytest

from app import db
from app.models import RateOverride

pytestmark = [pytest.mark.unit, pytest.mark.routes]


def test_list_rates_page(admin_authenticated_client, project):
    resp = admin_authenticated_client.get(f"/projects/{project.id}/rates")
    assert resp.status_code == 200
    html = resp.get_data(as_text=True)
    assert "Rates" in html or "rate" in html.lower()


def test_add_rate_override(admin_authenticated_client, project, user):
    resp = admin_authenticated_client.post(
        f"/projects/{project.id}/rates/add",
        data={
            "user_id": str(user.id),
            "hourly_rate": "125.00",
            "effective_from": "2024-01-01",
            "effective_to": "2024-12-31",
        },
    )
    assert resp.status_code in (302, 303)
    override = RateOverride.query.filter_by(project_id=project.id, user_id=user.id).one()
    assert override.hourly_rate == Decimal("125.00")
    assert override.effective_from == date(2024, 1, 1)


def test_add_everyone_override(admin_authenticated_client, project):
    resp = admin_authenticated_client.post(
        f"/projects/{project.id}/rates/add",
        data={"user_id": "", "hourly_rate": "95.00"},
    )
    assert resp.status_code in (302, 303)
    override = RateOverride.query.filter_by(project_id=project.id, user_id=None).one()
    assert override.hourly_rate == Decimal("95.00")


def test_edit_rate_override(admin_authenticated_client, project, user):
    override = RateOverride(
        project_id=project.id,
        user_id=user.id,
        hourly_rate=Decimal("100.00"),
        effective_from=date(2024, 1, 1),
    )
    db.session.add(override)
    db.session.commit()

    resp = admin_authenticated_client.post(
        f"/projects/{project.id}/rates/{override.id}/edit",
        data={
            "user_id": str(user.id),
            "hourly_rate": "150.00",
            "effective_from": "2024-01-01",
            "effective_to": "2024-06-30",
        },
    )
    assert resp.status_code in (302, 303)
    db.session.refresh(override)
    assert override.hourly_rate == Decimal("150.00")
    assert override.effective_to == date(2024, 6, 30)


def test_delete_rate_override(admin_authenticated_client, project):
    override = RateOverride(project_id=project.id, user_id=None, hourly_rate=Decimal("80.00"))
    db.session.add(override)
    db.session.commit()
    oid = override.id

    resp = admin_authenticated_client.post(f"/projects/{project.id}/rates/{oid}/delete")
    assert resp.status_code in (302, 303)
    assert RateOverride.query.get(oid) is None


def test_add_rejects_overlap(admin_authenticated_client, project, user):
    db.session.add(
        RateOverride(
            project_id=project.id,
            user_id=user.id,
            hourly_rate=Decimal("100.00"),
            effective_from=date(2024, 1, 1),
            effective_to=date(2024, 6, 30),
        )
    )
    db.session.commit()

    resp = admin_authenticated_client.post(
        f"/projects/{project.id}/rates/add",
        data={
            "user_id": str(user.id),
            "hourly_rate": "110.00",
            "effective_from": "2024-06-01",
            "effective_to": "2024-12-31",
        },
    )
    assert resp.status_code == 200
    assert RateOverride.query.filter_by(project_id=project.id, user_id=user.id).count() == 1


def test_regular_user_cannot_add_without_edit_permission(authenticated_client, project):
    """Users without edit_projects (or admin) get 403 on write routes."""
    resp = authenticated_client.post(
        f"/projects/{project.id}/rates/add",
        data={"user_id": "", "hourly_rate": "99.00"},
    )
    assert resp.status_code == 403
    assert RateOverride.query.filter_by(project_id=project.id).count() == 0
