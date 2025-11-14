"""Smoke tests to validate that factories create consistent, persisted models."""
import datetime as dt
from decimal import Decimal

import pytest

from app import db
from app.models import TimeEntry
from factories import (
    UserFactory,
    ClientFactory,
    ProjectFactory,
    TimeEntryFactory,
    InvoiceFactory,
    InvoiceItemFactory,
    ExpenseFactory,
    PaymentFactory,
    ExpenseCategoryFactory,
)


@pytest.mark.unit
def test_project_and_client_factory_persist(app):
    with app.app_context():
        client = ClientFactory()
        project = ProjectFactory()
        assert client.id is not None
        assert project.id is not None
        # Project should have a client_id wired
        assert project.client_id is not None


@pytest.mark.unit
def test_timeentry_factory_and_duration(app):
    with app.app_context():
        te = TimeEntryFactory()
        # Factory creates 2-hour block by default
        assert te.id is not None
        assert (te.end_time - te.start_time).total_seconds() == 2 * 3600
        # Ensure calculate_duration populates duration_seconds
        te.calculate_duration()
        db.session.commit()
        assert te.duration_seconds in (2 * 3600, )  # allow for rounding settings


@pytest.mark.unit
def test_invoice_and_items_factories(app):
    with app.app_context():
        invoice = InvoiceFactory()
        item1 = InvoiceItemFactory(invoice_id=invoice.id, quantity=Decimal("2.00"), unit_price=Decimal("50.00"))
        item2 = InvoiceItemFactory(invoice_id=invoice.id, quantity=Decimal("1.50"), unit_price=Decimal("100.00"))
        db.session.commit()
        # Items persisted and linked
        assert item1.invoice_id == invoice.id
        assert item2.invoice_id == invoice.id


@pytest.mark.unit
def test_expense_factory(app):
    with app.app_context():
        exp = ExpenseFactory()
        assert exp.id is not None
        assert exp.user_id is not None
        assert exp.project_id is not None
        # When project exists, client_id should be set
        assert exp.client_id == exp.project.client_id


@pytest.mark.unit
def test_payment_factory(app):
    with app.app_context():
        payment = PaymentFactory()
        db.session.commit()
        assert payment.id is not None
        assert payment.invoice_id is not None
        assert payment.amount > 0


@pytest.mark.unit
def test_expense_category_factory(app):
    with app.app_context():
        cat = ExpenseCategoryFactory()
        db.session.commit()
        assert cat.id is not None
        assert cat.name is not None
        assert cat.is_active is True


