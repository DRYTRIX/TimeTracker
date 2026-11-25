"""InvoiceTimeService: add hours with a layout, regroup a draft, rewrite descriptions, edited lines."""

from datetime import date, datetime, timedelta
from decimal import Decimal

import pytest
from factories import ClientFactory, InvoiceFactory, InvoiceItemFactory, ProjectFactory, TimeEntryFactory, UserFactory

from app import db
from app.models import Invoice, InvoiceItem, RateOverride, Task
from app.services import InvoiceService
from app.services.invoice_time_service import InvalidHoursLayoutError, InvoiceNotDraftError, InvoiceTimeService

pytestmark = [pytest.mark.unit]


@pytest.fixture
def setup(app, user):
    """Two tasks, two people (Ben from 40 to 50 on the 15th), five entries; 315.00 in all."""
    cl = ClientFactory(name="Regroup Client", default_hourly_rate=None)
    project = ProjectFactory(name="Regroup Project", client_id=cl.id, hourly_rate=Decimal("40.00"))
    ann = UserFactory(username="ann-regroup", full_name="Ann")
    ben = UserFactory(username="ben-regroup", full_name="Ben")
    db.session.flush()
    design = Task(name="Design", project_id=project.id, status="todo", created_by=ann.id)
    meetings = Task(name="Meetings", project_id=project.id, status="todo", created_by=ann.id)
    db.session.add_all([design, meetings])
    db.session.add(
        RateOverride(
            project_id=project.id, user_id=ben.id, hourly_rate=Decimal("50.00"), effective_from=date(2026, 10, 15)
        )
    )
    db.session.flush()

    def entry(person, task, day, hours, notes=None):
        start = datetime(2026, 10, day, 9, 0)
        return TimeEntryFactory(
            user_id=person.id,
            project_id=project.id,
            task_id=task.id,
            start_time=start,
            end_time=start + timedelta(hours=hours),
            notes=notes,
            billable=True,
        )

    entries = [
        entry(ann, design, 5, 2, "Wireframes"),
        entry(ann, meetings, 6, 1, "Kickoff"),
        entry(ben, design, 7, 3, "Layout"),
        entry(ben, design, 20, 1, "Layout"),
        entry(ben, meetings, 21, 0.5),
    ]
    invoice = InvoiceFactory(
        project_id=project.id, client_id=cl.id, client_name=cl.name, created_by=user.id, tax_rate=Decimal("0")
    )
    invoice.currency_code = "EUR"
    db.session.commit()
    return {"user": user, "project": project, "entries": entries, "invoice": invoice}


def _lines(invoice):
    db.session.expire_all()
    invoice = Invoice.query.get(invoice.id)
    return sorted(invoice.items.all(), key=lambda item: (item.position or 0, item.id))


def _linked(invoice):
    return sorted(InvoiceTimeService().invoice_entry_ids(invoice))


def _total(invoice):
    return sum((item.total_amount for item in _lines(invoice)), Decimal("0"))


def _add(setup, layout="task", template=None):
    lines = InvoiceTimeService().add_entries(setup["invoice"], setup["entries"], layout, template)
    db.session.commit()
    return lines


def test_add_entries_links_lines_and_remembers_the_layout(setup):
    lines = _add(setup, "task_person", "{task} / {person}")
    invoice, project = setup["invoice"], setup["project"]
    assert len(lines.items) == 5
    assert _linked(invoice) == sorted(e.id for e in setup["entries"])
    assert _total(invoice) == Decimal("315.00")
    assert [item.position for item in _lines(invoice)] == [0, 1, 2, 3, 4]
    assert all(item.kind == "time" for item in _lines(invoice))
    assert (invoice.hours_layout, invoice.line_template) == ("task_person", "{task} / {person}")
    assert (project.last_hours_layout, project.last_line_template) == ("task_person", "{task} / {person}")


def test_add_entries_defaults_to_the_projects_last_layout(setup):
    project = setup["project"]
    project.last_hours_layout = "person"
    project.last_line_template = "{person}"
    db.session.commit()
    _add(setup, layout=None)
    assert [item.description for item in _lines(setup["invoice"])][0] == "Ann"
    assert setup["invoice"].hours_layout == "person"


def test_a_template_written_for_another_layout_is_not_reused(setup):
    service = InvoiceTimeService()
    project = setup["project"]
    project.last_hours_layout = "person"
    project.last_line_template = "{person}"
    assert service.resolve_layout(project, "task") == ("task", "{task}")
    assert service.resolve_layout(project) == ("person", "{person}")
    project.last_hours_layout = None
    assert service.resolve_layout(project, fallback_layout="project") == ("project", "{project} ({date})")


def test_none_adds_no_lines_and_links_nothing(setup):
    lines = _add(setup, "none")
    assert lines.items == []
    assert _linked(setup["invoice"]) == []
    assert setup["invoice"].hours_layout == "none"


def test_regroup_keeps_links_and_total(setup):
    _add(setup, "task")
    for layout in ("person", "detailed", "project", "task_person", "task"):
        InvoiceTimeService().rebuild_lines(setup["invoice"], layout)
        db.session.commit()
        assert _linked(setup["invoice"]) == sorted(e.id for e in setup["entries"]), layout
        assert _total(setup["invoice"]) == Decimal("315.00"), layout
        assert setup["invoice"].hours_layout == layout
    assert setup["project"].last_hours_layout == "task"


def test_regroup_keeps_hours_of_each_link(setup):
    service = InvoiceTimeService()
    first = setup["entries"][0]
    # Only part of the entry is on this invoice (as after prepaid hours)
    service.add_entries(setup["invoice"], [first], "task")
    link = setup["invoice"].time_links.first()
    link.hours = Decimal("1.2500")
    db.session.commit()
    service.rebuild_lines(setup["invoice"], "detailed")
    db.session.commit()
    (item,) = _lines(setup["invoice"])
    assert item.quantity == Decimal("1.25")
    assert setup["invoice"].time_links.first().hours == Decimal("1.2500")


def test_regroup_keeps_edited_and_manual_lines_in_place(setup):
    invoice = setup["invoice"]
    manual = InvoiceItemFactory(
        invoice_id=invoice.id, description="Fixed fee", quantity=Decimal("1"), unit_price=Decimal("100")
    )
    manual.position = 0
    db.session.commit()
    _add(setup, "task")  # four time lines after the manual one, positions 1..4
    lines = _lines(invoice)
    edited = lines[1]  # Design at 40: Ann's 2 h and Ben's 3 h
    edited_entries = sorted(int(i) for i in edited.time_entry_ids.split(","))
    edited.description = "Design work, phase 1"
    edited.description_edited = True
    db.session.commit()

    InvoiceTimeService().rebuild_lines(invoice, "person")
    db.session.commit()

    lines = _lines(invoice)
    assert lines[0].description == "Fixed fee"
    assert lines[0].kind == "manual"
    assert lines[1].id == edited.id
    assert lines[1].description == "Design work, phase 1"
    assert sorted(int(i) for i in lines[1].time_entry_ids.split(",")) == edited_entries
    # The rest is regrouped by person from the entries the edited line does not hold
    rebuilt = lines[2:]
    rebuilt_entries = sorted(int(i) for item in rebuilt for i in item.time_entry_ids.split(","))
    assert rebuilt_entries == sorted(set(e.id for e in setup["entries"]) - set(edited_entries))
    assert [item.position for item in lines] == list(range(len(lines)))
    assert _total(invoice) == Decimal("415.00")
    assert _linked(invoice) == sorted(e.id for e in setup["entries"])


def test_regroup_without_keeping_rebuilds_edited_lines(setup):
    invoice = setup["invoice"]
    _add(setup, "task")
    edited = _lines(invoice)[0]
    edited.description = "Hand-written"
    edited.quantity = Decimal("4.00")
    edited.total_amount = edited.line_net
    edited.description_edited = True
    edited.quantity_edited = True
    db.session.commit()

    InvoiceTimeService().rebuild_lines(invoice, "task", keep_edited=False)
    db.session.commit()

    lines = _lines(invoice)
    assert "Hand-written" not in [item.description for item in lines]
    assert not any(item.is_edited for item in lines)
    assert _total(invoice) == Decimal("315.00")


def test_regroup_only_on_a_draft_and_never_to_none(setup):
    _add(setup, "task")
    with pytest.raises(InvalidHoursLayoutError):
        InvoiceTimeService().rebuild_lines(setup["invoice"], "none")
    setup["invoice"].status = "sent"
    db.session.commit()
    with pytest.raises(InvoiceNotDraftError):
        InvoiceTimeService().rebuild_lines(setup["invoice"], "person")


def test_apply_template_rewrites_lines_except_edited_ones(setup):
    invoice = setup["invoice"]
    _add(setup, "task")
    first = _lines(invoice)[0]
    first.description = "Kept"
    first.description_edited = True
    db.session.commit()

    service = InvoiceTimeService()
    assert service.apply_template(invoice, "{task} ({person})") == 3
    db.session.commit()
    descriptions = [item.description for item in _lines(invoice)]
    assert descriptions == [
        "Kept",
        "Design (Ben) – 50.00 EUR/h",
        "Meetings (Ann) – 40.00 EUR/h",
        "Meetings (Ben) – 50.00 EUR/h",
    ]
    assert invoice.line_template == "{task} ({person})"
    assert _total(invoice) == Decimal("315.00")

    assert service.apply_template(invoice, "{task} ({person})", keep_edited=False) == 4
    db.session.commit()
    first = _lines(invoice)[0]
    assert first.description == "Design (Ann, Ben) – 40.00 EUR/h"
    assert first.description_edited is False


def test_put_items_marks_only_what_changed_on_time_lines(setup):
    invoice, user = setup["invoice"], setup["user"]
    manual = InvoiceItemFactory(
        invoice_id=invoice.id, description="Fixed fee", quantity=Decimal("1"), unit_price=Decimal("100")
    )
    manual.position = 9
    db.session.commit()
    _add(setup, "task")
    lines = _lines(invoice)
    rows = [item.to_dict() for item in lines]
    by_desc = {row["description"]: row for row in rows}
    by_desc["Design – 40.00 EUR/h"]["description"] = "Design, phase 1"
    by_desc["Design – 50.00 EUR/h"]["unit_price"] = 55
    by_desc["Meetings – 40.00 EUR/h"]["quantity"] = 1.5
    by_desc["Fixed fee"]["description"] = "Fixed fee, October"
    # A row without its id is matched to its line by the same time entries
    del by_desc["Meetings – 50.00 EUR/h"]["id"]

    result = InvoiceService().set_invoice_items(invoice.id, user.id, rows, is_admin=True)
    assert result["success"], result

    flags = {
        item.description: (item.kind, item.description_edited, item.quantity_edited, item.price_edited)
        for item in _lines(invoice)
    }
    assert flags == {
        "Design, phase 1": ("time", True, False, False),
        "Design – 50.00 EUR/h": ("time", False, False, True),
        "Meetings – 40.00 EUR/h": ("time", False, True, False),
        "Meetings – 50.00 EUR/h": ("time", False, False, False),
        "Fixed fee, October": ("manual", False, False, False),
    }
    edited_price = next(i for i in _lines(invoice) if i.description == "Design – 50.00 EUR/h")
    assert edited_price.total_amount == Decimal("55.00")

    # Saving again unchanged keeps the flags
    result = InvoiceService().set_invoice_items(
        invoice.id, user.id, [item.to_dict() for item in _lines(invoice)], is_admin=True
    )
    assert result["success"], result
    assert sum(item.is_edited for item in _lines(invoice)) == 3


def test_recurring_invoice_keeps_the_global_layout_and_the_projects_default(setup):
    from factories import RecurringInvoiceFactory

    from app.services.recurring_invoice_service import RecurringInvoiceService

    project = setup["project"]
    project.last_hours_layout = "person"
    db.session.commit()
    recurring = RecurringInvoiceFactory(
        project_id=project.id,
        client_id=project.client_id,
        client_name="Regroup Client",
        created_by=setup["user"].id,
        next_run_date=date.today() - timedelta(days=1),  # due whatever the clock's time zone
        auto_include_time_entries=True,
    )
    db.session.commit()
    generated = RecurringInvoiceService().generate_invoice(recurring)
    db.session.commit()
    assert generated.hours_layout == "task"
    assert len(generated.items.all()) == 4
    assert project.last_hours_layout == "person"


def test_client_unbilled_uses_project_layout_and_does_not_change_the_default(setup):
    project = setup["project"]
    result = InvoiceService().create_client_unbilled_invoice(project.client_id, setup["user"].id)
    assert result["success"], result
    invoice = Invoice.query.get(result["invoice_id"])
    assert invoice.hours_layout == "project"
    assert len(invoice.items.all()) == 2
    assert project.last_hours_layout is None


def test_line_kind_defaults_to_manual(app, setup):
    item = InvoiceItem(setup["invoice"].id, "Typed in", 1, 10)
    db.session.add(item)
    db.session.commit()
    assert item.kind == "manual"
    assert item.is_edited is False


@pytest.mark.parametrize("layout", ["detailed", "task", "person", "task_person", "project"])
def test_every_layout_exports_balanced_pdf_ubl_and_cii(setup, layout):
    """PDF, Peppol UBL and Factur-X CII carry the same lines; each line is quantity x price."""
    import xml.etree.ElementTree as ET

    from app.integrations.peppol import PeppolParty, build_peppol_ubl_invoice_xml
    from app.utils import invoice_pdf_html
    from app.utils.cii_invoice import CIIParty, build_cii_invoice_xml
    from app.utils.invoice_validators import validate_cii_en16931, validate_ubl_peppol_bis3

    invoice = setup["invoice"]
    _add(setup, layout)
    invoice.calculate_totals()
    db.session.commit()
    lines = _lines(invoice)
    invoice = Invoice.query.get(invoice.id)
    assert invoice.subtotal == Decimal("315.00")

    context = invoice_pdf_html.build_context(invoice)
    assert [row.total for row in context["rows"]] == [item.total_amount for item in lines]
    assert context["total"] == Decimal("315.00")

    party = PeppolParty(
        endpoint_id="0208:0123456789",
        endpoint_scheme_id="0208",
        name="Seller",
        tax_id="BE0123456789",
        country_code="BE",
    )
    ubl, _sha = build_peppol_ubl_invoice_xml(invoice=invoice, supplier=party, customer=party)
    passed, issues = validate_ubl_peppol_bis3(ubl)
    assert passed, issues
    ns = {
        "cac": "urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2",
        "cbc": "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2",
    }
    root = ET.fromstring(ubl)
    ubl_lines = root.findall("cac:InvoiceLine", ns)
    assert len(ubl_lines) == len(lines)
    for node in ubl_lines:
        quantity = Decimal(node.find("cbc:InvoicedQuantity", ns).text)
        price = Decimal(node.find("cac:Price/cbc:PriceAmount", ns).text)
        amount = Decimal(node.find("cbc:LineExtensionAmount", ns).text)
        assert quantity * price == amount
    assert Decimal(root.find("cac:LegalMonetaryTotal/cbc:LineExtensionAmount", ns).text) == Decimal("315.00")

    seller = CIIParty(
        name="Seller", tax_id="DE123456789", address_line="Street 1", city="Berlin", postcode="10115", country_code="DE"
    )
    buyer = CIIParty(
        name="Buyer", tax_id="NL123456789B01", address_line="Street 2", city="Amsterdam", country_code="NL"
    )
    cii, _sha = build_cii_invoice_xml(invoice, seller, buyer)
    passed, issues = validate_cii_en16931(cii)
    assert passed, issues
    assert cii.count("IncludedSupplyChainTradeLineItem") // 2 == len(lines)
