"""Expenses and project costs on step 1 and on the draft page.

Step 1 lists the period's expenses and costs ticked, with their status; the draft bills expenses as
their own rows and costs on lines of kind "cost" (by cost, by category or one line).
"""

import re
from datetime import date, datetime, timedelta
from decimal import Decimal

import pytest
from dateutil.relativedelta import relativedelta
from factories import ClientFactory, ExpenseCategoryFactory, ProjectFactory, TimeEntryFactory, UserFactory
from flask import g

from app import db
from app.models import Expense, Invoice, InvoiceItem, ProjectCost, RecurringProjectCost
from app.services.invoice_costs_service import LINE_KIND_COST, InvoiceCostsService
from app.services.invoice_step_one_service import resolve_period

pytestmark = [pytest.mark.routes]

JSON = {"Accept": "application/json", "X-Requested-With": "XMLHttpRequest"}
LAST = resolve_period("last_month")


def _login(client, user):
    with client.session_transaction() as sess:
        sess["_user_id"] = str(user.id)
        sess["_fresh"] = True
    g.pop("_login_user", None)


def _day(n):
    return LAST.start + timedelta(days=n - 1)


@pytest.fixture
def user(admin_user):
    return admin_user


@pytest.fixture
def setup(app, user):
    """Client A: Analytics (40/h) with expenses and costs last month, Traffic, another client's project."""
    cl = ClientFactory(name="Costs Client", default_hourly_rate=None)
    analytics = ProjectFactory(name="Analytics", client_id=cl.id, hourly_rate=Decimal("40.00"))
    traffic = ProjectFactory(name="Traffic", client_id=cl.id, hourly_rate=Decimal("50.00"))
    other = ProjectFactory(name="Other client", hourly_rate=Decimal("10.00"))
    colleague = UserFactory(username="colleague-costs", full_name="Colleague")
    software = ExpenseCategoryFactory(name="Software", code="SW1")
    stock = ExpenseCategoryFactory(name="Stock media", code="ST1")
    db.session.flush()
    start = datetime.combine(_day(3), datetime.min.time()).replace(hour=9)
    TimeEntryFactory(
        user_id=user.id, project_id=analytics.id, start_time=start, end_time=start + timedelta(hours=2), billable=True
    )

    def expense(title, amount, day=5, project=analytics, status="approved", billable=True, person=None, **kw):
        made = Expense(
            user_id=(person or colleague).id,
            title=title,
            category="travel",
            amount=Decimal(amount),
            expense_date=_day(day) if isinstance(day, int) else day,
            project_id=project.id if project else None,
            client_id=project.client_id if project else cl.id,
            billable=billable,
            status=status,
            **kw,
        )
        db.session.add(made)
        db.session.commit()
        return made

    def cost(description, amount, category, day=6, project=analytics, billable=True, recurring=None, **kw):
        made = ProjectCost(
            project_id=project.id,
            user_id=user.id,
            description=description,
            category=None,
            amount=Decimal(amount),
            cost_date=_day(day) if isinstance(day, int) else day,
            billable=billable,
            **kw,
        )
        made.set_category(category)
        if recurring is not None:
            made.recurring_cost_id = recurring.id
        db.session.add(made)
        db.session.commit()
        return made

    recurring = RecurringProjectCost(
        project_id=analytics.id,
        user_id=user.id,
        description="Metabase",
        category="software",
        amount=Decimal("100"),
        frequency="monthly",
        next_run_date=date.today() + timedelta(days=10),
    )
    db.session.add(recurring)
    db.session.commit()

    e = {
        "train": expense("Train", "50"),
        "hotel": expense("Hotel", "120", status="pending"),
        "lunch": expense("Lunch", "30", billable=False),
        "taxi": expense("Taxi", "20", status="rejected"),
        "old": expense("Old trip", "10", day=LAST.start - timedelta(days=20)),
        "other": expense("Other client trip", "70", project=other),
        "traffic": expense("Traffic trip", "15", project=traffic),
    }
    c = {
        "metabase": cost("Metabase", "100", software, recurring=recurring),
        "looker": cost("Looker", "200", software, day=8),
        "photos": cost("Stock photos", "40", stock, day=9),
        "old": cost("Old hosting", "60", software, day=LAST.start - timedelta(days=20)),
        "old_nonbill": cost("Spare cables", "12", stock, day=11, billable=False),
    }
    return {
        "client": cl,
        "analytics": analytics,
        "traffic": traffic,
        "other": other,
        "software": software,
        "stock": stock,
        "colleague": colleague,
        "recurring": recurring,
        "expenses": e,
        "costs": c,
        "expense": expense,
        "cost": cost,
    }


def _form(setup, *, projects=("analytics",), expenses=None, costs=None, layout="cost", **extra):
    """Step 1 as posted; ``expenses`` / ``costs``: names ticked (None: the page posted none)."""
    data = {
        "client_id": setup["client"].id,
        "period": "last_month",
        "project_ids": [setup[p].id for p in projects],
        "projects_touched": "1",
        "hours_layout": "task",
        "line_template": "{task}",
        "currency_code": "EUR",
        "tax_rate": "0",
        "costs_layout": layout,
    }
    if expenses is not None or costs is not None:
        data["expenses_costs_shown"] = "1"
        period = resolve_period(data["period"], data.get("period_start"), data.get("period_end"))
        data["expenses_costs_scope"] = "%s|%s|%s|" % (
            period.start.isoformat() if period.start else "",
            period.end.isoformat() if period.end else "",
            ",".join(str(pid) for pid in sorted(data["project_ids"])),
        )
        data["expense_seen"] = [x.id for x in setup["expenses"].values()]
        data["expense_ids"] = [setup["expenses"][n].id for n in (expenses or ())]
        data["cost_seen"] = [x.id for x in setup["costs"].values()]
        data["cost_ids"] = [setup["costs"][n].id for n in (costs or ())]
    data.update(extra)
    return data


def _create(client, setup, **kw):
    resp = client.post("/invoices/new", data=_form(setup, **kw))
    assert resp.status_code == 302, resp.get_data(as_text=True)[:2000]
    db.session.expire_all()
    return Invoice.query.order_by(Invoice.id.desc()).first()


def _summary(client, body):
    resp = client.post("/invoices/step-1/summary", json=body)
    assert resp.status_code == 200, resp.get_data(as_text=True)[:2000]
    return resp.get_json()


def _body(setup, **kw):
    data = _form(setup, **kw)
    return {k: v for k, v in data.items() if k not in ("tax_rate",)}


def _amount(html):
    return Decimal(re.search(r"data-summary-amount>([\d.]+)", html).group(1))


def _ticked(html, name, item):
    """Whether the step 1 checkbox ``name`` for ``item`` is listed and ticked (None: not listed)."""
    match = re.search(rf'<input type="checkbox"[^>]*name="{name}" value="{item.id}"[^>]*>', html)
    return None if match is None else " checked" in match.group(0)


def _cost_lines(invoice):
    db.session.expire_all()
    return InvoiceCostsService.cost_lines(Invoice.query.get(invoice.id))


def _reload(obj):
    db.session.expire_all()
    return db.session.get(type(obj), obj.id)


# --- step 1 -------------------------------------------------------------------------------------


def test_step_one_lists_the_periods_expenses_and_costs_ticked_with_their_status(client, user, setup):
    _login(client, user)
    html = client.get(f"/invoices/new?client_id={setup['client'].id}").get_data(as_text=True)
    exp, costs = setup["expenses"], setup["costs"]
    for name in ("train", "hotel"):
        assert _ticked(html, "expense_ids", exp[name]) is True
    # Was non-billable: listed, not ticked
    assert _ticked(html, "expense_ids", exp["lunch"]) is False
    # Rejected, outside the period, another client's, a project not selected (no hours): not listed
    for name in ("taxi", "old", "other", "traffic"):
        assert f'data-expense-id="{exp[name].id}"' not in html
    for name in ("metabase", "looker", "photos"):
        assert _ticked(html, "cost_ids", costs[name]) is True
    assert _ticked(html, "cost_ids", costs["old_nonbill"]) is False
    assert f'data-cost-id="{costs["old"].id}"' not in html
    assert "waiting for approval" in html
    assert "was non-billable" in html
    assert "recurring · fixed" in html
    assert "logged" in html
    # Before you create: the pending expense with Approve; a non-billable one only once it is ticked
    assert 'data-warning="expenses_pending"' in html
    assert f'data-approve-expense="{exp["hotel"].id}"' in html
    assert 'data-warning="was_non_billable"' not in html
    ticked = _summary(client, _body(setup, expenses=("train", "lunch"), costs=("looker",)))["html"]
    assert 'data-warning="was_non_billable"' in ticked["warnings"] and "Lunch" in ticked["warnings"]


def test_projects_not_selected_leave_their_expenses_and_costs_out(client, user, setup):
    _login(client, user)
    traffic_cost = setup["cost"]("Traffic API", "25", setup["software"], project=setup["traffic"])
    data = _summary(client, _body(setup, projects=("analytics",)))
    assert f'data-expense-id="{setup["expenses"]["traffic"].id}"' not in data["html"]["expenses"]
    assert f'data-cost-id="{traffic_cost.id}"' not in data["html"]["costs"]
    data = _summary(client, _body(setup, projects=("analytics", "traffic")))
    assert f'data-expense-id="{setup["expenses"]["traffic"].id}"' in data["html"]["expenses"]
    assert f'data-cost-id="{traffic_cost.id}"' in data["html"]["costs"]


def test_created_draft_bills_what_is_ticked_and_the_rest_stays_unbilled(client, user, setup):
    _login(client, user)
    exp, costs = setup["expenses"], setup["costs"]
    invoice = _create(client, setup, expenses=("train", "hotel", "lunch"), costs=("metabase", "looker", "old_nonbill"))
    assert {e.id for e in invoice.expenses.all()} == {exp["train"].id, exp["hotel"].id, exp["lunch"].id}
    assert _reload(exp["traffic"]).invoice_id is None
    # Unticked: left as it is
    photos = _reload(costs["photos"])
    assert (photos.invoice_id, photos.invoiced) == (None, False)
    lines = _cost_lines(invoice)
    assert [line.description for line in lines] == [
        "Metabase (Software)",
        "Looker (Software)",
        "Spare cables (Stock media)",
    ]
    for line in lines:
        assert line.kind == LINE_KIND_COST
        billed = ProjectCost.query.filter_by(invoice_item_id=line.id).all()
        assert len(billed) == 1 and Decimal(line.unit_price) == Decimal(billed[0].amount)
        assert billed[0].invoice_id == invoice.id and billed[0].invoiced
    # The billable flag is not touched: a non-billable one is billed with it as it was
    assert _reload(exp["lunch"]).billable is False
    assert Decimal(invoice.subtotal) == Decimal("80") + 50 + 120 + 30 + 100 + 200 + 12


@pytest.mark.parametrize("layout,lines", [("cost", 3), ("category", 2), ("one_line", 1)])
def test_step_one_total_is_the_drafts_in_every_layout(client, user, setup, layout, lines):
    _login(client, user)
    ticked = dict(expenses=("train", "hotel"), costs=("metabase", "looker", "photos"), layout=layout)
    html = _summary(client, _body(setup, **ticked))["html"]["summary"]
    invoice = _create(client, setup, **ticked)
    assert _amount(html) == Decimal(invoice.subtotal) == Decimal("80") + 170 + 340
    cost_lines = _cost_lines(invoice)
    assert len(cost_lines) == lines
    assert sum(Decimal(line.total_amount) for line in cost_lines) == Decimal("340")
    assert invoice.costs_layout == layout
    if layout == "category":
        assert [line.description for line in cost_lines] == ["Software", "Stock media"]
    if layout == "one_line":
        assert cost_lines[0].description == "Project costs"


def test_without_the_blocks_posted_everything_billable_of_the_period_is_billed(client, user, setup):
    _login(client, user)
    invoice = _create(client, setup)
    # Train and Hotel (pending counts); Lunch was non-billable, Traffic's project is not selected
    assert {e.title for e in invoice.expenses.all()} == {"Train", "Hotel"}
    assert {c.description for c in ProjectCost.query.filter_by(invoice_id=invoice.id).all()} == {
        "Metabase",
        "Looker",
        "Stock photos",
    }
    assert _reload(setup["expenses"]["lunch"]).invoice_id is None


def test_step_one_does_not_count_costs_twice_or_as_lines_added_by_hand(client, user, setup):
    _login(client, user)
    invoice = _create(client, setup, expenses=("train",), costs=("looker",))
    body = _body(setup, expenses=("train",), costs=("looker",))
    body["invoice_id"] = invoice.id
    data = _summary(client, body)
    assert _amount(data["html"]["summary"]) == Decimal(invoice.subtotal) == Decimal("80") + 50 + 200
    assert "lines added by hand" not in data["html"]["summary"]
    assert 'data-warning="manual_lines"' not in data["html"]["warnings"]


def test_approve_from_step_one(client, user, setup):
    _login(client, user)
    hotel = setup["expenses"]["hotel"]
    resp = client.post(f"/invoices/expenses/{hotel.id}/approve", headers=JSON)
    assert resp.status_code == 200 and resp.get_json()["success"]
    assert _reload(hotel).status == "approved"
    # Not pending any more: refused
    assert client.post(f"/invoices/expenses/{hotel.id}/approve", headers=JSON).status_code == 400


def test_approve_needs_the_right_to_approve(client, app, setup):
    plain = UserFactory(username="plain-costs", role="user")
    db.session.commit()
    _login(client, plain)
    hotel = setup["expenses"]["hotel"]
    assert client.post(f"/invoices/expenses/{hotel.id}/approve", headers=JSON).status_code == 403
    assert _reload(hotel).status == "pending"


# --- step 1 of a draft --------------------------------------------------------------------------


def _edit(client, invoice, setup, **kw):
    data = _form(setup, **kw)
    data.update(
        {
            "invoice_number": invoice.invoice_number,
            "issue_date": invoice.issue_date.isoformat(),
            "due_date": invoice.due_date.isoformat(),
        }
    )
    resp = client.post(f"/invoices/{invoice.id}/step-1", data=data)
    assert resp.status_code == 302, resp.get_data(as_text=True)[:2000]
    db.session.expire_all()
    return Invoice.query.get(invoice.id)


def test_saving_step_one_with_only_the_header_changed_leaves_expenses_and_costs(client, user, setup):
    _login(client, user)
    invoice = _create(client, setup, expenses=("train",), costs=("looker", "metabase"))
    line = _cost_lines(invoice)[0]
    InvoiceCostsService().times.update_line(invoice, line, {"unit_price": "150"})
    db.session.commit()
    before = [(item.id, Decimal(item.unit_price)) for item in _cost_lines(invoice)]
    # No blocks posted (nothing ticked or unticked): what the draft bills is kept as it is
    invoice = _edit(client, invoice, setup, notes="New notes")
    assert invoice.notes == "New notes"
    assert [e.id for e in invoice.expenses.all()] == [setup["expenses"]["train"].id]
    assert [(item.id, Decimal(item.unit_price)) for item in _cost_lines(invoice)] == before
    # The same with the blocks posted as the page shows them
    invoice = _edit(client, invoice, setup, expenses=("train",), costs=("looker", "metabase"), notes="Again")
    assert [(item.id, Decimal(item.unit_price)) for item in _cost_lines(invoice)] == before


def test_another_period_collects_expenses_and_costs_again(client, user, setup):
    _login(client, user)
    invoice = _create(client, setup, expenses=("train",), costs=("looker",))
    # This month: last month's expenses and costs are let go, this month's are billed
    this_month = date.today().replace(day=1)
    fresh_expense = setup["expense"]("Fresh trip", "11", day=this_month)
    fresh_cost = setup["cost"]("Fresh tool", "22", setup["software"], day=this_month)
    invoice = _edit(client, invoice, setup, period="this_month")
    assert [e.id for e in invoice.expenses.all()] == [fresh_expense.id]
    assert _reload(setup["expenses"]["train"]).invoice_id is None
    assert _reload(setup["costs"]["looker"]).invoice_id is None
    lines = _cost_lines(invoice)
    assert [ProjectCost.query.filter_by(invoice_item_id=line.id).one().id for line in lines] == [fresh_cost.id]


def test_draft_step_one_lists_other_period_items_unticked_until_the_period_changes(client, user, setup):
    _login(client, user)
    invoice = _create(client, setup, expenses=("train",), costs=("looker",))
    body = _body(setup)
    body["invoice_id"] = invoice.id
    html = _summary(client, body)["html"]
    assert _ticked(html["expenses"], "expense_ids", setup["expenses"]["train"]) is True
    assert _ticked(html["expenses"], "expense_ids", setup["expenses"]["hotel"]) is False
    assert _ticked(html["costs"], "cost_ids", setup["costs"]["looker"]) is True
    assert _ticked(html["costs"], "cost_ids", setup["costs"]["photos"]) is False
    # Another period: everything of it comes ticked
    body["period"] = "custom"
    body["period_start"] = LAST.start.isoformat()
    body["period_end"] = (LAST.end - timedelta(days=1)).isoformat()
    html = _summary(client, body)["html"]
    assert _ticked(html["expenses"], "expense_ids", setup["expenses"]["hotel"]) is True
    assert _ticked(html["costs"], "cost_ids", setup["costs"]["photos"]) is True


def test_ticks_posted_for_another_period_do_not_count(client, user, setup):
    _login(client, user)
    body = _body(setup, expenses=("train",), costs=("looker",))
    assert _ticked(_summary(client, body)["html"]["expenses"], "expense_ids", setup["expenses"]["hotel"]) is False
    # The page changed the period: what was unticked for last month does not carry over
    body.update(
        period="custom", period_start=LAST.start.isoformat(), period_end=(LAST.end - timedelta(days=1)).isoformat()
    )
    html = _summary(client, body)["html"]
    assert _ticked(html["expenses"], "expense_ids", setup["expenses"]["hotel"]) is True
    assert _ticked(html["costs"], "cost_ids", setup["costs"]["photos"]) is True
    # A non-billable one stays unticked there too
    assert _ticked(html["expenses"], "expense_ids", setup["expenses"]["lunch"]) is False


def test_unticking_on_a_drafts_step_one_lets_go(client, user, setup):
    _login(client, user)
    invoice = _create(client, setup, expenses=("train", "hotel"), costs=("looker", "photos"))
    invoice = _edit(client, invoice, setup, expenses=("train",), costs=("looker",), layout="cost")
    assert [e.id for e in invoice.expenses.all()] == [setup["expenses"]["train"].id]
    assert _reload(setup["costs"]["photos"]).invoice_id is None
    assert len(_cost_lines(invoice)) == 1


# --- the draft page -----------------------------------------------------------------------------


def test_draft_page_shows_expenses_and_cost_lines(client, user, setup):
    _login(client, user)
    exp, costs = setup["expenses"], setup["costs"]
    invoice = _create(client, setup, expenses=("train", "hotel", "lunch"), costs=("metabase", "looker"))
    html = client.get(f"/invoices/{invoice.id}").get_data(as_text=True)
    assert 'id="expenses"' in html and 'id="costs"' in html
    assert f'id="expense-{exp["hotel"].id}"' in html
    assert f'/invoices/{invoice.id}/expenses/{exp["train"].id}/remove' in html
    assert f'data-approve-expense="{exp["hotel"].id}"' in html
    assert "Add receipt" in html
    for line in _cost_lines(invoice):
        assert f'id="line-{line.id}"' in html
        assert f'id="costs-{line.id}"' in html
    assert f'/invoices/{invoice.id}/costs/{costs["looker"].id}/remove' in html
    assert "Add bill" in html
    assert 'data-warning="expense-pending"' in html
    assert 'data-warning="was-non-billable"' in html
    assert 'data-total-block="expenses"' in html and 'data-total-block="costs"' in html
    # Other items no longer lists expenses or cost lines
    other = html.split('id="other-items"', 1)[1]
    assert "Looker (Software)" not in other


def test_x_on_an_expense_takes_it_off_and_the_total_follows(client, user, setup):
    _login(client, user)
    invoice = _create(client, setup, expenses=("train", "lunch"), costs=())
    lunch = setup["expenses"]["lunch"]
    resp = client.post(f"/invoices/{invoice.id}/expenses/{lunch.id}/remove", headers=JSON)
    assert resp.status_code == 200 and resp.get_json()["success"]
    lunch = _reload(lunch)
    assert (lunch.invoice_id, lunch.invoiced, lunch.billable) == (None, False, False)
    assert Decimal(_reload(invoice).subtotal) == Decimal("80") + 50


def test_x_on_a_cost_recalculates_its_line_and_drops_an_empty_one(client, user, setup):
    _login(client, user)
    costs = setup["costs"]
    invoice = _create(client, setup, expenses=(), costs=("metabase", "looker", "photos"), layout="category")
    software = _cost_lines(invoice)[0]
    assert Decimal(software.unit_price) == Decimal("300")
    client.post(f"/invoices/{invoice.id}/costs/{costs['metabase'].id}/remove", headers=JSON)
    software = _reload(software)
    assert (Decimal(software.unit_price), software.description) == (Decimal("200"), "Software")
    assert _reload(costs["metabase"]).invoice_item_id is None
    client.post(f"/invoices/{invoice.id}/costs/{costs['photos'].id}/remove", headers=JSON)
    assert [line.id for line in _cost_lines(invoice)] == [software.id]
    assert Decimal(_reload(invoice).subtotal) == Decimal("80") + 200


def test_deleting_a_cost_line_lets_go_of_its_costs(client, user, setup):
    _login(client, user)
    invoice = _create(client, setup, expenses=(), costs=("metabase", "looker"), layout="one_line")
    line = _cost_lines(invoice)[0]
    resp = client.post(f"/invoices/{invoice.id}/lines/{line.id}/delete", headers=JSON)
    assert resp.status_code == 200
    for name in ("metabase", "looker"):
        cost = _reload(setup["costs"][name])
        assert (cost.invoice_id, cost.invoice_item_id, cost.invoiced) == (None, None, False)


def test_approve_on_the_draft(client, user, setup):
    _login(client, user)
    invoice = _create(client, setup, expenses=("hotel",), costs=())
    hotel = setup["expenses"]["hotel"]
    resp = client.post(f"/invoices/expenses/{hotel.id}/approve", data={"invoice_id": invoice.id}, headers=JSON)
    assert resp.status_code == 200
    assert _reload(hotel).status == "approved"
    html = client.get(f"/invoices/{invoice.id}").get_data(as_text=True)
    assert 'data-warning="expense-pending"' not in html


def test_log_an_expense_by_an_approver_is_approved_and_billed(client, user, setup):
    _login(client, user)
    invoice = _create(client, setup, expenses=(), costs=())
    resp = client.post(
        f"/invoices/{invoice.id}/expenses",
        data={
            "expense_date": _day(12).isoformat(),
            "title": "Parking",
            "category": "travel",
            "amount": "30",
            "user_id": setup["colleague"].id,
            "reimbursable": "1",
        },
        headers=JSON,
    )
    assert resp.status_code == 200, resp.get_data(as_text=True)
    expense = Expense.query.filter_by(title="Parking").one()
    assert (expense.status, expense.invoice_id, expense.user_id) == ("approved", invoice.id, setup["colleague"].id)
    assert (expense.currency_code, expense.billable, expense.reimbursable) == ("EUR", True, True)
    assert Decimal(_reload(invoice).subtotal) == Decimal("80") + 30


def test_log_an_expense_outside_the_period_is_refused(client, user, setup):
    _login(client, user)
    invoice = _create(client, setup, expenses=(), costs=())
    resp = client.post(
        f"/invoices/{invoice.id}/expenses",
        data={
            "expense_date": (LAST.end + timedelta(days=3)).isoformat(),
            "title": "Late",
            "category": "travel",
            "amount": "5",
        },
        headers=JSON,
    )
    assert resp.status_code == 400
    assert Expense.query.filter_by(title="Late").first() is None


def test_log_an_expense_without_the_right_to_approve_is_pending(client, app, setup):
    owner = UserFactory(username="owner-costs", role="user")
    db.session.commit()
    _login(client, owner)
    invoice = Invoice(
        invoice_number="INV-COSTS-OWNER",
        project_id=setup["analytics"].id,
        client_name=setup["client"].name,
        due_date=date.today() + timedelta(days=30),
        created_by=owner.id,
        client_id=setup["client"].id,
    )
    invoice.period_start, invoice.period_end = LAST.start, LAST.end
    db.session.add(invoice)
    db.session.commit()
    resp = client.post(
        f"/invoices/{invoice.id}/expenses",
        data={"expense_date": _day(12).isoformat(), "title": "Courier", "category": "services", "amount": "30"},
        headers=JSON,
    )
    assert resp.status_code == 200, resp.get_data(as_text=True)
    expense = Expense.query.filter_by(title="Courier").one()
    assert (expense.status, expense.invoice_id) == ("pending", invoice.id)


def test_log_a_cost_that_repeats_every_month(client, user, setup):
    _login(client, user)
    invoice = _create(client, setup, expenses=(), costs=())
    resp = client.post(
        f"/invoices/{invoice.id}/costs",
        data={
            "cost_date": _day(20).isoformat(),
            "description": "Hosting",
            "category_id": setup["software"].id,
            "amount": "45",
            "repeat": "monthly",
        },
        headers=JSON,
    )
    assert resp.status_code == 200, resp.get_data(as_text=True)
    cost = ProjectCost.query.filter_by(description="Hosting").one()
    recurring = RecurringProjectCost.query.get(cost.recurring_cost_id)
    assert (recurring.frequency, Decimal(recurring.amount), recurring.category_id) == (
        "monthly",
        Decimal("45"),
        setup["software"].id,
    )
    assert recurring.project_id == setup["analytics"].id
    assert recurring.next_run_date == _day(20) + relativedelta(months=1)
    line = InvoiceItem.query.get(cost.invoice_item_id)
    assert (line.kind, line.description, Decimal(line.unit_price)) == (
        LINE_KIND_COST,
        "Hosting (Software)",
        Decimal("45"),
    )
    # Once: no recurring cost
    client.post(
        f"/invoices/{invoice.id}/costs",
        data={
            "cost_date": _day(21).isoformat(),
            "description": "Domain",
            "category_id": setup["software"].id,
            "amount": "9",
        },
        headers=JSON,
    )
    assert ProjectCost.query.filter_by(description="Domain").one().recurring_cost_id is None


@pytest.mark.parametrize("choice", ["keep", "rebuild"])
def test_regroup_costs_keeps_or_rebuilds_a_line_with_an_edited_price(client, user, setup, choice):
    _login(client, user)
    invoice = _create(client, setup, expenses=(), costs=("metabase", "looker", "photos"), layout="cost")
    edited = _cost_lines(invoice)[1]  # Looker
    resp = client.post(f"/invoices/{invoice.id}/lines/{edited.id}", data={"unit_price": "180"}, headers=JSON)
    assert resp.status_code == 200
    assert _reload(edited).price_edited
    html = client.get(f"/invoices/{invoice.id}").get_data(as_text=True)
    assert 'id="keepEditedCosts"' in html

    resp = client.post(
        f"/invoices/{invoice.id}/costs/regroup", data={"costs_layout": "one_line", "keep_edited": choice}, headers=JSON
    )
    assert resp.status_code == 200
    lines = _cost_lines(invoice)
    if choice == "keep":
        assert len(lines) == 2
        assert any(line.id == edited.id and Decimal(line.unit_price) == Decimal("180") for line in lines)
        assert Decimal(_reload(invoice).subtotal) == Decimal("80") + 180 + 140
    else:
        assert len(lines) == 1 and Decimal(lines[0].unit_price) == Decimal("340")
        assert Decimal(_reload(invoice).subtotal) == Decimal("80") + 340
    assert _reload(invoice).costs_layout == "one_line"


def test_receipts_are_uploaded_and_viewed_from_the_invoice(client, user, setup, app, tmp_path):
    import io

    app.config["UPLOAD_FOLDER"] = str(tmp_path)
    _login(client, user)
    invoice = _create(client, setup, expenses=("train",), costs=("looker",))
    train = setup["expenses"]["train"]
    resp = client.post(
        f"/invoices/{invoice.id}/expenses/{train.id}/receipt",
        data={"receipt_file": (io.BytesIO(b"%PDF-1.4 receipt"), "train.pdf")},
        content_type="multipart/form-data",
        headers=JSON,
    )
    assert resp.status_code == 200, resp.get_data(as_text=True)
    assert _reload(train).receipt_path.startswith("uploads/receipts/")
    view = client.get(f"/invoices/{invoice.id}/expenses/{train.id}/receipt")
    assert view.status_code == 200 and view.data.startswith(b"%PDF")
    looker = setup["costs"]["looker"]
    resp = client.post(
        f"/invoices/{invoice.id}/costs/{looker.id}/bill",
        data={"receipt_file": (io.BytesIO(b"\x89PNG bill"), "bill.png")},
        content_type="multipart/form-data",
        headers=JSON,
    )
    assert resp.status_code == 200
    assert client.get(f"/invoices/{invoice.id}/costs/{looker.id}/bill").status_code == 200
    # A file type the expense form does not take is refused
    resp = client.post(
        f"/invoices/{invoice.id}/expenses/{train.id}/receipt",
        data={"receipt_file": (io.BytesIO(b"x"), "script.exe")},
        content_type="multipart/form-data",
        headers=JSON,
    )
    assert resp.status_code == 400


# --- other ways in and out ----------------------------------------------------------------------


def test_deleting_the_draft_lets_go_of_expenses_and_costs(client, user, setup):
    _login(client, user)
    invoice = _create(client, setup, expenses=("train",), costs=("looker",))
    resp = client.post(f"/invoices/{invoice.id}/delete")
    assert resp.status_code == 302
    looker = _reload(setup["costs"]["looker"])
    assert (looker.invoice_id, looker.invoice_item_id, looker.invoiced) == (None, None, False)
    assert _reload(setup["expenses"]["train"]).invoice_id is None


def _issue(client, invoice):
    resp = client.post(f"/invoices/{invoice.id}/status", data={"new_status": "issued"})
    assert resp.status_code in (200, 302)
    db.session.expire_all()
    assert Invoice.query.get(invoice.id).status == "issued"


def test_cancel_lets_go_and_reissue_moves_costs_to_the_copy_of_their_line(client, user, setup):
    from app.services.invoice_correction_service import InvoiceCorrectionService

    _login(client, user)
    invoice = _create(client, setup, expenses=("train",), costs=("metabase", "looker", "photos"), layout="category")
    _issue(client, invoice)
    invoice = Invoice.query.get(invoice.id)
    draft = InvoiceCorrectionService().reissue(invoice, "Wrong amount", user.id)
    db.session.commit()
    lines = _cost_lines(draft)
    assert [(line.description, Decimal(line.unit_price)) for line in lines] == [
        ("Software", Decimal("300.00")),
        ("Stock media", Decimal("40.00")),
    ]
    for line in lines:
        for cost in ProjectCost.query.filter_by(invoice_item_id=line.id).all():
            assert cost.invoice_id == draft.id
    assert ProjectCost.query.filter_by(invoice_id=invoice.id).count() == 0
    assert _reload(setup["expenses"]["train"]).invoice_id == draft.id

    # Cancel the new draft's issued copy: everything is let go
    _issue(client, draft)
    InvoiceCorrectionService().cancel(Invoice.query.get(draft.id), "Not needed", user.id)
    db.session.commit()
    for name in ("metabase", "looker", "photos"):
        cost = _reload(setup["costs"][name])
        assert (cost.invoice_id, cost.invoice_item_id, cost.invoiced) == (None, None, False)


def test_edit_all_fields_keeps_cost_lines_and_lets_go_of_a_removed_one(client, user, setup):
    _login(client, user)
    invoice = _create(client, setup, expenses=(), costs=("metabase", "looker"), layout="cost")
    keep, drop = _cost_lines(invoice)
    time_line = invoice.items.filter_by(kind="time").first()
    rows = [time_line, keep]
    data = {
        "client_name": invoice.client_name,
        "due_date": invoice.due_date.isoformat(),
        "tax_rate": "0",
        "item_id[]": [r.id for r in rows],
        "description[]": [r.description for r in rows],
        "quantity[]": [str(r.quantity) for r in rows],
        "unit_price[]": [str(r.unit_price) for r in rows[:1]] + ["95"],
        "item_time_entry_ids[]": [time_line.time_entry_ids or "", ""],
    }
    resp = client.post(f"/invoices/{invoice.id}/edit", data=data)
    assert resp.status_code == 302, resp.get_data(as_text=True)[:2000]
    lines = _cost_lines(invoice)
    assert len(lines) == 1 and lines[0].price_edited
    kept_cost = ProjectCost.query.filter_by(invoice_item_id=lines[0].id).one()
    assert kept_cost.id == setup["costs"]["metabase"].id
    dropped = _reload(setup["costs"]["looker"])
    assert (dropped.invoice_id, dropped.invoice_item_id, dropped.invoiced) == (None, None, False)


def test_api_put_items_keeps_cost_lines_by_id_and_lets_go_of_the_others(app, client, user, setup):
    from app.services import InvoiceService

    _login(client, user)
    invoice = _create(client, setup, expenses=(), costs=("metabase", "looker"), layout="cost")
    keep, drop = _cost_lines(invoice)
    result = InvoiceService().set_invoice_items(
        invoice.id,
        user.id,
        [{"id": keep.id, "description": keep.description, "quantity": 1, "unit_price": str(keep.unit_price)}],
        is_admin=True,
    )
    assert result["success"], result
    lines = _cost_lines(invoice)
    assert len(lines) == 1 and not lines[0].price_edited
    assert ProjectCost.query.filter_by(invoice_item_id=lines[0].id).one().id == setup["costs"]["metabase"].id
    assert _reload(setup["costs"]["looker"]).invoice_id is None


def test_generate_from_time_makes_cost_lines(client, user, setup):
    _login(client, user)
    invoice = _create(client, setup, expenses=(), costs=())
    looker = setup["costs"]["looker"]
    resp = client.post(f"/invoices/{invoice.id}/generate-from-time", data={"project_costs[]": [looker.id]})
    assert resp.status_code == 302
    looker = _reload(looker)
    line = InvoiceItem.query.get(looker.invoice_item_id)
    assert (line.kind, line.invoice_id, line.description) == (LINE_KIND_COST, invoice.id, "Looker (Software)")


def test_recurring_cost_generator_links_the_cost_to_its_recurring_cost(app, setup):
    from app.services.recurring_project_cost_service import RecurringProjectCostService

    recurring = setup["recurring"]
    recurring.next_run_date = date.today()
    db.session.commit()
    cost = RecurringProjectCostService().generate_cost(recurring)
    db.session.commit()
    assert cost.recurring_cost_id == recurring.id


# --- review fixes -------------------------------------------------------------------------------


def _second_draft(setup, user, number="INV-COSTS-B"):
    invoice = Invoice(
        invoice_number=number,
        project_id=setup["analytics"].id,
        client_name=setup["client"].name,
        due_date=date.today() + timedelta(days=30),
        created_by=user.id,
        client_id=setup["client"].id,
    )
    invoice.period_start, invoice.period_end = LAST.start, LAST.end
    db.session.add(invoice)
    db.session.commit()
    return invoice


def test_generate_from_time_takes_only_what_this_invoice_may_bill(client, user, setup):
    _login(client, user)
    first = _create(client, setup, expenses=("train",), costs=("looker",))
    second = _second_draft(setup, user)
    looker, train = setup["costs"]["looker"], setup["expenses"]["train"]
    other_client = setup["expenses"]["other"]
    photos = setup["costs"]["photos"]
    resp = client.post(
        f"/invoices/{second.id}/generate-from-time",
        data={
            "project_costs[]": [looker.id, photos.id],
            "expenses[]": [train.id, other_client.id, setup["expenses"]["traffic"].id],
        },
    )
    assert resp.status_code == 302
    # On draft A they stay, with their line; A's total is unchanged
    looker, train = _reload(looker), _reload(train)
    assert looker.invoice_id == first.id and InvoiceItem.query.get(looker.invoice_item_id).invoice_id == first.id
    assert train.invoice_id == first.id
    assert Decimal(_reload(first).subtotal) == Decimal("80") + 50 + 200
    # Another client's expense is not taken; what B may bill is
    assert _reload(other_client).invoice_id is None
    assert _reload(photos).invoice_id == second.id
    assert _reload(setup["expenses"]["traffic"]).invoice_id == second.id
    assert Decimal(_reload(second).subtotal) == Decimal("40") + 15
    with client.session_transaction() as sess:
        flashes = [m for _c, m in sess.get("_flashes", [])]
    assert any("Not added" in m and str(looker.id) in m and str(other_client.id) in m for m in flashes)


def test_generate_from_time_does_not_take_a_cost_of_an_issued_invoice(client, user, setup):
    _login(client, user)
    first = _create(client, setup, expenses=(), costs=("looker",))
    _issue(client, first)
    second = _second_draft(setup, user)
    client.post(f"/invoices/{second.id}/generate-from-time", data={"project_costs[]": [setup["costs"]["looker"].id]})
    assert _reload(setup["costs"]["looker"]).invoice_id == first.id
    assert _cost_lines(second) == []


def _edit_line(client, invoice, line, **values):
    resp = client.post(f"/invoices/{invoice.id}/lines/{line.id}", data=values, headers=JSON)
    assert resp.status_code == 200, resp.get_data(as_text=True)


def test_x_on_a_cost_of_a_line_with_an_edited_quantity(client, user, setup):
    _login(client, user)
    invoice = _create(client, setup, expenses=(), costs=("metabase", "photos"), layout="one_line")
    line = _cost_lines(invoice)[0]  # 100 + 40 = 140
    _edit_line(client, invoice, line, quantity="2")
    line = _reload(line)
    assert line.quantity_edited and Decimal(line.total_amount) == Decimal("280.00")
    client.post(f"/invoices/{invoice.id}/costs/{setup['costs']['photos'].id}/remove", headers=JSON)
    line = _reload(line)
    # The quantity stays; the amount goes down by the cost, 40
    assert (Decimal(line.quantity), Decimal(line.unit_price)) == (Decimal("2"), Decimal("120.00"))
    assert Decimal(line.total_amount) == Decimal("240.00")


def test_x_on_a_cost_of_a_line_with_edited_quantity_and_price(client, user, setup):
    _login(client, user)
    invoice = _create(client, setup, expenses=(), costs=("metabase", "photos"), layout="one_line")
    line = _cost_lines(invoice)[0]
    _edit_line(client, invoice, line, quantity="2", unit_price="100")
    client.post(f"/invoices/{invoice.id}/costs/{setup['costs']['photos'].id}/remove", headers=JSON)
    line = _reload(line)
    assert Decimal(line.total_amount) == Decimal("160.00")  # 200 - 40, not 200 - 80
    assert Decimal(_reload(invoice).subtotal) == Decimal("80") + 160


def test_regroup_asks_about_a_line_with_an_edited_quantity(client, user, setup):
    _login(client, user)
    invoice = _create(client, setup, expenses=(), costs=("metabase", "looker"), layout="cost")
    edited = _cost_lines(invoice)[0]
    _edit_line(client, invoice, edited, quantity="3")
    assert 'id="keepEditedCosts"' in client.get(f"/invoices/{invoice.id}").get_data(as_text=True)
    client.post(
        f"/invoices/{invoice.id}/costs/regroup", data={"costs_layout": "one_line", "keep_edited": "keep"}, headers=JSON
    )
    lines = _cost_lines(invoice)
    assert any(line.id == edited.id and Decimal(line.quantity) == Decimal("3") for line in lines)
    assert len(lines) == 2


def test_paid_by_is_one_of_the_people_offered(client, user, setup):
    _login(client, user)
    invoice = _create(client, setup, expenses=(), costs=())
    gone = UserFactory(username="gone-costs")
    gone.is_active = False
    db.session.commit()
    for user_id in (gone.id, 987654):
        resp = client.post(
            f"/invoices/{invoice.id}/expenses",
            data={
                "expense_date": _day(12).isoformat(),
                "title": "Fuel",
                "category": "travel",
                "amount": "9",
                "user_id": user_id,
            },
            headers=JSON,
        )
        assert resp.status_code == 400
    assert Expense.query.filter_by(title="Fuel").first() is None


def test_api_put_items_refuses_a_line_id_sent_twice(app, client, user, setup):
    from app.services import InvoiceService

    _login(client, user)
    invoice = _create(client, setup, expenses=(), costs=("looker",), layout="cost")
    line = _cost_lines(invoice)[0]
    row = {"id": line.id, "description": line.description, "quantity": 1, "unit_price": str(line.unit_price)}
    result = InvoiceService().set_invoice_items(invoice.id, user.id, [row, dict(row)], is_admin=True)
    assert not result["success"] and result["error"] == "duplicate_line_id"
    db.session.rollback()
    assert [item.id for item in _cost_lines(invoice)] == [line.id]
    assert Decimal(_reload(invoice).subtotal) == Decimal("80") + 200

    # Through the API the answer names the problem
    from factories import ApiTokenFactory

    _token, plain = ApiTokenFactory.create(user_id=user.id, scopes="read:invoices,write:invoices")
    db.session.commit()
    resp = client.put(
        f"/api/v1/invoices/{invoice.id}/items",
        json={"items": [row, dict(row)]},
        headers={"Authorization": f"Bearer {plain}"},
    )
    assert resp.status_code == 400
    assert resp.get_json()["error_code"] == "duplicate_line_id"
    assert [item.id for item in _cost_lines(invoice)] == [line.id]


@pytest.mark.parametrize(
    "path,data,code,message",
    [
        (
            "expenses",
            {"title": "", "category": "travel", "amount": "5", "expense_date": "D"},
            "invalid_value",
            "Description is required.",
        ),
        (
            "expenses",
            {"title": "Fuel", "category": "travel", "amount": "abc", "expense_date": "D"},
            "invalid_value",
            "Amount must be a number.",
        ),
        (
            "expenses",
            {"title": "Fuel", "category": "travel", "amount": "0", "expense_date": "D"},
            "invalid_value",
            "Amount must be above 0.",
        ),
        (
            "expenses",
            {"title": "Fuel", "category": "travel", "amount": "5", "expense_date": ""},
            "invalid_value",
            "Date is required.",
        ),
        (
            "expenses",
            {"title": "Fuel", "category": "travel", "amount": "5", "expense_date": "soon"},
            "invalid_value",
            "Date must be a date.",
        ),
        (
            "expenses",
            {"title": "Fuel", "category": "travel", "amount": "5", "expense_date": "AFTER"},
            "date_outside_period",
            "The date is after the invoice's period.",
        ),
        (
            "expenses",
            {"title": "Fuel", "category": "travel", "amount": "5", "expense_date": "BEFORE"},
            "date_outside_period",
            "The date is before the invoice's period.",
        ),
        (
            "costs",
            {"description": "Hosting", "category_id": "", "amount": "5", "cost_date": "D"},
            "invalid_value",
            "Category is required.",
        ),
        (
            "costs",
            {"description": "", "category_id": "SW", "amount": "5", "cost_date": "D"},
            "invalid_value",
            "Description is required.",
        ),
        ("costs/regroup", {"costs_layout": "sideways"}, "invalid_costs_layout", "Choose how to show the costs."),
    ],
)
def test_draft_errors_answer_with_fixed_texts(client, user, setup, path, data, code, message):
    _login(client, user)
    invoice = _create(client, setup, expenses=(), costs=("looker",))
    days = {"D": _day(12).isoformat(), "AFTER": (LAST.end + timedelta(days=1)).isoformat()}
    days["BEFORE"] = (LAST.start - timedelta(days=1)).isoformat()
    form = {k: days.get(v, v) if k.endswith("date") else v for k, v in data.items()}
    if form.get("category_id") == "SW":
        form["category_id"] = setup["software"].id
    resp = client.post(f"/invoices/{invoice.id}/{path}", data=form, headers=JSON)
    assert resp.status_code == 400
    body = resp.get_json()
    assert (body["error"], body["message"]) == (code, message)


@pytest.mark.parametrize(
    "upload,message",
    [
        (None, "Choose a file."),
        (("script.exe", b"x"), "Receipts and bills can be PNG, JPG, GIF or PDF files."),
    ],
)
def test_receipt_errors_answer_with_fixed_texts(client, user, setup, app, tmp_path, upload, message):
    import io

    app.config["UPLOAD_FOLDER"] = str(tmp_path)
    _login(client, user)
    invoice = _create(client, setup, expenses=("train",), costs=())
    data = {} if upload is None else {"receipt_file": (io.BytesIO(upload[1]), upload[0])}
    resp = client.post(
        f"/invoices/{invoice.id}/expenses/{setup['expenses']['train'].id}/receipt",
        data=data,
        content_type="multipart/form-data",
        headers=JSON,
    )
    assert resp.status_code == 400
    assert resp.get_json() == {"success": False, "error": "receipt_not_saved", "message": message}
