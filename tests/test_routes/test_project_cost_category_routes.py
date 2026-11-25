"""Web forms for project costs pick their category from the expense categories."""

from datetime import date
from decimal import Decimal

import pytest
from factories import ExpenseCategoryFactory

from app import db
from app.models import ProjectCost, RecurringProjectCost

pytestmark = [pytest.mark.unit, pytest.mark.routes]


@pytest.fixture
def categories(app):
    active = ExpenseCategoryFactory(name="Hosting", code="hosting", is_active=True)
    retired = ExpenseCategoryFactory(name="Legacy licenses", code="legacy-lic", is_active=False)
    db.session.commit()
    return active, retired


def _cost_with_category(project, user, category):
    cost = ProjectCost(
        project_id=project.id,
        user_id=user.id,
        description="Old cost",
        category=None,
        amount=Decimal("12.00"),
        cost_date=date(2024, 3, 1),
    )
    cost.set_category(category)
    db.session.add(cost)
    db.session.commit()
    return cost


def test_add_cost_form_lists_only_active_categories(authenticated_client, project, categories):
    active, retired = categories
    resp = authenticated_client.get(f"/projects/{project.id}/costs/add")
    assert resp.status_code == 200
    html = resp.get_data(as_text=True)
    assert 'name="category_id"' in html
    assert f'value="{active.id}"' in html
    assert "Legacy licenses" not in html


def test_add_cost_with_category_from_directory(authenticated_client, project, categories):
    active, _ = categories
    resp = authenticated_client.post(
        f"/projects/{project.id}/costs/add",
        data={
            "description": "Server rent",
            "category_id": str(active.id),
            "amount": "99.50",
            "cost_date": "2024-04-01",
            "currency_code": "EUR",
        },
    )
    assert resp.status_code in (302, 303)
    cost = ProjectCost.query.filter_by(description="Server rent").one()
    assert cost.category_id == active.id
    assert cost.category == "hosting"


def test_add_cost_rejects_inactive_category(authenticated_client, project, categories):
    _, retired = categories
    resp = authenticated_client.post(
        f"/projects/{project.id}/costs/add",
        data={
            "description": "Should not save",
            "category_id": str(retired.id),
            "amount": "10",
            "cost_date": "2024-04-01",
        },
    )
    assert resp.status_code == 200
    assert ProjectCost.query.filter_by(description="Should not save").count() == 0


def test_add_cost_accepts_legacy_category_string(authenticated_client, project, categories):
    resp = authenticated_client.post(
        f"/projects/{project.id}/costs/add",
        data={"description": "Legacy post", "category": "HOSTING", "amount": "10", "cost_date": "2024-04-01"},
    )
    assert resp.status_code in (302, 303)
    cost = ProjectCost.query.filter_by(description="Legacy post").one()
    assert cost.category_id == categories[0].id


def test_edit_cost_changes_category(authenticated_client, project, user, categories):
    active, _ = categories
    other = ExpenseCategoryFactory(name="Consulting", code="consulting")
    db.session.commit()
    cost = _cost_with_category(project, user, active)

    resp = authenticated_client.post(
        f"/projects/{project.id}/costs/{cost.id}/edit",
        data={
            "description": "Old cost",
            "category_id": str(other.id),
            "amount": "12.00",
            "cost_date": "2024-03-01",
            "currency_code": "EUR",
        },
    )
    assert resp.status_code in (302, 303)
    db.session.refresh(cost)
    assert cost.category_id == other.id
    assert cost.category == "consulting"


def test_edit_cost_keeps_inactive_category_of_existing_cost(authenticated_client, project, user, categories):
    active, retired = categories
    cost = _cost_with_category(project, user, retired)

    resp = authenticated_client.get(f"/projects/{project.id}/costs/{cost.id}/edit")
    assert resp.status_code == 200
    html = resp.get_data(as_text=True)
    assert "Legacy licenses" in html
    assert f'value="{retired.id}" selected' in html

    resp = authenticated_client.post(
        f"/projects/{project.id}/costs/{cost.id}/edit",
        data={
            "description": "Old cost, edited",
            "category_id": str(retired.id),
            "amount": "12.00",
            "cost_date": "2024-03-01",
        },
    )
    assert resp.status_code in (302, 303)
    db.session.refresh(cost)
    assert cost.description == "Old cost, edited"
    assert cost.category_id == retired.id


def test_costs_list_filters_and_shows_category_name(authenticated_client, project, user, categories):
    active, retired = categories
    _cost_with_category(project, user, active)
    other = _cost_with_category(project, user, retired)
    other.description = "Retired cost"
    db.session.commit()

    resp = authenticated_client.get(f"/projects/{project.id}/costs?category_id={active.id}")
    assert resp.status_code == 200
    html = resp.get_data(as_text=True)
    assert "Hosting" in html
    assert "Retired cost" not in html


def test_add_recurring_cost_with_category(authenticated_client, project, categories):
    active, _ = categories
    resp = authenticated_client.post(
        f"/projects/{project.id}/costs/recurring/add",
        data={
            "description": "Monthly hosting",
            "category_id": str(active.id),
            "amount": "20",
            "frequency": "monthly",
            "interval": "1",
            "next_run_date": "2030-01-01",
            "currency_code": "EUR",
        },
    )
    assert resp.status_code in (302, 303)
    recurring = RecurringProjectCost.query.filter_by(description="Monthly hosting").one()
    assert recurring.category_id == active.id
    assert recurring.category == "hosting"

    resp = authenticated_client.get(f"/projects/{project.id}/costs/recurring")
    assert resp.status_code == 200
    assert "Hosting" in resp.get_data(as_text=True)

    resp = authenticated_client.get(f"/projects/{project.id}/costs/recurring/{recurring.id}/edit")
    assert resp.status_code == 200
    assert f'value="{active.id}" selected' in resp.get_data(as_text=True)
