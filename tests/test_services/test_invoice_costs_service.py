"""InvoiceCostsService: cost lines by cost, by category or one line, and the ticks of step 1."""

from datetime import date
from decimal import Decimal
from types import SimpleNamespace

import pytest
from factories import ClientFactory, ExpenseCategoryFactory, InvoiceFactory, ProjectFactory

from app import db
from app.models import ProjectCost
from app.services.invoice_costs_service import (
    COSTS_BY_CATEGORY,
    COSTS_BY_COST,
    COSTS_ONE_LINE,
    LINE_KIND_COST,
    InvoiceCostsService,
    cost_statuses,
)

pytestmark = [pytest.mark.unit]


@pytest.fixture
def setup(app, user):
    cl = ClientFactory(name="Cost Lines Client")
    project = ProjectFactory(name="Cost Lines Project", client_id=cl.id, hourly_rate=Decimal("50"))
    software = ExpenseCategoryFactory(name="Software", code="SWL")
    hosting = ExpenseCategoryFactory(name="Hosting", code="HSL")
    db.session.flush()
    invoice = InvoiceFactory(project_id=project.id, client_id=cl.id, client_name=cl.name, created_by=user.id)
    invoice.tax_rate = Decimal("0")
    db.session.flush()

    def cost(description, amount, category, day):
        made = ProjectCost(
            project_id=project.id,
            user_id=user.id,
            description=description,
            category=None,
            amount=Decimal(amount),
            cost_date=date(2026, 10, day),
        )
        made.set_category(category)
        db.session.add(made)
        db.session.flush()
        return made

    costs = [
        cost("Looker", "200", software, 8),
        cost("Server", "70", hosting, 3),
        cost("Metabase", "100", software, 5),
    ]
    db.session.commit()
    return {"invoice": invoice, "costs": costs}


def test_group_costs_by_cost_category_and_one_line(setup):
    costs = setup["costs"]
    service = InvoiceCostsService()
    assert [(d, [c.description for c in g]) for d, g in service.group_costs(costs, COSTS_BY_COST)] == [
        ("Server (Hosting)", ["Server"]),
        ("Metabase (Software)", ["Metabase"]),
        ("Looker (Software)", ["Looker"]),
    ]
    assert [(d, [c.description for c in g]) for d, g in service.group_costs(costs, COSTS_BY_CATEGORY)] == [
        ("Hosting", ["Server"]),
        ("Software", ["Metabase", "Looker"]),
    ]
    assert [(d, len(g)) for d, g in service.group_costs(costs, COSTS_ONE_LINE)] == [("Project costs", 3)]


def test_cost_lines_sum_their_costs_and_follow_a_removed_one(setup):
    invoice, costs = setup["invoice"], setup["costs"]
    service = InvoiceCostsService()
    lines = service.add_cost_lines(invoice, costs, COSTS_BY_CATEGORY)
    invoice.calculate_totals()
    db.session.commit()
    assert [(i.kind, i.description, Decimal(i.unit_price)) for i in lines] == [
        (LINE_KIND_COST, "Hosting", Decimal("70.00")),
        (LINE_KIND_COST, "Software", Decimal("300.00")),
    ]
    software = lines[1]
    # A price changed by hand goes down by the cost taken off
    software.unit_price = Decimal("280")
    software.price_edited = True
    service.remove_cost(invoice, costs[0])  # Looker, 200
    db.session.commit()
    assert Decimal(software.unit_price) == Decimal("80.00")
    assert Decimal(invoice.subtotal) == Decimal("150.00")


def test_choose_ticks_what_was_posted_and_the_default_for_what_was_not_shown():
    items = [SimpleNamespace(id=i) for i in (1, 2, 3)]
    choose = InvoiceCostsService.choose
    assert [i.id for i in choose(items, None, [], True)] == [1, 2, 3]
    assert [i.id for i in choose(items, None, [], False)] == []
    # 1 shown and ticked, 2 shown and not ticked, 3 not shown yet: its default
    assert [i.id for i in choose(items, [1], [1, 2], True)] == [1, 3]
    assert [i.id for i in choose(items, [1], [1, 2], lambda item: item.id != 3)] == [1]


def test_cost_statuses():
    assert cost_statuses(SimpleNamespace(recurring_cost_id=4, billable=True)) == ["recurring"]
    assert cost_statuses(SimpleNamespace(recurring_cost_id=None, billable=False)) == ["logged", "non_billable"]
