"""Tests for Phase 2 invoice line items: per-line tax, discounts, ordering.

Covers:
 - No discounts → same totals as before
 - Per-line discount (percent and amount)
 - Invoice-level discount
 - Mixed tax rates → correct tax_breakdown() and totals
 - position ordering
 - effective_tax_rate fallback
"""

from datetime import date, timedelta
from decimal import Decimal

import pytest

from app import db
from app.models import Client, Invoice, InvoiceItem, Project, Settings, User
from factories import ClientFactory, ProjectFactory, UserFactory


# ---------------------------------------------------------------------------
# Helpers / fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def base_user(app):
    u = UserFactory(username="disc_test_user", role="admin")
    db.session.commit()
    return u


@pytest.fixture
def base_client(app):
    c = ClientFactory(name="Discount Test Client")
    db.session.commit()
    return c


@pytest.fixture
def base_project(app, base_client):
    p = ProjectFactory(
        name="Discount Test Project",
        client_id=base_client.id,
        billable=True,
        hourly_rate=Decimal("100.00"),
    )
    db.session.commit()
    return p


def make_invoice(user, project, client, **kwargs) -> Invoice:
    inv = Invoice(
        invoice_number=f"INV-DISC-{id(kwargs)}",
        project_id=project.id,
        client_name="Test",
        due_date=date.today() + timedelta(days=30),
        created_by=user.id,
        client_id=client.id,
        **kwargs,
    )
    db.session.add(inv)
    db.session.flush()
    return inv


def add_item(invoice, description, quantity, unit_price, **kwargs) -> InvoiceItem:
    item = InvoiceItem(
        invoice_id=invoice.id,
        description=description,
        quantity=quantity,
        unit_price=unit_price,
        **kwargs,
    )
    db.session.add(item)
    return item


# ---------------------------------------------------------------------------
# 1. No discounts → same totals as before
# ---------------------------------------------------------------------------

@pytest.mark.invoices
def test_no_discounts_same_as_before(app, base_user, base_project, base_client):
    """Without any discounts the totals should equal qty×price + tax as before."""
    inv = make_invoice(base_user, base_project, base_client, tax_rate=Decimal("20"))
    add_item(inv, "Dev", Decimal("10"), Decimal("100"))  # 1000
    add_item(inv, "Design", Decimal("5"), Decimal("80"))  # 400
    db.session.commit()

    inv.calculate_totals()

    assert inv.subtotal == Decimal("1400.00")
    assert inv.tax_amount == Decimal("280.00")
    assert inv.total_amount == Decimal("1680.00")


@pytest.mark.invoices
def test_no_discounts_zero_tax(app, base_user, base_project, base_client):
    """Zero tax rate → subtotal == total_amount."""
    inv = make_invoice(base_user, base_project, base_client, tax_rate=Decimal("0"))
    add_item(inv, "Service", Decimal("3"), Decimal("50"))
    db.session.commit()
    inv.calculate_totals()
    assert inv.subtotal == Decimal("150.00")
    assert inv.tax_amount == Decimal("0.00")
    assert inv.total_amount == Decimal("150.00")


# ---------------------------------------------------------------------------
# 2. Per-line discount
# ---------------------------------------------------------------------------

@pytest.mark.invoices
def test_line_discount_percent(app, base_user, base_project, base_client):
    """Per-line 10% discount reduces line net correctly."""
    inv = make_invoice(base_user, base_project, base_client, tax_rate=Decimal("20"))
    add_item(inv, "Dev", Decimal("10"), Decimal("100"), discount_percent=Decimal("10"))
    # line gross = 1000, disc = 100, net = 900
    db.session.commit()

    item = inv.items.first()
    assert item.line_discount_total == Decimal("100.00")
    assert item.line_net == Decimal("900.00")
    # total_amount on item is set at construction
    assert item.total_amount == Decimal("900.00")

    inv.calculate_totals()
    assert inv.subtotal == Decimal("900.00")
    assert inv.tax_amount == Decimal("180.00")
    assert inv.total_amount == Decimal("1080.00")


@pytest.mark.invoices
def test_line_discount_amount(app, base_user, base_project, base_client):
    """Per-line fixed discount_amount takes priority over discount_percent."""
    inv = make_invoice(base_user, base_project, base_client, tax_rate=Decimal("10"))
    add_item(
        inv, "Item", Decimal("5"), Decimal("200"),
        discount_amount=Decimal("50"), discount_percent=Decimal("99"),  # amount wins
    )
    # gross = 1000, disc_amount = 50, net = 950
    db.session.commit()

    item = inv.items.first()
    assert item.line_discount_total == Decimal("50.00")
    assert item.line_net == Decimal("950.00")

    inv.calculate_totals()
    assert inv.subtotal == Decimal("950.00")
    assert inv.tax_amount == Decimal("95.00")
    assert inv.total_amount == Decimal("1045.00")


@pytest.mark.invoices
def test_line_no_discount(app, base_user, base_project, base_client):
    """Item with neither discount field set has zero discount."""
    inv = make_invoice(base_user, base_project, base_client, tax_rate=Decimal("0"))
    item = add_item(inv, "X", Decimal("2"), Decimal("100"))
    db.session.commit()
    assert item.line_discount_total == Decimal("0")
    assert item.line_net == Decimal("200.00")


# ---------------------------------------------------------------------------
# 3. Invoice-level discount
# ---------------------------------------------------------------------------

@pytest.mark.invoices
def test_invoice_discount_percent(app, base_user, base_project, base_client):
    """Invoice-level 5% discount applied after line totals, before tax."""
    inv = make_invoice(
        base_user, base_project, base_client,
        tax_rate=Decimal("20"),
        discount_percent=Decimal("5"),
    )
    add_item(inv, "A", Decimal("10"), Decimal("100"))  # 1000
    db.session.commit()

    inv.calculate_totals()
    # combined net = 1000, disc = 50, subtotal = 950, tax = 190
    assert inv.subtotal == Decimal("950.00")
    assert inv.tax_amount == Decimal("190.00")
    assert inv.total_amount == Decimal("1140.00")


@pytest.mark.invoices
def test_invoice_discount_amount(app, base_user, base_project, base_client):
    """Invoice-level fixed discount_amount applied before tax."""
    inv = make_invoice(
        base_user, base_project, base_client,
        tax_rate=Decimal("10"),
        discount_amount=Decimal("100"),
    )
    add_item(inv, "A", Decimal("2"), Decimal("500"))  # 1000
    db.session.commit()

    inv.calculate_totals()
    assert inv.subtotal == Decimal("900.00")
    assert inv.tax_amount == Decimal("90.00")
    assert inv.total_amount == Decimal("990.00")


@pytest.mark.invoices
def test_invoice_discount_amount_wins_over_percent(app, base_user, base_project, base_client):
    """When both discount_amount and discount_percent set, amount wins."""
    inv = make_invoice(
        base_user, base_project, base_client,
        tax_rate=Decimal("0"),
        discount_amount=Decimal("50"),
        discount_percent=Decimal("99"),  # should be ignored
    )
    add_item(inv, "A", Decimal("1"), Decimal("200"))
    db.session.commit()
    inv.calculate_totals()
    assert inv.subtotal == Decimal("150.00")


@pytest.mark.invoices
def test_combined_line_and_invoice_discount(app, base_user, base_project, base_client):
    """Line discount applied first, then invoice discount on the combined net."""
    inv = make_invoice(
        base_user, base_project, base_client,
        tax_rate=Decimal("20"),
        discount_percent=Decimal("10"),
    )
    # item gross=1000, 20% line disc → net 800
    add_item(inv, "A", Decimal("10"), Decimal("100"), discount_percent=Decimal("20"))
    db.session.commit()

    inv.calculate_totals()
    # combined_net=800, invoice_disc=80, subtotal=720, tax=144
    assert inv.subtotal == Decimal("720.00")
    assert inv.tax_amount == Decimal("144.00")
    assert inv.total_amount == Decimal("864.00")


# ---------------------------------------------------------------------------
# 4. Mixed tax rates → tax_breakdown() and totals
# ---------------------------------------------------------------------------

@pytest.mark.invoices
def test_mixed_tax_rates_breakdown(app, base_user, base_project, base_client):
    """Items with different tax rates produce correct tax_breakdown() entries."""
    inv = make_invoice(base_user, base_project, base_client, tax_rate=Decimal("20"))
    # Item1: net 500 @ 20% → tax 100
    add_item(inv, "Standard", Decimal("5"), Decimal("100"), tax_rate=Decimal("20"))
    # Item2: net 200 @ 10% → tax 20
    add_item(inv, "Reduced", Decimal("2"), Decimal("100"), tax_rate=Decimal("10"))
    # Item3: net 100 @ 0% (exempt) → tax 0
    add_item(inv, "Exempt", Decimal("1"), Decimal("100"), tax_rate=Decimal("0"), vat_category="E")
    db.session.commit()

    inv.calculate_totals()

    assert inv.subtotal == Decimal("800.00")
    assert inv.tax_amount == Decimal("120.00")  # 100+20+0
    assert inv.total_amount == Decimal("920.00")

    bd = inv.tax_breakdown()
    # Should have 3 groups
    assert len(bd) == 3
    by_rate = {grp["rate"]: grp for grp in bd}
    assert abs(by_rate[20.0]["taxable"] - 500.0) < 0.01
    assert abs(by_rate[20.0]["tax"] - 100.0) < 0.01
    assert abs(by_rate[10.0]["taxable"] - 200.0) < 0.01
    assert abs(by_rate[10.0]["tax"] - 20.0) < 0.01
    assert abs(by_rate[0.0]["taxable"] - 100.0) < 0.01
    assert abs(by_rate[0.0]["tax"] - 0.0) < 0.01


@pytest.mark.invoices
def test_mixed_tax_rates_with_invoice_discount(app, base_user, base_project, base_client):
    """Invoice discount is distributed proportionally across rate groups."""
    inv = make_invoice(
        base_user, base_project, base_client,
        tax_rate=Decimal("20"),
        discount_percent=Decimal("10"),
    )
    add_item(inv, "A", Decimal("10"), Decimal("100"), tax_rate=Decimal("20"))  # 1000
    add_item(inv, "B", Decimal("10"), Decimal("100"), tax_rate=Decimal("10"))  # 1000
    db.session.commit()

    inv.calculate_totals()
    # combined=2000, disc=200, subtotal=1800
    assert inv.subtotal == Decimal("1800.00")
    # each group taxable after 10% disc:
    # 20% group: 1000*0.9=900, tax=180
    # 10% group: 1000*0.9=900, tax=90
    expected_tax = Decimal("270.00")
    assert inv.tax_amount == expected_tax
    assert inv.total_amount == Decimal("2070.00")

    bd = inv.tax_breakdown()
    by_rate = {grp["rate"]: grp for grp in bd}
    assert abs(by_rate[20.0]["taxable"] - 900.0) < 0.01
    assert abs(by_rate[10.0]["taxable"] - 900.0) < 0.01


# ---------------------------------------------------------------------------
# 5. effective_tax_rate fallback
# ---------------------------------------------------------------------------

@pytest.mark.invoices
def test_effective_tax_rate_fallback(app, base_user, base_project, base_client):
    """Item without tax_rate falls back to invoice.tax_rate."""
    inv = make_invoice(base_user, base_project, base_client, tax_rate=Decimal("19"))
    item = add_item(inv, "A", Decimal("1"), Decimal("100"))
    db.session.commit()

    assert item.tax_rate is None
    assert item.effective_tax_rate(inv) == Decimal("19")


@pytest.mark.invoices
def test_effective_tax_rate_per_line_overrides(app, base_user, base_project, base_client):
    """Item with explicit tax_rate uses it over invoice.tax_rate."""
    inv = make_invoice(base_user, base_project, base_client, tax_rate=Decimal("20"))
    item = add_item(inv, "A", Decimal("1"), Decimal("100"), tax_rate=Decimal("7"))
    db.session.commit()

    assert item.effective_tax_rate(inv) == Decimal("7")


# ---------------------------------------------------------------------------
# 6. Position ordering
# ---------------------------------------------------------------------------

@pytest.mark.invoices
def test_item_position_stored(app, base_user, base_project, base_client):
    """Items retain their position value."""
    inv = make_invoice(base_user, base_project, base_client, tax_rate=Decimal("0"))
    add_item(inv, "First", Decimal("1"), Decimal("1"), position=0)
    add_item(inv, "Second", Decimal("1"), Decimal("2"), position=1)
    add_item(inv, "Third", Decimal("1"), Decimal("3"), position=2)
    db.session.commit()

    items = list(inv.items.order_by(InvoiceItem.position))
    assert [item.description for item in items] == ["First", "Second", "Third"]


@pytest.mark.invoices
def test_item_position_default_zero(app, base_user, base_project, base_client):
    """Items with no position set default to 0."""
    inv = make_invoice(base_user, base_project, base_client, tax_rate=Decimal("0"))
    item = add_item(inv, "X", Decimal("1"), Decimal("1"))
    db.session.commit()
    assert item.position == 0


# ---------------------------------------------------------------------------
# 7. to_dict includes new fields
# ---------------------------------------------------------------------------

@pytest.mark.invoices
def test_invoice_to_dict_new_fields(app, base_user, base_project, base_client):
    """Invoice.to_dict() includes discount_percent and discount_amount."""
    inv = make_invoice(
        base_user, base_project, base_client,
        tax_rate=Decimal("20"),
        discount_percent=Decimal("5"),
        discount_amount=Decimal("0"),
    )
    db.session.commit()
    d = inv.to_dict()
    assert "discount_percent" in d
    assert "discount_amount" in d
    assert d["discount_percent"] == 5.0


@pytest.mark.invoices
def test_item_to_dict_new_fields(app, base_user, base_project, base_client):
    """InvoiceItem.to_dict() includes tax_rate, discount_percent, discount_amount, position."""
    inv = make_invoice(base_user, base_project, base_client, tax_rate=Decimal("20"))
    item = add_item(
        inv, "X", Decimal("2"), Decimal("50"),
        tax_rate=Decimal("7"),
        discount_percent=Decimal("10"),
        position=3,
    )
    db.session.commit()
    d = item.to_dict()
    assert d["tax_rate"] == 7.0
    assert d["discount_percent"] == 10.0
    assert d["position"] == 3


# ---------------------------------------------------------------------------
# 8. Backward compatibility: existing items with null discounts unchanged
# ---------------------------------------------------------------------------

@pytest.mark.invoices
def test_backward_compat_null_discounts(app, base_user, base_project, base_client):
    """Items without discount fields behave exactly as before (no change to totals)."""
    inv = make_invoice(base_user, base_project, base_client, tax_rate=Decimal("20"))
    # Create items without any new fields (old-style)
    item1 = InvoiceItem(
        invoice_id=inv.id, description="A", quantity=Decimal("10"), unit_price=Decimal("75")
    )
    item2 = InvoiceItem(
        invoice_id=inv.id, description="B", quantity=Decimal("5"), unit_price=Decimal("100")
    )
    db.session.add(item1)
    db.session.add(item2)
    db.session.commit()

    inv.calculate_totals()
    # 10*75=750, 5*100=500, subtotal=1250, tax@20%=250
    assert inv.subtotal == Decimal("1250.00")
    assert inv.tax_amount == Decimal("250.00")
    assert inv.total_amount == Decimal("1500.00")


# ---------------------------------------------------------------------------
# 9. tax_breakdown() with single rate returns one entry
# ---------------------------------------------------------------------------

@pytest.mark.invoices
def test_tax_breakdown_single_rate(app, base_user, base_project, base_client):
    """Single tax rate produces a single breakdown entry."""
    inv = make_invoice(base_user, base_project, base_client, tax_rate=Decimal("19"))
    add_item(inv, "A", Decimal("1"), Decimal("100"))
    add_item(inv, "B", Decimal("2"), Decimal("50"))
    db.session.commit()
    inv.calculate_totals()

    bd = inv.tax_breakdown()
    assert len(bd) == 1
    assert bd[0]["rate"] == 19.0
    assert abs(bd[0]["taxable"] - 200.0) < 0.01
    assert abs(bd[0]["tax"] - 38.0) < 0.01
