"""Client legal entities module: the legal entities a client is billed through, and Bill to on invoices.

A client keeps several legal entities; an invoice picks one as Bill to. The entity's details are
copied into the invoice (a draft refreshes the copy on save) and the built-in PDFs print its
registration number and VAT. Without an entity, or with the module off, nothing changes.
"""

from datetime import date, timedelta

import pytest

from app import db
from app.models import Client, ClientEntity, Invoice, Settings
from app.utils import client_entities as bill_to

pytestmark = [pytest.mark.integration]


@pytest.fixture
def entity(app, test_client):
    e = ClientEntity(
        client_id=test_client.id,
        legal_name="Example Holding S.L.",
        registration_number="B12345678",
        vat_number="ESB12345678",
        country="ES",
        address="Calle Mayor 1, 28001 Madrid, Spain",
        email="billing@example.com",
    )
    db.session.add(e)
    db.session.commit()
    return e


@pytest.fixture
def second_entity(app, test_client):
    e = ClientEntity(client_id=test_client.id, legal_name="Example Trading Ltd", country="CY")
    db.session.add(e)
    db.session.commit()
    return e


def _create_form(project, test_client, **extra):
    data = {
        "project_id": project.id,
        "client_name": test_client.name,
        "due_date": (date.today() + timedelta(days=30)).strftime("%Y-%m-%d"),
        "tax_rate": "0",
        "currency_code": "EUR",
    }
    data.update(extra)
    return data


def _newest_invoice():
    return Invoice.query.order_by(Invoice.id.desc()).first()


def _disable_module():
    settings = Settings.get_settings()
    settings.disabled_module_ids = ["client_entities"]
    db.session.commit()


def _invoice_for(project, test_client, user, entity=None, issued=None):
    inv = Invoice(
        invoice_number=f"T-{Invoice.query.count() + 1}",
        project_id=project.id,
        client_id=test_client.id,
        client_name=test_client.name,
        due_date=date.today() + timedelta(days=30),
        created_by=user.id,
    )
    if issued:
        inv.issue_date = issued
    bill_to.apply_to_invoice(inv, entity)
    db.session.add(inv)
    db.session.commit()
    return inv


# --- model and helpers ---------------------------------------------------------------------------


def test_snapshot_and_label(app, entity):
    snap = entity.buyer_snapshot()
    assert snap["legal_name"] == "Example Holding S.L."
    assert snap["vat_number"] == "ESB12345678"
    assert entity.label == "Example Holding S.L. · ES"


def test_default_follows_client_then_only_entity(app, entity, second_entity):
    active = {entity.id, second_entity.id}
    # the client's latest invoice, whatever its project
    assert bill_to.default_entity_id(7, active, {7: second_entity.id}) == second_entity.id
    # the latest invoice used the client's own details: keep that
    assert bill_to.default_entity_id(7, active, {7: None}) is None
    # an archived entity is skipped
    assert bill_to.default_entity_id(7, {entity.id}, {7: second_entity.id}) == entity.id
    # no invoices: the only entity, else client details
    assert bill_to.default_entity_id(7, {entity.id}, {}) == entity.id
    assert bill_to.default_entity_id(7, active, {}) is None


def test_form_context_default_from_latest_client_invoice(app, user, project, test_client, entity, second_entity):
    _invoice_for(project, test_client, user, entity, issued=date(2026, 9, 30))
    _invoice_for(project, test_client, user, second_entity, issued=date(2026, 10, 31))
    ctx = bill_to.form_context([project])
    data = ctx["client_entity_data"]
    assert data["defaults"][str(project.id)] == second_entity.id
    assert {e["id"] for e in data["byClient"][str(test_client.id)]} == {entity.id, second_entity.id}
    assert data["clients"][str(test_client.id)]["email"] == test_client.email


def test_default_ignores_project_of_latest_invoice(app, user, project, test_client, entity, second_entity):
    """The project's last invoice went to X, a later one of the client (other project) to Y: Y."""
    from app.models import Project

    other = Project(name="Other project", client_id=test_client.id, billable=True)
    db.session.add(other)
    db.session.commit()
    _invoice_for(project, test_client, user, entity, issued=date(2026, 9, 30))
    _invoice_for(other, test_client, user, second_entity, issued=date(2026, 10, 31))
    data = bill_to.form_context([project, other])["client_entity_data"]
    assert data["defaults"][str(project.id)] == second_entity.id
    assert data["defaults"][str(other.id)] == second_entity.id


def test_archived_entity_not_offered(app, project, entity, second_entity):
    second_entity.status = "archived"
    db.session.commit()
    data = bill_to.form_context([project])["client_entity_data"]
    assert [e["id"] for e in data["byClient"][str(project.client_id)]] == [entity.id]


def test_buyer_lines(app, user, project, test_client, entity):
    inv = _invoice_for(project, test_client, user, entity)
    assert bill_to.buyer_lines(inv) == [("Registration number", "B12345678"), ("VAT", "ESB12345678")]
    inv.buyer_snapshot = None
    assert bill_to.buyer_lines(inv) == []


def test_pdf_html_prints_registration_and_vat(app, user, project, test_client, entity):
    from app.utils.pdf_generator import InvoicePDFGenerator

    inv = _invoice_for(project, test_client, user, entity)
    html = InvoicePDFGenerator(inv)._generate_html()
    assert "B12345678" in html
    assert "ESB12345678" in html


def test_pdf_html_unchanged_without_entity(app, invoice):
    from app.utils.pdf_generator import InvoicePDFGenerator

    html = InvoicePDFGenerator(invoice)._generate_html()
    assert "client-entity" not in html


# --- invoice form ----------------------------------------------------------------------------------


def test_create_form_has_bill_to(app, authenticated_client, project, entity):
    html = authenticated_client.get("/invoices/new").get_data(as_text=True)
    assert 'id="billToBlock"' in html
    assert 'name="client_entity_id"' in html
    assert "Example Holding S.L." in html


def test_create_form_without_module(app, authenticated_client, project, entity):
    _disable_module()
    html = authenticated_client.get("/invoices/new").get_data(as_text=True)
    assert 'name="client_entity_id"' not in html


def test_create_invoice_with_entity(app, authenticated_client, project, test_client, entity):
    resp = authenticated_client.post(
        "/invoices/create",
        data=_create_form(
            project, test_client, client_entity_id=entity.id, client_name="Example Holding S.L.", client_address="x"
        ),
    )
    assert resp.status_code == 302
    inv = _newest_invoice()
    assert inv.client_entity_id == entity.id
    assert inv.buyer_snapshot["registration_number"] == "B12345678"
    assert inv.client_name == "Example Holding S.L."  # the form fields are what the user saw
    assert inv.client_address == "x"


def test_create_invoice_with_client_details(app, authenticated_client, project, test_client, entity):
    authenticated_client.post("/invoices/create", data=_create_form(project, test_client, client_entity_id=""))
    inv = _newest_invoice()
    assert inv.client_entity_id is None
    assert inv.buyer_snapshot is None


def test_create_rejects_entity_of_another_client(app, authenticated_client, project, test_client, user):
    other = Client(name="Other Client", created_by=user.id)
    db.session.add(other)
    db.session.commit()
    foreign = ClientEntity(client_id=other.id, legal_name="Foreign Ltd")
    db.session.add(foreign)
    db.session.commit()
    before = Invoice.query.count()
    resp = authenticated_client.post(
        "/invoices/create", data=_create_form(project, test_client, client_entity_id=foreign.id)
    )
    assert resp.status_code == 302
    assert Invoice.query.count() == before


def test_create_rejects_archived_entity(app, authenticated_client, project, test_client, entity):
    entity.status = "archived"
    db.session.commit()
    before = Invoice.query.count()
    authenticated_client.post("/invoices/create", data=_create_form(project, test_client, client_entity_id=entity.id))
    assert Invoice.query.count() == before


def test_create_ignores_field_when_module_off(app, authenticated_client, project, test_client, entity):
    _disable_module()
    authenticated_client.post("/invoices/create", data=_create_form(project, test_client, client_entity_id=entity.id))
    inv = _newest_invoice()
    assert inv.client_entity_id is None


def _edit_form(inv, **extra):
    data = {
        "client_name": inv.client_name,
        "due_date": inv.due_date.strftime("%Y-%m-%d"),
        "tax_rate": "0",
        "currency_code": "EUR",
    }
    data.update(extra)
    return data


def test_draft_refreshes_copy(app, admin_authenticated_client, user, project, test_client, entity):
    inv = _invoice_for(project, test_client, user, entity)
    inv.status = "draft"
    db.session.commit()
    entity.vat_number = "ESNEW"
    db.session.commit()
    admin_authenticated_client.post(f"/invoices/{inv.id}/edit", data=_edit_form(inv, client_entity_id=entity.id))
    db.session.refresh(inv)
    assert inv.buyer_snapshot["vat_number"] == "ESNEW"


def test_draft_keeps_its_archived_entity(app, admin_authenticated_client, user, project, test_client, entity):
    inv = _invoice_for(project, test_client, user, entity)
    inv.status = "draft"
    entity.status = "archived"
    db.session.commit()
    html = admin_authenticated_client.get(f"/invoices/{inv.id}/edit").get_data(as_text=True)
    assert "Example Holding S.L." in html  # still offered on its own draft
    admin_authenticated_client.post(f"/invoices/{inv.id}/edit", data=_edit_form(inv, client_entity_id=entity.id))
    db.session.refresh(inv)
    assert inv.client_entity_id == entity.id


def test_sent_invoice_keeps_copy(app, admin_authenticated_client, user, project, test_client, entity):
    inv = _invoice_for(project, test_client, user, entity)
    inv.status = "sent"
    db.session.commit()
    entity.vat_number = "ESNEW"
    db.session.commit()
    admin_authenticated_client.post(f"/invoices/{inv.id}/edit", data=_edit_form(inv, client_entity_id=entity.id))
    db.session.refresh(inv)
    assert inv.buyer_snapshot["vat_number"] == "ESB12345678"


def test_invoice_page_shows_registration_and_vat(app, admin_authenticated_client, user, project, test_client, entity):
    inv = _invoice_for(project, test_client, user, entity)
    html = admin_authenticated_client.get(f"/invoices/{inv.id}").get_data(as_text=True)
    assert "B12345678" in html


# --- client page and entity pages ---------------------------------------------------------------------


def test_client_page_card(app, admin_authenticated_client, test_client, entity):
    html = admin_authenticated_client.get(f"/clients/{test_client.id}").get_data(as_text=True)
    assert "Legal entities" in html
    assert "Example Holding S.L." in html
    assert f"/clients/{test_client.id}/legal-entities/new" in html


def test_client_page_card_hidden_when_module_off(app, admin_authenticated_client, test_client, entity):
    _disable_module()
    html = admin_authenticated_client.get(f"/clients/{test_client.id}").get_data(as_text=True)
    assert "Example Holding S.L." not in html


def test_admin_creates_edits_and_archives(app, admin_authenticated_client, test_client):
    base = f"/clients/{test_client.id}/legal-entities"
    assert admin_authenticated_client.get(f"{base}/new").status_code == 200
    resp = admin_authenticated_client.post(
        f"{base}/new", data={"legal_name": "New Entity GmbH", "country": "de", "vat_number": "DE123"}
    )
    assert resp.status_code == 302
    e = ClientEntity.query.filter_by(legal_name="New Entity GmbH").one()
    assert e.country == "DE"
    admin_authenticated_client.post(f"{base}/{e.id}", data={"legal_name": "Renamed GmbH", "status": "active"})
    assert db.session.get(ClientEntity, e.id).legal_name == "Renamed GmbH"
    admin_authenticated_client.post(f"{base}/{e.id}/archive")
    assert db.session.get(ClientEntity, e.id).status == "archived"
    assert admin_authenticated_client.get(f"{base}/{e.id}").status_code == 200


def test_create_requires_legal_name(app, admin_authenticated_client, test_client):
    resp = admin_authenticated_client.post(
        f"/clients/{test_client.id}/legal-entities/new", data={"legal_name": "", "vat_number": "KEEP-ME"}
    )
    assert resp.status_code == 400
    assert "KEEP-ME" in resp.get_data(as_text=True)


def test_used_entity_cannot_be_deleted(app, admin_authenticated_client, user, project, test_client, entity):
    _invoice_for(project, test_client, user, entity)
    admin_authenticated_client.post(f"/clients/{test_client.id}/legal-entities/{entity.id}/delete")
    assert db.session.get(ClientEntity, entity.id) is not None


def test_unused_entity_can_be_deleted(app, admin_authenticated_client, test_client, entity):
    admin_authenticated_client.post(f"/clients/{test_client.id}/legal-entities/{entity.id}/delete")
    assert db.session.get(ClientEntity, entity.id) is None


def test_entity_of_another_client_is_404(app, admin_authenticated_client, user, entity):
    other = Client(name="Other Client", created_by=user.id)
    db.session.add(other)
    db.session.commit()
    assert admin_authenticated_client.get(f"/clients/{other.id}/legal-entities/{entity.id}").status_code == 404


def test_entity_pages_need_edit_rights(app, authenticated_client, test_client, entity):
    resp = authenticated_client.get(f"/clients/{test_client.id}/legal-entities/{entity.id}")
    assert resp.status_code in (302, 403)


def test_entity_pages_off_with_module(app, admin_authenticated_client, test_client):
    _disable_module()
    resp = admin_authenticated_client.get(f"/clients/{test_client.id}/legal-entities/new")
    assert resp.status_code in (302, 403, 404)


# --- module switched off after invoices were billed to entities ------------------------------------


def test_module_off_keeps_sent_invoice(app, admin_authenticated_client, user, project, test_client, entity):
    from app.utils.pdf_generator import InvoicePDFGenerator

    inv = _invoice_for(project, test_client, user, entity)
    inv.status = "sent"
    db.session.commit()
    _disable_module()
    assert "ESB12345678" in InvoicePDFGenerator(inv)._generate_html()
    assert "B12345678" in admin_authenticated_client.get(f"/invoices/{inv.id}").get_data(as_text=True)
    db.session.refresh(inv)
    assert inv.client_entity_id == entity.id


def test_module_off_draft_keeps_its_entity(app, admin_authenticated_client, user, project, test_client, entity):
    inv = _invoice_for(project, test_client, user, entity)
    inv.status = "draft"
    db.session.commit()
    _disable_module()
    entity.vat_number = "ESNEW"
    db.session.commit()
    html = admin_authenticated_client.get(f"/invoices/{inv.id}/edit").get_data(as_text=True)
    assert 'name="client_entity_id"' not in html
    assert "Bill to: Example Holding S.L." in html
    admin_authenticated_client.post(f"/invoices/{inv.id}/edit", data=_edit_form(inv))
    db.session.refresh(inv)
    assert inv.client_entity_id == entity.id
    assert inv.buyer_snapshot["vat_number"] == "ESB12345678"  # no refresh while the module is off


# --- together with the Legal entities module (billing_entities) ------------------------------------


@pytest.fixture
def seller(app):
    from app.models import BillingEntity, PaymentAccount

    e = BillingEntity(short_name="Seller One", legal_name="SELLER ONE LLC", number_format="S1-{YYYY}-{MM}")
    db.session.add(e)
    db.session.commit()
    a = PaymentAccount(
        billing_entity_id=e.id, currency="EUR", iban="DE89370400440532013000", details_text="IBAN {IBAN}"
    )
    db.session.add(a)
    db.session.commit()
    return e, a


def _modules_off(*ids):
    settings = Settings.get_settings()
    settings.disabled_module_ids = list(ids)
    db.session.commit()


@pytest.mark.parametrize(
    "off, has_seller_block, has_bill_to",
    [
        ([], True, True),
        (["billing_entities"], False, True),
        (["client_entities"], True, False),
        (["billing_entities", "client_entities"], False, False),
    ],
)
def test_form_per_module_combination(
    app, authenticated_client, project, seller, entity, off, has_seller_block, has_bill_to
):
    _modules_off(*off)
    html = authenticated_client.get("/invoices/new").get_data(as_text=True)
    assert ('id="billingSellerBlock"' in html) is has_seller_block
    assert ('id="billToBlock"' in html) is has_bill_to
    if has_seller_block:
        assert "data-bill-to-host" in html and 'id="billToSlot"' in html and 'id="billToPreviewSlot"' in html


@pytest.mark.parametrize(
    "off", [[], ["billing_entities"], ["client_entities"], ["billing_entities", "client_entities"]]
)
def test_create_invoice_per_module_combination(app, authenticated_client, project, test_client, seller, entity, off):
    _modules_off(*off)
    billing_entity, account = seller
    resp = authenticated_client.post(
        "/invoices/create",
        data=_create_form(
            project,
            test_client,
            billing_entity_id=billing_entity.id,
            payment_account_id=account.id,
            client_entity_id=entity.id,
        ),
    )
    assert resp.status_code == 302
    inv = _newest_invoice()
    assert (inv.billing_entity_id == billing_entity.id) is ("billing_entities" not in off)
    assert (inv.client_entity_id == entity.id) is ("client_entities" not in off)


def test_pdf_prints_seller_and_buyer(app, user, project, test_client, seller, entity):
    from app.utils import billing_entities as billing
    from app.utils.pdf_generator import InvoicePDFGenerator

    billing_entity, account = seller
    inv = _invoice_for(project, test_client, user, entity)
    billing.apply_to_invoice(inv, billing_entity, account)
    db.session.commit()
    html = InvoicePDFGenerator(inv)._generate_html()
    assert "SELLER ONE LLC" in html
    assert "ESB12345678" in html
