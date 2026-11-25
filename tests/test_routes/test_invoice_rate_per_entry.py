"""Hourly rate per time entry: UI, API and "Invoice unbilled" build the same lines."""

from datetime import date, datetime, timedelta
from decimal import Decimal

import pytest
from factories import ClientFactory, InvoiceFactory, ProjectFactory, TimeEntryFactory

from app import db
from app.models import ApiToken, Invoice, RateOverride
from app.services import InvoiceService
from app.utils import invoice_pdf_html

pytestmark = [pytest.mark.routes, pytest.mark.integration]


def _login(client, user):
    with client.session_transaction() as sess:
        sess["_user_id"] = str(user.id)
        sess["_fresh"] = True


def _token_headers(user):
    token, plain = ApiToken.create_token(user_id=user.id, name="Rate token", scopes="read:invoices,write:invoices")
    db.session.add(token)
    db.session.commit()
    return {"Authorization": f"Bearer {plain}", "Content-Type": "application/json"}


def _lines(invoice):
    return sorted(
        (item.description, Decimal(str(item.quantity)), Decimal(str(item.unit_price)), Decimal(str(item.total_amount)))
        for item in invoice.items
    )


@pytest.fixture
def rate_change(app, user):
    """Project at 100, the user's own rate 120 from the 15th; entries on the 10th, 20th and a 20-minute one."""
    cl = ClientFactory(name="Rate Client", default_hourly_rate=Decimal("80.00"))
    project = ProjectFactory(name="Rate Project", client_id=cl.id, hourly_rate=Decimal("100.00"))
    # Every path uses the project's last layout: one line per project (and rate)
    project.last_hours_layout = "project"
    project.last_line_template = "{project}"
    db.session.add(
        RateOverride(
            project_id=project.id, user_id=user.id, hourly_rate=Decimal("120.00"), effective_from=date(2026, 3, 15)
        )
    )
    db.session.commit()

    entries = []
    for start, minutes in (
        (datetime(2026, 3, 10, 9, 0), 60),
        (datetime(2026, 3, 20, 9, 0), 60),
        (datetime(2026, 3, 21, 9, 0), 20),
    ):
        entries.append(
            TimeEntryFactory(
                user_id=user.id,
                project_id=project.id,
                task_id=None,
                start_time=start,
                end_time=start + timedelta(minutes=minutes),
                billable=True,
            )
        )
    db.session.commit()
    return cl, project, [e.id for e in entries]


EXPECTED = [
    ("Rate Project \u2013 100.00 EUR/h", Decimal("1.00"), Decimal("100.00"), Decimal("100.00")),
    ("Rate Project \u2013 120.00 EUR/h", Decimal("1.33"), Decimal("120.00"), Decimal("159.60")),
]


def test_ui_api_and_client_unbilled_build_the_same_lines(app, client, user, rate_change):
    cl, project, entry_ids = rate_change
    service = InvoiceService()

    preview = service.get_client_unbilled_invoice_preview(cl.id)
    unbilled = service.create_client_unbilled_invoice(cl.id, acting_user_id=user.id)
    assert unbilled["success"], unbilled
    unbilled_invoice = Invoice.query.get(unbilled["invoice_id"])
    assert _lines(unbilled_invoice) == EXPECTED
    assert Decimal(str(preview["estimated_total"])) == Decimal("259.60")
    assert unbilled["warnings"] == []

    # An entry is on one invoice at a time: drop this draft so the next path can bill the same entries
    db.session.delete(unbilled_invoice)
    db.session.commit()

    _login(client, user)
    ui_invoice = InvoiceFactory(project_id=project.id, client_id=cl.id, created_by=user.id, tax_rate=Decimal("0"))
    db.session.commit()
    resp = client.post(
        f"/invoices/{ui_invoice.id}/generate-from-time",
        data={"time_entries[]": [str(i) for i in entry_ids]},
    )
    assert resp.status_code == 302
    ui_invoice = Invoice.query.get(ui_invoice.id)
    assert _lines(ui_invoice) == EXPECTED

    # An entry is on one invoice at a time: drop this draft so the next path can bill the same entries
    db.session.delete(ui_invoice)
    db.session.commit()

    headers = _token_headers(user)
    resp = client.post(
        "/api/v1/invoices/from-time-entries",
        headers=headers,
        json={"project_id": project.id, "time_entry_ids": entry_ids},
    )
    assert resp.status_code == 201, resp.get_json()
    body = resp.get_json()
    assert body["warnings"] == []
    api_invoice = Invoice.query.get(body["invoice"]["id"])
    assert _lines(api_invoice) == EXPECTED

    # An entry is on one invoice at a time: drop this draft so the next path can bill the same entries
    db.session.delete(api_invoice)
    db.session.commit()

    api_draft = InvoiceFactory(project_id=project.id, client_id=cl.id, created_by=user.id)
    db.session.commit()
    resp = client.post(
        f"/api/v1/invoices/{api_draft.id}/generate-from-time",
        headers=headers,
        json={"time_entry_ids": entry_ids},
    )
    assert resp.status_code == 200, resp.get_json()
    assert _lines(Invoice.query.get(api_draft.id)) == EXPECTED


def test_twenty_minutes_is_33_in_line_total_and_pdf(app, client, user):
    cl = ClientFactory(name="Short Client")
    project = ProjectFactory(name="Short Project", client_id=cl.id, hourly_rate=Decimal("100.00"))
    db.session.commit()
    start = datetime(2026, 3, 10, 9, 0)
    entry = TimeEntryFactory(
        user_id=user.id,
        project_id=project.id,
        task_id=None,
        start_time=start,
        end_time=start + timedelta(minutes=20),
        billable=True,
    )
    db.session.commit()

    result = InvoiceService().create_invoice_from_time_entries(
        project_id=project.id, time_entry_ids=[entry.id], created_by=user.id
    )
    assert result["success"], result
    invoice = Invoice.query.get(result["invoice"].id)
    invoice.tax_rate = Decimal("0")
    invoice.calculate_totals()
    db.session.commit()

    (item,) = list(invoice.items)
    assert Decimal(str(item.quantity)) == Decimal("0.33")
    assert Decimal(str(item.total_amount)) == Decimal("33.00")
    assert Decimal(str(invoice.subtotal)) == Decimal("33.00")
    assert Decimal(str(invoice.total_amount)) == Decimal("33.00")

    context = invoice_pdf_html.build_context(invoice)
    (row,) = context["rows"]
    assert row.quantity == Decimal("0.33")
    assert row.total == Decimal("33.00")
    assert context["total"] == Decimal("33.00")


def test_missing_rate_warns_in_ui_and_api(app, client, user):
    cl = ClientFactory(name="No Rate Client", default_hourly_rate=None)
    project = ProjectFactory(name="No Rate Project", client_id=cl.id, hourly_rate=None)
    db.session.commit()
    start = datetime(2026, 3, 10, 9, 0)
    entry = TimeEntryFactory(
        user_id=user.id,
        project_id=project.id,
        task_id=None,
        start_time=start,
        end_time=start + timedelta(minutes=90),
        billable=True,
    )
    db.session.commit()
    who = user.display_name

    preview = InvoiceService().get_client_unbilled_invoice_preview(cl.id)
    assert preview["rate_warnings"] == [f"1.50 h were added at 0: no hourly rate for No Rate Project / {who}"]

    _login(client, user)
    inv = InvoiceFactory(project_id=project.id, client_id=cl.id, created_by=user.id)
    db.session.commit()
    resp = client.post(
        f"/invoices/{inv.id}/generate-from-time",
        data={"time_entries[]": [str(entry.id)]},
        follow_redirects=False,
    )
    assert resp.status_code == 302
    with client.session_transaction() as sess:
        flashes = sess.get("_flashes", [])
    assert ("warning", f"1.50 h were added at 0: no hourly rate for No Rate Project / {who}") in flashes
    (item,) = list(Invoice.query.get(inv.id).items)
    assert Decimal(str(item.unit_price)) == Decimal("0")

    # An entry is on one invoice at a time: drop this draft so the next path can bill the same entries
    db.session.delete(Invoice.query.get(inv.id))
    db.session.commit()

    resp = client.post(
        "/api/v1/invoices/from-time-entries",
        headers=_token_headers(user),
        json={"project_id": project.id, "time_entry_ids": [entry.id]},
    )
    assert resp.status_code == 201
    assert resp.get_json()["warnings"] == [f"1.50 h were added at 0: no hourly rate for No Rate Project / {who}"]
