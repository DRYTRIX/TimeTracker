"""InvoiceTimeService on a draft: recalculate a line, take entries off, lines typed in, new entries of the period."""

from datetime import date, datetime, timedelta
from decimal import Decimal

import pytest
from factories import ClientFactory, InvoiceFactory, ProjectFactory, TimeEntryFactory

from app import db
from app.models import InvoiceItem, Task
from app.services.invoice_time_service import (
    LINE_KIND_MANUAL_HOURS,
    EntryNotOnLineError,
    InvalidLineValueError,
    InvoiceNotDraftError,
    InvoiceTimeService,
)

pytestmark = [pytest.mark.unit]


@pytest.fixture
def setup(app, user):
    cl = ClientFactory(name="Draft Service Client", default_hourly_rate=None)
    project = ProjectFactory(name="Draft Service Project", client_id=cl.id, hourly_rate=Decimal("50.00"))
    db.session.flush()
    task = Task(name="Build", project_id=project.id, status="todo", created_by=user.id)
    db.session.add(task)
    db.session.flush()

    def entry(day, minutes, notes=None, logged=datetime(2026, 11, 1, 8, 0)):
        start = datetime(2026, 10, day, 9, 0)
        made = TimeEntryFactory(
            user_id=user.id,
            project_id=project.id,
            task_id=task.id,
            start_time=start,
            end_time=start + timedelta(minutes=minutes),
            notes=notes,
            billable=True,
        )
        made.created_at = logged
        db.session.commit()
        return made

    entries = [entry(5, 60, "A"), entry(6, 20, "B"), entry(7, 90, "C")]
    invoice = InvoiceFactory(project_id=project.id, client_id=cl.id, client_name=cl.name, created_by=user.id)
    invoice.tax_rate = Decimal("0")
    invoice.period_start, invoice.period_end = date(2026, 10, 1), date(2026, 10, 31)
    invoice.created_at = datetime(2026, 11, 2, 8, 0)
    db.session.commit()
    service = InvoiceTimeService()
    service.add_entries(invoice, entries, "task", "{task}: {note}")
    db.session.commit()
    return {"invoice": invoice, "entries": entries, "entry": entry, "service": service}


def test_removing_an_entry_follows_the_rounded_hours_of_the_rest(setup):
    service, invoice, entries = setup["service"], setup["invoice"], setup["entries"]
    line = invoice.items.first()
    # 1.00 + 0.33 + 1.50: each entry is rounded before the line adds them up
    assert Decimal(str(line.quantity)) == Decimal("2.83")
    result = service.remove_line_entry(invoice, line, entries[1])
    db.session.commit()
    assert result == {"line": "updated", "hours": Decimal("0.33"), "prepaid_freed": Decimal("0")}
    assert Decimal(str(line.quantity)) == Decimal("2.50")
    assert Decimal(str(line.total_amount)) == Decimal("125.00")
    assert line.description == "Build: A\nC"
    assert Decimal(str(invoice.total_amount)) == Decimal("125.00")


def test_an_edited_quantity_never_goes_below_zero(setup):
    service, invoice, entries = setup["service"], setup["invoice"], setup["entries"]
    line = invoice.items.first()
    line.quantity = Decimal("1.00")
    line.quantity_edited = True
    db.session.commit()
    service.remove_line_entry(invoice, line, entries[2])
    assert Decimal(str(line.quantity)) == Decimal("0.00")


def test_an_entry_not_on_the_line_and_a_non_draft_are_refused(setup):
    service, invoice, entries = setup["service"], setup["invoice"], setup["entries"]
    line = invoice.items.first()
    service.remove_line_entry(invoice, line, entries[0])
    db.session.commit()
    with pytest.raises(EntryNotOnLineError):
        service.remove_line_entry(invoice, line, entries[0])
    invoice.status = "issued"
    with pytest.raises(InvoiceNotDraftError):
        service.remove_line_entry(invoice, line, entries[1])
    with pytest.raises(InvoiceNotDraftError):
        service.add_manual_line(invoice, "X", "1", "1")


def test_hand_lines_and_their_values(setup):
    service, invoice = setup["service"], setup["invoice"]
    hours_line = service.add_manual_line(invoice, "  Support  ", "2,5", None, hours=True)
    assert (hours_line.kind, hours_line.description) == (LINE_KIND_MANUAL_HOURS, "Support")
    assert Decimal(str(hours_line.unit_price)) == Decimal("50.00")
    assert Decimal(str(hours_line.total_amount)) == Decimal("125.00")
    with pytest.raises(InvalidLineValueError):
        service.add_manual_line(invoice, "X", "-1", "1")
    with pytest.raises(InvalidLineValueError):
        service.update_line(invoice, hours_line, {"vat_category": "XX"})
    with pytest.raises(InvalidLineValueError):
        service.update_line(invoice, hours_line, {"discount_percent": "120"})
    # A line typed in is never marked as edited
    service.update_line(invoice, hours_line, {"quantity": "3"})
    assert not hours_line.is_edited


def test_update_line_marks_only_real_changes(setup):
    service, invoice = setup["service"], setup["invoice"]
    line = invoice.items.first()
    service.update_line(
        invoice, line, {"description": line.description + "  \r\n", "quantity": str(line.quantity), "unit_price": "50"}
    )
    assert not line.is_edited
    service.update_line(invoice, line, {"unit_price": "55"})
    assert (line.description_edited, line.quantity_edited, line.price_edited) == (False, False, True)


def test_new_entries_join_the_line_and_rewrite_text_that_was_not_edited(setup):
    service, invoice = setup["service"], setup["invoice"]
    line = invoice.items.first()
    late = setup["entry"](20, 30, "D", logged=datetime(2026, 11, 3, 8, 0))
    result = service.add_new_entries(invoice)
    db.session.commit()
    assert result["entries"] == 1 and result["new_lines"] == 0
    assert result["added"] == {line.id: Decimal("0.50")}
    assert str(late.id) in line.time_entry_ids.split(",")
    assert Decimal(str(line.quantity)) == Decimal("3.33")
    assert line.description.endswith("D")
    assert service.new_period_entries(invoice) == []


def test_draft_lines_reads_lines_and_entries(setup):
    service, invoice, entries = setup["service"], setup["invoice"], setup["entries"]
    service.add_manual_line(invoice, "Retainer", "1", "100")
    rows = service.draft_lines(invoice)
    assert [row["kind"] for row in rows] == ["time", "manual"]
    assert [entry.id for _link, entry in rows[0]["entries"]] == [e.id for e in entries]
    assert rows[0]["tracked"] == Decimal("2.83")
    assert rows[1]["entries"] == []
    assert InvoiceItem.query.count() >= 2
