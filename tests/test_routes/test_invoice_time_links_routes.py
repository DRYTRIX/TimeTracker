"""Routes around invoice time links: adding hours, the draft-only rule, cancelling, and the entry lock."""

from datetime import datetime, timedelta
from decimal import Decimal

import pytest
from factories import ClientFactory, InvoiceFactory, ProjectFactory, TimeEntryFactory

from app import db
from app.models import ApiToken, Invoice, InvoiceItem, InvoiceTimeLink, TimeEntry
from app.services import InvoiceService
from app.services.invoice_time_service import BILLED, ON_DRAFT, UNBILLED, InvoiceTimeService
from app.services.unpaid_hours_service import UnpaidHoursService

pytestmark = [pytest.mark.routes]


@pytest.fixture
def billing(app, user):
    cl = ClientFactory(name="Route Links Client", email="route-links@example.com")
    db.session.flush()
    project = ProjectFactory(name="Route Links Project", client_id=cl.id, hourly_rate=Decimal("100.00"))
    db.session.flush()
    start = datetime(2026, 10, 5, 9, 0)
    entries = [
        TimeEntryFactory(
            user_id=user.id,
            project_id=project.id,
            start_time=start + timedelta(days=i),
            end_time=start + timedelta(days=i, hours=2),
            billable=True,
        )
        for i in range(2)
    ]
    db.session.commit()
    return {"client": cl, "project": project, "entries": entries}


def _invoice(billing, user, number, status="draft"):
    inv = InvoiceFactory(
        invoice_number=number,
        project_id=billing["project"].id,
        client_id=billing["client"].id,
        client_name=billing["client"].name,
        created_by=user.id,
        tax_rate=Decimal("0"),
    )
    inv.status = status
    db.session.commit()
    return inv


def _login(client, user):
    with client.session_transaction() as sess:
        sess["_user_id"] = str(user.id)
        sess["_fresh"] = True


def _token(user, scopes="read:invoices,write:invoices,read:time_entries,write:time_entries"):
    token, plain = ApiToken.create_token(user_id=user.id, name="Links token", scopes=scopes)
    db.session.add(token)
    db.session.commit()
    return {"Authorization": f"Bearer {plain}"}


def _bill(billing, user, number="INV-LINK-1", status="draft"):
    """An invoice that bills both entries through one line."""
    inv = _invoice(billing, user, number)
    result = InvoiceService().add_time_entries_to_invoice(
        inv.id, user.id, [e.id for e in billing["entries"]], replace_existing=True
    )
    assert result["success"], result
    if status != "draft":
        inv.status = status
        db.session.commit()
    return inv


def _snapshot(invoice_id):
    db.session.expire_all()
    inv = Invoice.query.get(invoice_id)
    items = sorted((i.description, str(i.quantity), i.time_entry_ids) for i in inv.items)
    links = sorted(
        (link.time_entry_id, link.invoice_item_id, link.released_at is None)
        for link in InvoiceTimeLink.query.filter_by(invoice_id=invoice_id)
    )
    return items, links, inv.subtotal


def test_generate_from_time_on_a_draft_links_entries_and_writes_the_cache(client, user, billing):
    _login(client, user)
    inv = _invoice(billing, user, "INV-LINK-GEN")
    ids = [e.id for e in billing["entries"]]

    resp = client.post(f"/invoices/{inv.id}/generate-from-time", data={"time_entries[]": [str(i) for i in ids]})
    assert resp.status_code == 302

    db.session.expire_all()
    service = InvoiceTimeService()
    links = InvoiceTimeLink.query.filter_by(invoice_id=inv.id).all()
    assert sorted(link.time_entry_id for link in links) == sorted(ids)
    assert all(link.invoice_item_id is not None and link.hours == Decimal("2.0000") for link in links)
    cached = set()
    for item in Invoice.query.get(inv.id).items:
        cached.update(int(i) for i in (item.time_entry_ids or "").split(",") if i)
    assert cached == set(ids)

    # Both entries leave the picker and the unpaid (unbilled) hours
    data = InvoiceService().get_unbilled_data_for_invoice(Invoice.query.get(inv.id))
    assert data["time_entries"] == []
    unpaid = UnpaidHoursService().get_unpaid_time_entries(project_id=billing["project"].id)
    assert unpaid == []
    assert {service.billing_state(e) for e in TimeEntry.query.filter(TimeEntry.id.in_(ids))} == {ON_DRAFT}


def test_generate_from_time_refuses_a_sent_invoice(client, user, billing):
    _login(client, user)
    inv = _invoice(billing, user, "INV-LINK-SENT", status="sent")
    before = _snapshot(inv.id)

    resp = client.post(
        f"/invoices/{inv.id}/generate-from-time",
        data={"time_entries[]": [str(e.id) for e in billing["entries"]]},
        follow_redirects=True,
    )
    assert resp.status_code == 200
    assert b"can only be added to a draft invoice" in resp.data
    assert _snapshot(inv.id) == before
    assert InvoiceTimeLink.query.count() == 0


def test_api_generate_from_time_refuses_a_sent_invoice(client, user, billing):
    inv = _bill(billing, user, "INV-LINK-API-SENT", status="sent")
    before = _snapshot(inv.id)

    resp = client.post(
        f"/api/v1/invoices/{inv.id}/generate-from-time",
        json={"time_entry_ids": [e.id for e in billing["entries"]]},
        headers=_token(user),
    )
    assert resp.status_code == 409
    assert _snapshot(inv.id) == before


def test_api_refuses_an_entry_already_on_another_invoice(client, user, billing):
    first = _bill(billing, user, "INV-LINK-FIRST")
    other = _invoice(billing, user, "INV-LINK-OTHER")
    headers = _token(user)
    ids = [e.id for e in billing["entries"]]
    invoices_before = Invoice.query.count()

    resp = client.post(
        "/api/v1/invoices/from-time-entries",
        json={"project_id": billing["project"].id, "time_entry_ids": ids},
        headers=headers,
    )
    assert resp.status_code == 409
    assert first.invoice_number in resp.get_json()["message"]
    assert Invoice.query.count() == invoices_before

    resp = client.post(f"/api/v1/invoices/{other.id}/generate-from-time", json={"time_entry_ids": ids}, headers=headers)
    assert resp.status_code == 409
    assert InvoiceTimeLink.query.filter_by(invoice_id=other.id).count() == 0


def test_cancel_releases_links_and_returns_entries_to_the_picker(client, user, billing):
    _login(client, user)
    inv = _bill(billing, user, "INV-LINK-CANCEL")
    resp = client.post(f"/invoices/{inv.id}/status", data={"new_status": "sent"})
    assert resp.status_code == 200
    db.session.expire_all()
    entries = TimeEntry.query.filter(TimeEntry.id.in_([e.id for e in billing["entries"]])).all()
    assert all(e.paid and e.invoice_number == "INV-LINK-CANCEL" for e in entries)
    assert {InvoiceTimeService().billing_state(e) for e in entries} == {BILLED}

    resp = client.post(f"/invoices/{inv.id}/status", data={"new_status": "cancelled"})
    assert resp.status_code == 200

    db.session.expire_all()
    links = InvoiceTimeLink.query.filter_by(invoice_id=inv.id).all()
    assert links and all(link.released_at is not None for link in links)
    entries = TimeEntry.query.filter(TimeEntry.id.in_([e.id for e in billing["entries"]])).all()
    assert all(not e.paid and e.invoice_number is None for e in entries)
    assert {InvoiceTimeService().billing_state(e) for e in entries} == {UNBILLED}

    draft = _invoice(billing, user, "INV-LINK-AFTER")
    picker = {e.id for e in InvoiceService().get_unbilled_data_for_invoice(draft)["time_entries"]}
    assert picker == {e.id for e in entries}
    unpaid = {e.id for e in UnpaidHoursService().get_unpaid_time_entries(project_id=billing["project"].id)}
    assert unpaid == picker


def test_api_cancel_releases_links(client, user, billing):
    inv = _bill(billing, user, "INV-LINK-API-CANCEL", status="sent")
    resp = client.delete(f"/api/v1/invoices/{inv.id}", headers=_token(user))
    assert resp.status_code == 200
    db.session.expire_all()
    assert InvoiceTimeLink.query.filter_by(invoice_id=inv.id, released_at=None).count() == 0
    entry = billing["entries"][0]
    assert InvoiceTimeService().billing_state(TimeEntry.query.get(entry.id)) == UNBILLED


def test_edit_form_keeps_links_of_the_lines_it_saves(client, user, billing):
    _login(client, user)
    inv = _bill(billing, user, "INV-LINK-EDIT")
    item = Invoice.query.get(inv.id).items.first()

    resp = client.post(
        f"/invoices/{inv.id}/edit",
        data={
            "client_name": billing["client"].name,
            "due_date": inv.due_date.strftime("%Y-%m-%d"),
            "tax_rate": "0",
            "description[]": ["Renamed hours"],
            "quantity[]": [str(item.quantity)],
            "unit_price[]": [str(item.unit_price)],
            "item_time_entry_ids[]": [item.time_entry_ids],
        },
    )
    assert resp.status_code == 302

    db.session.expire_all()
    new_item = InvoiceItem.query.filter_by(invoice_id=inv.id).one()
    links = InvoiceTimeLink.query.filter_by(invoice_id=inv.id).all()
    assert new_item.description == "Renamed hours"
    assert sorted(link.time_entry_id for link in links) == sorted(e.id for e in billing["entries"])
    assert {link.invoice_item_id for link in links} == {new_item.id}


def test_the_same_entry_cannot_get_a_second_line_on_its_invoice(client, user, billing):
    """Adding hours again (API, replace_existing=false) or listing an entry on two lines is refused."""
    inv = _bill(billing, user, "INV-LINK-TWICE")
    before = _snapshot(inv.id)
    headers = _token(user)
    ids = [e.id for e in billing["entries"]]

    resp = client.post(
        f"/api/v1/invoices/{inv.id}/generate-from-time",
        json={"time_entry_ids": ids[:1], "replace_existing": False},
        headers=headers,
    )
    assert resp.status_code == 409
    assert "INV-LINK-TWICE" in resp.get_json()["message"]
    assert _snapshot(inv.id) == before

    # Rebuilding the lines from the same entries is fine
    resp = client.post(
        f"/api/v1/invoices/{inv.id}/generate-from-time",
        json={"time_entry_ids": ids, "replace_existing": True},
        headers=headers,
    )
    assert resp.status_code == 200
    assert sorted(link.time_entry_id for link in InvoiceTimeLink.query.filter_by(invoice_id=inv.id)) == sorted(ids)

    # The edit form cannot list one entry on two lines
    _login(client, user)
    item = Invoice.query.get(inv.id).items.first()
    before = _snapshot(inv.id)
    resp = client.post(
        f"/invoices/{inv.id}/edit",
        data={
            "client_name": billing["client"].name,
            "due_date": inv.due_date.strftime("%Y-%m-%d"),
            "tax_rate": "0",
            "description[]": ["Hours", "Same hours again"],
            "quantity[]": [str(item.quantity), str(item.quantity)],
            "unit_price[]": [str(item.unit_price), str(item.unit_price)],
            "item_time_entry_ids[]": [item.time_entry_ids, item.time_entry_ids],
        },
        follow_redirects=True,
    )
    assert b"listed on two lines" in resp.data
    assert _snapshot(inv.id) == before


@pytest.mark.parametrize("as_admin", [False, True])
def test_entry_on_an_invoice_cannot_be_edited_or_deleted(client, user, admin_user, billing, as_admin):
    actor = admin_user if as_admin else user
    _bill(billing, user, f"INV-LOCK-{int(as_admin)}")
    entry = billing["entries"][0]
    notes_before = entry.notes
    _login(client, actor)

    # Web form
    resp = client.post(f"/timer/edit/{entry.id}", data={"notes": "changed", "reason": "test"}, follow_redirects=True)
    assert f"on invoice INV-LOCK-{int(as_admin)}".encode() in resp.data
    resp = client.post(f"/timer/delete/{entry.id}", follow_redirects=True)
    assert f"on invoice INV-LOCK-{int(as_admin)}".encode() in resp.data

    # API v1
    headers = _token(actor)
    for method in ("put", "patch"):
        resp = getattr(client, method)(f"/api/v1/time-entries/{entry.id}", json={"notes": "changed"}, headers=headers)
        assert resp.status_code == 409
        assert f"INV-LOCK-{int(as_admin)}" in resp.get_json()["message"]
    resp = client.delete(f"/api/v1/time-entries/{entry.id}", headers=headers)
    assert resp.status_code == 409

    # Bulk actions
    resp = client.post("/api/v1/time-entries/bulk", json={"entry_ids": [entry.id], "action": "delete"}, headers=headers)
    assert resp.status_code == 400
    assert resp.get_json()["details"]["skipped_reasons"] == {"already_invoiced": 1}
    resp = client.post(
        "/time-entries/bulk-billable",
        data={"entry_ids[]": [str(entry.id)], "set_billable": "false"},
        follow_redirects=True,
    )
    assert b"1 already invoiced" in resp.data
    resp = client.post("/time-entries/bulk-delete", data={"entry_ids[]": [str(entry.id)]}, follow_redirects=True)
    assert b"on an invoice" in resp.data
    resp = client.post(
        "/time-entries/bulk-paid", data={"entry_ids[]": [str(entry.id)], "paid": "true"}, follow_redirects=True
    )
    assert b"on an invoice" in resp.data

    db.session.expire_all()
    still = TimeEntry.query.get(entry.id)
    assert still is not None
    assert still.notes == notes_before
    assert still.paid is False
    assert still.billable is True


def test_bulk_skips_invoiced_entries_and_changes_the_rest(client, user, billing):
    billed, free = billing["entries"]
    inv = _invoice(billing, user, "INV-LINK-BULK")
    InvoiceService().add_time_entries_to_invoice(inv.id, user.id, [billed.id], replace_existing=True)

    resp = client.post(
        "/api/v1/time-entries/bulk",
        json={"entry_ids": [billed.id, free.id], "action": "add_tag", "value": "checked"},
        headers=_token(user),
    )
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["affected"] == 1
    assert body["skipped"] == 1
    assert body["skipped_reasons"] == {"already_invoiced": 1}
    db.session.expire_all()
    assert "checked" not in (TimeEntry.query.get(billed.id).tags or "")
    assert "checked" in (TimeEntry.query.get(free.id).tags or "")


def test_recurring_and_client_unbilled_invoices_link_only_unbilled_entries(app, user, billing):
    from datetime import date

    from factories import RecurringInvoiceFactory

    from app.services.recurring_invoice_service import RecurringInvoiceService

    billed, free = billing["entries"]
    first = _invoice(billing, user, "INV-LINK-EARLIER")
    InvoiceService().add_time_entries_to_invoice(first.id, user.id, [billed.id], replace_existing=True)

    recurring = RecurringInvoiceFactory(
        project_id=billing["project"].id,
        client_id=billing["client"].id,
        client_name=billing["client"].name,
        created_by=user.id,
        next_run_date=date.today(),
        auto_include_time_entries=True,
    )
    db.session.commit()
    generated = RecurringInvoiceService().generate_invoice(recurring)
    db.session.commit()

    assert InvoiceTimeService().invoice_entry_ids(generated) == [free.id]
    assert {i.time_entry_ids for i in generated.items} == {str(free.id)}

    # Nothing left for the client
    result = InvoiceService().create_client_unbilled_invoice(billing["client"].id, user.id)
    assert result["success"] is False
    assert result["error"] == "no_unbilled_entries"

    # Cancelling the recurring invoice frees the entry for the client's unbilled invoice
    generated.status = "cancelled"
    InvoiceTimeService().on_status_change(generated, "draft")
    db.session.commit()
    result = InvoiceService().create_client_unbilled_invoice(billing["client"].id, user.id)
    assert result["success"] is True
    assert InvoiceTimeService().invoice_entry_ids(result["invoice"]) == [free.id]


# --- Review: which entries an invoice may bill -------------------------------------------------


def _entry(billing, user, day, hours=2, **kwargs):
    start = datetime(2026, 10, 20, 9, 0) + timedelta(days=day)
    entry = TimeEntryFactory(
        user_id=user.id,
        project_id=kwargs.pop("project_id", billing["project"].id),
        start_time=start,
        end_time=None if kwargs.pop("running", False) else start + timedelta(hours=hours),
        **kwargs,
    )
    db.session.commit()
    return entry


def _ineligible_entries(billing, user):
    """One entry per reason an invoice of the billing project may not bill it."""
    other_client = ClientFactory(name="Someone Else", email="else@example.com")
    db.session.flush()
    other_project = ProjectFactory(name="Someone Else's Project", client_id=other_client.id)
    db.session.commit()
    outside = _entry(billing, user, 4)
    outside.paid, outside.invoice_number = True, "OLD-9"
    db.session.commit()
    return {
        "other client": _entry(billing, user, 1, project_id=other_project.id),
        "non-billable": _entry(billing, user, 2, billable=False),
        "timer running": _entry(billing, user, 3, running=True),
        "marked paid outside an invoice": outside,
    }


def test_two_generate_from_time_calls_cannot_bill_one_entry_twice(client, user, billing):
    inv = _invoice(billing, user, "INV-LINK-AGAIN")
    headers = _token(user)
    entry = billing["entries"][0]
    payload = {"time_entry_ids": [entry.id], "replace_existing": False}

    first = client.post(f"/api/v1/invoices/{inv.id}/generate-from-time", json=payload, headers=headers)
    assert first.status_code == 200
    before = _snapshot(inv.id)

    second = client.post(f"/api/v1/invoices/{inv.id}/generate-from-time", json=payload, headers=headers)
    assert second.status_code == 409
    assert _snapshot(inv.id) == before
    assert InvoiceTimeLink.query.filter_by(time_entry_id=entry.id).count() == 1


@pytest.mark.parametrize(
    "reason", ["other client", "non-billable", "timer running", "marked paid outside an invoice", "two lines"]
)
def test_put_items_refuses_entries_the_invoice_may_not_bill(client, user, billing, reason):
    inv = _bill(billing, user, "INV-LINK-PUT")
    item = Invoice.query.get(inv.id).items.first()
    if reason == "two lines":
        extra_ids = [billing["entries"][0].id]
    else:
        extra_ids = [_ineligible_entries(billing, user)[reason].id]
    before = _snapshot(inv.id)

    resp = client.put(
        f"/api/v1/invoices/{inv.id}/items",
        json={
            "items": [
                {"description": "Hours", "quantity": 4, "unit_price": 100, "time_entry_ids": item.time_entry_ids},
                {"description": "More", "quantity": 1, "unit_price": 100, "time_entry_ids": extra_ids},
            ]
        },
        headers=_token(user),
    )
    assert resp.status_code == 409, resp.get_json()
    message = resp.get_json()["message"]
    assert str(extra_ids[0]) in message
    if reason == "two lines":
        assert "listed on two lines" in message
    elif reason == "other client":
        assert "not on this invoice's project or client" in message
    else:
        assert reason in message
    assert _snapshot(inv.id) == before


@pytest.mark.parametrize("reason", ["other client", "non-billable", "timer running", "marked paid outside an invoice"])
def test_edit_form_refuses_entries_the_invoice_may_not_bill(client, user, billing, reason):
    _login(client, user)
    inv = _bill(billing, user, "INV-LINK-FORM")
    item = Invoice.query.get(inv.id).items.first()
    extra = _ineligible_entries(billing, user)[reason]
    before = _snapshot(inv.id)

    resp = client.post(
        f"/invoices/{inv.id}/edit",
        data={
            "client_name": billing["client"].name,
            "due_date": inv.due_date.strftime("%Y-%m-%d"),
            "tax_rate": "0",
            "description[]": ["Hours", "More"],
            "quantity[]": [str(item.quantity), "1"],
            "unit_price[]": [str(item.unit_price), "100"],
            "item_time_entry_ids[]": [item.time_entry_ids, str(extra.id)],
        },
        follow_redirects=True,
    )
    assert b"cannot be billed on this invoice" in resp.data
    assert _snapshot(inv.id) == before


def test_generate_from_time_leaves_out_running_and_billed_outside_entries(client, user, billing):
    bad = _ineligible_entries(billing, user)
    running, outside = bad["timer running"], bad["marked paid outside an invoice"]
    good = billing["entries"][0]

    _login(client, user)
    inv = _invoice(billing, user, "INV-LINK-PICK")
    resp = client.post(
        f"/invoices/{inv.id}/generate-from-time",
        data={"time_entries[]": [str(good.id), str(running.id), str(outside.id)]},
        follow_redirects=True,
    )
    assert b"2 selected time entry/entries were not added" in resp.data
    assert InvoiceTimeService().invoice_entry_ids(Invoice.query.get(inv.id)) == [good.id]

    headers = _token(user)
    api_inv = _invoice(billing, user, "INV-LINK-PICK-API")
    resp = client.post(
        f"/api/v1/invoices/{api_inv.id}/generate-from-time",
        json={"time_entry_ids": [billing["entries"][1].id, running.id, outside.id]},
        headers=headers,
    )
    assert resp.status_code == 200
    assert InvoiceTimeService().invoice_entry_ids(Invoice.query.get(api_inv.id)) == [billing["entries"][1].id]

    resp = client.post(
        "/api/v1/invoices/from-time-entries",
        json={"project_id": billing["project"].id, "time_entry_ids": [running.id, outside.id]},
        headers=headers,
    )
    assert resp.status_code == 400
    assert InvoiceTimeLink.query.filter(InvoiceTimeLink.time_entry_id.in_([running.id, outside.id])).count() == 0


# --- Review: a cancelled invoice stays cancelled ----------------------------------------------


@pytest.mark.parametrize("new_status", ["sent", "draft"])
def test_bulk_status_does_not_bring_back_a_cancelled_invoice(client, user, billing, new_status):
    _login(client, user)
    inv = _bill(billing, user, f"INV-LINK-BACK-{new_status}", status="sent")
    assert client.post(f"/invoices/{inv.id}/status", data={"new_status": "cancelled"}).status_code == 200

    resp = client.post(
        "/invoices/bulk-status", data={"invoice_ids[]": [str(inv.id)], "status": new_status}, follow_redirects=True
    )
    assert b"keeps its status" in resp.data
    db.session.expire_all()
    assert Invoice.query.get(inv.id).status == "cancelled"
    assert InvoiceTimeLink.query.filter_by(invoice_id=inv.id, released_at=None).count() == 0
    entry = TimeEntry.query.get(billing["entries"][0].id)
    assert InvoiceTimeService().billing_state(entry) == UNBILLED


def test_bulk_status_sent_marks_time_entries_paid(client, user, billing):
    _login(client, user)
    inv = _bill(billing, user, "INV-LINK-BULK-SENT")
    resp = client.post(
        "/invoices/bulk-status",
        data={"invoice_ids[]": [str(inv.id)], "status": "sent"},
        follow_redirects=True,
    )
    assert resp.status_code == 200
    db.session.expire_all()
    assert Invoice.query.get(inv.id).status == "sent"
    entries = TimeEntry.query.filter(TimeEntry.id.in_([e.id for e in billing["entries"]])).all()
    assert all(e.paid and e.invoice_number == "INV-LINK-BULK-SENT" for e in entries)


def test_bulk_status_cancelled_releases_a_sent_invoice(client, user, billing):
    _login(client, user)
    inv = _bill(billing, user, "INV-LINK-BULK-CANCEL")
    assert (
        client.post(
            "/invoices/bulk-status",
            data={"invoice_ids[]": [str(inv.id)], "status": "sent"},
            follow_redirects=True,
        ).status_code
        == 200
    )

    resp = client.post(
        "/invoices/bulk-status",
        data={"invoice_ids[]": [str(inv.id)], "status": "cancelled"},
        follow_redirects=True,
    )
    assert resp.status_code == 200
    db.session.expire_all()
    assert Invoice.query.get(inv.id).status == "cancelled"
    assert InvoiceTimeLink.query.filter_by(invoice_id=inv.id, released_at=None).count() == 0
    entry = TimeEntry.query.get(billing["entries"][0].id)
    assert InvoiceTimeService().billing_state(entry) == UNBILLED
    assert not entry.paid


def test_on_status_change_refuses_to_leave_cancelled(app, user, billing):
    from app.services.invoice_time_service import InvoiceStatusChangeError

    inv = _bill(billing, user, "INV-LINK-STAY", status="sent")
    inv.status = "cancelled"
    InvoiceTimeService().on_status_change(inv, "sent")
    db.session.commit()

    inv.status = "draft"
    with pytest.raises(InvoiceStatusChangeError):
        InvoiceTimeService().on_status_change(inv, "cancelled")
    db.session.rollback()


# --- Review: "billed" filters and exports, task project changes --------------------------------


def test_billed_filters_and_export_follow_the_invoice(client, user, billing):
    from app.utils.excel_export import create_time_entries_excel

    on_draft, on_sent = billing["entries"]
    on_draft.notes, on_sent.notes = "on-draft-entry", "on-sent-entry"
    outside = _entry(billing, user, 5, notes="paid-outside-entry")
    outside.paid = True
    free = _entry(billing, user, 6, notes="free-entry")
    db.session.commit()
    draft = _invoice(billing, user, "INV-LINK-FDRAFT")
    InvoiceService().add_time_entries_to_invoice(draft.id, user.id, [on_draft.id], replace_existing=True)
    sent = _invoice(billing, user, "INV-LINK-FSENT")
    InvoiceService().add_time_entries_to_invoice(sent.id, user.id, [on_sent.id], replace_existing=True)
    sent.status = "sent"
    db.session.commit()

    billed = {e.id for e in TimeEntry.query.filter(InvoiceTimeService.billed_clause())}
    assert {on_sent.id, outside.id} <= billed
    assert not {on_draft.id, free.id} & billed

    _login(client, user)
    page = client.get("/time-entries?paid=true").data
    assert b"on-sent-entry" in page and b"paid-outside-entry" in page
    assert b"on-draft-entry" not in page and b"free-entry" not in page
    page = client.get("/time-entries?paid=false").data
    assert b"on-draft-entry" in page and b"free-entry" in page and b"on-sent-entry" not in page

    from openpyxl import load_workbook

    entries = [on_draft, on_sent, outside, free]
    output, _name = create_time_entries_excel(entries, columns=["id", "billed"])
    rows = {row[0]: row[1] for row in load_workbook(output).active.iter_rows(min_row=2, values_only=True)}
    assert rows == {on_draft.id: "No", on_sent.id: "Yes", outside.id: "Yes", free.id: "No"}


def test_moving_a_task_keeps_its_invoiced_entries_on_the_old_project(client, user, billing):
    from app.models import Task

    task = Task(name="Billing task", project_id=billing["project"].id, created_by=user.id)
    db.session.add(task)
    db.session.commit()
    billed, free = billing["entries"]
    billed.task_id = free.task_id = task.id
    db.session.commit()
    inv = _invoice(billing, user, "INV-LINK-TASK")
    InvoiceService().add_time_entries_to_invoice(inv.id, user.id, [billed.id], replace_existing=True)
    new_project = ProjectFactory(name="New Home", client_id=billing["client"].id)
    db.session.commit()

    _login(client, user)
    resp = client.post(
        "/tasks/bulk-move-project",
        data={"task_ids[]": [str(task.id)], "project_id": str(new_project.id)},
        follow_redirects=True,
    )
    assert b"1 time entry/entries of these tasks are on an invoice" in resp.data
    db.session.expire_all()
    assert TimeEntry.query.get(billed.id).project_id == billing["project"].id
    assert TimeEntry.query.get(free.id).project_id == new_project.id


# --- Review, second round --------------------------------------------------------------------


def test_a_payment_does_not_bring_back_a_cancelled_invoice(client, user, billing):
    from app.models import Payment

    _login(client, user)
    inv = _bill(billing, user, "INV-LINK-PAYCANCEL", status="sent")
    assert client.post(f"/invoices/{inv.id}/status", data={"new_status": "cancelled"}).status_code == 200
    db.session.expire_all()
    total = str(Invoice.query.get(inv.id).total_amount or "100")

    resp = client.post(
        "/api/v1/payments",
        json={"invoice_id": inv.id, "amount": total},
        headers=_token(user, scopes="read:payments,write:payments,read:invoices,write:invoices"),
    )
    assert resp.status_code == 409
    assert "cancelled" in resp.get_json()["error"]

    resp = client.post(
        "/payments/create",
        data={"invoice_id": str(inv.id), "amount": total, "payment_date": "2026-11-20", "status": "completed"},
        follow_redirects=True,
    )
    assert b"is cancelled; payments cannot be recorded on it" in resp.data

    db.session.expire_all()
    assert Invoice.query.get(inv.id).status == "cancelled"
    assert Payment.query.filter_by(invoice_id=inv.id).count() == 0
    draft = _invoice(billing, user, "INV-LINK-PAYAFTER")
    picker = {e.id for e in InvoiceService().get_unbilled_data_for_invoice(draft)["time_entries"]}
    assert picker == {e.id for e in billing["entries"]}


@pytest.fixture
def prepaid_draft(client, user, billing):
    """A draft whose first entry is fully covered by a 2 h plan; the second is billed at the rate."""
    from app.models import ClientPrepaidConsumption

    billing["client"].prepaid_hours_monthly = Decimal("2")
    db.session.commit()
    _login(client, user)
    inv = _invoice(billing, user, "INV-LINK-PREPAID")
    covered, billed = billing["entries"]
    resp = client.post(
        f"/invoices/{inv.id}/generate-from-time", data={"time_entries[]": [str(covered.id), str(billed.id)]}
    )
    assert resp.status_code == 302
    db.session.expire_all()
    links = {
        (link.time_entry_id, link.invoice_item_id is None)
        for link in InvoiceTimeLink.query.filter_by(invoice_id=inv.id, released_at=None)
    }
    assert links == {(covered.id, True), (billed.id, False)}
    assert ClientPrepaidConsumption.query.filter_by(invoice_id=inv.id).count() == 1
    return {"invoice": Invoice.query.get(inv.id), "covered": covered, "billed": billed}


def test_a_prepaid_entry_cannot_be_written_into_a_line(client, user, billing, prepaid_draft):
    inv, covered = prepaid_draft["invoice"], prepaid_draft["covered"]
    item = inv.items.first()
    before = _snapshot(inv.id)

    resp = client.post(
        f"/invoices/{inv.id}/edit",
        data={
            "client_name": billing["client"].name,
            "due_date": inv.due_date.strftime("%Y-%m-%d"),
            "tax_rate": "0",
            "description[]": [item.description],
            "quantity[]": [str(item.quantity)],
            "unit_price[]": [str(item.unit_price)],
            "item_time_entry_ids[]": [f"{item.time_entry_ids},{covered.id}"],
        },
        follow_redirects=True,
    )
    assert b"covered by prepaid hours on this invoice" in resp.data
    assert _snapshot(inv.id) == before


def test_api_replace_existing_keeps_prepaid_links(client, user, billing, prepaid_draft):
    from app.models import ClientPrepaidConsumption

    inv, covered, billed = prepaid_draft["invoice"], prepaid_draft["covered"], prepaid_draft["billed"]
    resp = client.post(
        f"/api/v1/invoices/{inv.id}/generate-from-time",
        json={"time_entry_ids": [covered.id, billed.id], "replace_existing": True},
        headers=_token(user),
    )
    assert resp.status_code == 200, resp.get_json()

    db.session.expire_all()
    links = {
        (link.time_entry_id, link.invoice_item_id is None)
        for link in InvoiceTimeLink.query.filter_by(invoice_id=inv.id, released_at=None)
    }
    # The covered entry keeps its link without a line and stays off the lines; the ledger is unchanged
    assert links == {(covered.id, True), (billed.id, False)}
    assert ClientPrepaidConsumption.query.filter_by(invoice_id=inv.id, time_entry_id=covered.id).count() == 1
    lines = [i.time_entry_ids for i in Invoice.query.get(inv.id).items]
    assert lines == [str(billed.id)]
