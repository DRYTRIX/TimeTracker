"""Tests for Phase 4 invoice reminder service (reminders & late fees).

Covers:
- Level fires once (idempotent via last_sent_at)
- Draft invoice skipped
- Fully-paid invoice skipped
- Late fee (fixed) applied once
- Late fee (percent_annual) applied
- resolve_policy resolution order: invoice > client > default
"""

from __future__ import annotations

import pytest
from datetime import date, datetime
from decimal import Decimal


# ---------------------------------------------------------------------------
# Helpers to create minimal DB rows
# ---------------------------------------------------------------------------

def _create_project(db, user, client):
    from app.models import Project

    p = Project(
        name="Test Project",
        client=client.name,
        created_by=user.id,
    )
    p.client_id = client.id
    db.session.add(p)
    db.session.flush()
    return p


def _create_client(db, user, name="Test Client", reminder_policy_id=None):
    from app.models import Client

    c = Client(
        name=name,
        created_by=user.id,
    )
    if reminder_policy_id:
        c.reminder_policy_id = reminder_policy_id
    db.session.add(c)
    db.session.flush()
    return c


def _create_invoice(db, user, project, client, due_date, status="sent", payment_status="unpaid"):
    from app.models import Invoice

    inv = Invoice(
        invoice_number=f"INV-TEST-{id(due_date)}",
        project_id=project.id,
        client_name=client.name,
        client_email="client@example.com",
        due_date=due_date,
        created_by=user.id,
        client_id=client.id,
    )
    inv.status = status
    inv.payment_status = payment_status
    inv.total_amount = Decimal("1000.00")
    inv.subtotal = Decimal("1000.00")
    inv.tax_amount = Decimal("0.00")
    inv.amount_paid = Decimal("0.00")
    inv.late_fee_amount = Decimal("0.00")
    db.session.add(inv)
    db.session.flush()
    return inv


def _create_policy(db, name="Test Policy", is_default=False):
    from app.models.reminder_policy import ReminderPolicy, ReminderPolicyLevel

    policy = ReminderPolicy(name=name, active=True, is_default=is_default)
    db.session.add(policy)
    db.session.flush()
    return policy


def _add_level(db, policy, days_offset, late_fee_type=None, late_fee_value=None, sort_order=0):
    from app.models.reminder_policy import ReminderPolicyLevel

    lv = ReminderPolicyLevel(
        policy_id=policy.id,
        days_offset=days_offset,
        active=True,
        sort_order=sort_order,
        late_fee_type=late_fee_type,
        late_fee_value=Decimal(str(late_fee_value)) if late_fee_value is not None else None,
    )
    db.session.add(lv)
    db.session.flush()
    return lv


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestProcessDueReminders:
    def test_level_fires_once(self, app, user):
        """A level whose days_offset is reached is fired exactly once."""
        with app.app_context():
            from app import db
            from app.models.payments import InvoiceReminderSchedule
            from app.services.invoice_reminder_service import process_due_reminders

            # due date was 5 days ago
            today = date(2024, 6, 10)
            due = date(2024, 6, 5)

            client = _create_client(db, user)
            project = _create_project(db, user, client)
            policy = _create_policy(db, "FireOnce")
            _add_level(db, policy, days_offset=1)  # fires 1+ day overdue
            client.reminder_policy_id = policy.id
            db.session.commit()

            inv = _create_invoice(db, user, project, client, due_date=due)
            db.session.commit()

            # First run – should fire
            count1 = process_due_reminders(today=today)
            assert count1 >= 1

            # Second run on same day – must NOT fire again
            count2 = process_due_reminders(today=today)
            assert count2 == 0, "Level should not fire twice for the same invoice+offset"

    def test_draft_skipped(self, app, user):
        """Draft invoices are never processed."""
        with app.app_context():
            from app import db
            from app.services.invoice_reminder_service import process_due_reminders

            today = date(2024, 6, 10)
            due = date(2024, 6, 1)  # very overdue

            client = _create_client(db, user, name="Draft Client")
            project = _create_project(db, user, client)
            policy = _create_policy(db, "DraftPolicy", is_default=True)
            _add_level(db, policy, days_offset=0)
            db.session.commit()

            inv = _create_invoice(db, user, project, client, due_date=due, status="draft")
            db.session.commit()

            count = process_due_reminders(today=today)
            # The draft invoice must not be in the result (other invoices may exist)
            # We verify by checking no schedule row was created for this draft invoice
            from app.models.payments import InvoiceReminderSchedule
            rows = InvoiceReminderSchedule.query.filter_by(invoice_id=inv.id).all()
            assert rows == [], "No reminder schedule rows should be created for a draft invoice"

    def test_paid_skipped(self, app, user):
        """Fully-paid invoices are never processed."""
        with app.app_context():
            from app import db
            from app.services.invoice_reminder_service import process_due_reminders

            today = date(2024, 6, 10)
            due = date(2024, 6, 1)

            client = _create_client(db, user, name="Paid Client")
            project = _create_project(db, user, client)
            policy = _create_policy(db, "PaidPolicy", is_default=True)
            _add_level(db, policy, days_offset=0)
            db.session.commit()

            inv = _create_invoice(
                db, user, project, client,
                due_date=due, status="overdue", payment_status="fully_paid"
            )
            inv.amount_paid = inv.total_amount
            db.session.commit()

            from app.models.payments import InvoiceReminderSchedule
            # Clear any rows that may have been added by other tests
            InvoiceReminderSchedule.query.filter_by(invoice_id=inv.id).delete()
            db.session.commit()

            process_due_reminders(today=today)
            rows = InvoiceReminderSchedule.query.filter_by(invoice_id=inv.id).all()
            assert rows == [], "Fully-paid invoice must not receive reminder"

    def test_late_fee_fixed_applied_once(self, app, user):
        """Fixed late fee is added exactly once to invoice.late_fee_amount."""
        with app.app_context():
            from app import db
            from app.services.invoice_reminder_service import process_due_reminders
            from app.models import Invoice

            today = date(2024, 6, 10)
            due = date(2024, 6, 5)

            client = _create_client(db, user, name="Fee Client Fixed")
            project = _create_project(db, user, client)
            policy = _create_policy(db, "FixedFeePolicy")
            _add_level(db, policy, days_offset=1, late_fee_type="fixed", late_fee_value=50)
            client.reminder_policy_id = policy.id
            db.session.commit()

            inv = _create_invoice(db, user, project, client, due_date=due)
            inv_id = inv.id
            db.session.commit()

            # First run: late fee should be applied
            process_due_reminders(today=today)
            db.session.expire_all()
            inv = Invoice.query.get(inv_id)
            assert inv.late_fee_amount == Decimal("50.00"), (
                f"Expected late_fee_amount=50, got {inv.late_fee_amount}"
            )

            # Second run: late fee must NOT be added again
            process_due_reminders(today=today)
            db.session.expire_all()
            inv = Invoice.query.get(inv_id)
            assert inv.late_fee_amount == Decimal("50.00"), (
                "Late fee must only be applied once per level"
            )

    def test_late_fee_percent_annual_applied(self, app, user):
        """Percent-annual late fee is computed and added."""
        with app.app_context():
            from app import db
            from app.services.invoice_reminder_service import process_due_reminders
            from app.models import Invoice

            today = date(2024, 6, 10)
            due = date(2024, 6, 5)  # 5 days overdue

            client = _create_client(db, user, name="Fee Client Percent")
            project = _create_project(db, user, client)
            policy = _create_policy(db, "PercentFeePolicy")
            _add_level(db, policy, days_offset=1, late_fee_type="percent_annual", late_fee_value=36.5)
            client.reminder_policy_id = policy.id
            db.session.commit()

            inv = _create_invoice(db, user, project, client, due_date=due)
            inv_id = inv.id
            db.session.commit()

            process_due_reminders(today=today)
            db.session.expire_all()
            inv = Invoice.query.get(inv_id)

            # 36.5% annual / 365 = 0.1% per day; 5 days * 0.001 * 1000 = 5.00
            assert inv.late_fee_amount > Decimal("0"), "Late fee should be positive"
            assert inv.late_fee_amount == Decimal("5.00"), (
                f"Expected 5.00, got {inv.late_fee_amount}"
            )


class TestResolvePolicy:
    def test_invoice_level_wins_over_client(self, app, user):
        """Invoice-level policy overrides client-level policy."""
        with app.app_context():
            from app import db
            from app.models.reminder_policy import ReminderPolicy
            from app.services.invoice_reminder_service import resolve_policy

            client = _create_client(db, user, name="RC Client")
            project = _create_project(db, user, client)

            policy_client = _create_policy(db, "Client Policy")
            policy_invoice = _create_policy(db, "Invoice Policy")
            client.reminder_policy_id = policy_client.id
            db.session.commit()

            due = date(2024, 6, 10)
            inv = _create_invoice(db, user, project, client, due_date=due)
            inv.reminder_policy_id = policy_invoice.id
            db.session.commit()

            resolved = resolve_policy(inv)
            assert resolved is not None
            assert resolved.id == policy_invoice.id

    def test_client_level_wins_over_default(self, app, user):
        """Client policy overrides system default."""
        with app.app_context():
            from app import db
            from app.services.invoice_reminder_service import resolve_policy

            policy_default = _create_policy(db, "Default Policy", is_default=True)
            policy_client = _create_policy(db, "Client Policy 2")
            client = _create_client(db, user, name="RC Client 2", reminder_policy_id=policy_client.id)
            project = _create_project(db, user, client)
            db.session.commit()

            due = date(2024, 6, 10)
            inv = _create_invoice(db, user, project, client, due_date=due)
            db.session.commit()

            resolved = resolve_policy(inv)
            assert resolved is not None
            assert resolved.id == policy_client.id

    def test_fallback_to_default(self, app, user):
        """When no invoice/client policy, fall back to system default."""
        with app.app_context():
            from app import db
            from app.services.invoice_reminder_service import resolve_policy

            policy_default = _create_policy(db, "Default Policy 3", is_default=True)
            client = _create_client(db, user, name="RC Client 3")
            project = _create_project(db, user, client)
            db.session.commit()

            due = date(2024, 6, 10)
            inv = _create_invoice(db, user, project, client, due_date=due)
            db.session.commit()

            resolved = resolve_policy(inv)
            assert resolved is not None
            assert resolved.id == policy_default.id


class TestOutstandingAmount:
    def test_late_fee_included_in_outstanding(self, app, user):
        """outstanding_amount = total + late_fee - amount_paid - credits."""
        with app.app_context():
            from app import db

            client = _create_client(db, user, name="OA Client")
            project = _create_project(db, user, client)
            due = date(2024, 6, 10)
            inv = _create_invoice(db, user, project, client, due_date=due)
            inv.late_fee_amount = Decimal("25.00")
            db.session.commit()
            db.session.refresh(inv)

            assert inv.outstanding_amount == Decimal("1025.00")
