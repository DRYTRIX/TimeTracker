"""SDI service and transport tests with mocked HTTP."""

from datetime import date
from decimal import Decimal
from unittest.mock import MagicMock, patch

import pytest

from app.integrations.sdi_transport import GenericSdiTransport, SdiTransportError, bridge_base_url
from app.models.invoice_sdi import InvoiceSdiTransmission, SDI_FINAL_STATUSES


def test_bridge_base_url_strips_send():
    assert bridge_base_url("https://example.com/send") == "https://example.com"
    assert bridge_base_url("https://example.com/api/send/") == "https://example.com/api"


def test_generic_transport_send_success():
    transport = GenericSdiTransport(url="https://adapter.example/send", token="secret", timeout=10)
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {"message_id": "msg-1", "sdi_identifier": "SDI123"}
    with patch("app.integrations.sdi_transport.requests.post", return_value=mock_resp) as post:
        data = transport.send(
            filename="IT01234567890_00001.xml",
            formato="FPR12",
            codice_destinatario="ABC1234",
            pec=None,
            xml="<xml/>",
            sha256="abc",
        )
    assert data["message_id"] == "msg-1"
    args, kwargs = post.call_args
    assert kwargs["headers"]["Authorization"] == "Bearer secret"
    assert "xml_base64" in kwargs["json"]


def test_generic_transport_send_http_error():
    transport = GenericSdiTransport(url="https://adapter.example/send", token=None)
    mock_resp = MagicMock()
    mock_resp.status_code = 500
    mock_resp.text = "boom"
    with patch("app.integrations.sdi_transport.requests.post", return_value=mock_resp):
        with pytest.raises(SdiTransportError):
            transport.send(
                filename="x.xml",
                formato="FPR12",
                codice_destinatario="ABC1234",
                pec=None,
                xml="<xml/>",
                sha256="abc",
            )


def test_apply_notification_transitions():
    tx = InvoiceSdiTransmission(invoice_id=1, status="sent")
    tx.apply_notification("RC")
    assert tx.status == "delivered"
    tx2 = InvoiceSdiTransmission(invoice_id=1, status="sent")
    tx2.apply_notification("NS", detail="error 00404")
    assert tx2.status == "rejected"
    assert "00404" in (tx2.error_message or "")
    tx3 = InvoiceSdiTransmission(invoice_id=1, status="sent")
    tx3.apply_notification("NE", detail="Esito accettato")
    assert tx3.status == "accepted"
    tx4 = InvoiceSdiTransmission(invoice_id=1, status="sent")
    tx4.apply_notification("NE", detail="Documento rifiutato EC02")
    assert tx4.status == "refused"
    assert "delivered" in SDI_FINAL_STATUSES


def _configure_italian_settings(settings):
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
    settings.set_secret("sdi_transport_token", "tok-secret")
    settings.sdi_timeout = 15


@pytest.fixture
def sdi_ready_invoice(app, db_session, user):
    """Invoice + Italian seller/client fields for SDI send (own client to avoid audit locks)."""
    from app.models import Client, Invoice, InvoiceItem, Project, Settings

    with app.app_context():
        settings = Settings.get_settings()
        _configure_italian_settings(settings)

        client = Client(
            name="SDI Cliente Spa",
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
            name="SDI Project",
            client_id=client.id,
            description="SDI test",
            billable=True,
            hourly_rate=Decimal("75.00"),
            created_by=user.id,
        )
        project.status = "active"
        db_session.add(project)
        db_session.flush()

        inv = Invoice(
            invoice_number="SDI-TEST-1",
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


def test_sdi_service_send_success(app, db_session, sdi_ready_invoice):
    from app.models import Invoice, InvoiceSdiTransmission
    from app.services.sdi_service import SdiService

    with app.app_context():
        inv = Invoice.query.get(sdi_ready_invoice)
        mock_transport = MagicMock()
        mock_transport.send.return_value = {"message_id": "m-99", "sdi_identifier": "SDI99"}

        with patch.object(SdiService, "_transport", return_value=mock_transport):
            ok, tx, msg = SdiService().send_invoice(inv)

        assert ok is True
        assert tx is not None
        assert tx.status == "sent"
        assert tx.message_id == "m-99"
        assert tx.xml and "FatturaElettronica" in tx.xml
        assert InvoiceSdiTransmission.query.filter_by(invoice_id=inv.id).count() == 1


def test_sdi_service_send_disabled(app, db_session, sdi_ready_invoice):
    from app.models import Invoice, Settings
    from app.services.sdi_service import SdiService

    with app.app_context():
        Settings.get_settings().sdi_enabled = False
        db_session.commit()
        inv = Invoice.query.get(sdi_ready_invoice)
        ok, tx, msg = SdiService().send_invoice(inv)
        assert ok is False
        assert tx is None
        assert "not enabled" in msg.lower()


def test_sdi_service_refresh_status(app, db_session, sdi_ready_invoice):
    from app.models import Invoice, InvoiceSdiTransmission
    from app.services.sdi_service import SdiService

    with app.app_context():
        inv = Invoice.query.get(sdi_ready_invoice)
        tx = InvoiceSdiTransmission(
            invoice_id=inv.id,
            status="sent",
            message_id="m-1",
            formato="FPR12",
            progressivo="00001",
        )
        db_session.add(tx)
        db_session.commit()

        mock_transport = MagicMock()
        mock_transport.get_status.return_value = {
            "status": "delivered",
            "sdi_identifier": "SDI1",
            "notifications": [{"type": "RC", "date": "2026-11-08", "detail": "ok"}],
        }
        with patch.object(SdiService, "_transport", return_value=mock_transport):
            result = SdiService().refresh_status(tx)

        assert result["ok"] is True
        assert tx.status == "delivered"
        assert tx.sdi_identifier == "SDI1"
