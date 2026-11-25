"""Step 1 of a new invoice: client, number, period, projects and how hours become lines (/invoices/new)."""

from datetime import date, datetime, timedelta
from decimal import Decimal

import pytest
from factories import ClientFactory, ProjectFactory, TimeEntryFactory, UserFactory
from flask import g

from app import db
from app.models import (
    BillingEntity,
    Invoice,
    InvoiceItem,
    InvoiceTimeLink,
    Project,
    RateOverride,
    Settings,
    Task,
    TimeEntry,
)
from app.services.invoice_step_one_service import resolve_period
from app.services.invoice_time_service import InvoiceTimeService

pytestmark = [pytest.mark.routes]


def _login(client, user):
    with client.session_transaction() as sess:
        sess["_user_id"] = str(user.id)
        sess["_fresh"] = True
    # The test's app context outlives requests: drop the user Flask-Login cached in ``g``
    g.pop("_login_user", None)


LAST = resolve_period("last_month")


@pytest.fixture
def user(admin_user):
    """Invoices are made by someone who sees every project (as on the old create form)."""
    return admin_user


def _day(n, hour=9):
    """Day ``n`` of last month, at ``hour``."""
    return datetime.combine(LAST.start, datetime.min.time()).replace(hour=hour) + timedelta(days=n - 1)


@pytest.fixture
def setup(app, user):
    """A client with two projects and a third without a rate, hours in and around last month."""
    cl = ClientFactory(name="Step One Client", default_hourly_rate=None)
    analytics = ProjectFactory(name="Analytics", client_id=cl.id, hourly_rate=Decimal("40.00"))
    traffic = ProjectFactory(name="Traffic forecasting", client_id=cl.id, hourly_rate=Decimal("50.00"))
    norate = ProjectFactory(name="Zero rate", client_id=cl.id, hourly_rate=None)
    other = ProjectFactory(name="Other client project", hourly_rate=Decimal("10.00"))
    colleague = UserFactory(username="colleague-step1", full_name="Colleague")
    db.session.flush()
    design = Task(name="Design", project_id=analytics.id, status="todo", created_by=user.id)
    db.session.add(design)
    db.session.flush()

    def entry(project, start, hours, person=None, **kw):
        if project is None:
            kw["client_id"] = cl.id
        made = TimeEntryFactory(
            user_id=(person or user).id,
            project_id=project.id if project is not None else None,
            start_time=start,
            end_time=start + timedelta(hours=hours) if hours is not None else None,
            billable=kw.pop("billable", True),
            **kw,
        )
        db.session.commit()
        return made

    e = {
        "a1": entry(analytics, _day(5), 2, task_id=design.id, notes="Wireframes"),
        "a2": entry(analytics, _day(7), 3, colleague, task_id=design.id),
        "t1": entry(traffic, _day(10), 1.5),
        "before": entry(analytics, _day(1) - timedelta(days=40), 2),
        "after": entry(analytics, _day(1) + timedelta(days=40), 1),
        "nonbillable": entry(analytics, _day(12), 0.5, billable=False),
        "outside": entry(analytics, _day(14), 1, paid=True, invoice_number="OLD-1"),
        "running": entry(traffic, _day(15), None),
        "client_direct": entry(None, _day(16), 1),
        "norate": entry(norate, _day(18), 2),
        "other_client": entry(other, _day(18), 2),
    }
    return {
        "client": cl,
        "analytics": analytics,
        "traffic": traffic,
        "norate": norate,
        "entries": e,
        "colleague": colleague,
        "entry": entry,
    }


def _form(setup, **extra):
    data = {
        "client_id": setup["client"].id,
        "period": "last_month",
        "project_ids": [setup["analytics"].id, setup["traffic"].id],
        "projects_touched": "1",
        "hours_layout": "task_person",
        "line_template": "{task} - {person}",
        "currency_code": "EUR",
        "tax_rate": "0",
    }
    data.update(extra)
    return data


def _newest():
    db.session.expire_all()
    return Invoice.query.order_by(Invoice.id.desc()).first()


def _linked_ids(invoice):
    return set(InvoiceTimeService.invoice_entry_ids(invoice))


def _summary(client, **body):
    resp = client.post("/invoices/step-1/summary", json=body)
    assert resp.status_code == 200, resp.get_data(as_text=True)
    return resp.get_json()


# --- the page ------------------------------------------------------------------------------------


def test_old_create_page_redirects_to_step_one_with_its_parameters(client, user, setup):
    _login(client, user)
    resp = client.get(f"/invoices/create?project_id={setup['analytics'].id}")
    assert resp.status_code == 302
    assert resp.headers["Location"].endswith(f"/invoices/new?project_id={setup['analytics'].id}")


def test_page_from_a_project_selects_its_client_and_only_that_project(client, user, setup):
    _login(client, user)
    resp = client.get(f"/invoices/new?project_id={setup['traffic'].id}")
    assert resp.status_code == 200
    html = resp.get_data(as_text=True)
    assert "Who bills whom" in html
    assert f'<option value="{setup["client"].id}" selected>' in html
    assert f'name="project_ids" value="{setup["traffic"].id}" checked' in html
    assert f'name="project_ids" value="{setup["analytics"].id}">' in html
    assert f'id="project_id" value="{setup["traffic"].id}"' in html


def test_page_for_a_client_selects_its_projects_with_hours(client, user, setup):
    _login(client, user)
    html = client.get(f"/invoices/new?client_id={setup['client'].id}").get_data(as_text=True)
    for key in ("analytics", "traffic", "norate"):
        assert f'name="project_ids" value="{setup[key].id}" checked' in html
    assert "5.00 h" in html  # Analytics: 2 h + 3 h last month
    assert 'id="client_entries" name="client_entries" value="1" checked' in html
    assert "Create draft with" in html


def test_new_invoice_buttons_lead_to_step_one(client, admin_user, setup):
    _login(client, admin_user)
    html = client.get(f"/projects/{setup['analytics'].id}/invoices").get_data(as_text=True)
    assert f"/invoices/new?project_id={setup['analytics'].id}" in html


# --- creating the draft --------------------------------------------------------------------------


def test_create_last_month_two_projects(client, user, setup):
    _login(client, user)
    e = setup["entries"]
    resp = client.post("/invoices/new", data=_form(setup))
    assert resp.status_code == 302
    invoice = _newest()
    assert resp.headers["Location"].endswith(f"/invoices/{invoice.id}")
    assert invoice.status == "draft"
    assert invoice.project_id == setup["analytics"].id
    assert invoice.client_id == setup["client"].id
    assert (invoice.period_start, invoice.period_end) == (LAST.start, LAST.end)
    assert invoice.issue_date == LAST.end
    assert invoice.hours_layout == "task_person"
    assert invoice.line_template == "{task} - {person}"
    assert _linked_ids(invoice) == {e["a1"].id, e["a2"].id, e["t1"].id}
    items = sorted(invoice.items.all(), key=lambda i: i.position)
    assert [i.kind for i in items] == ["time"] * len(items)
    assert sum(Decimal(i.total_amount) for i in items) == Decimal("2") * 40 + Decimal("3") * 40 + Decimal("1.5") * 50
    db.session.refresh(setup["analytics"])
    db.session.refresh(setup["traffic"])
    for project in (setup["analytics"], setup["traffic"]):
        assert project.last_hours_layout == "task_person"
        assert project.last_line_template == "{task} - {person}"
    # Running, non-billable, billed outside, other periods, other projects: not on it
    for key in ("before", "after", "nonbillable", "outside", "running", "client_direct", "norate"):
        assert e[key].id not in _linked_ids(invoice), key


def test_create_custom_period_and_client_entries(client, user, setup):
    _login(client, user)
    e = setup["entries"]
    resp = client.post(
        "/invoices/new",
        data=_form(
            setup,
            period="custom",
            period_start=_day(6).date().isoformat(),
            period_end=_day(16).date().isoformat(),
            client_entries="1",
        ),
    )
    assert resp.status_code == 302
    invoice = _newest()
    assert (invoice.period_start, invoice.period_end) == (_day(6).date(), _day(16).date())
    assert invoice.issue_date == _day(16).date()
    assert _linked_ids(invoice) == {e["a2"].id, e["t1"].id, e["client_direct"].id}


def test_create_all_unbilled_takes_the_period_of_its_entries(client, user, setup):
    _login(client, user)
    e = setup["entries"]
    resp = client.post("/invoices/new", data=_form(setup, period="all", project_ids=[setup["analytics"].id]))
    assert resp.status_code == 302
    invoice = _newest()
    assert _linked_ids(invoice) == {e["before"].id, e["a1"].id, e["a2"].id, e["after"].id}
    assert invoice.period_start == e["before"].start_time.date()
    assert invoice.period_end == e["after"].start_time.date()
    assert invoice.issue_date == date.today()


def test_entries_on_another_invoice_are_not_collected(client, user, setup):
    _login(client, user)
    e = setup["entries"]
    first = client.post("/invoices/new", data=_form(setup, project_ids=[setup["analytics"].id]))
    assert first.status_code == 302
    client.post("/invoices/new", data=_form(setup))
    second = _newest()
    assert _linked_ids(second) == {e["t1"].id}


def test_dont_add_any_hours_makes_an_empty_draft(client, user, setup):
    _login(client, user)
    setup["analytics"].last_hours_layout = "person"
    db.session.commit()
    resp = client.post("/invoices/new", data=_form(setup, hours_layout="none"))
    assert resp.status_code == 302
    invoice = _newest()
    assert invoice.items.count() == 0
    assert invoice.hours_layout == "none"
    db.session.refresh(setup["analytics"])
    assert setup["analytics"].last_hours_layout == "person"


def test_header_fields_reach_the_invoice(client, user, setup):
    _login(client, user)
    resp = client.post(
        "/invoices/new",
        data=_form(
            setup,
            client_name="Step One Client GmbH",
            client_email="",
            client_address="Main St 1",
            buyer_reference="PO-77",
            vat_category="AE",
            vat_exemption_reason="Reverse charge",
            vat_exemption_code="VATEX-EU-AE",
            cig="CIG1",
            cup="CUP1",
            tax_rate="19",
            notes="Payment order 123",
            terms="Net 14",
            issue_date=_day(28).date().isoformat(),
            due_date=(_day(28) + timedelta(days=14)).date().isoformat(),
        ),
    )
    assert resp.status_code == 302
    invoice = _newest()
    assert invoice.client_name == "Step One Client GmbH"
    assert invoice.client_email is None
    assert invoice.buyer_reference == "PO-77"
    assert (invoice.vat_category, invoice.vat_exemption_code) == ("AE", "VATEX-EU-AE")
    assert (invoice.cig, invoice.cup) == ("CIG1", "CUP1")
    assert invoice.tax_rate == Decimal("19")
    assert (invoice.notes, invoice.terms) == ("Payment order 123", "Net 14")
    assert invoice.issue_date == _day(28).date()
    assert invoice.due_date == (_day(28) + timedelta(days=14)).date()


def test_due_date_follows_the_clients_last_invoice(client, user, setup):
    _login(client, user)
    client.post("/invoices/new", data=_form(setup, project_ids=[setup["traffic"].id], due_date=""))
    first = _newest()
    assert first.due_date == first.issue_date + timedelta(days=30)
    first.due_date = first.issue_date + timedelta(days=10)
    db.session.commit()
    client.post("/invoices/new", data=_form(setup, project_ids=[setup["analytics"].id], due_date=""))
    second = _newest()
    assert second.due_date == second.issue_date + timedelta(days=10)


def test_no_project_selected_creates_nothing(client, user, setup):
    _login(client, user)
    before = Invoice.query.count()
    resp = client.post("/invoices/new", data=_form(setup, project_ids=[]))
    assert resp.status_code == 400
    assert Invoice.query.count() == before


def test_taken_number_is_an_error_and_nothing_is_created(client, user, setup):
    entity = BillingEntity(short_name="Example", legal_name="EXAMPLE GMBH", number_format="EX-{YYYY}-{MM}")
    db.session.add(entity)
    db.session.commit()
    _login(client, user)
    client.post("/invoices/new", data=_form(setup, billing_entity_id=entity.id, project_ids=[setup["traffic"].id]))
    taken = _newest().invoice_number
    before = Invoice.query.count()
    links = InvoiceTimeLink.query.count()
    resp = client.post(
        "/invoices/new",
        data=_form(setup, billing_entity_id=entity.id, invoice_number=taken, invoice_number_preview="EX-other"),
    )
    assert resp.status_code == 409
    assert Invoice.query.count() == before
    assert InvoiceTimeLink.query.count() == links
    html = resp.get_data(as_text=True)
    assert f"Number already taken by {taken}" in html
    assert "Use next free" in html


def test_modules_off_creation_works(client, user, setup):
    settings = Settings.get_settings()
    settings.disabled_module_ids = ["billing_entities", "client_entities"]
    db.session.commit()
    _login(client, user)
    html = client.get(f"/invoices/new?client_id={setup['client'].id}").get_data(as_text=True)
    assert 'id="billingSellerBlock"' not in html
    assert "From, as printed" in html
    resp = client.post("/invoices/new", data=_form(setup))
    assert resp.status_code == 302
    invoice = _newest()
    assert invoice.billing_entity_id is None and invoice.client_entity_id is None
    assert invoice.items.count() > 0


def test_summary_amount_matches_the_created_draft(client, user, setup):
    """Rates loaded at once for the page give what the lines get: person override with a date."""
    db.session.add(
        RateOverride(
            project_id=setup["analytics"].id,
            user_id=setup["colleague"].id,
            hourly_rate=Decimal("55.00"),
            effective_from=_day(6).date(),
        )
    )
    db.session.commit()
    _login(client, user)
    data = _summary(
        client,
        client_id=setup["client"].id,
        period="last_month",
        project_ids=[setup["analytics"].id, setup["traffic"].id],
        projects_touched="1",
        hours_layout="detailed",
        currency_code="EUR",
    )
    assert "Create draft with 3 lines" in data["html"]["summary"]
    assert "320.00 EUR" in data["html"]["summary"]  # 2 x 40 + 3 x 55 + 1.5 x 50
    client.post("/invoices/new", data=_form(setup, hours_layout="detailed"))
    invoice = _newest()
    assert invoice.items.count() == 3
    assert Decimal(invoice.subtotal) == Decimal("320.00")


# --- warnings ------------------------------------------------------------------------------------


def test_each_warning_on_its_own_data_and_none_blocks(client, user, setup):
    _login(client, user)
    data = _summary(
        client,
        client_id=setup["client"].id,
        period="last_month",
        project_ids=[setup["analytics"].id, setup["traffic"].id, setup["norate"].id],
        projects_touched="1",
        hours_layout="task",
        currency_code="EUR",
    )
    html = data["html"]["warnings"]
    assert "Before you create" in html
    assert 'data-warning="no_rate"' in html and f"/projects/{setup['norate'].id}/rates" in html
    assert 'data-warning="timer_running"' in html
    assert 'data-warning="before_period"' in html
    assert f'data-include-from="{setup["entries"]["before"].start_time.date().isoformat()}"' in html
    assert 'data-warning="other_projects"' in html  # time logged on the client, not selected
    assert 'data-warning="after_period"' in html
    assert 'data-warning="non_billable"' in html
    resp = client.post("/invoices/new", data=_form(setup, project_ids=[setup["norate"].id]))
    assert resp.status_code == 302
    assert _newest().items.first().unit_price == 0


def test_summary_picks_projects_with_hours_until_the_user_chooses(client, user, setup):
    _login(client, user)
    empty = ProjectFactory(name="Empty", client_id=setup["client"].id)
    db.session.commit()
    data = _summary(client, client_id=setup["client"].id, period="last_month", hours_layout="task")
    assert set(data["project_ids"]) == {setup["analytics"].id, setup["traffic"].id, setup["norate"].id}
    assert empty.id not in data["project_ids"]
    assert data["period"]["start"] == LAST.start.isoformat()
    assert data["period"]["issue_date"] == LAST.end.isoformat()
    chosen = _summary(
        client,
        client_id=setup["client"].id,
        period="last_month",
        project_ids=[empty.id],
        projects_touched="1",
        hours_layout="task",
    )
    assert chosen["project_ids"] == [empty.id]
    assert chosen["lines"] == 0


def test_summary_examples_for_each_layout(client, user, setup):
    _login(client, user)
    data = _summary(
        client,
        client_id=setup["client"].id,
        period="last_month",
        project_ids=[setup["analytics"].id],
        projects_touched="1",
        hours_layout="task",
    )
    assert data["examples"]["task"].startswith("Design")
    assert data["examples"]["none"] == "No hours lines"


def test_summary_refuses_a_client_outside_the_users_scope(client, scope_restricted_user, setup):
    _login(client, scope_restricted_user)
    resp = client.post("/invoices/step-1/summary", json={"client_id": setup["client"].id})
    assert resp.status_code == 403
    resp = client.post("/invoices/new", data=_form(setup))
    assert resp.status_code == 400


def test_prepaid_plan_shows_whats_left_and_creation_bills_as_before(client, user, setup):
    cl = setup["client"]
    cl.prepaid_hours_monthly = Decimal("3")
    cl.prepaid_reset_day = 1
    db.session.commit()
    _login(client, user)
    data = _summary(
        client,
        client_id=cl.id,
        period="last_month",
        project_ids=[setup["analytics"].id],
        projects_touched="1",
        hours_layout="task",
    )
    assert "3.00 h per month, resets on the 1st." in data["html"]["hours"]
    assert "3.00 of 3.00 left" in data["html"]["hours"]
    assert 'data-warning="prepaid_left"' in data["html"]["warnings"]
    resp = client.post("/invoices/new", data=_form(setup, project_ids=[setup["analytics"].id], hours_layout="task"))
    assert resp.status_code == 302
    invoice = _newest()
    # 2 h + 1 h of the 3 h entry go to the plan; 2 h are billed; no line for the prepaid hours
    assert sum(Decimal(i.quantity) for i in invoice.items.all()) == Decimal("2.00")
    e = setup["entries"]
    assert _linked_ids(invoice) == {e["a1"].id, e["a2"].id}
    data = _summary(
        client,
        client_id=cl.id,
        period="last_month",
        project_ids=[setup["traffic"].id],
        projects_touched="1",
        hours_layout="task",
    )
    assert "0.00 of 3.00 left" in data["html"]["hours"]
    assert f"plan used up on {invoice.invoice_number}" in data["html"]["warnings"]


# --- step 1 of a draft ---------------------------------------------------------------------------


def _draft(client, setup, **extra):
    resp = client.post("/invoices/new", data=_form(setup, **extra))
    assert resp.status_code == 302
    return _newest()


def _edit_form(invoice, setup, **extra):
    data = _form(setup, **extra)
    data.update(
        {
            "invoice_number": extra.get("invoice_number", invoice.invoice_number),
            "issue_date": extra.get("issue_date", invoice.issue_date.isoformat()),
            "due_date": extra.get("due_date", invoice.due_date.isoformat()),
            "terms": extra.get("terms", invoice.terms or ""),
        }
    )
    return data


def test_step_one_of_a_draft_is_filled_from_the_invoice(client, user, setup):
    _login(client, user)
    invoice = _draft(client, setup, notes="Payment order 9")
    resp = client.get(f"/invoices/{invoice.id}/step-1")
    assert resp.status_code == 200
    html = resp.get_data(as_text=True)
    assert f'value="{invoice.invoice_number}"' in html
    assert "Payment order 9" in html
    assert 'name="period" value="last_month" class="js-period" checked' in html
    assert f'name="project_ids" value="{setup["analytics"].id}" checked' in html
    assert f'name="project_ids" value="{setup["norate"].id}">' in html
    assert 'value="task_person" checked' in html


def test_header_only_change_keeps_lines_and_links(client, user, setup):
    _login(client, user)
    invoice = _draft(client, setup)
    items = {i.id: (i.description, i.quantity) for i in invoice.items.all()}
    links = {(link.time_entry_id, link.invoice_item_id) for link in invoice.time_links.all()}
    resp = client.post(
        f"/invoices/{invoice.id}/step-1",
        data=_edit_form(invoice, setup, notes="New notes", invoice_number="MANUAL-77", tax_rate="7"),
    )
    assert resp.status_code == 302
    invoice = _newest()
    assert invoice.notes == "New notes"
    assert invoice.invoice_number == "MANUAL-77"
    assert invoice.tax_rate == Decimal("7")
    assert {i.id: (i.description, i.quantity) for i in invoice.items.all()} == items
    assert {(link.time_entry_id, link.invoice_item_id) for link in invoice.time_links.all()} == links


def test_period_change_collects_hours_again_and_keeps_manual_lines(client, user, setup):
    _login(client, user)
    e = setup["entries"]
    invoice = _draft(client, setup)
    manual = InvoiceItem(invoice_id=invoice.id, description="CTO support", quantity=4, unit_price=100)
    manual.kind = "manual"
    db.session.add(manual)
    edited = invoice.items.filter_by(kind="time").first()
    edited.description = "Rewritten by hand"
    edited.description_edited = True
    db.session.commit()
    # Marked non-billable on the draft (as G2's Non-billable does)
    InvoiceTimeService().unlink_entry(invoice, e["t1"])
    e["t1"].billable = False
    db.session.commit()

    resp = client.post(f"/invoices/{invoice.id}/step-1", data=_edit_form(invoice, setup, period="all"))
    assert resp.status_code == 302
    invoice = _newest()
    descriptions = [i.description for i in invoice.items.all()]
    assert "CTO support" in descriptions
    assert "Rewritten by hand" not in descriptions  # hours lines are rebuilt
    assert _linked_ids(invoice) == {e["before"].id, e["a1"].id, e["a2"].id, e["after"].id}
    db.session.refresh(e["t1"])
    assert e["t1"].billable is False
    assert invoice.period_start == e["before"].start_time.date()
    assert Decimal(invoice.subtotal) == Decimal("400") + Decimal(8) * 40


def test_project_or_layout_change_collects_hours_again(client, user, setup):
    _login(client, user)
    e = setup["entries"]
    invoice = _draft(client, setup)
    resp = client.post(
        f"/invoices/{invoice.id}/step-1",
        data=_edit_form(invoice, setup, project_ids=[setup["traffic"].id], hours_layout="project", line_template=""),
    )
    assert resp.status_code == 302
    invoice = _newest()
    assert invoice.project_id == setup["traffic"].id
    assert _linked_ids(invoice) == {e["t1"].id}
    assert invoice.hours_layout == "project"
    # The released entries are unbilled again
    unbilled = {x.id for x in InvoiceTimeService().billable_unbilled([setup["analytics"].id])}
    assert {e["a1"].id, e["a2"].id} <= unbilled


def test_step_one_of_a_draft_with_a_taken_number_changes_nothing(client, user, setup):
    _login(client, user)
    first = _draft(client, setup, project_ids=[setup["traffic"].id])
    invoice = _draft(client, setup, project_ids=[setup["analytics"].id])
    resp = client.post(
        f"/invoices/{invoice.id}/step-1",
        data=_edit_form(invoice, setup, invoice_number=first.invoice_number, notes="x", period="all"),
    )
    assert resp.status_code == 409
    assert f"Number already taken by {first.invoice_number}" in resp.get_data(as_text=True)
    db.session.expire_all()
    again = Invoice.query.get(invoice.id)
    assert again.notes is None
    assert again.period_start == LAST.start


def test_step_one_only_for_drafts_and_their_owner(app, client, user, setup):
    _login(client, user)
    invoice = _draft(client, setup)
    invoice.status = "issued"
    db.session.commit()
    resp = client.get(f"/invoices/{invoice.id}/step-1")
    assert resp.status_code == 302 and resp.headers["Location"].endswith(f"/invoices/{invoice.id}")
    resp = client.post("/invoices/step-1/summary", json={"invoice_id": invoice.id})
    assert resp.status_code == 409

    invoice.status = "draft"
    db.session.commit()
    stranger = UserFactory(username="stranger-step1")
    db.session.commit()
    other = app.test_client()
    _login(other, stranger)
    resp = other.get(f"/invoices/{invoice.id}/step-1")
    assert resp.status_code == 302 and resp.headers["Location"].endswith("/invoices")
    assert other.post("/invoices/step-1/summary", json={"invoice_id": invoice.id}).status_code == 403


def test_draft_summary_counts_its_own_hours_as_available(client, user, setup):
    _login(client, user)
    invoice = _draft(client, setup)
    data = _summary(
        client,
        invoice_id=invoice.id,
        period="last_month",
        project_ids=[setup["analytics"].id, setup["traffic"].id],
        hours_layout="task_person",
    )
    assert "6.50 h" in data["html"]["hours"]


def test_old_draft_without_a_period_keeps_its_lines_on_save(client, user, setup):
    """A draft from Generate from Time: step 1 shows the period of its entries and saving keeps the lines."""
    _login(client, user)
    e = setup["entries"]
    invoice = Invoice(
        invoice_number="OLD-DRAFT-1",
        project_id=setup["analytics"].id,
        client_name="Step One Client",
        due_date=date.today() + timedelta(days=30),
        created_by=user.id,
        client_id=setup["client"].id,
    )
    db.session.add(invoice)
    db.session.flush()
    InvoiceTimeService().add_entries(invoice, [e["a1"], e["a2"]], "task", created_by=user.id)
    invoice.calculate_totals()
    db.session.commit()
    items = sorted(i.id for i in invoice.items.all())

    html = client.get(f"/invoices/{invoice.id}/step-1").get_data(as_text=True)
    assert 'name="period" value="custom" class="js-period" checked' in html
    form = {
        "period": "custom",
        "period_start": e["a1"].start_time.date().isoformat(),
        "period_end": e["a2"].start_time.date().isoformat(),
        "project_ids": [setup["analytics"].id],
        "hours_layout": "task",
        "line_template": "{task}",
        "currency_code": invoice.currency_code,
        "tax_rate": "0",
        "invoice_number": invoice.invoice_number,
        "issue_date": invoice.issue_date.isoformat(),
        "due_date": invoice.due_date.isoformat(),
    }
    resp = client.post(f"/invoices/{invoice.id}/step-1", data=form)
    assert resp.status_code == 302
    invoice = Invoice.query.get(invoice.id)
    assert sorted(i.id for i in invoice.items.all()) == items
    assert invoice.period_start == e["a1"].start_time.date()


def test_draft_step_one_lists_lines_added_by_hand_and_removes_marked_ones_on_save(client, user, setup):
    _login(client, user)
    invoice = _draft(client, setup)
    keep = InvoiceItem(invoice_id=invoice.id, description="CTO support", quantity=4, unit_price=100)
    drop = InvoiceItem(invoice_id=invoice.id, description="Hosting", quantity=1, unit_price=30)
    keep.kind = drop.kind = "manual"
    db.session.add_all([keep, drop])
    db.session.commit()
    body = dict(
        invoice_id=invoice.id,
        period="last_month",
        project_ids=[setup["analytics"].id, setup["traffic"].id],
        hours_layout="task_person",
        currency_code="EUR",
    )
    html = _summary(client, **body)["html"]["warnings"]
    assert "Before you save" in html
    assert "2 lines added by hand. Saving step 1 keeps them unless you remove them." in html
    assert "CTO support – 400.00 EUR" in html and f'data-remove-line="{drop.id}"' in html
    summary = _summary(client, **body)["html"]["summary"]
    assert "Amount before tax" in summary
    assert "705.00 EUR" in summary  # 275.00 for hours + 400.00 + 30.00 by hand
    assert "275.00 for hours + 430.00 in lines added by hand" in summary
    marked = _summary(client, remove_line_ids=[drop.id], **body)["html"]
    assert f'name="remove_line_ids" value="{drop.id}"' in marked["warnings"] and "Undo" in marked["warnings"]
    assert "675.00 EUR" in marked["summary"]
    hours = sorted(i.id for i in invoice.items.all() if i.kind == "time")

    resp = client.post(f"/invoices/{invoice.id}/step-1", data=_edit_form(invoice, setup, remove_line_ids=[drop.id]))
    assert resp.status_code == 302
    invoice = _newest()
    assert [i.description for i in invoice.items.all() if i.kind == "manual"] == ["CTO support"]
    assert sorted(i.id for i in invoice.items.all() if i.kind == "time") == hours
    assert Decimal(invoice.subtotal) == Decimal("400") + Decimal("2") * 40 + Decimal("3") * 40 + Decimal("1.5") * 50


def test_new_invoice_has_no_lines_added_by_hand_warning(client, user, setup):
    _login(client, user)
    data = _summary(client, client_id=setup["client"].id, period="last_month", hours_layout="task")
    assert 'data-warning="manual_lines"' not in data["html"]["warnings"]


# --- review: client rate, number by period, scoped users, currency ------------------------------


def test_time_logged_on_the_client_takes_the_clients_rate(client, user, setup):
    setup["client"].default_hourly_rate = Decimal("80.00")
    db.session.commit()
    _login(client, user)
    body = dict(
        client_id=setup["client"].id,
        period="last_month",
        project_ids=[setup["traffic"].id],
        projects_touched="1",
        client_entries="1",
        hours_layout="detailed",
        currency_code="EUR",
    )
    data = _summary(client, **body)
    assert "155.00 EUR" in data["html"]["summary"]  # 1.5 h x 50 + 1 h x 80
    assert 'data-warning="no_rate"' not in data["html"]["warnings"]
    resp = client.post("/invoices/new", data=_form(setup, project_ids=[setup["traffic"].id], client_entries="1"))
    assert resp.status_code == 302
    invoice = _newest()
    assert Decimal(invoice.subtotal) == Decimal("155.00")
    assert Decimal("80.00") in {Decimal(i.unit_price) for i in invoice.items.all()}


def test_time_logged_on_a_client_without_a_rate_links_to_the_client(client, user, setup):
    _login(client, user)
    data = _summary(
        client,
        client_id=setup["client"].id,
        period="last_month",
        project_ids=[setup["traffic"].id],
        projects_touched="1",
        client_entries="1",
        hours_layout="detailed",
    )
    html = data["html"]["warnings"]
    assert "No hourly rate for time logged on the client" in html
    assert f"/clients/{setup['client'].id}/edit" in html


@pytest.fixture
def numbered(setup):
    entity = BillingEntity(short_name="Example", legal_name="EXAMPLE GMBH", number_format="EX-{YYYY}{MM}-{DD}")
    db.session.add(entity)
    db.session.commit()
    return entity


def test_number_takes_the_month_of_last_month(client, user, setup, numbered):
    _login(client, user)
    client.post("/invoices/new", data=_form(setup, billing_entity_id=numbered.id))
    assert _newest().invoice_number == "EX-%s-%s" % (LAST.end.strftime("%Y%m"), LAST.end.strftime("%d"))


def test_number_takes_the_month_of_this_month(client, user, setup, numbered):
    _login(client, user)
    today = date.today()
    data = _summary(client, client_id=setup["client"].id, period="this_month", hours_layout="task", currency_code="EUR")
    assert data["numbers"][str(numbered.id)]["number"] == "EX-%s-%s" % (today.strftime("%Y%m"), today.strftime("%d"))
    client.post("/invoices/new", data=_form(setup, billing_entity_id=numbered.id, period="this_month"))
    assert _newest().invoice_number == "EX-%s-%s" % (today.strftime("%Y%m"), today.strftime("%d"))


def test_number_takes_the_month_of_a_custom_period_and_the_day_of_issue(client, user, setup, numbered):
    _login(client, user)
    form = _form(
        setup,
        billing_entity_id=numbered.id,
        period="custom",
        period_start="2026-03-05",
        period_end="2026-03-20",
        issue_date="2026-04-02",
        due_date="2026-05-02",
    )
    client.post("/invoices/new", data=form)
    assert _newest().invoice_number == "EX-202603-02"
    data = _summary(
        client,
        client_id=setup["client"].id,
        period="custom",
        period_start="2026-03-05",
        period_end="2026-03-20",
        issue_date="2026-04-02",
        hours_layout="task",
    )
    assert data["numbers"][str(numbered.id)]["number"] == "EX-202603-02"
    assert data["numbers"][str(numbered.id)]["taken"]["number"] == "EX-202603-02"


def test_user_limited_to_projects_does_not_see_or_bill_time_on_the_client(app, setup, scope_restricted_user):
    from app.models import UserClient

    db.session.add(UserClient(user_id=scope_restricted_user.id, client_id=setup["client"].id))
    db.session.commit()
    restricted = app.test_client()
    _login(restricted, scope_restricted_user)
    data = _summary(
        restricted,
        client_id=setup["client"].id,
        period="last_month",
        project_ids=[setup["traffic"].id],
        projects_touched="1",
        client_entries="1",
        hours_layout="task",
    )
    assert 'id="client_entries"' not in data["html"]["projects"]
    assert data["client_entries"] is False
    assert "time logged on the client" not in data["html"]["warnings"]
    first = restricted.get(f"/invoices/new?client_id={setup['client'].id}").get_data(as_text=True)
    assert 'id="client_entries"' not in first
    resp = restricted.post("/invoices/new", data=_form(setup, project_ids=[setup["traffic"].id], client_entries="1"))
    assert resp.status_code == 302
    assert _linked_ids(_newest()) == {setup["entries"]["t1"].id}


def test_currency_change_alone_rewrites_the_rate_in_hours_lines(client, user, setup):
    db.session.add(
        RateOverride(project_id=setup["analytics"].id, user_id=setup["colleague"].id, hourly_rate=Decimal("55.00"))
    )
    db.session.commit()
    _login(client, user)
    invoice = _draft(client, setup, project_ids=[setup["analytics"].id], hours_layout="task", line_template="")
    before = {i.id: i.description for i in invoice.items.all()}
    assert all(d.endswith("EUR/h") for d in before.values()), before
    links = {(link.time_entry_id, link.invoice_item_id) for link in invoice.time_links.all()}
    resp = client.post(
        f"/invoices/{invoice.id}/step-1",
        data=_edit_form(
            invoice,
            setup,
            project_ids=[setup["analytics"].id],
            hours_layout="task",
            line_template=invoice.line_template or "",
            currency_code="USD",
        ),
    )
    assert resp.status_code == 302
    invoice = _newest()
    assert invoice.currency_code == "USD"
    after = {i.id: i.description for i in invoice.items.all()}
    assert set(after) == set(before)
    assert all(d.endswith("USD/h") for d in after.values()), after
    assert {(link.time_entry_id, link.invoice_item_id) for link in invoice.time_links.all()} == links


# --- review 2: the draft's amount on step 1, the number of a draft ------------------------------


def _draft_body(invoice, setup, **extra):
    body = dict(
        invoice_id=invoice.id,
        period="last_month",
        project_ids=[setup["analytics"].id, setup["traffic"].id],
        hours_layout="task_person",
        line_template="{task} - {person}",
        currency_code="EUR",
    )
    body.update(extra)
    return body


def _amount(html):
    import re

    return Decimal(re.search(r"data-summary-amount>([\d.]+)", html).group(1))


def test_step_one_amount_is_the_drafts_with_an_edited_quantity(client, user, setup):
    _login(client, user)
    invoice = _draft(client, setup)
    line = invoice.items.filter_by(kind="time").first()
    line.quantity = Decimal(line.quantity) + 8
    line.quantity_edited = True
    line.total_amount = Decimal(line.quantity) * Decimal(line.unit_price)
    invoice.calculate_totals()
    db.session.commit()
    html = _summary(client, **_draft_body(invoice, setup))["html"]["summary"]
    assert _amount(html) == Decimal(invoice.subtotal)
    # Another period: the hours as collected again, the edit is gone
    html = _summary(client, **_draft_body(invoice, setup, period="all"))["html"]["summary"]
    assert _amount(html) == Decimal(8) * 40 + Decimal("1.5") * 50 + Decimal(1) * 50 * 0


def test_step_one_amount_counts_hours_lines_typed_in_and_goods(client, user, setup):
    from app.models import ExtraGood

    _login(client, user)
    invoice = _draft(client, setup)
    typed = InvoiceItem(invoice_id=invoice.id, description="Support hours", quantity=2, unit_price=40)
    typed.kind = "manual_hours"
    db.session.add(typed)
    db.session.add(
        ExtraGood(name="License", unit_price=Decimal("25.00"), quantity=2, invoice_id=invoice.id, created_by=user.id)
    )
    db.session.flush()
    invoice.calculate_totals()
    db.session.commit()
    data = _summary(client, **_draft_body(invoice, setup))["html"]
    assert _amount(data["summary"]) == Decimal(invoice.subtotal) == Decimal("275.00") + 80 + 50
    assert "80.00 in lines added by hand" in data["summary"]
    assert "50.00 in goods" in data["summary"]
    assert "Support hours – 80.00 EUR" in data["warnings"]
    assert f'data-remove-line="{typed.id}"' in data["warnings"]
    marked = _summary(client, remove_line_ids=[typed.id], **_draft_body(invoice, setup))["html"]["summary"]
    assert _amount(marked) == Decimal("325.00")

    resp = client.post(f"/invoices/{invoice.id}/step-1", data=_edit_form(invoice, setup, remove_line_ids=[typed.id]))
    assert resp.status_code == 302
    invoice = _newest()
    assert [i.kind for i in invoice.items.all() if i.kind != "time"] == []
    assert Decimal(invoice.subtotal) == Decimal("325.00")


def test_step_one_amount_applies_the_drafts_discount(client, user, setup):
    _login(client, user)
    invoice = _draft(client, setup)
    invoice.discount_percent = Decimal("10")
    invoice.calculate_totals()
    db.session.commit()
    html = _summary(client, **_draft_body(invoice, setup))["html"]["summary"]
    assert _amount(html) == Decimal(invoice.subtotal) == Decimal("247.50")


def test_taken_number_on_a_drafts_step_one_offers_this_months_next_free(client, user, setup):
    entity = BillingEntity(short_name="Example", legal_name="EXAMPLE GMBH", number_format="EX-{YYYY}{MM}-{SEQ}")
    db.session.add(entity)
    db.session.commit()
    _login(client, user)
    month = date.today().strftime("%Y%m")
    first = _draft(client, setup, billing_entity_id=entity.id, period="this_month", project_ids=[setup["traffic"].id])
    second = _draft(client, setup, billing_entity_id=entity.id, period="this_month")
    assert (first.invoice_number, second.invoice_number) == (f"EX-{month}-1", f"EX-{month}-2")

    form = _edit_form(
        first,
        setup,
        billing_entity_id=entity.id,
        period="this_month",
        project_ids=[setup["traffic"].id],
        invoice_number=second.invoice_number,
    )
    resp = client.post(f"/invoices/{first.id}/step-1", data=form)
    assert resp.status_code == 409
    assert f"Use next free: EX-{month}-3" in resp.get_data(as_text=True)

    form["invoice_number"] = f"EX-{month}-7"
    resp = client.post(f"/invoices/{first.id}/step-1", data=form)
    assert resp.status_code == 302
    db.session.expire_all()
    assert Invoice.query.get(first.id).invoice_number == f"EX-{month}-7"
    assert BillingEntity.query.get(entity.id).number_counter == 7
