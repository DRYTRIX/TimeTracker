"""Tests for project costs linked to expense categories."""

from datetime import date
from decimal import Decimal

import pytest
from factories import ExpenseCategoryFactory

from app import db
from app.models import ExpenseCategory, ProjectCost, RecurringProjectCost

pytestmark = [pytest.mark.unit, pytest.mark.models]


def _cost(project, user, category, amount, category_id=None):
    cost = ProjectCost(
        project_id=project.id,
        user_id=user.id,
        description=f"Cost {category}",
        category=category,
        amount=Decimal(amount),
        cost_date=date(2024, 1, 15),
        category_id=category_id,
    )
    db.session.add(cost)
    return cost


def test_category_name_comes_from_linked_category(app, project, user):
    category = ExpenseCategoryFactory(name="Travel", code="travel")
    db.session.commit()
    cost = _cost(project, user, "travel", "10.00")
    cost.set_category(category)
    db.session.commit()

    assert cost.category_id == category.id
    assert cost.category == "travel"
    assert cost.category_name == "Travel"
    data = cost.to_dict()
    assert data["category"] == "Travel"
    assert data["category_id"] == category.id


def test_category_name_falls_back_to_legacy_string(app, project, user):
    cost = _cost(project, user, "materials", "10.00")
    db.session.commit()

    assert cost.category_id is None
    assert cost.category_name == "materials"
    data = cost.to_dict()
    assert data["category"] == "materials"
    assert data["category_id"] is None


def test_set_category_fills_legacy_string_from_name(app, project, user):
    with_code = ExpenseCategoryFactory(name="Equipment", code="EQUIP")
    without_code = ExpenseCategoryFactory(name="Cloud hosting", code=None)
    db.session.commit()
    cost = _cost(project, user, "other", "5.00")

    cost.set_category(with_code)
    assert cost.category == "equipment"
    cost.set_category(without_code)
    assert cost.category == "cloud hosting"
    assert cost.category_id == without_code.id


def test_set_category_from_input_resolves_string_case_insensitively(app, project, user):
    category = ExpenseCategoryFactory(name="Software", code="software")
    db.session.commit()
    cost = _cost(project, user, "other", "5.00")

    assert cost.set_category_from_input(category="SOFTWARE") is None
    assert cost.category_id == category.id

    assert cost.set_category_from_input(category="unknown-thing") is None
    assert cost.category_id is None
    assert cost.category == "unknown-thing"

    assert cost.set_category_from_input(category_id=999999) == "Category not found"
    assert cost.set_category_from_input() == "Category is required"


def test_get_costs_by_category_mixed_set(app, project, user):
    travel = ExpenseCategoryFactory(name="Travel", code="travel")
    db.session.commit()
    _cost(project, user, "travel", "100.00", category_id=travel.id)
    # Same category, legacy string drifted after a rename: still grouped by the link
    _cost(project, user, "trips", "50.00", category_id=travel.id)
    # Not linked: grouped by legacy string, ignoring case
    _cost(project, user, "custom", "20.00")
    _cost(project, user, "Custom", "30.00")
    db.session.commit()

    groups = {g["category"].lower(): g for g in ProjectCost.get_costs_by_category(project.id)}

    assert set(groups) == {"travel", "custom"}
    assert groups["travel"]["category"] == "Travel"
    assert groups["travel"]["category_id"] == travel.id
    assert groups["travel"]["total_amount"] == pytest.approx(150.0)
    assert groups["travel"]["count"] == 2
    assert groups["custom"]["category_id"] is None
    assert groups["custom"]["total_amount"] == pytest.approx(50.0)
    assert groups["custom"]["count"] == 2


def test_recurring_cost_carries_category_to_generated_cost(app, project, user):
    category = ExpenseCategoryFactory(name="Services", code="services")
    db.session.commit()
    recurring = RecurringProjectCost(
        project_id=project.id,
        user_id=user.id,
        description="Monthly support",
        category=None,
        amount=Decimal("40.00"),
        frequency="monthly",
        next_run_date=date(2000, 1, 1),
    )
    recurring.set_category(category)
    db.session.add(recurring)
    db.session.commit()

    assert recurring.to_dict()["category_id"] == category.id
    cost = recurring.generate_cost()
    db.session.commit()

    assert cost.category_id == category.id
    assert cost.category == "services"
    assert cost.category_name == "Services"


def test_get_choices_includes_current_inactive_category(app):
    active = ExpenseCategoryFactory(name="Active one", is_active=True)
    inactive = ExpenseCategoryFactory(name="Retired one", is_active=False)
    db.session.commit()

    ids = [c.id for c in ExpenseCategory.get_choices()]
    assert active.id in ids
    assert inactive.id not in ids

    ids = [c.id for c in ExpenseCategory.get_choices(include_id=inactive.id)]
    assert inactive.id in ids
