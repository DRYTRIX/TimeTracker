"""Tests for the invoice time links migration: links backfilled from line CSVs and the prepaid ledger.

The migration module is loaded by file and its functions are called directly, so these tests do not
depend on the revision chain under it: they touch only the tables and columns the backfill reads.
"""

import glob
import importlib.util
import logging
import os
from datetime import date, datetime, timedelta
from decimal import Decimal

import pytest
from factories import ClientFactory, InvoiceFactory, InvoiceItemFactory, ProjectFactory, TimeEntryFactory

from app import db
from app.models import ClientPrepaidConsumption, Expense, InvoiceItem, InvoiceTimeLink, ProjectCost
from app.services.invoice_time_service import BILLED_OUTSIDE, InvoiceTimeService

pytestmark = [pytest.mark.unit]

NOW = datetime(2026, 11, 22, 12, 0)


def _load_migration():
    versions = os.path.join(os.path.dirname(__file__), os.pardir, "migrations", "versions")
    (path,) = glob.glob(os.path.join(versions, "*_add_invoice_time_links.py"))
    spec = importlib.util.spec_from_file_location("migration_add_invoice_time_links", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


migration = _load_migration()


def _invoice(status="draft", issued=date(2026, 10, 31)):
    return {"status": status, "issue_date": issued, "created_at": datetime.combine(issued, datetime.min.time())}


def _rows(rows):
    return sorted(
        (r["time_entry_id"], r["invoice_id"], r["invoice_item_id"], r["hours"], r["released_at"]) for r in rows
    )


def test_each_entry_on_a_line_gets_a_link_with_its_hours():
    rows = migration.build_links(
        invoices={1: _invoice("sent")},
        items=[(10, 1, "100,101"), (11, 1, "")],
        entries={100: 7200, 101: 1800},
        consumptions=[],
        now=NOW,
    )
    assert _rows(rows) == [(100, 1, 10, Decimal("2.0000"), None), (101, 1, 10, Decimal("0.5000"), None)]


def test_entry_on_two_invoices_keeps_the_later_issued_one_and_is_logged(caplog):
    with caplog.at_level(logging.WARNING, logger="alembic.runtime.migration"):
        rows = migration.build_links(
            invoices={1: _invoice("sent", date(2026, 9, 30)), 2: _invoice("paid", date(2026, 10, 31))},
            items=[(10, 1, "100"), (20, 2, "100")],
            entries={100: 3600},
            consumptions=[],
            now=NOW,
        )
    assert _rows(rows) == [(100, 2, 20, Decimal("1.0000"), None)]
    assert any("time entry 100" in message for message in caplog.messages)


def test_an_issued_invoice_wins_over_a_later_draft():
    rows = migration.build_links(
        invoices={1: _invoice("sent", date(2026, 9, 30)), 2: _invoice("draft", date(2026, 10, 31))},
        items=[(10, 1, "100"), (20, 2, "100")],
        entries={100: 3600},
        consumptions=[],
        now=NOW,
    )
    assert _rows(rows) == [(100, 1, 10, Decimal("1.0000"), None)]


def test_a_draft_gets_the_entry_only_without_an_issued_invoice():
    rows = migration.build_links(
        invoices={
            1: _invoice("draft", date(2026, 9, 30)),
            2: _invoice("draft", date(2026, 10, 31)),
            3: _invoice("cancelled", date(2026, 11, 15)),
        },
        items=[(10, 1, "100"), (20, 2, "100"), (30, 3, "100")],
        entries={100: 3600},
        consumptions=[],
        now=NOW,
    )
    assert _rows(rows) == [(100, 2, 20, Decimal("1.0000"), None), (100, 3, 30, Decimal("1.0000"), NOW)]


def test_cancelled_invoice_links_are_released_and_do_not_compete():
    rows = migration.build_links(
        invoices={1: _invoice("cancelled", date(2026, 11, 15)), 2: _invoice("sent", date(2026, 10, 31))},
        items=[(10, 1, "100"), (20, 2, "100")],
        entries={100: 3600},
        consumptions=[],
        now=NOW,
    )
    assert _rows(rows) == [(100, 1, 10, Decimal("1.0000"), NOW), (100, 2, 20, Decimal("1.0000"), None)]
    released = [r for r in rows if r["released_at"]]
    assert released[0]["released_reason"] == "migration: invoice cancelled"


def test_prepaid_entries_without_a_line_get_a_link_without_a_line():
    rows = migration.build_links(
        invoices={1: _invoice("sent")},
        items=[(10, 1, "101")],
        entries={100: 7200, 101: 10800},
        # 100 fully covered (no line); 101 partly covered: 1 of its 3 hours
        consumptions=[(100, 1, 7200), (101, 1, 3600)],
        now=NOW,
    )
    assert _rows(rows) == [(100, 1, None, Decimal("2.0000"), None), (101, 1, 10, Decimal("2.0000"), None)]


def test_entry_on_two_lines_of_one_invoice_keeps_the_first_line(caplog):
    with caplog.at_level(logging.WARNING, logger="alembic.runtime.migration"):
        rows = migration.build_links(
            invoices={1: _invoice("draft")},
            items=[(11, 1, "100"), (10, 1, "100,101")],
            entries={100: 3600, 101: 3600},
            consumptions=[],
            now=NOW,
        )
    assert _rows(rows) == [(100, 1, 10, Decimal("1.0000"), None), (101, 1, 10, Decimal("1.0000"), None)]
    assert any("lines [10, 11]" in message for message in caplog.messages)


def test_prepaid_ledger_rows_of_one_entry_make_one_link():
    rows = migration.build_links(
        invoices={1: _invoice("sent")},
        items=[],
        entries={100: 7200},
        consumptions=[(100, 1, 3600), (100, 1, 3600)],
        now=NOW,
    )
    assert _rows(rows) == [(100, 1, None, Decimal("2.0000"), None)]


def test_drafts_drop_the_entries_they_lost():
    invoices = {1: _invoice("sent", date(2026, 9, 30)), 2: _invoice("draft", date(2026, 10, 31))}
    items = [(10, 1, "100"), (20, 2, "100,101"), (21, 2, "101")]
    rows = migration.build_links(invoices, items, {100: 3600, 101: 3600}, [], NOW)
    # 100 went to the sent invoice; 101 stays on the draft's first line only
    assert sorted(migration.lost_draft_lines(invoices, items, rows)) == [(20, 100), (21, 101)]


def test_missing_entries_are_skipped():
    rows = migration.build_links(
        invoices={1: _invoice("sent")}, items=[(10, 1, "100,999")], entries={100: 3600}, consumptions=[], now=NOW
    )
    assert _rows(rows) == [(100, 1, 10, Decimal("1.0000"), None)]


def test_backfill_on_the_database(app, user):
    """Backfill against real tables: CSV lines, a cancelled invoice, the ledger, and paid-without-link."""
    cl = ClientFactory(name="Migration Client", email="migration@example.com")
    db.session.flush()
    project = ProjectFactory(name="Migration Project", client_id=cl.id)
    db.session.flush()

    def entry(day, hours=1):
        start = datetime(2026, 10, 1, 9, 0) + timedelta(days=day)
        return TimeEntryFactory(
            user_id=user.id, project_id=project.id, start_time=start, end_time=start + timedelta(hours=hours)
        )

    def invoice(status, issued):
        inv = InvoiceFactory(
            project_id=project.id, client_id=cl.id, client_name=cl.name, created_by=user.id, issue_date=issued
        )
        inv.status = status
        return inv

    on_line, twice, prepaid, in_cancelled, outside, prepaid_cancelled, rebilled = (entry(d) for d in range(7))
    outside.paid, outside.invoice_number = True, "OLD-7"

    september = invoice("sent", date(2026, 9, 30))
    october = invoice("draft", date(2026, 10, 31))
    cancelled = invoice("cancelled", date(2026, 10, 15))
    db.session.flush()
    # The cancelled invoice still holds its hours, as before this migration
    in_cancelled.paid, in_cancelled.invoice_number = True, cancelled.invoice_number
    # Billed again on the sent September invoice, still marked with the cancelled number
    rebilled.paid, rebilled.invoice_number = True, cancelled.invoice_number
    prepaid_cancelled.billable = False
    cost = ProjectCost(
        project_id=project.id,
        user_id=user.id,
        description="Hosting",
        category="services",
        amount=Decimal("10"),
        cost_date=date(2026, 10, 5),
        billable=True,
    )
    expense = Expense(
        user_id=user.id,
        title="Train",
        category="travel",
        amount=Decimal("20"),
        expense_date=date(2026, 10, 5),
        project_id=project.id,
        billable=True,
    )
    db.session.add_all([cost, expense])
    db.session.flush()
    cost.mark_as_invoiced(cancelled.id)
    expense.mark_as_invoiced(cancelled.id)
    db.session.add(
        ClientPrepaidConsumption(
            client_id=cl.id,
            time_entry_id=prepaid_cancelled.id,
            invoice_id=cancelled.id,
            allocation_month=date(2026, 10, 1),
            seconds_consumed=3600,
        )
    )
    InvoiceItemFactory(
        invoice_id=september.id, description="Sep", time_entry_ids=f"{on_line.id},{twice.id},{rebilled.id}"
    )
    oct_line = InvoiceItemFactory(invoice_id=october.id, description="Oct", time_entry_ids=str(twice.id))
    InvoiceItemFactory(invoice_id=cancelled.id, description="Void", time_entry_ids=f"{in_cancelled.id},{rebilled.id}")
    db.session.add(
        ClientPrepaidConsumption(
            client_id=cl.id,
            time_entry_id=prepaid.id,
            invoice_id=september.id,
            allocation_month=date(2026, 10, 1),
            seconds_consumed=3600,
        )
    )
    db.session.commit()

    created = migration.backfill(db.session.connection(), now=NOW)
    db.session.commit()

    assert created == 7
    links = {
        (link.time_entry_id, link.invoice_id): link for link in InvoiceTimeLink.query.order_by(InvoiceTimeLink.id).all()
    }
    # The sent September invoice keeps the entry that is also on the October draft
    assert set(links) == {
        (on_line.id, september.id),
        (twice.id, september.id),
        (prepaid.id, september.id),
        (in_cancelled.id, cancelled.id),
        (prepaid_cancelled.id, cancelled.id),
        (rebilled.id, september.id),
        (rebilled.id, cancelled.id),
    }
    assert links[(prepaid.id, september.id)].invoice_item_id is None
    assert links[(in_cancelled.id, cancelled.id)].released_at is not None
    assert links[(prepaid_cancelled.id, cancelled.id)].released_at is not None

    # The cancelled invoice let go of its hours, costs, expenses and prepaid hours
    db.session.expire_all()
    assert (in_cancelled.paid, in_cancelled.invoice_number) == (False, None)
    assert (outside.paid, outside.invoice_number) == (True, "OLD-7")
    # Billed again by September: still paid, now under September's number
    assert (rebilled.paid, rebilled.invoice_number) == (True, september.invoice_number)
    # The October draft lost its only entry to September: its line no longer lists it
    assert InvoiceItem.query.get(oct_line.id).time_entry_ids is None
    assert (cost.invoiced, cost.invoice_id) == (False, None)
    assert (expense.invoiced, expense.invoice_id) == (False, None)
    assert ClientPrepaidConsumption.query.filter_by(invoice_id=cancelled.id).count() == 0
    assert ClientPrepaidConsumption.query.filter_by(invoice_id=september.id).count() == 1
    assert prepaid_cancelled.billable is True

    service = InvoiceTimeService()
    assert service.billing_state(outside) == BILLED_OUTSIDE
    unbilled = {e.id for e in service.billable_unbilled([project.id])}
    assert unbilled == {in_cancelled.id, prepaid_cancelled.id}
    assert outside.id not in unbilled

    # Cancelling September later lets the rebilled entry go as well
    september.status = "cancelled"
    service.on_status_change(september, "sent")
    db.session.commit()
    db.session.expire_all()
    assert (rebilled.paid, rebilled.invoice_number) == (False, None)
    assert rebilled.id in {e.id for e in service.billable_unbilled([project.id])}
