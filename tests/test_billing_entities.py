"""Legal entities module: our billing entities, their payment accounts, and From / Pay to on invoices.

An invoice may name the legal entity that issues it and the account the client pays to. Their
details are copied into the invoice when it is created, and the PDF prints them instead of
Settings.company_*. With no entity on the invoice, or the module off, nothing changes.
"""

from datetime import date, timedelta

import pytest

from app import db
from app.models import BillingEntity, Invoice, PaymentAccount, Settings
from app.utils import billing_entities as billing

pytestmark = [pytest.mark.integration]

PAYMENT_TEXT = (
    "Account with institution: Example Bank AG\n"
    "SWIFT: EXAMDEFFXXX\n"
    "Beneficiary: Example Consulting GmbH\n"
    "Account (IBAN): {IBAN}"
)
IBAN = "DE89370400440532013000"


@pytest.fixture
def entity(app):
    e = BillingEntity(
        short_name="Example Consulting",
        legal_name="EXAMPLE CONSULTING GMBH",
        country="DE",
        registration_number="HRB 12345",
        address="Example Street 1, Berlin",
        email="billing@example.com",
        number_format="EC-{YYYY}-{MM}",
        default_vat_category="O",
        default_terms="Electronic version: valid without signature.",
    )
    db.session.add(e)
    db.session.commit()
    return e


@pytest.fixture
def account(app, entity):
    a = PaymentAccount(
        billing_entity_id=entity.id, currency="USD", iban=IBAN, bank_name="Example Bank", details_text=PAYMENT_TEXT
    )
    db.session.add(a)
    db.session.commit()
    return a


def _create_form(project, test_client, **extra):
    data = {
        "project_id": project.id,
        "client_name": test_client.name,
        "due_date": (date.today() + timedelta(days=30)).strftime("%Y-%m-%d"),
        "tax_rate": "0",
        "currency_code": "USD",
    }
    data.update(extra)
    return data


def _newest_invoice():
    return Invoice.query.order_by(Invoice.id.desc()).first()


def _disable_module():
    settings = Settings.get_settings()
    settings.disabled_module_ids = ["billing_entities"]
    db.session.commit()


# --- model and helpers ---------------------------------------------------------------------------


def test_payment_text_fills_iban(app, account):
    text = account.printed_text
    assert IBAN in text
    assert "{IBAN}" not in text
    assert account.label == "Example Bank · USD · DE89…3000"


def test_number_uses_billing_period_month(app, entity):
    assert billing.format_invoice_number(entity, date(2026, 11, 11)) == "EC-2026-10"
    assert billing.format_invoice_number(entity, date(2027, 1, 5)) == "EC-2026-12"


def test_taken_number_gets_suffix(app, entity, invoice):
    invoice.invoice_number = "EC-2026-10"
    db.session.commit()
    assert billing.allocate_invoice_number(entity, date(2026, 11, 11)) == "EC-2026-10-2"


def test_seq_token_uses_entity_counter(app, entity):
    entity.number_format = "INV-{YYYY}-{SEQ}"
    assert billing.allocate_invoice_number(entity, date(2026, 12, 1)) == "INV-2026-1"
    assert billing.allocate_invoice_number(entity, date(2026, 12, 2)) == "INV-2026-2"
    assert entity.number_counter == 2


def test_seller_settings_prints_invoice_seller(app, entity, account, invoice):
    settings = Settings.get_settings()
    settings.company_name = "Settings Company"
    billing.apply_to_invoice(invoice, entity, account)
    db.session.commit()

    view = billing.seller_settings_for(invoice, settings)
    assert view.company_name == "EXAMPLE CONSULTING GMBH"
    assert view.company_tax_id == "HRB 12345"
    assert view.company_iban == IBAN
    assert "EXAMDEFFXXX<br/>" in view.company_bank_info
    assert view.has_logo() is False
    assert view.currency == settings.currency  # everything else from Settings


def test_seller_settings_without_entity_is_settings(app, invoice):
    settings = Settings.get_settings()
    assert billing.seller_settings_for(invoice, settings) is settings


def test_pdf_html_uses_invoice_seller(app, entity, account, invoice):
    from app.utils.pdf_generator import InvoicePDFGenerator

    settings = Settings.get_settings()
    settings.company_name = "Settings Company"
    db.session.commit()
    billing.apply_to_invoice(invoice, entity, account)
    db.session.commit()

    html = InvoicePDFGenerator(invoice)._generate_html()
    assert "EXAMPLE CONSULTING GMBH" in html
    assert IBAN in html
    assert "Settings Company" not in html


def test_snapshot_does_not_follow_entity_edits(app, entity, account, invoice):
    billing.apply_to_invoice(invoice, entity, account)
    db.session.commit()
    entity.legal_name = "Renamed"
    db.session.commit()
    assert billing.seller_settings_for(invoice, Settings.get_settings()).company_name == "EXAMPLE CONSULTING GMBH"


def test_draft_save_takes_current_entity_details(app, admin_authenticated_client, entity, account, invoice):
    billing.apply_to_invoice(invoice, entity, account)
    invoice.status = "draft"
    invoice.currency_code = "USD"
    db.session.commit()
    entity.legal_name = "Renamed"
    account.details_text = "New text {IBAN}"
    db.session.commit()
    admin_authenticated_client.post(
        f"/invoices/{invoice.id}/edit",
        data={
            "client_name": invoice.client_name,
            "due_date": invoice.due_date.strftime("%Y-%m-%d"),
            "tax_rate": "0",
            "currency_code": "USD",
            "billing_entity_id": entity.id,
            "payment_account_id": account.id,
        },
    )
    db.session.refresh(invoice)
    assert invoice.seller_snapshot["legal_name"] == "Renamed"
    assert invoice.payment_details_text == f"New text {IBAN}"


# --- invoice form ----------------------------------------------------------------------------------


def test_create_form_shows_from_and_pay_to(app, authenticated_client, project, entity, account):
    html = authenticated_client.get("/invoices/create").get_data(as_text=True)
    assert 'name="billing_entity_id"' in html
    assert 'name="payment_account_id"' in html
    assert "Example Consulting" in html


def test_create_form_hidden_when_module_off(app, authenticated_client, project, entity, account):
    _disable_module()
    html = authenticated_client.get("/invoices/create").get_data(as_text=True)
    assert 'name="billing_entity_id"' not in html


def test_create_invoice_with_entity(app, authenticated_client, project, test_client, entity, account):
    resp = authenticated_client.post(
        "/invoices/create",
        data=_create_form(project, test_client, billing_entity_id=entity.id, payment_account_id=account.id),
    )
    assert resp.status_code in (200, 302)
    inv = _newest_invoice()
    assert inv.billing_entity_id == entity.id
    assert inv.payment_account_id == account.id
    assert inv.seller_snapshot["legal_name"] == "EXAMPLE CONSULTING GMBH"
    assert IBAN in inv.payment_details_text
    assert inv.invoice_number == billing.format_invoice_number(entity, inv.issue_date)


def test_create_invoice_keeps_typed_number(app, authenticated_client, project, test_client, entity, account):
    authenticated_client.post(
        "/invoices/create",
        data=_create_form(
            project,
            test_client,
            billing_entity_id=entity.id,
            payment_account_id=account.id,
            invoice_number="EC-2026-11-manual",
            invoice_number_preview="EC-2026-11",
        ),
    )
    assert _newest_invoice().invoice_number == "EC-2026-11-manual"


def test_create_invoice_rejects_account_in_other_currency(
    app, authenticated_client, project, test_client, entity, account
):
    before = Invoice.query.count()
    authenticated_client.post(
        "/invoices/create",
        data=_create_form(
            project, test_client, currency_code="EUR", billing_entity_id=entity.id, payment_account_id=account.id
        ),
    )
    assert Invoice.query.count() == before


def test_create_invoice_without_entity_is_unchanged(app, authenticated_client, project, test_client, entity):
    authenticated_client.post("/invoices/create", data=_create_form(project, test_client))
    inv = _newest_invoice()
    assert inv.billing_entity_id is None
    assert inv.seller_snapshot is None


def test_create_ignores_entity_when_module_off(app, authenticated_client, project, test_client, entity, account):
    _disable_module()
    authenticated_client.post(
        "/invoices/create",
        data=_create_form(project, test_client, billing_entity_id=entity.id, payment_account_id=account.id),
    )
    assert _newest_invoice().billing_entity_id is None


def test_form_defaults_to_clients_last_entity(app, project, test_client, entity, invoice):
    invoice.billing_entity_id = entity.id
    db.session.commit()
    assert billing.default_entity_for_client(test_client.id) == entity


# --- admin pages -----------------------------------------------------------------------------------


def test_admin_creates_entity_and_account(app, admin_authenticated_client):
    resp = admin_authenticated_client.post(
        "/admin/legal-entities/new",
        data={
            "short_name": "Second Entity Ltd",
            "legal_name": "Second Entity Ltd",
            "country": "gb",
            "number_format": "INV-{SEQ}",
        },
    )
    assert resp.status_code == 302
    entity = BillingEntity.query.filter_by(short_name="Second Entity Ltd").one()
    assert entity.country == "GB"

    resp = admin_authenticated_client.post(
        f"/admin/legal-entities/{entity.id}/accounts/new",
        data={
            "currency": "eur",
            "iban": "GB82 WEST 1234 5698 7654 32",
            "bank_name": "Other Bank",
            "details_text": "IBAN: {IBAN}",
        },
    )
    assert resp.status_code == 302
    acc = PaymentAccount.query.filter_by(billing_entity_id=entity.id).one()
    assert acc.currency == "EUR"
    assert acc.iban == "GB82WEST12345698765432"
    assert acc.printed_text == "IBAN: GB82WEST12345698765432"


def test_admin_cannot_add_duplicate_iban_currency(app, admin_authenticated_client, entity, account):
    admin_authenticated_client.post(
        f"/admin/legal-entities/{entity.id}/accounts/new",
        data={"currency": "USD", "iban": IBAN},
    )
    assert PaymentAccount.query.filter_by(iban=IBAN, currency="USD").count() == 1


def test_used_account_cannot_be_deleted(app, admin_authenticated_client, entity, account, invoice):
    billing.apply_to_invoice(invoice, entity, account)
    db.session.commit()
    admin_authenticated_client.post(f"/admin/legal-entities/{entity.id}/accounts/{account.id}/delete")
    assert PaymentAccount.query.get(account.id) is not None


def test_unused_account_can_be_deleted(app, admin_authenticated_client, entity, account):
    admin_authenticated_client.post(f"/admin/legal-entities/{entity.id}/accounts/{account.id}/delete")
    assert PaymentAccount.query.get(account.id) is None


def test_admin_pages_render(app, admin_authenticated_client, entity, account):
    assert admin_authenticated_client.get("/admin/legal-entities").status_code == 200
    page = admin_authenticated_client.get(f"/admin/legal-entities/{entity.id}/accounts/{account.id}")
    assert page.status_code == 200
    assert "EXAMDEFFXXX" in page.get_data(as_text=True)


def test_admin_pages_need_admin(app, authenticated_client, entity):
    resp = authenticated_client.get("/admin/legal-entities")
    assert resp.status_code in (302, 403)


# --- screens: Add entity page, step 2, redirects -------------------------------------------------


def test_create_leads_to_account_step(app, admin_authenticated_client):
    resp = admin_authenticated_client.post("/admin/legal-entities/new", data={"short_name": "DVS UAB"})
    entity = BillingEntity.query.filter_by(short_name="DVS UAB").one()
    assert resp.status_code == 302
    assert f"/admin/legal-entities/{entity.id}/accounts/new" in resp.headers["Location"]
    assert "created=1" in resp.headers["Location"]
    page = admin_authenticated_client.get(resp.headers["Location"]).get_data(as_text=True)
    assert "Legal entity created." in page
    assert "Skip, add later" in page


def test_create_error_keeps_typed_values(app, admin_authenticated_client):
    resp = admin_authenticated_client.post(
        "/admin/legal-entities/new", data={"short_name": "", "legal_name": "Typed Legal Name LLC"}
    )
    assert resp.status_code == 400
    assert "Typed Legal Name LLC" in resp.get_data(as_text=True)
    assert BillingEntity.query.count() == 0


def test_add_entity_is_a_separate_page(app, admin_authenticated_client, entity):
    html = admin_authenticated_client.get("/admin/legal-entities/new").get_data(as_text=True)
    assert "Create entity" in html
    assert "Back to legal entities" in html


def test_save_and_add_another(app, admin_authenticated_client, entity):
    resp = admin_authenticated_client.post(
        f"/admin/legal-entities/{entity.id}/accounts/new",
        data={"currency": "USD", "iban": IBAN, "next": "another"},
    )
    assert resp.headers["Location"].endswith(f"/admin/legal-entities/{entity.id}/accounts/new")
    resp = admin_authenticated_client.post(
        f"/admin/legal-entities/{entity.id}/accounts/new", data={"currency": "EUR", "iban": IBAN}
    )
    assert resp.headers["Location"].endswith(f"/admin/legal-entities/{entity.id}")
    assert entity.payment_accounts.count() == 2


def test_entity_page_lists_accounts_above_defaults(app, admin_authenticated_client, entity, account):
    html = admin_authenticated_client.get(f"/admin/legal-entities/{entity.id}").get_data(as_text=True)
    assert html.index("DE89 3704 0044") < html.index("Number format")
    assert html.index("Number format") < html.index("Save changes")
