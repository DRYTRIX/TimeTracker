"""Draft invoice page: lines with their time entries, × and Non-billable, Regroup, Apply, hand lines, new entries."""

from datetime import date, datetime, timedelta
from decimal import Decimal

import pytest
from factories import ClientFactory, InvoiceFactory, ProjectFactory, TimeEntryFactory, UserFactory

from app import db
from app.models import Invoice, InvoiceItem, Task, TimeEntry
from app.services.invoice_time_service import LINE_KIND_MANUAL, LINE_KIND_MANUAL_HOURS, UNBILLED, InvoiceTimeService

pytestmark = [pytest.mark.routes]

JSON = {"Accept": "application/json", "X-Requested-With": "XMLHttpRequest"}
LOGGED_BEFORE = datetime(2026, 11, 1, 8, 0)


@pytest.fixture
def draft(app, user):
    """A draft for October by task and person: the user and a colleague on Design and Meetings, 40/h."""
    cl = ClientFactory(name="Draft Page Client", default_hourly_rate=None)
    # The user created the project, so it is one of the projects they may see
    project = ProjectFactory(
        name="Draft Page Project", client_id=cl.id, hourly_rate=Decimal("40.00"), created_by=user.id
    )
    colleague = UserFactory(username="colleague-draft", full_name="Colleague")
    db.session.flush()
    design = Task(name="Design", project_id=project.id, status="todo", created_by=user.id)
    meetings = Task(name="Meetings", project_id=project.id, status="todo", created_by=user.id)
    db.session.add_all([design, meetings])
    db.session.flush()

    def entry(person, task, day, hours, notes=None, month=10, logged=LOGGED_BEFORE, running=False):
        start = datetime(2026, month, day, 9, 0)
        made = TimeEntryFactory(
            user_id=person.id,
            project_id=project.id,
            task_id=task.id,
            start_time=start,
            end_time=None if running else start + timedelta(hours=hours),
            notes=notes,
            billable=True,
        )
        made.created_at = logged
        db.session.commit()
        return made

    entries = [
        entry(user, design, 5, 2, "Wireframes"),
        entry(colleague, design, 7, 3, "Layout"),
        entry(colleague, meetings, 8, 1, "Call"),
        entry(colleague, meetings, 9, 0.5, "Weekly sync"),
    ]
    invoice = InvoiceFactory(
        project_id=project.id, client_id=cl.id, client_name=cl.name, created_by=user.id, tax_rate=Decimal("0")
    )
    invoice.currency_code = "EUR"
    invoice.period_start = date(2026, 10, 1)
    invoice.period_end = date(2026, 10, 31)
    invoice.created_at = datetime(2026, 11, 2, 8, 0)
    db.session.commit()
    InvoiceTimeService().add_entries(invoice, entries, "task_person", "{task} - {person}", created_by=user.id)
    invoice.calculate_totals()
    db.session.commit()
    return {
        "invoice": invoice,
        "project": project,
        "entries": entries,
        "entry": entry,
        "user": user,
        "colleague": colleague,
        "design": design,
        "meetings": meetings,
    }


def app_view_functions(client):
    return client.application.view_functions


def _login(client, user):
    with client.session_transaction() as sess:
        sess["_user_id"] = str(user.id)
        sess["_fresh"] = True


def _lines(invoice_id):
    db.session.expire_all()
    invoice = Invoice.query.get(invoice_id)
    return sorted(invoice.items.all(), key=lambda item: (item.position or 0, item.id))


def _line_of(invoice_id, entry):
    for item in _lines(invoice_id):
        if str(entry.id) in (item.time_entry_ids or "").split(","):
            return item
    return None


def _total(invoice_id):
    db.session.expire_all()
    return Decimal(str(Invoice.query.get(invoice_id).total_amount))


# ----------------------------------------------------------------------
# The page
# ----------------------------------------------------------------------
def test_draft_page_shows_each_line_with_its_entries(client, user, draft):
    _login(client, user)
    invoice = draft["invoice"]
    resp = client.get(f"/invoices/{invoice.id}")
    assert resp.status_code == 200
    html = resp.get_data(as_text=True)
    assert 'id="invoiceDraft"' in html
    for item in _lines(invoice.id):
        assert f'id="line-{item.id}"' in html
        assert f'id="entries-{item.id}"' in html
    for entry in draft["entries"]:
        line = _line_of(invoice.id, entry)
        assert f"/invoices/{invoice.id}/lines/{line.id}/entries/{entry.id}/remove" in html
        assert f"/invoices/{invoice.id}/lines/{line.id}/entries/{entry.id}/non-billable" in html
    assert "Weekly sync" in html
    assert "= tracked" in html
    assert 'id="newEntries"' not in html
    # Edit in step 1 leads to step 1 when the app has it, and is shown disabled otherwise
    if "invoices.edit_step_one" in app_view_functions(client):
        assert 'id="editStepOne" disabled' not in html
        assert 'id="backToStepOne"' in html
    else:
        assert 'id="editStepOne" disabled' in html
        assert 'id="backToStepOne"' not in html


def test_full_page_stays_available_and_issued_invoices_keep_the_old_page(client, user, draft):
    _login(client, user)
    invoice = draft["invoice"]
    html = client.get(f"/invoices/{invoice.id}?view=full").get_data(as_text=True)
    assert 'id="invoiceDraft"' not in html
    assert "showSendEmailModal" in html

    invoice.status = "issued"
    db.session.commit()
    html = client.get(f"/invoices/{invoice.id}").get_data(as_text=True)
    assert 'id="invoiceDraft"' not in html
    assert 'id="lockedNotice"' in html


def test_new_entries_banner_lists_only_entries_of_the_period_logged_after_the_draft(client, user, draft):
    _login(client, user)
    invoice = draft["invoice"]
    logged_after = datetime(2026, 11, 3, 9, 0)
    new = draft["entry"](draft["user"], draft["design"], 20, 1.5, "Late design", logged=logged_after)
    draft["entry"](draft["user"], draft["design"], 21, 1, "Old one, not picked", logged=LOGGED_BEFORE)
    draft["entry"](draft["user"], draft["design"], 3, 1, "November", month=11, logged=logged_after)
    other = draft["entry"](draft["user"], draft["design"], 22, 1, "Not billable", logged=logged_after)
    other.billable = False
    db.session.commit()

    assert [e.id for e in InvoiceTimeService().new_period_entries(invoice)] == [new.id]
    html = client.get(f"/invoices/{invoice.id}").get_data(as_text=True)
    assert 'id="newEntries"' in html
    assert "1 new entry in this invoice" in html
    assert "Late design" in html
    assert "Old one, not picked" not in html
    assert 'data-warning="new-entries"' in html


def test_invoice_without_a_period_has_no_new_entries_banner(client, user, draft):
    invoice = draft["invoice"]
    invoice.period_start = invoice.period_end = None
    db.session.commit()
    draft["entry"](draft["user"], draft["design"], 20, 1.5, "Late", logged=datetime(2026, 11, 3, 9, 0))
    _login(client, user)
    html = client.get(f"/invoices/{invoice.id}").get_data(as_text=True)
    assert 'id="newEntries"' not in html


def test_before_you_issue_lists_zero_rate_lines_and_running_timers(client, user, draft):
    invoice = draft["invoice"]
    draft["entry"](draft["user"], draft["design"], 25, 0, running=True)
    item = _lines(invoice.id)[0]
    item.unit_price = Decimal("0")
    db.session.commit()
    _login(client, user)
    html = client.get(f"/invoices/{invoice.id}").get_data(as_text=True)
    assert 'id="beforeIssue"' in html
    assert 'data-warning="zero-rate"' in html
    assert 'data-warning="running-timer"' in html


# ----------------------------------------------------------------------
# × and Non-billable
# ----------------------------------------------------------------------
def test_remove_puts_the_entry_back_in_unbilled_and_recalculates_the_line(client, user, draft):
    _login(client, user)
    invoice = draft["invoice"]
    call, sync = draft["entries"][2], draft["entries"][3]
    line = _line_of(invoice.id, call)
    assert Decimal(str(line.quantity)) == Decimal("1.50")

    resp = client.post(f"/invoices/{invoice.id}/lines/{line.id}/entries/{call.id}/remove", headers=JSON)
    assert resp.status_code == 200, resp.get_data(as_text=True)
    assert resp.get_json()["success"] is True

    db.session.expire_all()
    entry = TimeEntry.query.get(call.id)
    assert InvoiceTimeService().billing_state(entry) == UNBILLED
    assert entry.billable is True
    line = InvoiceItem.query.get(line.id)
    assert Decimal(str(line.quantity)) == Decimal("0.50")
    assert Decimal(str(line.total_amount)) == Decimal("20.00")
    assert line.time_entry_ids == str(sync.id)
    assert _total(invoice.id) == Decimal("220.00")


def test_non_billable_takes_the_entry_off_and_out_of_the_picker(client, user, draft):
    _login(client, user)
    invoice = draft["invoice"]
    call = draft["entries"][2]
    line = _line_of(invoice.id, call)
    resp = client.post(f"/invoices/{invoice.id}/lines/{line.id}/entries/{call.id}/non-billable")
    assert resp.status_code == 302

    db.session.expire_all()
    entry = TimeEntry.query.get(call.id)
    assert entry.billable is False
    assert InvoiceTimeService().billing_invoice(entry) is None
    unbilled = InvoiceTimeService().billable_unbilled([draft["project"].id])
    assert call.id not in [e.id for e in unbilled]


def test_an_edited_line_loses_the_entry_hours_and_keeps_its_text(client, user, draft):
    _login(client, user)
    invoice = draft["invoice"]
    call = draft["entries"][2]
    line = _line_of(invoice.id, call)
    line.description = "Client calls, October"
    line.description_edited = True
    line.quantity = Decimal("4.00")
    line.quantity_edited = True
    line.total_amount = line.line_net
    db.session.commit()

    resp = client.post(f"/invoices/{invoice.id}/lines/{line.id}/entries/{call.id}/remove", headers=JSON)
    assert resp.status_code == 200
    db.session.expire_all()
    line = InvoiceItem.query.get(line.id)
    assert line.description == "Client calls, October"
    assert Decimal(str(line.quantity)) == Decimal("3.00")
    assert Decimal(str(line.total_amount)) == Decimal("120.00")


def test_the_last_entry_removes_the_line_or_leaves_an_edited_one_as_a_hand_line(client, user, draft):
    _login(client, user)
    invoice = draft["invoice"]
    wireframes, layout = draft["entries"][0], draft["entries"][1]
    own_line = _line_of(invoice.id, wireframes)
    resp = client.post(f"/invoices/{invoice.id}/lines/{own_line.id}/entries/{wireframes.id}/remove", headers=JSON)
    assert resp.get_json()["line"] == "deleted"
    db.session.expire_all()
    assert InvoiceItem.query.get(own_line.id) is None

    colleague_line = _line_of(invoice.id, layout)
    colleague_line.description = "Design work"
    colleague_line.description_edited = True
    db.session.commit()
    resp = client.post(f"/invoices/{invoice.id}/lines/{colleague_line.id}/entries/{layout.id}/remove", headers=JSON)
    assert resp.get_json()["line"] == "manual"
    db.session.expire_all()
    kept = InvoiceItem.query.get(colleague_line.id)
    assert kept.kind == LINE_KIND_MANUAL_HOURS
    assert kept.time_entry_ids is None
    assert kept.description == "Design work"


def test_an_entry_on_another_line_is_refused(client, user, draft):
    _login(client, user)
    invoice = draft["invoice"]
    wireframes, call = draft["entries"][0], draft["entries"][2]
    other_line = _line_of(invoice.id, call)
    resp = client.post(f"/invoices/{invoice.id}/lines/{other_line.id}/entries/{wireframes.id}/remove", headers=JSON)
    assert resp.status_code == 400
    assert resp.get_json()["error"] == "not_on_line"


# ----------------------------------------------------------------------
# Regroup and Apply to lines
# ----------------------------------------------------------------------
def test_regroup_keeps_or_rebuilds_edited_lines_and_the_total_stays(client, user, draft):
    _login(client, user)
    invoice = draft["invoice"]
    total = _total(invoice.id)
    call = draft["entries"][2]
    line = _line_of(invoice.id, call)
    line.description = "Calls"
    line.description_edited = True
    db.session.commit()

    resp = client.post(f"/invoices/{invoice.id}/regroup", data={"hours_layout": "project", "keep_edited": "keep"})
    assert resp.status_code == 302
    descriptions = [item.description for item in _lines(invoice.id)]
    assert "Calls" in descriptions
    assert len(descriptions) == 2
    assert _total(invoice.id) == total

    resp = client.post(
        f"/invoices/{invoice.id}/regroup", data={"hours_layout": "person", "keep_edited": "rebuild"}, headers=JSON
    )
    assert resp.status_code == 200
    descriptions = [item.description for item in _lines(invoice.id)]
    assert "Calls" not in descriptions
    assert len(descriptions) == 2  # the user and the colleague
    assert _total(invoice.id) == total
    db.session.expire_all()
    assert Invoice.query.get(invoice.id).hours_layout == "person"


def test_regroup_refuses_an_unknown_layout(client, user, draft):
    _login(client, user)
    resp = client.post(f"/invoices/{draft['invoice'].id}/regroup", data={"hours_layout": "none"}, headers=JSON)
    assert resp.status_code == 400


def test_apply_to_lines_rewrites_lines_not_edited_unless_rebuild(client, user, draft):
    _login(client, user)
    invoice = draft["invoice"]
    edited = _lines(invoice.id)[0]
    edited.description = "Kept text"
    edited.description_edited = True
    db.session.commit()

    resp = client.post(f"/invoices/{invoice.id}/apply-template", data={"line_template": "{person}: {task}"})
    assert resp.status_code == 302
    lines = _lines(invoice.id)
    assert lines[0].description == "Kept text"
    assert all(": " in item.description for item in lines[1:])

    client.post(
        f"/invoices/{invoice.id}/apply-template",
        data={"line_template": "{person}: {task}", "keep_edited": "rebuild"},
    )
    lines = _lines(invoice.id)
    assert lines[0].description != "Kept text"
    assert lines[0].description_edited is False


# ----------------------------------------------------------------------
# Lines typed in, line edits
# ----------------------------------------------------------------------
def test_add_hours_line_has_no_entries_takes_the_project_rate_and_survives_regroup(client, user, draft):
    _login(client, user)
    invoice = draft["invoice"]
    total = _total(invoice.id)
    resp = client.post(
        f"/invoices/{invoice.id}/lines",
        data={"line_type": "hours", "description": "CTO support", "quantity": "4", "unit_price": ""},
        headers=JSON,
    )
    assert resp.status_code == 200, resp.get_data(as_text=True)
    item = InvoiceItem.query.get(resp.get_json()["item_id"])
    assert item.kind == LINE_KIND_MANUAL_HOURS
    assert item.time_entry_ids is None
    assert Decimal(str(item.unit_price)) == Decimal("40.00")
    assert _total(invoice.id) == total + Decimal("160.00")

    client.post(f"/invoices/{invoice.id}/regroup", data={"hours_layout": "project"})
    db.session.expire_all()
    assert InvoiceItem.query.get(item.id).description == "CTO support"
    html = client.get(f"/invoices/{invoice.id}").get_data(as_text=True)
    hours_block = html.split('id="hours"')[1].split('id="other-items"')[0]
    assert f'id="line-{item.id}"' in hours_block


def test_add_item_goes_to_other_items(client, user, draft):
    _login(client, user)
    invoice = draft["invoice"]
    resp = client.post(
        f"/invoices/{invoice.id}/lines",
        data={"line_type": "item", "description": "Retainer", "quantity": "1", "unit_price": "150"},
        headers=JSON,
    )
    item = InvoiceItem.query.get(resp.get_json()["item_id"])
    assert item.kind == LINE_KIND_MANUAL
    html = client.get(f"/invoices/{invoice.id}").get_data(as_text=True)
    other_block = html.split('id="other-items"')[1]
    assert f'id="line-{item.id}"' in other_block


def test_add_line_needs_a_description_and_a_number(client, user, draft):
    _login(client, user)
    invoice = draft["invoice"]
    resp = client.post(
        f"/invoices/{invoice.id}/lines", data={"line_type": "hours", "description": "", "quantity": "1"}, headers=JSON
    )
    assert resp.status_code == 400
    resp = client.post(
        f"/invoices/{invoice.id}/lines",
        data={"line_type": "hours", "description": "X", "quantity": "abc"},
        headers=JSON,
    )
    assert resp.status_code == 400


def test_editing_a_line_marks_what_changed_and_recalculates(client, user, draft):
    _login(client, user)
    invoice = draft["invoice"]
    line = _lines(invoice.id)[0]
    resp = client.post(
        f"/invoices/{invoice.id}/lines/{line.id}",
        data={"description": "Design, October", "quantity": "2.50", "unit_price": str(line.unit_price)},
        headers=JSON,
    )
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["line"]["amount"] == "100.00"
    assert data["line"]["quantity_note"].startswith("edited")
    db.session.expire_all()
    line = InvoiceItem.query.get(line.id)
    assert (line.description_edited, line.quantity_edited, line.price_edited) == (True, True, False)

    resp = client.post(
        f"/invoices/{invoice.id}/lines/{line.id}",
        data={"tax_rate": "20", "vat_category": "S", "discount_percent": "10", "position": "7"},
        headers=JSON,
    )
    assert resp.status_code == 200
    db.session.expire_all()
    line = InvoiceItem.query.get(line.id)
    assert Decimal(str(line.tax_rate)) == Decimal("20")
    assert Decimal(str(line.total_amount)) == Decimal("90.00")
    assert line.position == 7


def test_deleting_a_line_returns_its_entries_to_unbilled(client, user, draft):
    _login(client, user)
    invoice = draft["invoice"]
    call, sync = draft["entries"][2], draft["entries"][3]
    line = _line_of(invoice.id, call)
    resp = client.post(f"/invoices/{invoice.id}/lines/{line.id}/delete", headers=JSON)
    assert resp.status_code == 200
    db.session.expire_all()
    assert InvoiceItem.query.get(line.id) is None
    service = InvoiceTimeService()
    assert service.billing_state(TimeEntry.query.get(call.id)) == UNBILLED
    assert service.billing_state(TimeEntry.query.get(sync.id)) == UNBILLED


def test_a_hand_hours_line_stays_one_after_the_full_edit_form(client, user, draft):
    _login(client, user)
    invoice = draft["invoice"]
    InvoiceTimeService().add_manual_line(invoice, "CTO support", "4", "40", hours=True)
    db.session.commit()
    lines = _lines(invoice.id)
    data = {
        "client_name": invoice.client_name,
        "due_date": invoice.due_date.strftime("%Y-%m-%d"),
        "tax_rate": "0",
        "item_id[]": [str(i.id) for i in lines],
        "description[]": [i.description for i in lines],
        "quantity[]": [str(i.quantity) for i in lines],
        "unit_price[]": [str(i.unit_price) for i in lines],
        "item_time_entry_ids[]": [i.time_entry_ids or "" for i in lines],
    }
    resp = client.post(f"/invoices/{invoice.id}/edit", data=data)
    assert resp.status_code == 302
    assert resp.headers["Location"].endswith(f"/invoices/{invoice.id}")
    kinds = {i.description: i.kind for i in _lines(invoice.id)}
    assert kinds["CTO support"] == LINE_KIND_MANUAL_HOURS


# ----------------------------------------------------------------------
# New entries of the period
# ----------------------------------------------------------------------
def test_add_to_matching_lines_joins_the_line_of_the_same_group_and_rate(client, user, draft):
    _login(client, user)
    invoice = draft["invoice"]
    logged_after = datetime(2026, 11, 3, 9, 0)
    calls_line = _line_of(invoice.id, draft["entries"][2])
    design_line = _line_of(invoice.id, draft["entries"][0])
    design_line.description = "Wireframes for the shop"
    design_line.description_edited = True
    design_line.quantity = Decimal("3.00")
    design_line.quantity_edited = True
    design_line.total_amount = design_line.line_net
    db.session.commit()
    before = len(_lines(invoice.id))

    another_call = draft["entry"](draft["colleague"], draft["meetings"], 20, 1, "Follow-up call", logged=logged_after)
    more_design = draft["entry"](draft["user"], draft["design"], 21, 1.5, "Icons", logged=logged_after)
    newcomer = UserFactory(username="newcomer-draft", full_name="Newcomer")
    db.session.commit()
    stranger = draft["entry"](newcomer, draft["design"], 22, 2, "Fresh eyes", logged=logged_after)

    resp = client.post(f"/invoices/{invoice.id}/new-entries/add")
    assert resp.status_code == 302

    db.session.expire_all()
    calls_line = InvoiceItem.query.get(calls_line.id)
    assert str(another_call.id) in calls_line.time_entry_ids.split(",")
    assert Decimal(str(calls_line.quantity)) == Decimal("2.50")
    design_line = InvoiceItem.query.get(design_line.id)
    assert str(more_design.id) in design_line.time_entry_ids.split(",")
    assert design_line.description == "Wireframes for the shop"
    assert Decimal(str(design_line.quantity)) == Decimal("4.50")
    assert len(_lines(invoice.id)) == before + 1
    assert _line_of(invoice.id, stranger) is not None
    assert InvoiceTimeService().new_period_entries(invoice) == []

    html = client.get(f"/invoices/{invoice.id}").get_data(as_text=True)
    assert "+1.5 h tracked" in html
    assert 'id="newEntries"' not in html


# ----------------------------------------------------------------------
# Notes, terms, discount, PDF
# ----------------------------------------------------------------------
def test_notes_terms_and_discount_are_saved_and_the_total_follows(client, user, draft):
    _login(client, user)
    invoice = draft["invoice"]
    total = _total(invoice.id)
    resp = client.post(
        f"/invoices/{invoice.id}/notes-terms", data={"notes": "Payment order 123", "terms": "15 days"}, headers=JSON
    )
    assert resp.status_code == 200
    resp = client.post(
        f"/invoices/{invoice.id}/discount", data={"discount_type": "percent", "discount_value": "5"}, headers=JSON
    )
    assert resp.status_code == 200
    db.session.expire_all()
    saved = Invoice.query.get(invoice.id)
    assert (saved.notes, saved.terms) == ("Payment order 123", "15 days")
    assert Decimal(str(saved.total_amount)) == (total * Decimal("0.95")).quantize(Decimal("0.01"))
    assert resp.get_json()["totals"]["total"] == "%.2f" % saved.total_amount

    pdf = client.get(f"/invoices/{invoice.id}/export/pdf")
    assert pdf.status_code == 200

    resp = client.post(
        f"/invoices/{invoice.id}/discount", data={"discount_type": "amount", "discount_value": "500"}, headers=JSON
    )
    assert resp.status_code == 200
    resp = client.post(
        f"/invoices/{invoice.id}/discount", data={"discount_type": "percent", "discount_value": "150"}, headers=JSON
    )
    assert resp.status_code == 400
    assert _total(invoice.id) == total - Decimal("500.00")


# ----------------------------------------------------------------------
# Refusals
# ----------------------------------------------------------------------
def _action_urls(invoice, line, entry):
    base = f"/invoices/{invoice.id}"
    return [
        (f"{base}/lines/{line.id}/entries/{entry.id}/remove", {}),
        (f"{base}/lines/{line.id}/entries/{entry.id}/non-billable", {}),
        (f"{base}/regroup", {"hours_layout": "project"}),
        (f"{base}/apply-template", {"line_template": "{task}"}),
        (f"{base}/lines", {"line_type": "hours", "description": "X", "quantity": "1"}),
        (f"{base}/lines/{line.id}", {"description": "Changed"}),
        (f"{base}/lines/{line.id}/delete", {}),
        (f"{base}/new-entries/add", {}),
        (f"{base}/notes-terms", {"notes": "N"}),
        (f"{base}/discount", {"discount_value": "5"}),
    ]


def test_actions_on_an_issued_invoice_are_refused(client, user, draft):
    _login(client, user)
    invoice = draft["invoice"]
    entry = draft["entries"][0]
    line = _line_of(invoice.id, entry)
    invoice.status = "issued"
    db.session.commit()
    for url, data in _action_urls(invoice, line, entry):
        resp = client.post(url, data=data, headers=JSON)
        assert resp.status_code == 400, url
        assert resp.get_json()["error"] == "invalid_status", url
    db.session.expire_all()
    assert InvoiceItem.query.get(line.id).description == line.description
    assert TimeEntry.query.get(entry.id).billable is True


def test_actions_without_permission_are_refused(client, draft):
    invoice = draft["invoice"]
    entry = draft["entries"][0]
    line = _line_of(invoice.id, entry)
    stranger = UserFactory(username="stranger-draft")
    db.session.commit()
    _login(client, stranger)
    for url, data in _action_urls(invoice, line, entry):
        resp = client.post(url, data=data, headers=JSON)
        assert resp.status_code == 403, url
    assert client.get(f"/invoices/{invoice.id}").status_code == 302


def test_a_template_typed_in_the_browser_keeps_plain_line_breaks(client, user, draft):
    _login(client, user)
    invoice = draft["invoice"]
    client.post(f"/invoices/{invoice.id}/apply-template", data={"line_template": "{task}\r\n{note}"})
    client.post(f"/invoices/{invoice.id}/regroup", data={"hours_layout": "task", "line_template": "{task}\r\n{note}"})
    descriptions = [item.description for item in _lines(invoice.id)]
    assert all("\r" not in text for text in descriptions)
    assert "Design\nWireframes\nLayout" in descriptions
    db.session.expire_all()
    assert Invoice.query.get(invoice.id).line_template == "{task}\n{note}"


# ----------------------------------------------------------------------
# Prepaid hours
# ----------------------------------------------------------------------
@pytest.fixture
def prepaid(app, user):
    """A client with 10 prepaid hours a month, 30/h, and a helper that bills entries as generate-from-time does."""
    from app.utils.prepaid_hours import PrepaidHoursAllocator

    cl = ClientFactory(name="Prepaid Draft Client", default_hourly_rate=None)
    cl.prepaid_hours_monthly = Decimal("10")
    cl.prepaid_reset_day = 1
    project = ProjectFactory(
        name="Prepaid Draft Project", client_id=cl.id, hourly_rate=Decimal("30.00"), created_by=user.id
    )
    db.session.flush()
    task = Task(name="Support", project_id=project.id, status="todo", created_by=user.id)
    db.session.add(task)
    db.session.commit()

    def entry(day, hours, logged=LOGGED_BEFORE):
        start = datetime(2026, 10, day, 9, 0)
        made = TimeEntryFactory(
            user_id=user.id,
            project_id=project.id,
            task_id=task.id,
            start_time=start,
            end_time=start + timedelta(hours=hours),
            billable=True,
        )
        made.created_at = logged
        db.session.commit()
        return made

    def draft_with(entries):
        invoice = InvoiceFactory(
            project_id=project.id, client_id=cl.id, client_name=cl.name, created_by=user.id, tax_rate=Decimal("0")
        )
        invoice.period_start, invoice.period_end = date(2026, 10, 1), date(2026, 10, 31)
        invoice.created_at = datetime(2026, 11, 2, 8, 0)
        db.session.commit()
        service = InvoiceTimeService()
        allocator = PrepaidHoursAllocator(client=cl, invoice=invoice, keep_entry_ids=service.invoice_entry_ids(invoice))
        processed = allocator.process(entries)
        service.add_entries(invoice, processed, "task", "{task}", created_by=user.id)
        service.link_entries(
            invoice,
            None,
            [(p.entry, p.prepaid_hours) for p in processed if p.prepaid_hours > 0 and p.billable_hours <= 0],
        )
        invoice.calculate_totals()
        db.session.commit()
        return invoice

    return {"client": cl, "entry": entry, "draft_with": draft_with}


def _ledger(entry_id, invoice_id=None):
    from app.models import ClientPrepaidConsumption

    query = ClientPrepaidConsumption.query.filter_by(time_entry_id=entry_id)
    if invoice_id is not None:
        query = query.filter_by(invoice_id=invoice_id)
    return query.all()


def test_new_entries_fully_covered_by_prepaid_hours_get_no_line(client, user, prepaid):
    _login(client, user)
    used = prepaid["entry"](3, 2)
    invoice = prepaid["draft_with"]([used])  # 2 of the 10 prepaid hours
    assert _lines(invoice.id) == []
    late = prepaid["entry"](20, 3, logged=datetime(2026, 11, 3, 9, 0))

    resp = client.post(f"/invoices/{invoice.id}/new-entries/add", headers=JSON)
    assert resp.status_code == 200, resp.get_data(as_text=True)
    assert "covered by prepaid hours" in resp.get_json()["message"]
    assert _lines(invoice.id) == []
    assert _total(invoice.id) == Decimal("0.00")
    ledger = _ledger(late.id, invoice.id)
    assert len(ledger) == 1 and ledger[0].hours_consumed == Decimal("3.00")
    assert InvoiceTimeService().billing_invoice(TimeEntry.query.get(late.id)).id == invoice.id
    # The entries already on the draft keep their prepaid hours
    assert _ledger(used.id, invoice.id)[0].hours_consumed == Decimal("2.00")


def test_new_entries_partly_covered_by_prepaid_hours_bill_only_the_rest(client, user, prepaid):
    _login(client, user)
    invoice = prepaid["draft_with"]([prepaid["entry"](3, 4), prepaid["entry"](4, 4)])  # 8 prepaid hours used
    late = prepaid["entry"](20, 3, logged=datetime(2026, 11, 3, 9, 0))

    resp = client.post(f"/invoices/{invoice.id}/new-entries/add")
    assert resp.status_code == 302
    line = _line_of(invoice.id, late)
    assert line is not None
    assert Decimal(str(line.quantity)) == Decimal("1.00")
    assert Decimal(str(line.total_amount)) == Decimal("30.00")
    assert _ledger(late.id, invoice.id)[0].hours_consumed == Decimal("2.00")
    assert _total(invoice.id) == Decimal("30.00")


@pytest.mark.parametrize("action", ["remove", "non-billable"])
def test_taking_off_a_partly_prepaid_entry_frees_its_prepaid_hours(client, user, prepaid, action):
    _login(client, user)
    first, partly = prepaid["entry"](3, 8), prepaid["entry"](4, 3)  # 8 + 2 prepaid, 1 h billed
    invoice = prepaid["draft_with"]([first, partly])
    line = _line_of(invoice.id, partly)
    assert Decimal(str(line.quantity)) == Decimal("1.00")
    assert _ledger(partly.id, invoice.id)

    resp = client.post(f"/invoices/{invoice.id}/lines/{line.id}/entries/{partly.id}/{action}", headers=JSON)
    assert resp.status_code == 200, resp.get_data(as_text=True)
    assert resp.get_json()["warnings"] == ["Prepaid hours were freed. Rebuild from step 1 to apply them."]

    db.session.expire_all()
    entry = TimeEntry.query.get(partly.id)
    assert _ledger(partly.id) == []
    assert InvoiceTimeService().billing_invoice(entry) is None
    assert entry.billable is (action == "remove")
    # The other entry keeps its prepaid hours; the freed ones are not spread over it
    assert _ledger(first.id, invoice.id)[0].hours_consumed == Decimal("8.00")


def test_an_entry_taken_off_takes_prepaid_hours_again_on_another_draft(client, user, prepaid):
    _login(client, user)
    first, partly = prepaid["entry"](3, 8), prepaid["entry"](4, 3)
    invoice = prepaid["draft_with"]([first, partly])
    line = _line_of(invoice.id, partly)
    client.post(f"/invoices/{invoice.id}/lines/{line.id}/entries/{partly.id}/remove", headers=JSON)

    db.session.expire_all()
    other = prepaid["draft_with"]([TimeEntry.query.get(partly.id)])
    other_line = _line_of(other.id, partly)
    assert _ledger(partly.id, other.id)[0].hours_consumed == Decimal("2.00")
    assert Decimal(str(other_line.quantity)) == Decimal("1.00")


def test_deleting_a_line_frees_the_prepaid_hours_of_its_entries(client, user, prepaid):
    _login(client, user)
    partly = prepaid["entry"](4, 12)  # 10 prepaid, 2 billed
    invoice = prepaid["draft_with"]([partly])
    line = _line_of(invoice.id, partly)
    resp = client.post(f"/invoices/{invoice.id}/lines/{line.id}/delete", headers=JSON)
    assert resp.status_code == 200
    assert resp.get_json()["warnings"]
    db.session.expire_all()
    assert _ledger(partly.id) == []
    assert TimeEntry.query.get(partly.id).billable is True
    assert InvoiceTimeService().billing_invoice(TimeEntry.query.get(partly.id)) is None


# ----------------------------------------------------------------------
# Regroup warnings, the user's projects
# ----------------------------------------------------------------------
def test_regroup_returns_missing_rate_warnings_in_the_answer(client, user, draft):
    _login(client, user)
    invoice = draft["invoice"]
    draft["project"].hourly_rate = None
    db.session.commit()
    resp = client.post(f"/invoices/{invoice.id}/regroup", data={"hours_layout": "person"}, headers=JSON)
    assert resp.status_code == 200
    warnings = resp.get_json()["warnings"]
    assert warnings and all(isinstance(w, str) for w in warnings)
    # Shown at once by the page, not left for the next page as a flash message
    with client.session_transaction() as sess:
        assert not [m for m in sess.get("_flashes", []) if m[0] == "warning"]


def test_new_entries_follow_the_projects_the_user_may_see(client, user, draft, monkeypatch):
    from app.models import User

    invoice = draft["invoice"]
    other_project = ProjectFactory(
        name="Draft Page Other Project", client_id=invoice.client_id, hourly_rate=Decimal("40.00")
    )
    db.session.commit()
    logged_after = datetime(2026, 11, 3, 9, 0)
    own = draft["entry"](draft["user"], draft["design"], 20, 1, "Own project", logged=logged_after)
    start = datetime(2026, 10, 21, 9, 0)
    foreign = TimeEntryFactory(
        user_id=draft["colleague"].id,
        project_id=other_project.id,
        start_time=start,
        end_time=start + timedelta(hours=2),
        notes="Other project",
        billable=True,
    )
    foreign.created_at = logged_after
    db.session.commit()

    allowed = [draft["project"].id]
    monkeypatch.setattr(User, "get_allowed_project_ids", lambda self: allowed)
    _login(client, user)

    html = client.get(f"/invoices/{invoice.id}").get_data(as_text=True)
    assert "1 new entry in this invoice" in html
    assert "Own project" in html
    assert "Other project" not in html

    client.post(f"/invoices/{invoice.id}/new-entries/add", data={"entry_ids[]": [str(own.id), str(foreign.id)]})
    db.session.expire_all()
    service = InvoiceTimeService()
    assert service.billing_invoice(TimeEntry.query.get(own.id)).id == invoice.id
    assert service.billing_invoice(TimeEntry.query.get(foreign.id)) is None


def _api_token(user):
    from app.models import ApiToken

    token, plain = ApiToken.create_token(
        user_id=user.id, name="Draft page token", scopes="read:invoices,write:invoices"
    )
    db.session.add(token)
    db.session.commit()
    return {"Authorization": f"Bearer {plain}"}


def _drop_line_in_full_form(client, invoice, dropped):
    keep = [item for item in _lines(invoice.id) if item.id != dropped.id]
    return client.post(
        f"/invoices/{invoice.id}/edit",
        data={
            "client_name": invoice.client_name,
            "due_date": invoice.due_date.strftime("%Y-%m-%d"),
            "tax_rate": "0",
            "item_id[]": [str(i.id) for i in keep],
            "description[]": [i.description for i in keep],
            "quantity[]": [str(i.quantity) for i in keep],
            "unit_price[]": [str(i.unit_price) for i in keep],
            "item_time_entry_ids[]": [i.time_entry_ids or "" for i in keep],
        },
    )


def _drop_line_by_api(client, user, invoice, dropped):
    keep = [item for item in _lines(invoice.id) if item.id != dropped.id]
    return client.put(
        f"/api/v1/invoices/{invoice.id}/items",
        json={
            "items": [
                {
                    "id": i.id,
                    "description": i.description,
                    "quantity": float(i.quantity),
                    "unit_price": float(i.unit_price),
                    "time_entry_ids": i.time_entry_ids,
                }
                for i in keep
            ]
        },
        headers=_api_token(user),
    )


@pytest.mark.parametrize("path", ["full_form", "api_items"])
def test_dropping_a_partly_prepaid_line_elsewhere_frees_its_prepaid_hours(client, user, prepaid, path):
    # 3 prepaid hours: A takes 2, B takes 1 and bills 2 on its own line
    prepaid["client"].prepaid_hours_monthly = Decimal("3")
    db.session.commit()
    a, b = prepaid["entry"](3, 2), prepaid["entry"](4, 3)
    invoice = prepaid["draft_with"]([a, b])
    line_b = _line_of(invoice.id, b)
    assert Decimal(str(line_b.quantity)) == Decimal("2.00")
    assert _ledger(b.id, invoice.id)[0].hours_consumed == Decimal("1.00")
    _login(client, user)

    if path == "full_form":
        resp = _drop_line_in_full_form(client, invoice, line_b)
        assert resp.status_code == 302
        with client.session_transaction() as sess:
            assert ("warning", "Prepaid hours were freed. Rebuild from step 1 to apply them.") in sess.get(
                "_flashes", []
            )
    else:
        resp = _drop_line_by_api(client, user, invoice, line_b)
        assert resp.status_code == 200, resp.get_data(as_text=True)

    db.session.expire_all()
    entry = TimeEntry.query.get(b.id)
    assert _ledger(b.id) == []
    assert entry.billable is True
    assert InvoiceTimeService().billing_invoice(entry) is None
    # A keeps its prepaid hours; the hour B gave back is not spread over it
    assert _ledger(a.id, invoice.id)[0].hours_consumed == Decimal("2.00")

    # On another draft B takes the freed prepaid hour again and bills the rest
    other = prepaid["draft_with"]([entry])
    assert _ledger(b.id, other.id)[0].hours_consumed == Decimal("1.00")
    assert Decimal(str(_line_of(other.id, b).quantity)) == Decimal("2.00")


def _plan_of_three(prepaid):
    """3 prepaid hours at 40/h: A (2 h) is fully covered, B (3 h) takes 1 and bills 2, C (2 h) is new."""
    prepaid["client"].prepaid_hours_monthly = Decimal("3")
    a, b, c = prepaid["entry"](3, 2), prepaid["entry"](4, 3), prepaid["entry"](5, 2)
    a.project.hourly_rate = Decimal("40.00")
    db.session.commit()
    invoice = prepaid["draft_with"]([a, b])
    assert Decimal(str(_line_of(invoice.id, b).quantity)) == Decimal("2.00")
    return invoice, a, b, c


def _generate(client, user, invoice, entries, path):
    """Rebuild the draft's hours from ``entries`` one line per entry: by the API (replace) or the page."""
    if path == "api":
        resp = client.post(
            f"/api/v1/invoices/{invoice.id}/generate-from-time",
            json={"time_entry_ids": [e.id for e in entries], "replace_existing": True, "hours_layout": "detailed"},
            headers=_api_token(user),
        )
        assert resp.status_code == 200, resp.get_data(as_text=True)
    else:
        _login(client, user)
        resp = client.post(
            f"/invoices/{invoice.id}/generate-from-time",
            data={"time_entries[]": [str(e.id) for e in entries], "hours_layout": "detailed"},
        )
        assert resp.status_code == 302
    db.session.expire_all()


def _link_hours(invoice_id, entry):
    from app.models import InvoiceTimeLink

    return sorted(
        (link.invoice_item_id is None, Decimal(link.hours))
        for link in InvoiceTimeLink.query.filter_by(invoice_id=invoice_id, time_entry_id=entry.id, released_at=None)
    )


@pytest.mark.parametrize("listed", ["b_c", "a_b_c"])
@pytest.mark.parametrize("path", ["api", "page"])
def test_replacing_lines_bills_only_the_hours_prepaid_did_not_cover(client, user, prepaid, path, listed):
    invoice, a, b, c = _plan_of_three(prepaid)

    _generate(client, user, invoice, [b, c] if listed == "b_c" else [a, b, c], path)

    # B bills the 2 hours left after its prepaid hour, and its link says the same
    line_b = _line_of(invoice.id, b)
    assert (Decimal(str(line_b.quantity)), Decimal(str(line_b.total_amount))) == (Decimal("2.00"), Decimal("80.00"))
    assert _link_hours(invoice.id, b) == [(False, Decimal("2.00"))]
    assert [row.hours_consumed for row in _ledger(b.id, invoice.id)] == [Decimal("1.00")]
    # A stays fully covered: a link without a line
    assert _line_of(invoice.id, a) is None
    assert _link_hours(invoice.id, a) == [(True, Decimal("2.00"))]
    assert [row.hours_consumed for row in _ledger(a.id, invoice.id)] == [Decimal("2.00")]
    # C has no prepaid hours left and bills all of them
    assert Decimal(str(_line_of(invoice.id, c).quantity)) == Decimal("2.00")
    assert _ledger(c.id) == []
    assert _total(invoice.id) == Decimal("160.00")


def test_replacing_lines_without_the_entry_gives_back_its_prepaid_hours(client, user, prepaid):
    invoice, a, b, c = _plan_of_three(prepaid)

    _generate(client, user, invoice, [c], "api")

    entry = TimeEntry.query.get(b.id)
    assert _line_of(invoice.id, b) is None
    assert InvoiceTimeService().billing_invoice(entry) is None
    assert _ledger(b.id) == []
    assert entry.billable is True
    assert [row.hours_consumed for row in _ledger(a.id, invoice.id)] == [Decimal("2.00")]


def test_replacing_lines_of_a_client_without_prepaid_hours_bills_every_hour(client, user, prepaid):
    prepaid["client"].prepaid_hours_monthly = Decimal("0")
    db.session.commit()
    b, c = prepaid["entry"](4, 3), prepaid["entry"](5, 2)
    invoice = prepaid["draft_with"]([b])

    _generate(client, user, invoice, [b, c], "api")

    assert Decimal(str(_line_of(invoice.id, b).quantity)) == Decimal("3.00")
    assert _link_hours(invoice.id, b) == [(False, Decimal("3.00"))]
    assert Decimal(str(_line_of(invoice.id, c).quantity)) == Decimal("2.00")
    assert _total(invoice.id) == Decimal("150.00")


def test_add_new_entries_leaves_out_an_entry_prepaid_on_another_invoice(client, user, prepaid):
    from app.models import ClientPrepaidConsumption

    invoice = prepaid["draft_with"]([prepaid["entry"](3, 1)])
    late = prepaid["entry"](20, 2, logged=datetime(2026, 11, 3, 9, 0))
    elsewhere = InvoiceFactory(
        project_id=invoice.project_id, client_id=invoice.client_id, client_name=invoice.client_name, created_by=user.id
    )
    db.session.flush()
    db.session.add(
        ClientPrepaidConsumption(
            client_id=invoice.client_id,
            time_entry_id=late.id,
            invoice_id=elsewhere.id,
            seconds_consumed=3600,
            allocation_month=date(2026, 10, 1),
        )
    )
    db.session.commit()
    _login(client, user)

    resp = client.post(f"/invoices/{invoice.id}/new-entries/add", headers=JSON)
    assert resp.status_code == 200, resp.get_data(as_text=True)
    data = resp.get_json()
    assert data["warnings"] == ["1 entries were left out: their prepaid hours are recorded on another invoice."]
    db.session.expire_all()
    assert InvoiceTimeService().billing_invoice(TimeEntry.query.get(late.id)) is None
    assert [row.invoice_id for row in _ledger(late.id)] == [elsewhere.id]


def test_a_bad_value_is_answered_with_a_fixed_message(client, user, draft):
    _login(client, user)
    invoice = draft["invoice"]
    line = _lines(invoice.id)[0]
    resp = client.post(f"/invoices/{invoice.id}/lines/{line.id}", data={"quantity": "abc"}, headers=JSON)
    assert resp.status_code == 400
    assert resp.get_json() == {"success": False, "error": "invalid_value", "message": "Quantity must be a number."}
    resp = client.post(f"/invoices/{invoice.id}/lines/{line.id}", data={"vat_category": "XX"}, headers=JSON)
    assert resp.get_json()["message"] == "VAT category is not one of the allowed values."
    resp = client.post(
        f"/invoices/{invoice.id}/discount", data={"discount_type": "percent", "discount_value": "150"}, headers=JSON
    )
    assert resp.get_json()["message"] == "Discount cannot be above 100%."
