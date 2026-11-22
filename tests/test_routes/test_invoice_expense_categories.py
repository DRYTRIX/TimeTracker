"""Invoice edit form: inline expense categories come from the expense categories."""

import pytest
from factories import ExpenseCategoryFactory

from app import db

pytestmark = [pytest.mark.unit, pytest.mark.routes, pytest.mark.invoices]


def test_invoice_edit_lists_expense_categories_from_directory(authenticated_client, invoice, expense):
    ExpenseCategoryFactory(name="Travel", code="TRAVEL")
    ExpenseCategoryFactory(name="Client gifts", code="gifts")
    expense.mark_as_invoiced(invoice.id)
    db.session.commit()

    resp = authenticated_client.get(f"/invoices/{invoice.id}/edit")
    assert resp.status_code == 200
    html = resp.get_data(as_text=True)
    assert 'name="expense_category[]"' in html
    # A category added in the admin shows up as an option
    assert "Client gifts" in html
    # The expense's string "travel" matches the category by code, ignoring case
    assert 'value="TRAVEL" selected' in html


def test_invoice_edit_keeps_unknown_expense_category(authenticated_client, invoice, expense):
    expense.category = "marketing"
    expense.mark_as_invoiced(invoice.id)
    db.session.commit()

    resp = authenticated_client.get(f"/invoices/{invoice.id}/edit")
    assert resp.status_code == 200
    assert 'value="marketing" selected' in resp.get_data(as_text=True)


def test_generate_from_time_shows_cost_category_name(authenticated_client, invoice, project, user):
    from datetime import date
    from decimal import Decimal

    from app.models import ProjectCost

    category = ExpenseCategoryFactory(name="Hosting", code="hosting")
    db.session.commit()
    cost = ProjectCost(
        project_id=project.id,
        user_id=user.id,
        description="Server rent",
        category=None,
        amount=Decimal("30.00"),
        cost_date=date.today(),
    )
    cost.set_category(category)
    db.session.add(cost)
    db.session.commit()

    resp = authenticated_client.get(f"/invoices/{invoice.id}/generate-from-time")
    assert resp.status_code == 200
    assert "Server rent (Hosting)" in resp.get_data(as_text=True)
