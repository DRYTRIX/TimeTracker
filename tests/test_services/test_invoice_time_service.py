"""Tests for InvoiceTimeService: which invoice line bills a time entry."""

from datetime import date, datetime, timedelta
from decimal import Decimal

import pytest
from factories import ClientFactory, InvoiceFactory, InvoiceItemFactory, ProjectFactory, TimeEntryFactory

from app import db
from app.models import Expense, InvoiceTimeLink, ProjectCost, TimeEntry
from app.services.invoice_time_service import (
    BILLED,
    BILLED_OUTSIDE,
    NON_BILLABLE,
    ON_DRAFT,
    UNBILLED,
    InvoiceNotDraftError,
    InvoiceTimeService,
    TimeEntryAlreadyInvoicedError,
)

pytestmark = [pytest.mark.unit]


@pytest.fixture
def setup(app, user):
    cl = ClientFactory(name="Links Client", email="links@example.com")
    db.session.flush()
    project = ProjectFactory(name="Links Project", client_id=cl.id, hourly_rate=Decimal("100.00"))
    db.session.flush()

    def entry(hours=2, day=0, **kwargs):
        start = datetime(2026, 10, 5, 9, 0) + timedelta(days=day)
        return TimeEntryFactory(
            user_id=user.id,
            project_id=project.id,
            start_time=start,
            end_time=start + timedelta(hours=hours),
            **kwargs,
        )

    def invoice(status="draft", number=None):
        kwargs = {"invoice_number": number} if number else {}
        inv = InvoiceFactory(
            project_id=project.id,
            client_id=cl.id,
            client_name=cl.name,
            created_by=user.id,
            tax_rate=Decimal("0"),
            **kwargs,
        )
        inv.status = status  # Invoice() ignores a status argument
        db.session.flush()
        return inv

    def line(inv, description="Hours"):
        return InvoiceItemFactory(
            invoice_id=inv.id, description=description, quantity=Decimal("1"), unit_price=Decimal("100")
        )

    db.session.commit()
    return {"user": user, "client": cl, "project": project, "entry": entry, "invoice": invoice, "line": line}


def test_billing_state_covers_all_five_states(setup):
    service = InvoiceTimeService()
    unbilled = setup["entry"]()
    non_billable = setup["entry"](day=1, billable=False)
    outside = setup["entry"](day=2)
    outside.paid = True
    outside.invoice_number = "OLD-1"
    on_draft = setup["entry"](day=3)
    billed = setup["entry"](day=4)

    draft = setup["invoice"]()
    draft_line = setup["line"](draft)
    service.link_entries(draft, draft_line, [on_draft])

    sent = setup["invoice"]()
    sent_line = setup["line"](sent)
    service.link_entries(sent, sent_line, [billed])
    sent.status = "sent"
    db.session.commit()

    assert service.billing_state(unbilled) == UNBILLED
    assert service.billing_state(non_billable) == NON_BILLABLE
    assert service.billing_state(outside) == BILLED_OUTSIDE
    assert service.billing_state(on_draft) == ON_DRAFT
    assert service.billing_state(billed) == BILLED


def test_second_link_to_another_invoice_is_refused(setup):
    service = InvoiceTimeService()
    entry = setup["entry"]()
    first = setup["invoice"]()
    service.link_entries(first, setup["line"](first), [entry])
    second = setup["invoice"]()
    second_line = setup["line"](second)
    db.session.commit()

    with pytest.raises(TimeEntryAlreadyInvoicedError) as exc_info:
        service.link_entries(second, second_line, [entry])

    assert exc_info.value.invoice_number == first.invoice_number
    assert InvoiceTimeLink.query.filter_by(invoice_id=second.id).count() == 0


def test_same_invoice_may_hold_two_links_of_one_entry(setup):
    """A partly prepaid entry: one link without a line, one on the line billed at the rate."""
    service = InvoiceTimeService()
    entry = setup["entry"](hours=3)
    inv = setup["invoice"]()
    line = setup["line"](inv)

    service.link_entries(inv, None, [(entry, Decimal("1"))])
    service.link_entries(inv, line, [(entry, Decimal("2"))])
    db.session.commit()

    links = InvoiceTimeLink.query.filter_by(time_entry_id=entry.id).order_by(InvoiceTimeLink.id).all()
    assert [(link.invoice_item_id, link.hours) for link in links] == [(None, Decimal("1")), (line.id, Decimal("2"))]


def test_links_only_on_draft_invoices(setup):
    service = InvoiceTimeService()
    entry = setup["entry"]()
    inv = setup["invoice"](status="sent")
    line = setup["line"](inv)
    db.session.commit()

    with pytest.raises(InvoiceNotDraftError):
        service.link_entries(inv, line, [entry])


def test_line_cache_is_written_from_links(setup):
    service = InvoiceTimeService()
    first, second = setup["entry"](), setup["entry"](day=1)
    inv = setup["invoice"]()
    line = setup["line"](inv)

    service.link_entries(inv, line, [first, second])
    assert line.time_entry_ids == f"{first.id},{second.id}"
    assert InvoiceTimeLink.query.filter_by(time_entry_id=first.id).one().hours == Decimal("2.0000")

    service.unlink_entry(inv, first)
    assert line.time_entry_ids == str(second.id)
    assert service.billing_state(first) == UNBILLED


def test_billable_unbilled_leaves_out_linked_paid_outside_non_billable_and_running(setup, user):
    service = InvoiceTimeService()
    free = setup["entry"]()
    linked = setup["entry"](day=1)
    outside = setup["entry"](day=2)
    outside.paid = True
    setup["entry"](day=3, billable=False)
    running = TimeEntry(
        user_id=user.id, project_id=setup["project"].id, start_time=datetime(2026, 10, 9, 9, 0), source="manual"
    )
    db.session.add(running)
    inv = setup["invoice"]()
    service.link_entries(inv, setup["line"](inv), [linked])
    db.session.commit()

    ids = [e.id for e in service.billable_unbilled([setup["project"].id])]
    assert ids == [free.id]

    in_period = service.billable_unbilled(
        [setup["project"].id], start=datetime(2026, 10, 5), end=datetime(2026, 10, 5, 23, 59)
    )
    assert [e.id for e in in_period] == [free.id]
    assert service.billable_unbilled([setup["project"].id], start=datetime(2026, 10, 6)) == []


def test_release_lets_go_of_hours_costs_and_expenses(setup, user):
    service = InvoiceTimeService()
    entry = setup["entry"]()
    other_paid = setup["entry"](day=1)
    inv = setup["invoice"](number="INV-REL-1")
    service.link_entries(inv, setup["line"](inv), [entry, other_paid])

    cost = ProjectCost(
        project_id=setup["project"].id,
        user_id=user.id,
        description="Hosting",
        category="services",
        amount=Decimal("10"),
        cost_date=date(2026, 10, 5),
        billable=True,
    )
    db.session.add(cost)
    expense = Expense(
        user_id=user.id,
        title="Train",
        category="travel",
        amount=Decimal("20"),
        expense_date=date(2026, 10, 5),
        project_id=setup["project"].id,
        billable=True,
    )
    db.session.add(expense)
    db.session.flush()
    cost.mark_as_invoiced(inv.id)
    expense.mark_as_invoiced(inv.id)

    inv.status = "sent"
    entry.paid, entry.invoice_number = True, "INV-REL-1"
    other_paid.paid, other_paid.invoice_number = True, "SET-BY-HAND"
    db.session.commit()

    inv.status = "cancelled"
    released = service.on_status_change(inv, "sent")
    db.session.commit()

    assert released == 2
    links = InvoiceTimeLink.query.filter_by(invoice_id=inv.id).all()
    assert all(link.released_at is not None and link.released_reason for link in links)
    assert (entry.paid, entry.invoice_number) == (False, None)
    assert (other_paid.paid, other_paid.invoice_number) == (True, "SET-BY-HAND")
    assert service.billing_state(entry) == UNBILLED
    assert entry.id in {e.id for e in service.billable_unbilled([setup["project"].id])}
    assert ProjectCost.query.get(cost.id).invoice_id is None
    assert Expense.query.get(expense.id).invoice_id is None

    # Releasing twice changes nothing
    assert service.on_status_change(inv, "cancelled") == 0


def test_deleting_a_line_or_a_draft_deletes_its_links(setup):
    service = InvoiceTimeService()
    first, second = setup["entry"](), setup["entry"](day=1)
    inv = setup["invoice"]()
    line_a, line_b = setup["line"](inv, "A"), setup["line"](inv, "B")
    service.link_entries(inv, line_a, [first])
    service.link_entries(inv, line_b, [second])
    db.session.commit()

    db.session.delete(line_a)
    db.session.commit()
    assert service.billing_state(first) == UNBILLED
    assert service.billing_state(second) == ON_DRAFT

    db.session.delete(inv)
    db.session.commit()
    assert InvoiceTimeLink.query.count() == 0
    assert service.billing_state(second) == UNBILLED


def test_entry_gets_one_line_on_its_invoice(setup):
    """The same hours cannot be billed twice on one invoice through a second line."""
    service = InvoiceTimeService()
    entry = setup["entry"]()
    inv = setup["invoice"]()
    first, second = setup["line"](inv, "First"), setup["line"](inv, "Second")
    service.link_entries(inv, first, [entry])
    db.session.commit()

    with pytest.raises(TimeEntryAlreadyInvoicedError) as exc_info:
        service.link_entries(inv, second, [entry])
    db.session.rollback()

    assert 'line "First"' in str(exc_info.value)
    assert InvoiceTimeLink.query.filter_by(time_entry_id=entry.id).count() == 1
    assert service.find_conflicts([entry], inv) == [(entry, inv)]

    # Linking again to the same line only updates the hours
    service.link_entries(inv, first, [(entry, Decimal("1.5"))])
    service.link_entries(inv, None, [(entry, Decimal("0.5"))])
    service.link_entries(inv, None, [(entry, Decimal("0.25"))])
    db.session.commit()
    links = InvoiceTimeLink.query.filter_by(time_entry_id=entry.id).order_by(InvoiceTimeLink.id).all()
    assert [(link.invoice_item_id, link.hours) for link in links] == [
        (first.id, Decimal("1.5")),
        (None, Decimal("0.25")),
    ]


def test_database_refuses_a_second_active_line_link(setup):
    from sqlalchemy.exc import IntegrityError

    entry = setup["entry"]()
    inv = setup["invoice"]()
    first, second = setup["line"](inv, "First"), setup["line"](inv, "Second")
    db.session.add(InvoiceTimeLink(time_entry=entry, invoice=inv, invoice_item=first, hours=Decimal("2")))
    db.session.commit()

    db.session.add(InvoiceTimeLink(time_entry=entry, invoice=inv, invoice_item=second, hours=Decimal("2")))
    with pytest.raises(IntegrityError):
        db.session.commit()
    db.session.rollback()

    # A released link does not count
    link = InvoiceTimeLink.query.filter_by(time_entry_id=entry.id).one()
    link.released_at = datetime(2026, 11, 1)
    db.session.add(InvoiceTimeLink(time_entry=entry, invoice=inv, invoice_item=second, hours=Decimal("2")))
    db.session.commit()
    assert InvoiceTimeLink.query.filter_by(time_entry_id=entry.id).count() == 2
