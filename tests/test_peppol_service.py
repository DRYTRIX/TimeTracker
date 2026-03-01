from datetime import date, timedelta
from decimal import Decimal

import pytest

from app import db
from app.models import Client, Invoice, InvoiceItem, InvoicePeppolTransmission, Project, User


class _FakeResponse:
    def __init__(self, status_code=200, json_data=None, text="", content_type="application/json"):
        self.status_code = status_code
        self._json_data = json_data or {}
        self.text = text
        self.headers = {"content-type": content_type}

    def json(self):
        return self._json_data


@pytest.mark.unit
def test_peppol_service_disabled_returns_error(app):
    from app.services import PeppolService

    with app.app_context():
        svc = PeppolService()
        ok, tx, msg = svc.send_invoice(invoice=None)  # invoice isn't accessed when disabled
        assert ok is False
        assert tx is None
        assert "not enabled" in msg.lower()


@pytest.mark.unit
def test_peppol_service_requires_client_endpoint(app, monkeypatch):
    from app.services import PeppolService

    with app.app_context():
        monkeypatch.setenv("PEPPOL_ENABLED", "true")
        monkeypatch.setenv("PEPPOL_SENDER_ENDPOINT_ID", "9915:123456789")
        monkeypatch.setenv("PEPPOL_SENDER_SCHEME_ID", "9915")

        user = User(username="peppoluser", role="user", email="peppoluser@example.com")
        user.is_active = True
        user.set_password("password123")
        db.session.add(user)

        client = Client(name="Peppol Client", email="client@example.com", address="Street 1")
        db.session.add(client)
        db.session.commit()

        project = Project(name="Peppol Project", client_id=client.id, billable=True, hourly_rate=Decimal("75.00"))
        project.status = "active"
        db.session.add(project)
        db.session.commit()

        inv = Invoice(
            invoice_number="INV-PEPPOL-001",
            project_id=project.id,
            client_name=client.name,
            client_id=client.id,
            due_date=date.today() + timedelta(days=30),
            created_by=user.id,
        )
        db.session.add(inv)
        db.session.commit()

        svc = PeppolService()
        ok, tx, msg = svc.send_invoice(invoice=inv, triggered_by_user_id=user.id)
        assert ok is False
        assert tx is None
        assert "missing peppol endpoint" in msg.lower()


@pytest.mark.unit
def test_peppol_service_success_creates_transmission(app, monkeypatch):
    from app.services import PeppolService

    with app.app_context():
        monkeypatch.setenv("PEPPOL_ENABLED", "true")
        monkeypatch.setenv("PEPPOL_SENDER_ENDPOINT_ID", "9915:987654321")
        monkeypatch.setenv("PEPPOL_SENDER_SCHEME_ID", "9915")
        monkeypatch.setenv("PEPPOL_ACCESS_POINT_URL", "https://access-point.example.test/send")

        # Mock HTTP post
        def _fake_post(url, json, headers, timeout):
            assert url == "https://access-point.example.test/send"
            assert "payload" in json and "ubl_xml" in json["payload"]
            return _FakeResponse(status_code=200, json_data={"message_id": "MSG-123"})

        monkeypatch.setattr("app.integrations.peppol.requests.post", _fake_post)

        user = User(username="peppoluser2", role="user", email="peppoluser2@example.com")
        user.is_active = True
        user.set_password("password123")
        db.session.add(user)

        client = Client(name="Peppol Client 2", email="client2@example.com", address="Street 2")
        client.set_custom_field("peppol_endpoint_id", "0088:1234567890123")
        client.set_custom_field("peppol_scheme_id", "0088")
        db.session.add(client)
        db.session.commit()

        project = Project(name="Peppol Project 2", client_id=client.id, billable=True, hourly_rate=Decimal("75.00"))
        project.status = "active"
        db.session.add(project)
        db.session.commit()

        inv = Invoice(
            invoice_number="INV-PEPPOL-002",
            project_id=project.id,
            client_name=client.name,
            client_id=client.id,
            due_date=date.today() + timedelta(days=30),
            created_by=user.id,
            currency_code="EUR",
        )
        db.session.add(inv)
        db.session.commit()

        db.session.add(InvoiceItem(invoice_id=inv.id, description="Work", quantity=Decimal("2.00"), unit_price=Decimal("50.00")))
        db.session.commit()
        inv.calculate_totals()
        db.session.commit()

        svc = PeppolService()
        ok, tx, msg = svc.send_invoice(invoice=inv, triggered_by_user_id=user.id)
        assert ok is True
        assert tx is not None
        assert tx.status == "sent"
        assert tx.message_id == "MSG-123"
        assert tx.ubl_xml and "<Invoice" in tx.ubl_xml

        # Ensure persisted and queryable
        found = InvoicePeppolTransmission.query.filter_by(invoice_id=inv.id).first()
        assert found is not None
        assert found.status == "sent"

        # UBL must include PEPPOL mandatory elements (InvoiceTypeCode 380, BuyerReference)
        assert "InvoiceTypeCode" in tx.ubl_xml and "380" in tx.ubl_xml
        assert "BuyerReference" in tx.ubl_xml
        # EN 16931 requires unitCode on InvoicedQuantity (e.g. C62 = unit/each)
        assert "InvoicedQuantity" in tx.ubl_xml and 'unitCode="C62"' in tx.ubl_xml

