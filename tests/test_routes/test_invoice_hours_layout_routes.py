"""Generate from Time: Show hours as and Line description; edited lines survive; API parameters."""

from datetime import date, datetime, timedelta
from decimal import Decimal

import pytest
from factories import ClientFactory, InvoiceFactory, ProjectFactory, TimeEntryFactory, UserFactory

from app import db
from app.models import ApiToken, Invoice, RateOverride, Task

pytestmark = [pytest.mark.routes]


@pytest.fixture
def layout_setup(app, user):
    """Two tasks; the user and a colleague whose rate goes from 40 to 50 on the 15th."""
    cl = ClientFactory(name="Layout Route Client", default_hourly_rate=None)
    project = ProjectFactory(name="Layout Route Project", client_id=cl.id, hourly_rate=Decimal("40.00"))
    colleague = UserFactory(username="colleague-layout", full_name="Colleague")
    db.session.flush()
    design = Task(name="Design", project_id=project.id, status="todo", created_by=user.id)
    meetings = Task(name="Meetings", project_id=project.id, status="todo", created_by=user.id)
    db.session.add_all([design, meetings])
    db.session.add(
        RateOverride(
            project_id=project.id, user_id=colleague.id, hourly_rate=Decimal("50.00"), effective_from=date(2026, 10, 15)
        )
    )
    db.session.flush()

    def entry(person, task, day, hours, notes=None):
        start = datetime(2026, 10, day, 9, 0)
        made = TimeEntryFactory(
            user_id=person.id,
            project_id=project.id,
            task_id=task.id,
            start_time=start,
            end_time=start + timedelta(hours=hours),
            notes=notes,
            billable=True,
        )
        db.session.commit()
        return made

    entries = [
        entry(user, design, 5, 2, "Wireframes"),
        entry(colleague, design, 7, 3, "Layout"),
        entry(colleague, design, 20, 1, "Layout"),
        entry(colleague, meetings, 21, 1),
    ]
    invoice = InvoiceFactory(
        project_id=project.id, client_id=cl.id, client_name=cl.name, created_by=user.id, tax_rate=Decimal("0")
    )
    invoice.currency_code = "EUR"
    db.session.commit()
    return {
        "client": cl,
        "project": project,
        "invoice": invoice,
        "entries": entries,
        "entry": entry,
        "colleague": colleague,
        "design": design,
    }


def _login(client, user):
    with client.session_transaction() as sess:
        sess["_user_id"] = str(user.id)
        sess["_fresh"] = True


def _token(user):
    token, plain = ApiToken.create_token(user_id=user.id, name="Layout token", scopes="read:invoices,write:invoices")
    db.session.add(token)
    db.session.commit()
    return {"Authorization": f"Bearer {plain}"}


def _lines(invoice_id):
    db.session.expire_all()
    invoice = Invoice.query.get(invoice_id)
    return sorted(invoice.items.all(), key=lambda item: (item.position or 0, item.id))


def _generate(client, invoice, entries, **fields):
    data = {"time_entries[]": [str(e.id) for e in entries]}
    data.update(fields)
    return client.post(f"/invoices/{invoice.id}/generate-from-time", data=data)


def test_page_offers_the_layouts_with_the_projects_last_one_checked(client, user, layout_setup):
    project = layout_setup["project"]
    project.last_hours_layout = "person"
    project.last_line_template = "{person}: {date}"
    db.session.commit()
    _login(client, user)
    resp = client.get(f"/invoices/{layout_setup['invoice'].id}/generate-from-time")
    assert resp.status_code == 200
    html = resp.get_data(as_text=True)
    for layout in ("detailed", "task", "person", "task_person", "project", "none"):
        assert f'value="{layout}"' in html
    assert 'value="person" checked' in html
    assert 'value="{person}: {date}"' in html
    assert 'name="per_entry_lines"' not in html


def test_layout_and_template_from_the_form_build_the_lines(client, user, layout_setup):
    _login(client, user)
    invoice = layout_setup["invoice"]
    resp = _generate(
        client, invoice, layout_setup["entries"], hours_layout="task_person", line_template="{task} - {person}"
    )
    assert resp.status_code == 302
    descriptions = [item.description for item in _lines(invoice.id)]
    # By task, then person; the colleague's Design hours differ by rate
    assert descriptions == [
        "Design - Colleague – 40.00 EUR/h",
        "Design - Colleague – 50.00 EUR/h",
        f"Design - {user.display_name}",
        "Meetings - Colleague",
    ]
    db.session.expire_all()
    project = Invoice.query.get(invoice.id).project
    assert (project.last_hours_layout, project.last_line_template) == ("task_person", "{task} - {person}")


def test_an_edited_line_survives_adding_hours_again(client, user, layout_setup):
    """Create by task and person, rename one line in the edit form, add hours again: the renamed line stays."""
    _login(client, user)
    invoice = layout_setup["invoice"]
    resp = _generate(
        client, invoice, layout_setup["entries"], hours_layout="task_person", line_template="{task} - {person}"
    )
    assert resp.status_code == 302
    lines = _lines(invoice.id)

    descriptions = [item.description for item in lines]
    descriptions[0] = "Design review with the client"
    resp = client.post(
        f"/invoices/{invoice.id}/edit",
        data={
            "client_name": layout_setup["client"].name,
            "due_date": invoice.due_date.strftime("%Y-%m-%d"),
            "tax_rate": "0",
            "item_id[]": [str(item.id) for item in lines],
            "description[]": descriptions,
            "quantity[]": [str(item.quantity) for item in lines],
            "unit_price[]": [str(item.unit_price) for item in lines],
            "item_time_entry_ids[]": [item.time_entry_ids for item in lines],
        },
    )
    assert resp.status_code == 302
    lines = _lines(invoice.id)
    flags = [(item.description, item.description_edited, item.quantity_edited, item.price_edited) for item in lines]
    assert flags[0] == ("Design review with the client", True, False, False)
    assert all(not any(flag[1:]) for flag in flags[1:])
    renamed_entries = lines[0].time_entry_ids

    late = layout_setup["entry"](user, layout_setup["design"], 28, 1, "Handover")
    resp = _generate(client, invoice, [late], hours_layout="task_person", line_template="{task} - {person}")
    assert resp.status_code == 302

    lines = _lines(invoice.id)
    kept = [item for item in lines if item.description == "Design review with the client"]
    assert len(kept) == 1
    assert kept[0].description_edited is True
    assert kept[0].time_entry_ids == renamed_entries
    # The new entry got its own line; the kept line did not take it
    assert str(late.id) not in kept[0].time_entry_ids.split(",")
    assert any(str(late.id) in (item.time_entry_ids or "").split(",") for item in lines)


def test_edit_form_save_without_changes_sets_no_flags(client, user, layout_setup):
    _login(client, user)
    invoice = layout_setup["invoice"]
    _generate(client, invoice, layout_setup["entries"], hours_layout="task")
    lines = _lines(invoice.id)
    resp = client.post(
        f"/invoices/{invoice.id}/edit",
        data={
            "client_name": layout_setup["client"].name,
            "due_date": invoice.due_date.strftime("%Y-%m-%d"),
            "tax_rate": "0",
            "item_id[]": [str(item.id) for item in lines],
            "description[]": [item.description for item in lines],
            "quantity[]": [str(item.quantity) for item in lines],
            "unit_price[]": [str(item.unit_price) for item in lines],
            "item_time_entry_ids[]": [item.time_entry_ids for item in lines],
        },
    )
    assert resp.status_code == 302
    assert not any(item.is_edited for item in _lines(invoice.id))
    assert all(item.kind == "time" for item in _lines(invoice.id))


def test_edit_form_keeps_a_quantity_changed_by_hand(client, user, layout_setup):
    _login(client, user)
    invoice = layout_setup["invoice"]
    _generate(client, invoice, layout_setup["entries"][:1], hours_layout="task")
    (line,) = _lines(invoice.id)
    resp = client.post(
        f"/invoices/{invoice.id}/edit",
        data={
            "client_name": layout_setup["client"].name,
            "due_date": invoice.due_date.strftime("%Y-%m-%d"),
            "tax_rate": "0",
            "item_id[]": [str(line.id)],
            "description[]": [line.description],
            "quantity[]": ["1.50"],
            "unit_price[]": ["45.00"],
            "item_time_entry_ids[]": [line.time_entry_ids],
        },
    )
    assert resp.status_code == 302
    (line,) = _lines(invoice.id)
    assert (line.quantity, line.unit_price, line.total_amount) == (Decimal("1.50"), Decimal("45.00"), Decimal("67.50"))
    assert (line.description_edited, line.quantity_edited, line.price_edited) == (False, True, True)


def test_dont_add_any_hours_leaves_the_invoice_hours_alone(client, user, layout_setup):
    _login(client, user)
    invoice = layout_setup["invoice"]
    _generate(client, invoice, layout_setup["entries"][:2], hours_layout="task")
    before = [(item.id, item.description) for item in _lines(invoice.id)]
    resp = _generate(client, invoice, layout_setup["entries"][2:], hours_layout="none")
    assert resp.status_code == 302
    assert [(item.id, item.description) for item in _lines(invoice.id)] == before
    db.session.expire_all()
    # "none" is not the project's default for the next invoice
    assert Invoice.query.get(invoice.id).project.last_hours_layout == "task"


def test_older_per_entry_checkbox_still_means_one_line_per_entry(client, user, layout_setup):
    _login(client, user)
    invoice = layout_setup["invoice"]
    _generate(client, invoice, layout_setup["entries"], per_entry_lines="on")
    assert len(_lines(invoice.id)) == 4
    db.session.expire_all()
    assert Invoice.query.get(invoice.id).hours_layout == "detailed"


def test_preview_gives_an_example_line_per_layout(client, user, layout_setup):
    _login(client, user)
    invoice = layout_setup["invoice"]
    resp = client.post(
        f"/invoices/{invoice.id}/hours-layout-preview",
        json={"time_entry_ids": [e.id for e in layout_setup["entries"]]},
    )
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["entry_count"] == 4
    assert body["layouts"]["detailed"]["lines"] == 4
    assert body["layouts"]["task"]["example"] == "Design – 40.00 EUR/h"
    assert body["layouts"]["none"]["lines"] == 0

    resp = client.post(
        f"/invoices/{invoice.id}/hours-layout-preview",
        json={"time_entry_ids": [layout_setup["entries"][0].id], "line_template": "{task}: {note}"},
    )
    assert resp.get_json()["layouts"]["person"]["example"] == "Design: Wireframes"
    # Nothing was added
    assert _lines(invoice.id) == []


def test_preview_is_refused_to_other_users(client, layout_setup):
    other = UserFactory(username="other-layout")
    db.session.commit()
    _login(client, other)
    resp = client.post(f"/invoices/{layout_setup['invoice'].id}/hours-layout-preview", json={"time_entry_ids": []})
    assert resp.status_code == 403


def test_api_from_time_entries_takes_layout_and_template(client, user, layout_setup):
    project = layout_setup["project"]
    resp = client.post(
        "/api/v1/invoices/from-time-entries",
        headers=_token(user),
        json={
            "project_id": project.id,
            "time_entry_ids": [e.id for e in layout_setup["entries"]],
            "hours_layout": "person",
            "line_template": "{person}",
        },
    )
    assert resp.status_code == 201, resp.get_json()
    invoice_id = resp.get_json()["invoice"]["id"]
    assert [item.description for item in _lines(invoice_id)] == [
        "Colleague – 40.00 EUR/h",
        "Colleague – 50.00 EUR/h",
        user.display_name,
    ]
    db.session.expire_all()
    project = Invoice.query.get(invoice_id).project
    assert (project.last_hours_layout, project.last_line_template) == ("person", "{person}")


def test_api_generate_from_time_uses_the_projects_default_without_a_layout(client, user, layout_setup):
    project = layout_setup["project"]
    project.last_hours_layout = "detailed"
    project.last_line_template = "{note}"
    db.session.commit()
    invoice = layout_setup["invoice"]
    resp = client.post(
        f"/api/v1/invoices/{invoice.id}/generate-from-time",
        headers=_token(user),
        json={"time_entry_ids": [e.id for e in layout_setup["entries"]]},
    )
    assert resp.status_code == 200, resp.get_json()
    assert [item.description for item in _lines(invoice.id)] == [
        "Wireframes",
        "Layout",
        "Layout",
        "Layout Route Project",
    ]

    resp = client.post(
        f"/api/v1/invoices/{invoice.id}/generate-from-time",
        headers=_token(user),
        json={"time_entry_ids": [e.id for e in layout_setup["entries"]], "hours_layout": "project"},
    )
    assert resp.status_code == 200, resp.get_json()
    assert len(_lines(invoice.id)) == 2


def test_api_refuses_an_unknown_layout(client, user, layout_setup):
    resp = client.post(
        f"/api/v1/invoices/{layout_setup['invoice'].id}/generate-from-time",
        headers=_token(user),
        json={"time_entry_ids": [layout_setup["entries"][0].id], "hours_layout": "weekly"},
    )
    assert resp.status_code == 400
    resp = client.post(
        f"/api/v1/invoices/{layout_setup['invoice'].id}/generate-from-time",
        headers=_token(user),
        json={"time_entry_ids": [layout_setup["entries"][0].id], "line_template": "x" * 256},
    )
    assert resp.status_code == 400


def _edit_form(layout_setup, invoice, lines, **overrides):
    data = {
        "client_name": layout_setup["client"].name,
        "due_date": invoice.due_date.strftime("%Y-%m-%d"),
        "tax_rate": "0",
        "item_id[]": [str(item.id) for item in lines],
        "description[]": [item.description for item in lines],
        "quantity[]": [str(item.quantity) for item in lines],
        "unit_price[]": [str(item.unit_price) for item in lines],
        "item_time_entry_ids[]": [item.time_entry_ids for item in lines],
    }
    data.update(overrides)
    return data


def test_none_is_never_the_default_for_the_next_invoice(client, user, layout_setup):
    """After "Don't add any hours": API without a layout, Invoice unbilled and API replace use the real default."""
    from app.services import InvoiceService

    _login(client, user)
    project, invoice = layout_setup["project"], layout_setup["invoice"]
    project.last_hours_layout = "person"
    project.last_line_template = "{person}"
    db.session.commit()
    _generate(client, invoice, layout_setup["entries"][:1], hours_layout="none")
    db.session.expire_all()
    assert Invoice.query.get(invoice.id).project.last_hours_layout == "person"

    resp = client.post(
        "/api/v1/invoices/from-time-entries",
        headers=_token(user),
        json={"project_id": project.id, "time_entry_ids": [layout_setup["entries"][0].id]},
    )
    assert resp.status_code == 201, resp.get_json()
    created = Invoice.query.get(resp.get_json()["invoice"]["id"])
    assert created.hours_layout == "person"
    assert [item.description for item in created.items] == [user.display_name]

    # A project whose stored default is "none" (older data) falls back as if it had none
    project = Invoice.query.get(invoice.id).project
    project.last_hours_layout = "none"
    db.session.commit()
    result = InvoiceService().create_client_unbilled_invoice(layout_setup["client"].id, user.id)
    assert result["success"], result
    assert Invoice.query.get(result["invoice_id"]).hours_layout == "project"

    other = InvoiceFactory(
        project_id=project.id, client_id=layout_setup["client"].id, client_name="x", created_by=user.id
    )
    db.session.commit()
    entry = layout_setup["entry"](user, layout_setup["design"], 29, 1, "Late")
    resp = client.post(
        f"/api/v1/invoices/{other.id}/generate-from-time",
        headers=_token(user),
        json={"time_entry_ids": [entry.id], "replace_existing": True},
    )
    assert resp.status_code == 200, resp.get_json()
    db.session.expire_all()
    other = Invoice.query.get(other.id)
    assert other.hours_layout == "task"
    assert len(other.items.all()) == 1

    resp = client.post(
        f"/api/v1/invoices/{other.id}/generate-from-time",
        headers=_token(user),
        json={"time_entry_ids": [entry.id], "replace_existing": True, "hours_layout": "none"},
    )
    assert resp.status_code == 400
    resp = client.post(
        "/api/v1/invoices/from-time-entries",
        headers=_token(user),
        json={"project_id": project.id, "time_entry_ids": [entry.id], "hours_layout": "none"},
    )
    assert resp.status_code == 400


def test_multiline_description_saved_unchanged_is_not_edited(client, user, layout_setup):
    _login(client, user)
    invoice = layout_setup["invoice"]
    entry = layout_setup["entries"][0]
    entry.notes = "First point\nSecond point"
    db.session.commit()
    _generate(client, invoice, [entry], hours_layout="detailed", line_template="{note}")
    (line,) = _lines(invoice.id)
    assert line.description == "First point\nSecond point"

    page = client.get(f"/invoices/{invoice.id}/edit").get_data(as_text=True)
    assert '<textarea name="description[]" rows="2"' in page
    assert "First point\nSecond point</textarea>" in page

    # A browser sends a textarea with CRLF line breaks, sometimes with a trailing newline
    resp = client.post(
        f"/invoices/{invoice.id}/edit",
        data=_edit_form(layout_setup, invoice, [line], **{"description[]": ["First point\r\nSecond point\r\n"]}),
    )
    assert resp.status_code == 302
    (line,) = _lines(invoice.id)
    assert line.description == "First point\nSecond point"
    assert line.description_edited is False


@pytest.fixture
def prepaid(layout_setup):
    """A 0.3 h monthly plan for the client."""
    layout_setup["client"].prepaid_hours_monthly = Decimal("0.3")
    db.session.commit()
    return layout_setup


def _ledger(invoice_id):
    from app.models import ClientPrepaidConsumption

    db.session.expire_all()
    return {
        (row.id, row.time_entry_id, row.seconds_consumed)
        for row in ClientPrepaidConsumption.query.filter_by(invoice_id=invoice_id)
    }


def _link_hours(invoice_id):
    from app.models import InvoiceTimeLink

    db.session.expire_all()
    return {
        (link.time_entry_id, link.invoice_item_id is None, link.hours)
        for link in InvoiceTimeLink.query.filter_by(invoice_id=invoice_id, released_at=None)
    }


def test_edit_form_quantity_follows_linked_hours_after_prepaid(client, user, prepaid):
    _login(client, user)
    invoice = prepaid["invoice"]
    late = prepaid["entry"](user, prepaid["design"], 12, 1, "Partly prepaid")
    _generate(client, invoice, [late], hours_layout="detailed", line_template="{note}")
    (line,) = _lines(invoice.id)
    assert line.quantity == Decimal("0.70")

    # Saved as shown: the quantity stays the linked 0.70 h (not the entry's 1.00 h) and is not edited
    resp = client.post(f"/invoices/{invoice.id}/edit", data=_edit_form(prepaid, invoice, [line]))
    assert resp.status_code == 302
    (line,) = _lines(invoice.id)
    assert (line.quantity, line.quantity_edited) == (Decimal("0.70"), False)

    resp = client.post(
        f"/invoices/{invoice.id}/edit", data=_edit_form(prepaid, invoice, [line], **{"quantity[]": ["1.00"]})
    )
    assert resp.status_code == 302
    (line,) = _lines(invoice.id)
    assert (line.quantity, line.total_amount, line.quantity_edited) == (Decimal("1.00"), Decimal("40.00"), True)


def test_kept_edited_line_keeps_its_prepaid_hours(client, user, prepaid):
    """Plan 0.3 h; an edited line holds a partly prepaid entry; an earlier entry added later does not take its hours."""
    _login(client, user)
    invoice = prepaid["invoice"]
    late = prepaid["entry"](user, prepaid["design"], 12, 1, "Partly prepaid")
    _generate(client, invoice, [late], hours_layout="detailed", line_template="{note}")
    (line,) = _lines(invoice.id)
    resp = client.post(
        f"/invoices/{invoice.id}/edit",
        data=_edit_form(prepaid, invoice, [line], **{"description[]": ["Kept by hand"]}),
    )
    assert resp.status_code == 302
    ledger_before = _ledger(invoice.id)
    assert {(entry_id, seconds) for _id, entry_id, seconds in ledger_before} == {(late.id, 1080)}
    links_before = _link_hours(invoice.id)
    assert links_before == {(late.id, False, Decimal("0.7000"))}

    early = prepaid["entry"](user, prepaid["design"], 2, 1, "Earlier")
    resp = _generate(client, invoice, [early], hours_layout="detailed", line_template="{note}")
    assert resp.status_code == 302

    assert _ledger(invoice.id) == ledger_before
    assert _link_hours(invoice.id) == links_before | {(early.id, False, Decimal("1.0000"))}
    lines = {item.description: item.quantity for item in _lines(invoice.id)}
    assert lines == {"Kept by hand": Decimal("0.70"), "Earlier": Decimal("1.00")}


def test_preview_uses_only_the_entries_the_picker_offers(client, user, layout_setup):
    _login(client, user)
    other_project = ProjectFactory(name="Other Project", client_id=layout_setup["client"].id)
    db.session.commit()
    start = datetime(2026, 10, 9, 9, 0)
    elsewhere = TimeEntryFactory(
        user_id=user.id,
        project_id=other_project.id,
        start_time=start,
        end_time=start + timedelta(hours=1),
        billable=True,
    )
    db.session.commit()
    resp = client.post(
        f"/invoices/{layout_setup['invoice'].id}/hours-layout-preview",
        json={"time_entry_ids": [layout_setup["entries"][0].id, elsewhere.id]},
    )
    assert resp.get_json()["entry_count"] == 1


def test_preview_is_refused_outside_the_users_project_scope(client, scope_restricted_user, layout_setup):
    invoice = InvoiceFactory(
        project_id=layout_setup["project"].id,
        client_id=layout_setup["client"].id,
        client_name=layout_setup["client"].name,
        created_by=scope_restricted_user.id,
    )
    db.session.commit()
    _login(client, scope_restricted_user)
    resp = client.post(
        f"/invoices/{invoice.id}/hours-layout-preview",
        json={"time_entry_ids": [layout_setup["entries"][0].id]},
    )
    assert resp.status_code == 403


def test_rates_set_on_the_rates_page_and_through_the_api_split_lines(client, admin_user):
    """A person's rate from the Rates page and a dated project rate from the API both split lines by rate."""
    from app.models import RateOverride

    cl = ClientFactory(name="Rates Client", default_hourly_rate=None)
    project = ProjectFactory(name="Rates Project", client_id=cl.id, hourly_rate=Decimal("40.00"))
    colleague = UserFactory(username="colleague-rates", full_name="Colleague")
    db.session.flush()
    task = Task(name="Design", project_id=project.id, status="todo", created_by=admin_user.id)
    db.session.add(task)
    db.session.commit()
    _login(client, admin_user)

    # The colleague's rate from the 15th, on the Rates page
    resp = client.post(
        f"/projects/{project.id}/rates/add",
        data={"user_id": str(colleague.id), "hourly_rate": "50.00", "effective_from": "2026-10-15"},
    )
    assert resp.status_code == 302, resp.get_data(as_text=True)[:500]
    # A project rate for the first ten days, through the API
    token, plain = ApiToken.create_token(user_id=admin_user.id, name="Rates", scopes="read:projects,write:projects")
    db.session.add(token)
    db.session.commit()
    resp = client.post(
        f"/api/v1/projects/{project.id}/rate-overrides",
        headers={"Authorization": f"Bearer {plain}"},
        json={"hourly_rate": 45, "effective_from": "2026-10-01", "effective_to": "2026-10-10"},
    )
    assert resp.status_code == 201, resp.get_json()
    assert RateOverride.query.filter_by(project_id=project.id).count() == 2

    def entry(person, day, hours):
        start = datetime(2026, 10, day, 9, 0)
        made = TimeEntryFactory(
            user_id=person.id,
            project_id=project.id,
            task_id=task.id,
            start_time=start,
            end_time=start + timedelta(hours=hours),
            billable=True,
        )
        db.session.commit()
        return made

    entries = [entry(admin_user, 5, 2), entry(admin_user, 20, 1), entry(colleague, 7, 3), entry(colleague, 20, 1)]
    invoice = InvoiceFactory(
        project_id=project.id, client_id=cl.id, client_name=cl.name, created_by=admin_user.id, tax_rate=Decimal("0")
    )
    invoice.currency_code = "EUR"
    db.session.commit()

    resp = _generate(client, invoice, entries, hours_layout="task", line_template="{task}")
    assert resp.status_code == 302
    rows = [(item.description, item.quantity, item.unit_price, item.total_amount) for item in _lines(invoice.id)]
    assert rows == [
        # 1-10 Oct: the dated project rate for both people
        ("Design – 45.00 EUR/h", Decimal("5.00"), Decimal("45.00"), Decimal("225.00")),
        # After the 10th: the project rate, and the colleague's own rate from the 15th
        ("Design – 40.00 EUR/h", Decimal("1.00"), Decimal("40.00"), Decimal("40.00")),
        ("Design – 50.00 EUR/h", Decimal("1.00"), Decimal("50.00"), Decimal("50.00")),
    ]
    by_person = InvoiceFactory(
        project_id=project.id, client_id=cl.id, client_name=cl.name, created_by=admin_user.id, tax_rate=Decimal("0")
    )
    db.session.commit()
    # Same entries in another layout give the same total (the first invoice releases them first)
    db.session.delete(Invoice.query.get(invoice.id))
    db.session.commit()
    resp = _generate(client, by_person, entries, hours_layout="person", line_template="{person}")
    assert resp.status_code == 302
    assert sum(item.total_amount for item in _lines(by_person.id)) == Decimal("315.00")
    assert len(_lines(by_person.id)) == 4
