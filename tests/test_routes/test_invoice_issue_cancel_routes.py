"""Issuing an invoice, Cancel and reissue, Only cancel, and the billing badges of time entries."""

from datetime import date, datetime, timedelta
from decimal import Decimal

import pytest
from factories import ClientFactory, InvoiceFactory, ProjectFactory, TimeEntryFactory
from sqlalchemy import event

from app import db
from app.models import ApiToken, Expense, Invoice, InvoiceItem, InvoiceTimeLink, ProjectCost, TimeEntry
from app.models.audit_log import AuditLog
from app.services.invoice_time_service import BILLED, BILLED_OUTSIDE, ON_DRAFT, UNBILLED, InvoiceTimeService

pytestmark = [pytest.mark.routes]


def _login(client, user):
    with client.session_transaction() as sess:
        sess["_user_id"] = str(user.id)
        sess["_fresh"] = True


def _token(user):
    token, plain = ApiToken.create_token(
        user_id=user.id, name="Issue token", scopes="read:invoices,write:invoices,read:time_entries"
    )
    db.session.add(token)
    db.session.commit()
    return {"Authorization": f"Bearer {plain}"}


@pytest.fixture
def billing(app, user):
    cl = ClientFactory(name="Issue Client", email="issue@example.com")
    db.session.flush()
    project = ProjectFactory(name="Issue Project", client_id=cl.id, hourly_rate=Decimal("100.00"))
    db.session.flush()
    start = datetime(2026, 10, 5, 9, 0)
    entries = [
        TimeEntryFactory(
            user_id=user.id,
            project_id=project.id,
            start_time=start + timedelta(days=i),
            end_time=start + timedelta(days=i, hours=hours),
            billable=True,
        )
        for i, hours in enumerate((2, 2, 3))
    ]
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
    db.session.commit()
    return {"client": cl, "project": project, "entries": entries, "cost": cost, "expense": expense}


def _draft(client, user, billing, number="INV-ISSUE-1"):
    """A draft billing the three entries, the cost and the expense, built by Generate from Time."""
    inv = InvoiceFactory(
        invoice_number=number,
        project_id=billing["project"].id,
        client_id=billing["client"].id,
        client_name=billing["client"].name,
        created_by=user.id,
        tax_rate=Decimal("0"),
    )
    inv.status = "draft"
    db.session.commit()
    _login(client, user)
    resp = client.post(
        f"/invoices/{inv.id}/generate-from-time",
        data={
            "time_entries[]": [str(e.id) for e in billing["entries"]],
            "project_costs[]": [str(billing["cost"].id)],
            "expenses[]": [str(billing["expense"].id)],
        },
    )
    assert resp.status_code == 302
    db.session.expire_all()
    return Invoice.query.get(inv.id)


def _issue(client, inv):
    resp = client.post(f"/invoices/{inv.id}/status", data={"new_status": "issued"})
    assert resp.status_code == 200, resp.get_data(as_text=True)
    assert resp.get_json()["success"] is True
    db.session.expire_all()
    return Invoice.query.get(inv.id)


def _lines(inv):
    return sorted(
        (i.description, Decimal(i.quantity), Decimal(i.unit_price))
        for i in InvoiceItem.query.filter_by(invoice_id=inv.id)
    )


def _active_links(inv):
    return sorted(
        (link.time_entry_id, Decimal(link.hours))
        for link in InvoiceTimeLink.query.filter_by(invoice_id=inv.id, released_at=None)
    )


# --- Mark as issued ---------------------------------------------------------------------------


def test_draft_page_offers_mark_as_issued_with_the_counts(client, user, billing):
    inv = _draft(client, user, billing)

    page = client.get(f"/invoices/{inv.id}").get_data(as_text=True)

    assert "Mark as issued" in page
    assert (
        "Lines and amounts will be locked. 3 time entries, 1 expense and 1 project cost will be marked as billed."
        in page
    )
    assert "Cancel and reissue" not in page


def test_mark_as_issued_bills_the_entries_and_locks_the_lines(client, user, billing):
    inv = _issue(client, _draft(client, user, billing))
    assert inv.status == "issued"

    entries = TimeEntry.query.filter(TimeEntry.id.in_([e.id for e in billing["entries"]])).all()
    assert {(e.paid, e.invoice_number) for e in entries} == {(True, "INV-ISSUE-1")}
    assert {InvoiceTimeService().billing_state(e) for e in entries} == {BILLED}

    # The page says what is locked, and what is still editable
    page = client.get(f"/invoices/{inv.id}").get_data(as_text=True)
    assert (
        "Lines and amounts are locked. 3 time entries (7 h tracked, 7 h billed), 1 expense and 1 project cost "
        "are billed on this invoice." in page
    )
    assert "Still editable after issuing:" in page
    assert "Mark as issued" not in page
    assert "Cancel and reissue" in page

    # Lines cannot change, by the form or the API
    before = _lines(inv)
    client.post(
        f"/invoices/{inv.id}/edit",
        data={
            "client_name": inv.client_name,
            "due_date": inv.due_date.strftime("%Y-%m-%d"),
            "tax_rate": "0",
            "notes": "Paid by transfer",
            "terms": "Net 14",
            "description[]": ["Changed"],
            "quantity[]": ["99"],
            "unit_price[]": ["1"],
        },
    )
    resp = client.put(
        f"/api/v1/invoices/{inv.id}/items",
        json={"items": [{"description": "Changed", "quantity": 99, "unit_price": 1}]},
        headers=_token(user),
    )
    assert resp.status_code in (400, 409)

    db.session.expire_all()
    inv = Invoice.query.get(inv.id)
    assert _lines(inv) == before
    # Notes and terms still change
    assert (inv.notes, inv.terms) == ("Paid by transfer", "Net 14")


@pytest.mark.parametrize("path", ["single", "bulk", "email", "quickbooks"])
def test_every_way_out_of_draft_marks_the_entries_billed(client, user, billing, path, monkeypatch):
    if path == "quickbooks":
        from app.integrations.quickbooks import QuickBooksConnector

        monkeypatch.setattr(QuickBooksConnector, "sync_data", lambda self, sync_type="incremental": {"success": True})
        connector = QuickBooksConnector.__new__(QuickBooksConnector)
        result = connector.export_approved_time_entries(
            billing["project"].id, [e.id for e in billing["entries"]], user.id
        )
        assert result["success"], result
        number = result["invoice_number"]
    else:
        inv = _draft(client, user, billing, number=f"INV-WAY-{path}")
        number = inv.invoice_number
        if path == "single":
            assert client.post(f"/invoices/{inv.id}/status", data={"new_status": "sent"}).status_code == 200
        elif path == "bulk":
            resp = client.post("/invoices/bulk-status", data={"invoice_ids[]": [str(inv.id)], "status": "sent"})
            assert resp.status_code == 302
        else:
            from app.utils import email as email_utils

            # No PDF rendering and no SMTP in tests
            monkeypatch.setattr(
                email_utils,
                "_build_invoice_email_payload",
                lambda invoice, email_template_id=None, custom_message=None: (b"%PDF", "<p>Hi</p>", "Hi", "Invoice"),
            )
            monkeypatch.setattr(email_utils.mail, "send", lambda msg: None)
            resp = client.post(f"/invoices/{inv.id}/send-email", data={"recipient_email": "billing@example.com"})
            assert resp.status_code == 200, resp.get_data(as_text=True)

    db.session.expire_all()
    invoice = Invoice.query.filter_by(invoice_number=number).one()
    assert invoice.status == "sent"
    entries = TimeEntry.query.filter(TimeEntry.id.in_([e.id for e in billing["entries"]])).all()
    assert {(e.paid, e.invoice_number) for e in entries} == {(True, number)}


def test_invoice_list_shows_and_filters_issued(client, user, billing):
    inv = _issue(client, _draft(client, user, billing))

    page = client.get("/invoices?status=issued").get_data(as_text=True)

    assert inv.invoice_number in page
    assert 'data-status="issued"' in page
    assert 'fa-lock mr-1"></i>Issued' in page


# --- Cancel and reissue ----------------------------------------------------------------------


def test_cancel_and_reissue_moves_everything_to_a_new_draft(client, user, billing):
    inv = _issue(client, _draft(client, user, billing))
    # A line corrected before issuing keeps its correction on the reissue
    first = InvoiceItem.query.filter_by(invoice_id=inv.id).order_by(InvoiceItem.id).first()
    first.description = "Consulting (agreed rate)"
    first.unit_price = Decimal("90")
    db.session.commit()
    inv.calculate_totals()
    db.session.commit()
    lines, links, total = _lines(inv), _active_links(inv), Decimal(Invoice.query.get(inv.id).total_amount)

    resp = client.post(f"/invoices/{inv.id}/correct", data={"action": "reissue", "reason": "Wrong rate"})
    assert resp.status_code == 302

    db.session.expire_all()
    old = Invoice.query.get(inv.id)
    draft = Invoice.query.filter(Invoice.id != old.id, Invoice.client_id == billing["client"].id).one()
    assert resp.headers["Location"].endswith(f"/invoices/{draft.id}")

    # The old invoice is cancelled, keeps its number, and its links are released
    assert old.status == "cancelled"
    assert old.invoice_number == "INV-ISSUE-1"
    assert _active_links(old) == []
    assert all(link.released_at is not None for link in InvoiceTimeLink.query.filter_by(invoice_id=old.id))

    # The draft has the next number, the same lines and amounts, the same entries and hours
    assert draft.status == "draft"
    assert draft.invoice_number != old.invoice_number
    assert _lines(draft) == lines
    assert any(line[0] == "Consulting (agreed rate)" and line[2] == Decimal("90") for line in _lines(draft))
    assert _active_links(draft) == links
    assert Decimal(draft.total_amount) == total
    assert ProjectCost.query.get(billing["cost"].id).invoice_id == draft.id
    assert Expense.query.get(billing["expense"].id).invoice_id == draft.id

    entries = TimeEntry.query.filter(TimeEntry.id.in_([e.id for e in billing["entries"]])).all()
    states = InvoiceTimeService().billing_states(entries)
    assert {state for state, _invoice in states.values()} == {ON_DRAFT}
    assert {invoice.id for _state, invoice in states.values()} == {draft.id}
    assert {e.paid for e in entries} == {False}

    # The draft says what it replaces; the cancelled invoice says why and where its lines went
    page = client.get(f"/invoices/{draft.id}").get_data(as_text=True)
    assert "Reissue of" in page and "INV-ISSUE-1" in page and "cancelled: Wrong rate" in page
    page = client.get(f"/invoices/{old.id}").get_data(as_text=True)
    assert "Cancelled: Wrong rate" in page and draft.invoice_number in page

    # The reason is kept in the audit trail
    row = AuditLog.query.filter_by(entity_type="Invoice", entity_id=old.id, field_name="status", reason="Wrong rate")
    assert row.count() == 1

    # The cancelled invoice stays in the list
    assert old.invoice_number in client.get("/invoices").get_data(as_text=True)


def test_reissue_keeps_prepaid_hours_on_the_new_draft(client, user, billing):
    from app.models import ClientPrepaidConsumption

    billing["client"].prepaid_hours_monthly = Decimal("2")
    db.session.commit()
    inv = _issue(client, _draft(client, user, billing, number="INV-PREPAID-1"))
    links = _active_links(inv)
    assert ClientPrepaidConsumption.query.filter_by(invoice_id=inv.id).count() == 1

    client.post(f"/invoices/{inv.id}/correct", data={"action": "reissue", "reason": "Wrong client address"})

    db.session.expire_all()
    draft = Invoice.query.filter(Invoice.id != inv.id, Invoice.client_id == billing["client"].id).one()
    assert _active_links(draft) == links
    assert ClientPrepaidConsumption.query.filter_by(invoice_id=draft.id).count() == 1
    assert ClientPrepaidConsumption.query.filter_by(invoice_id=inv.id).count() == 0


def test_reissue_uses_the_next_number_of_the_legal_entity(client, user, billing):
    from app.models import BillingEntity

    entity = BillingEntity(short_name="Seller", legal_name="Seller Ltd", number_format="S-{SEQ}", number_counter=7)
    db.session.add(entity)
    db.session.commit()
    inv = _draft(client, user, billing, number="S-7")
    inv.billing_entity_id = entity.id
    db.session.commit()
    inv = _issue(client, inv)

    client.post(f"/invoices/{inv.id}/correct", data={"action": "reissue", "reason": "Typo"})

    db.session.expire_all()
    draft = Invoice.query.filter(Invoice.id != inv.id, Invoice.client_id == billing["client"].id).one()
    assert draft.invoice_number == "S-8"
    assert draft.billing_entity_id == entity.id
    assert db.session.get(BillingEntity, entity.id).number_counter == 8


# --- Only cancel -----------------------------------------------------------------------------


def test_only_cancel_returns_everything_to_unbilled(client, user, billing):
    from app.models import ClientPrepaidConsumption

    billing["client"].prepaid_hours_monthly = Decimal("2")
    db.session.commit()
    inv = _issue(client, _draft(client, user, billing, number="INV-ONLY-1"))
    month = ClientPrepaidConsumption.query.filter_by(invoice_id=inv.id).one().allocation_month
    month_name = month.strftime("%B")

    page = client.get(f"/invoices/{inv.id}").get_data(as_text=True)
    effect = f"7 h tracked, 1 expense and 1 cost go back to Unbilled; 2 h go back to the {month_name} prepaid plan."
    assert effect in page

    resp = client.post(f"/invoices/{inv.id}/correct", data={"action": "cancel", "reason": "Client cancelled"})
    assert resp.status_code == 302

    db.session.expire_all()
    old = Invoice.query.get(inv.id)
    assert old.status == "cancelled"
    assert Invoice.query.filter_by(client_id=billing["client"].id).count() == 1
    entries = TimeEntry.query.filter(TimeEntry.id.in_([e.id for e in billing["entries"]])).all()
    assert {InvoiceTimeService().billing_state(e) for e in entries} == {UNBILLED}
    assert {e.paid for e in entries} == {False}
    assert ProjectCost.query.get(billing["cost"].id).invoice_id is None
    assert Expense.query.get(billing["expense"].id).invoice_id is None
    assert ClientPrepaidConsumption.query.filter_by(invoice_id=inv.id).count() == 0

    # Everything is in Generate from Time again
    from app.services import InvoiceService

    second = InvoiceFactory(
        invoice_number="INV-ONLY-2",
        project_id=billing["project"].id,
        client_id=billing["client"].id,
        client_name=billing["client"].name,
        created_by=user.id,
    )
    second.status = "draft"
    db.session.commit()
    data = InvoiceService().get_unbilled_data_for_invoice(second)
    assert {e.id for e in data["time_entries"]} == {e.id for e in billing["entries"]}


@pytest.mark.parametrize("action", ["cancel", "reissue"])
def test_a_reason_is_required(client, user, billing, action):
    inv = _issue(client, _draft(client, user, billing, number=f"INV-NOREASON-{action}"))

    resp = client.post(f"/invoices/{inv.id}/correct", data={"action": action, "reason": "  "}, follow_redirects=True)

    assert b"Enter a reason to cancel the invoice." in resp.data
    db.session.expire_all()
    assert Invoice.query.get(inv.id).status == "issued"
    assert Invoice.query.filter_by(client_id=billing["client"].id).count() == 1
    assert len(_active_links(inv)) == 3


@pytest.mark.parametrize("status", ["draft", "paid", "cancelled"])
def test_only_an_issued_unpaid_invoice_can_be_corrected(client, user, billing, status):
    inv = _draft(client, user, billing, number=f"INV-NOFIX-{status}")
    if status != "draft":
        inv.status = status
        db.session.commit()

    page = client.get(f"/invoices/{inv.id}").get_data(as_text=True)
    assert "Cancel and reissue" not in page
    resp = client.post(f"/invoices/{inv.id}/correct", data={"action": "cancel", "reason": "x"}, follow_redirects=True)
    assert b"Could not cancel the invoice" in resp.data
    db.session.expire_all()
    assert Invoice.query.get(inv.id).status == status


def test_credit_note_from_the_correct_menu_works_as_before(client, user, billing):
    from app.models import CreditNote

    inv = _issue(client, _draft(client, user, billing, number="INV-CN-1"))
    page = client.get(f"/invoices/{inv.id}").get_data(as_text=True)
    assert 'id="correctMenu"' in page and "creditNoteModal" in page

    resp = client.post(f"/credit-notes/create-from-invoice/{inv.id}", data={"mode": "full", "reason": "Refund"})
    assert resp.status_code in (200, 302)

    db.session.expire_all()
    assert CreditNote.query.filter_by(invoice_id=inv.id).count() == 1
    assert Invoice.query.get(inv.id).status == "cancelled"
    assert _active_links(inv) == []


# --- Badges and the entry form ---------------------------------------------------------------


def test_time_entries_list_shows_a_badge_per_state_with_one_query(client, user, billing):
    inv = _issue(client, _draft(client, user, billing, number="INV-BADGE-1"))
    project = billing["project"]
    start = datetime(2026, 10, 20, 9, 0)

    def entry(day, **kwargs):
        return TimeEntryFactory(
            user_id=user.id,
            project_id=project.id,
            start_time=start + timedelta(days=day),
            end_time=start + timedelta(days=day, hours=1),
            **kwargs,
        )

    on_draft, unbilled = entry(0, billable=True), entry(1, billable=True)
    entry(2, billable=False)
    outside = entry(3, billable=True)
    outside.paid, outside.invoice_number = True, "OLD-7"
    draft = InvoiceFactory(
        invoice_number="INV-BADGE-2",
        project_id=project.id,
        client_id=billing["client"].id,
        client_name=billing["client"].name,
        created_by=user.id,
    )
    draft.status = "draft"
    db.session.commit()
    client.post(f"/invoices/{draft.id}/generate-from-time", data={"time_entries[]": [str(on_draft.id)]})

    # Count the queries that read invoice links while the page renders
    link_queries = []

    def count(conn, cursor, statement, parameters, context, executemany):
        if "invoice_time_links" in statement:
            link_queries.append(statement)

    event.listen(db.engine, "before_cursor_execute", count)
    try:
        page = client.get("/time-entries?per_page=50").get_data(as_text=True)
    finally:
        event.remove(db.engine, "before_cursor_execute", count)

    assert f"Billed {inv.invoice_number}" in page
    assert f'href="/invoices/{inv.id}"' in page
    assert "On draft INV-BADGE-2" in page
    assert 'data-billing-state="non_billable"' in page
    assert "Marked paid OLD-7" in page
    assert page.count('data-billing-state="billed"') == 3
    assert page.count('data-billing-state="') == 3 + 1 + 1 + 1  # the unbilled entry has none
    assert len(link_queries) == 1, link_queries

    states = InvoiceTimeService().billing_states([unbilled, outside])
    assert states[unbilled.id] == (UNBILLED, None)
    assert states[outside.id] == (BILLED_OUTSIDE, None)


def test_entry_form_shows_the_invoice_and_hides_the_manual_paid_mark(client, user, billing):
    inv = _issue(client, _draft(client, user, billing, number="INV-FORM-1"))
    on_invoice = billing["entries"][0]

    page = client.get(f"/timer/edit/{on_invoice.id}").get_data(as_text=True)
    assert "This entry is on invoice INV-FORM-1, so it is locked, for everyone." in page
    assert f'href="/invoices/{inv.id}"' in page
    assert 'id="paid"' not in page
    assert 'id="invoice_number"' not in page

    free = TimeEntryFactory(
        user_id=user.id,
        project_id=billing["project"].id,
        start_time=datetime(2026, 11, 2, 9, 0),
        end_time=datetime(2026, 11, 2, 10, 0),
        billable=True,
    )
    db.session.commit()
    page = client.get(f"/timer/edit/{free.id}").get_data(as_text=True)
    assert "This entry is on invoice" not in page
    assert 'id="paid"' in page and 'id="invoice_number"' in page

    # The manual mark still works for an entry that no invoice bills
    resp = client.post(
        f"/timer/edit/{free.id}",
        data={
            "project_id": str(billing["project"].id),
            "start_date": "2026-11-02",
            "start_time": "09:00",
            "end_date": "2026-11-02",
            "end_time": "10:00",
            "billable": "on",
            "paid": "on",
            "invoice_number": "EXT-1",
        },
    )
    assert resp.status_code in (200, 302)
    db.session.expire_all()
    entry = TimeEntry.query.get(free.id)
    assert (entry.paid, entry.invoice_number) == (True, "EXT-1")
    assert InvoiceTimeService().billing_state(entry) == BILLED_OUTSIDE


# --- Deliveries and payments go through the status hook --------------------------------------


def _entries_state(billing):
    entries = TimeEntry.query.filter(TimeEntry.id.in_([e.id for e in billing["entries"]])).all()
    return {(e.paid, e.invoice_number) for e in entries}


@pytest.mark.parametrize("channel", ["peppol", "sdi"])
@pytest.mark.parametrize(
    "start,delivered,expected",
    [("draft", True, "sent"), ("issued", True, "sent"), ("draft", False, "draft"), ("issued", False, "issued")],
)
def test_peppol_and_sdi_delivery_marks_the_invoice_sent(
    client, user, billing, monkeypatch, channel, start, delivered, expected
):
    from app.services import PeppolService, SdiService

    service = PeppolService if channel == "peppol" else SdiService
    monkeypatch.setattr(
        service,
        "_transmit",
        lambda self, invoice, triggered_by_user_id=None: (delivered, None, "ok" if delivered else "failed"),
    )
    inv = _draft(client, user, billing, number=f"INV-{channel.upper()}-{start}-{delivered}")
    if start == "issued":
        inv = _issue(client, inv)

    resp = client.post(f"/invoices/{inv.id}/send-{channel}")

    assert resp.status_code == (200 if delivered else 400)
    db.session.expire_all()
    assert Invoice.query.get(inv.id).status == expected
    if expected == "draft":
        assert _entries_state(billing) == {(False, None)}
    else:
        assert _entries_state(billing) == {(True, inv.invoice_number)}


def test_email_on_an_issued_invoice_marks_it_sent(client, user, billing, monkeypatch):
    from app.utils import email as email_utils

    monkeypatch.setattr(
        email_utils,
        "_build_invoice_email_payload",
        lambda invoice, email_template_id=None, custom_message=None: (b"%PDF", "<p>Hi</p>", "Hi", "Invoice"),
    )
    monkeypatch.setattr(email_utils.mail, "send", lambda msg: None)
    inv = _issue(client, _draft(client, user, billing, number="INV-MAIL-ISSUED"))

    resp = client.post(f"/invoices/{inv.id}/send-email", data={"recipient_email": "billing@example.com"})

    assert resp.status_code == 200, resp.get_data(as_text=True)
    db.session.expire_all()
    assert Invoice.query.get(inv.id).status == "sent"
    assert _entries_state(billing) == {(True, "INV-MAIL-ISSUED")}


def test_a_payment_that_covers_a_draft_marks_it_paid_and_bills_the_entries(client, user, billing):
    inv = _draft(client, user, billing, number="INV-PAY-DRAFT")
    inv.calculate_totals()
    db.session.commit()
    total = Decimal(Invoice.query.get(inv.id).total_amount)
    assert total > 0

    resp = client.post(
        "/payments/create",
        data={
            "invoice_id": str(inv.id),
            "amount": str(total),
            "payment_date": "2026-11-01",
            "status": "completed",
        },
    )
    assert resp.status_code == 302

    db.session.expire_all()
    assert Invoice.query.get(inv.id).status == "paid"
    assert _entries_state(billing) == {(True, "INV-PAY-DRAFT")}


def test_service_payment_that_covers_a_draft_marks_it_paid(client, user, billing):
    from app.services.payment_service import PaymentService

    inv = _draft(client, user, billing, number="INV-PAY-SVC")
    inv.calculate_totals()
    db.session.commit()

    result = PaymentService().create_payment(
        invoice_id=inv.id, amount=Decimal(inv.total_amount), payment_date=date(2026, 11, 1), received_by=user.id
    )

    assert result["success"], result
    db.session.expire_all()
    assert Invoice.query.get(inv.id).status == "paid"
    assert _entries_state(billing) == {(True, "INV-PAY-SVC")}


@pytest.mark.parametrize("paid_by", ["amount_paid", "payment"])
def test_an_invoice_with_payments_can_only_be_credited(client, user, billing, paid_by):
    from app.models import Payment

    inv = _issue(client, _draft(client, user, billing, number=f"INV-HASPAY-{paid_by}"))
    if paid_by == "amount_paid":
        inv.amount_paid = Decimal("50")
    else:
        db.session.add(
            Payment(invoice_id=inv.id, amount=Decimal("50"), payment_date=date(2026, 11, 1), status="completed")
        )
    db.session.commit()

    page = client.get(f"/invoices/{inv.id}").get_data(as_text=True)
    assert 'id="cancelReissueDisabled"' in page
    assert "This invoice has payments; use a credit note" in page
    assert 'id="cancelReissueModal"' not in page
    assert "creditNoteModal" in page

    for action in ("reissue", "cancel"):
        resp = client.post(
            f"/invoices/{inv.id}/correct", data={"action": action, "reason": "Wrong rate"}, follow_redirects=True
        )
        assert b"This invoice has payments; use a credit note" in resp.data
    db.session.expire_all()
    assert Invoice.query.get(inv.id).status == "issued"
    assert Invoice.query.filter_by(client_id=billing["client"].id).count() == 1
    assert len(_active_links(inv)) == 3


def test_one_place_to_cancel_an_issued_invoice(client, user, billing):
    inv = _draft(client, user, billing, number="INV-ONE-CANCEL")

    # A draft keeps the plain Cancel invoice button
    page = client.get(f"/invoices/{inv.id}").get_data(as_text=True)
    assert f"cancelInvoice({inv.id})" in page
    assert 'id="correctMenu"' not in page

    # An issued invoice is cancelled from Correct, with a reason
    _issue(client, inv)
    page = client.get(f"/invoices/{inv.id}").get_data(as_text=True)
    assert f"cancelInvoice({inv.id})" not in page
    assert 'id="correctMenu"' in page and 'id="cancelReissueModal"' in page
