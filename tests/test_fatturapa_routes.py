"""Route tests for FatturaPA export and SDI send."""

from datetime import date
from decimal import Decimal

import pytest


@pytest.fixture
def fatturapa_ready(app, db_session, authenticated_client, user):
    from app.models import Client, Invoice, InvoiceItem, Project, Settings

    with app.app_context():
        settings = Settings.get_settings()
        settings.company_name = "Acme Srl"
        settings.company_street = "Via Roma 1"
        settings.company_postcode = "20121"
        settings.company_city = "Milano"
        settings.company_country = "IT"
        settings.company_provincia = "MI"
        settings.company_tax_id = "IT01234567890"
        settings.company_codice_fiscale = "01234567890"
        settings.company_regime_fiscale = "RF01"
        settings.company_iban = "IT60X0542811101000000123456"
        settings.sdi_enabled = True
        settings.sdi_transport_url = "https://adapter.example/send"
        settings.set_secret("sdi_transport_token", "tok")

        client = Client(
            name="FatturaPA Cliente",
            email="acquisti@cliente.it",
            street="Corso Italia 10",
            postcode="00187",
            city="Roma",
            country="IT",
            provincia="RM",
            vat_id="IT09876543210",
            codice_fiscale="09876543210",
            sdi_codice_destinatario="ABC1234",
            created_by=user.id,
        )
        client.status = "active"
        db_session.add(client)
        db_session.flush()

        project = Project(
            name="FatturaPA Project",
            client_id=client.id,
            description="FP test",
            billable=True,
            hourly_rate=Decimal("75.00"),
            created_by=user.id,
        )
        project.status = "active"
        db_session.add(project)
        db_session.flush()

        inv = Invoice(
            invoice_number="FP-ROUTE-1",
            project_id=project.id,
            client_id=client.id,
            client_name=client.name,
            due_date=date(2026, 12, 31),
            created_by=user.id,
            tax_rate=Decimal("22"),
            subtotal=Decimal("100.00"),
            tax_amount=Decimal("22.00"),
            total_amount=Decimal("122.00"),
            currency_code="EUR",
            issue_date=date(2026, 11, 7),
        )
        db_session.add(inv)
        db_session.flush()
        db_session.add(
            InvoiceItem(
                invoice_id=inv.id,
                description="Consulenza",
                quantity=Decimal("1"),
                unit_price=Decimal("100.00"),
            )
        )
        db_session.commit()
        return inv.id


def test_export_fatturapa_ok(authenticated_client, fatturapa_ready):
    resp = authenticated_client.get(f"/invoices/{fatturapa_ready}/export/fatturapa")
    assert resp.status_code == 200
    assert "xml" in (resp.mimetype or "")
    body = resp.data.decode("utf-8")
    assert "FatturaElettronica" in body
    assert "FPR12" in body


def test_export_fatturapa_not_ready(authenticated_client, app, db_session, user):
    from app.models import Client, Invoice, Project, Settings

    with app.app_context():
        settings = Settings.get_settings()
        settings.company_name = "Acme Srl"
        settings.company_street = "Via Roma 1"
        settings.company_postcode = "20121"
        settings.company_city = "Milano"
        settings.company_country = "IT"
        settings.company_provincia = "MI"
        settings.company_tax_id = "IT01234567890"
        settings.company_regime_fiscale = "RF01"

        client = Client(
            name="Incomplete SDI Client",
            email="x@example.it",
            street="Via 1",
            postcode="20100",
            city="Milano",
            country="IT",
            provincia="MI",
            vat_id="IT01111111111",
            # intentionally no sdi_codice_destinatario / pec
            created_by=user.id,
        )
        client.status = "active"
        db_session.add(client)
        db_session.flush()
        project = Project(
            name="Incomplete Project",
            client_id=client.id,
            billable=True,
            hourly_rate=Decimal("50"),
            created_by=user.id,
        )
        project.status = "active"
        db_session.add(project)
        db_session.flush()
        inv = Invoice(
            invoice_number="FP-BAD-1",
            project_id=project.id,
            client_id=client.id,
            client_name=client.name,
            due_date=date(2026, 12, 31),
            created_by=user.id,
            currency_code="EUR",
            issue_date=date(2026, 11, 7),
        )
        db_session.add(inv)
        db_session.commit()
        inv_id = inv.id

    resp = authenticated_client.get(f"/invoices/{inv_id}/export/fatturapa")
    assert resp.status_code == 400
    data = resp.get_json()
    assert data["error"] == "fatturapa_not_ready"
    assert data["messages"]


def test_send_sdi_permission_and_mock(authenticated_client, fatturapa_ready, monkeypatch):
    from app.services.sdi_service import SdiService

    class FakeTx:
        id = 7
        status = "sent"
        filename = "IT01234567890_00001.xml"

    def fake_send(self, invoice, triggered_by_user_id=None):
        return True, FakeTx(), "Invoice sent via SDI"

    monkeypatch.setattr(SdiService, "send_invoice", fake_send)
    resp = authenticated_client.post(f"/invoices/{fatturapa_ready}/send-sdi")
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["success"] is True
    assert data["sdi_tx_id"] == 7
