"""Tests for issuing (entries become billed), the invoice summary, and InvoiceCorrectionService."""

from datetime import datetime, timedelta
from decimal import Decimal

import pytest
from factories import ClientFactory, InvoiceFactory, InvoiceItemFactory, ProjectFactory, TimeEntryFactory

from app import db
from app.models import Invoice, InvoiceTimeLink
from app.services.invoice_correction_service import (
    CancelReasonRequiredError,
    InvoiceCorrectionService,
    InvoiceNotCorrectableError,
)
from app.services.invoice_time_service import BILLED, NON_BILLABLE, ON_DRAFT, UNBILLED, InvoiceTimeService

pytestmark = [pytest.mark.unit]


@pytest.fixture
def setup(app, user):
    cl = ClientFactory(name="Correction Client", email="correction@example.com")
    db.session.flush()
    project = ProjectFactory(name="Correction Project", client_id=cl.id, hourly_rate=Decimal("100.00"))
    db.session.flush()

    def entry(hours=2, day=0, **kwargs):
        start = datetime(2026, 10, 5, 9, 0) + timedelta(days=day)
        return TimeEntryFactory(
            user_id=user.id, project_id=project.id, start_time=start, end_time=start + timedelta(hours=hours), **kwargs
        )

    def invoice(number, status="draft"):
        inv = InvoiceFactory(
            invoice_number=number,
            project_id=project.id,
            client_id=cl.id,
            client_name=cl.name,
            created_by=user.id,
            tax_rate=Decimal("0"),
        )
        inv.status = status
        db.session.flush()
        return inv

    def line(inv, quantity="2", description="Hours"):
        return InvoiceItemFactory(
            invoice_id=inv.id, description=description, quantity=Decimal(quantity), unit_price=Decimal("100")
        )

    db.session.commit()
    return {"user": user, "entry": entry, "invoice": invoice, "line": line}


def test_issuing_marks_line_entries_billed_once(setup):
    from app.services import InvoiceService

    service = InvoiceTimeService()
    on_line, prepaid_only = setup["entry"](), setup["entry"](day=1)
    inv = setup["invoice"]("INV-COR-1")
    service.link_entries(inv, setup["line"](inv), [on_line])
    service.link_entries(inv, None, [prepaid_only])
    db.session.commit()

    issued = InvoiceService().transition_status(inv, "issued", actor_id=setup["user"].id)
    assert (issued["success"], issued["marked_count"]) == (True, 1)
    # Sending later changes nothing more
    sent = InvoiceService().transition_status(inv, "sent", actor_id=setup["user"].id)
    assert (sent["success"], sent["marked_count"]) == (True, 0)

    assert (on_line.paid, on_line.invoice_number) == (True, "INV-COR-1")
    # Entries fully covered by prepaid hours have no line and stay as they are
    assert (prepaid_only.paid, prepaid_only.invoice_number) == (False, None)


def test_summary_counts_entries_hours_and_lines(setup):
    service = InvoiceTimeService()
    first, second = setup["entry"](hours=2), setup["entry"](hours=1.5, day=1)
    inv = setup["invoice"]("INV-COR-SUM")
    service.link_entries(inv, setup["line"](inv, quantity="4"), [first, second])
    setup["line"](inv, quantity="9", description="Fixed fee")  # not a time line
    db.session.commit()

    summary = service.invoice_summary(inv)

    assert summary["entries"] == 2
    assert summary["tracked_hours"] == Decimal("3.50")
    assert summary["billed_hours"] == Decimal("4.00")
    assert (summary["expenses"], summary["costs"], summary["prepaid"]) == (0, 0, [])


def test_billing_states_match_billing_state(setup):
    service = InvoiceTimeService()
    unbilled, non_billable = setup["entry"](), setup["entry"](day=1, billable=False)
    on_draft, billed = setup["entry"](day=2), setup["entry"](day=3)
    draft = setup["invoice"]("INV-COR-D")
    service.link_entries(draft, setup["line"](draft), [on_draft])
    sent = setup["invoice"]("INV-COR-S")
    service.link_entries(sent, setup["line"](sent), [billed])
    sent.status = "sent"
    db.session.commit()

    entries = [unbilled, non_billable, on_draft, billed]
    states = service.billing_states(entries)

    assert {e.id: states[e.id][0] for e in entries} == {
        unbilled.id: UNBILLED,
        non_billable.id: NON_BILLABLE,
        on_draft.id: ON_DRAFT,
        billed.id: BILLED,
    }
    assert states[billed.id][1].id == sent.id
    assert all(states[e.id][0] == service.billing_state(e) for e in entries)


def test_reissue_copies_lines_and_links_with_the_same_hours(setup):
    service = InvoiceTimeService()
    entry = setup["entry"](hours=3)
    inv = setup["invoice"]("INV-COR-R")
    line = setup["line"](inv, quantity="2.5", description="Edited hours")
    service.link_entries(inv, line, [(entry, Decimal("2.5"))])
    inv.calculate_totals()
    from app.services import InvoiceService

    assert InvoiceService().transition_status(inv, "issued")["success"]
    db.session.commit()

    draft = InvoiceCorrectionService().reissue(inv, "Wrong hours", setup["user"].id)
    db.session.commit()

    assert inv.status == "cancelled"
    assert (entry.paid, entry.invoice_number) == (False, None)
    new_line = draft.items.one()
    assert (new_line.description, new_line.quantity) == ("Edited hours", Decimal("2.50"))
    link = InvoiceTimeLink.query.filter_by(invoice_id=draft.id, released_at=None).one()
    assert (link.time_entry_id, link.invoice_item_id, link.hours) == (entry.id, new_line.id, Decimal("2.5"))
    assert new_line.time_entry_ids == str(entry.id)
    assert draft.total_amount == inv.total_amount
    old_link = InvoiceTimeLink.query.filter_by(invoice_id=inv.id).one()
    assert old_link.released_at is not None

    assert InvoiceCorrectionService.reissue_of(draft) == {
        "invoice": inv,
        "number": "INV-COR-R",
        "reason": "Wrong hours",
    }
    assert InvoiceCorrectionService.cancellation(inv) == {"reason": "Wrong hours", "reissued_as": draft}


def test_reissue_keeps_line_kinds_edit_flags_hours_layout_and_pdf_template(setup):
    from datetime import date

    from app.models import InvoiceHtmlTemplate, InvoiceHtmlTemplateVersion
    from app.services import InvoiceService

    template = InvoiceHtmlTemplate(name="Own layout", html="<html>{{ invoice.invoice_number }}</html>")
    db.session.add(template)
    db.session.flush()
    version = InvoiceHtmlTemplateVersion(template_id=template.id, number=1, html=template.html)
    db.session.add(version)
    db.session.flush()

    service = InvoiceTimeService()
    first, second, extra = setup["entry"](hours=2), setup["entry"](hours=1, day=1), setup["entry"](hours=1, day=2)
    inv = setup["invoice"]("INV-COR-KIND")
    inv.hours_layout = "task"
    inv.line_template = "{task} ({hours} h)"
    inv.period_start, inv.period_end = date(2026, 10, 1), date(2026, 10, 31)
    inv.pdf_template_ref, inv.pdf_template_version_id = f"html:{template.id}", version.id
    time_line = setup["line"](inv, quantity="3", description="Design, reworded")
    service.link_entries(inv, time_line, [first, second])
    time_line.kind = "time"
    time_line.description_edited = True
    hours_line = setup["line"](inv, quantity="1", description="Extra hours")
    service.link_entries(inv, hours_line, [extra])
    hours_line.kind = "manual_hours"
    hours_line.quantity_edited = True
    hours_line.price_edited = True
    fee = setup["line"](inv, quantity="1", description="Fixed fee")
    fee.kind = "manual"
    inv.calculate_totals()
    assert InvoiceService().transition_status(inv, "issued")["success"]
    db.session.commit()

    draft = InvoiceCorrectionService().reissue(inv, "Wrong client", setup["user"].id)
    db.session.commit()

    def state(invoice):
        return [
            (i.description, i.kind, i.description_edited, i.quantity_edited, i.price_edited)
            for i in invoice.items.order_by("position", "id").all()
        ]

    assert state(draft) == state(inv)
    assert state(draft) == [
        ("Design, reworded", "time", True, False, False),
        ("Extra hours", "manual_hours", False, True, True),
        ("Fixed fee", "manual", False, False, False),
    ]
    assert (draft.hours_layout, draft.line_template) == ("task", "{task} ({hours} h)")
    assert (draft.period_start, draft.period_end) == (date(2026, 10, 1), date(2026, 10, 31))
    assert (draft.pdf_template_ref, draft.pdf_template_version_id) == (f"html:{template.id}", version.id)

    # Regroup keeps the edited time line as it is, with its entries
    service.rebuild_lines(draft)
    db.session.commit()
    kept = draft.items.filter_by(description="Design, reworded").one()
    assert (kept.kind, kept.description_edited, kept.quantity) == ("time", True, Decimal("3.00"))
    assert sorted(int(i) for i in kept.time_entry_ids.split(",")) == sorted([first.id, second.id])


def test_reason_and_status_are_checked(setup):
    service = InvoiceCorrectionService()
    issued = setup["invoice"]("INV-COR-CHK", status="issued")
    draft = setup["invoice"]("INV-COR-DRAFT")
    db.session.commit()

    with pytest.raises(CancelReasonRequiredError):
        service.cancel(issued, "   ", setup["user"].id)
    with pytest.raises(InvoiceNotCorrectableError):
        service.reissue(draft, "Typo", setup["user"].id)
    assert Invoice.query.get(issued.id).status == "issued"


def test_invoice_with_payments_is_refused(setup):
    from app.services.invoice_correction_service import InvoiceHasPaymentsError

    issued = setup["invoice"]("INV-COR-PAID", status="sent")
    issued.amount_paid = Decimal("10")
    db.session.commit()

    assert InvoiceCorrectionService.has_payments(issued)
    with pytest.raises(InvoiceHasPaymentsError, match="This invoice has payments; use a credit note"):
        InvoiceCorrectionService().cancel(issued, "Typo", setup["user"].id)
    assert Invoice.query.get(issued.id).status == "sent"


@pytest.mark.parametrize("status", ["draft", "issued"])
def test_payment_covering_the_invoice_makes_it_paid_and_bills_entries(setup, status):
    from app.services.payment_service import PaymentService

    service = InvoiceTimeService()
    entry = setup["entry"]()
    inv = setup["invoice"](f"INV-COR-PAY-{status}")
    service.link_entries(inv, setup["line"](inv), [entry])
    inv.calculate_totals()
    inv.status = status
    db.session.commit()

    result = PaymentService().create_payment(
        invoice_id=inv.id,
        amount=Decimal(inv.total_amount) + 5,
        payment_date=datetime(2026, 11, 1).date(),
        received_by=setup["user"].id,
    )

    assert result["success"], result
    inv = Invoice.query.get(inv.id)
    assert (inv.status, inv.payment_status) == ("paid", "overpaid")
    # The overpayment is kept: transition_status does not reset the amount paid
    assert Decimal(inv.amount_paid) == Decimal(inv.total_amount) + 5
    assert (entry.paid, entry.invoice_number) == (True, inv.invoice_number)
