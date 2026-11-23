"""Expense category list/view and budget alerts with budgets set (#942)."""

from datetime import date

import pytest
from factories import ExpenseCategoryFactory, ExpenseFactory

from app import db

pytestmark = [pytest.mark.unit, pytest.mark.routes]


def test_expense_category_pages_ok_with_budget(admin_authenticated_client, admin_user):
    """List and detail must not 500 when a monthly budget is set."""
    category = ExpenseCategoryFactory(
        name="Travel",
        code="travel",
        monthly_budget=100,
        budget_threshold_percent=80,
        is_active=True,
    )
    expense = ExpenseFactory(
        user_id=admin_user.id,
        title="Hotel",
        category="travel",
        amount=90,
        expense_date=date.today(),
        status="approved",
    )
    db.session.add_all([category, expense])
    db.session.commit()

    list_resp = admin_authenticated_client.get("/expense-categories")
    assert list_resp.status_code == 200
    html = list_resp.get_data(as_text=True)
    assert "90.0%" in html or "90%" in html

    view_resp = admin_authenticated_client.get(f"/expense-categories/{category.id}")
    assert view_resp.status_code == 200
    view_html = view_resp.get_data(as_text=True)
    assert "90.0%" in view_html or "90%" in view_html


def test_budget_alerts_api_counts_lowercase_category_spend(admin_authenticated_client, admin_user):
    """Budget alerts must see spend stored as lowercase expense category values."""
    category = ExpenseCategoryFactory(
        name="Travel",
        code="travel",
        monthly_budget=100,
        budget_threshold_percent=80,
        is_active=True,
    )
    expense = ExpenseFactory(
        user_id=admin_user.id,
        title="Taxi",
        category="travel",
        amount=90,
        expense_date=date.today(),
        status="approved",
    )
    db.session.add_all([category, expense])
    db.session.commit()

    resp = admin_authenticated_client.get("/api/expense-categories/budget-alerts?period=monthly")
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["count"] >= 1
    assert any(alert["category"]["id"] == category.id for alert in data["alerts"])
