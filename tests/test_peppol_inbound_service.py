from decimal import Decimal
from unittest.mock import MagicMock

import pytest
import responses

from app import db
from app.models import Client, PeppolInboundDocument, Settings


SAMPLE_UBL = """<?xml version="1.0" encoding="UTF-8"?>
<Invoice xmlns="urn:oasis:names:specification:ubl:schema:xsd:Invoice-2"
         xmlns:cac="urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2"
         xmlns:cbc="urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2">
  <cbc:ID>SUP-42</cbc:ID>
  <cbc:IssueDate>2026-03-01</cbc:IssueDate>
  <cbc:DocumentCurrencyCode>EUR</cbc:DocumentCurrencyCode>
  <cac:AccountingSupplierParty>
    <cac:Party>
      <cbc:EndpointID schemeID="0208">0999999999</cbc:EndpointID>
      <cac:PartyLegalEntity>
        <cbc:RegistrationName>Supplier BV</cbc:RegistrationName>
      </cac:PartyLegalEntity>
    </cac:Party>
  </cac:AccountingSupplierParty>
  <cac:LegalMonetaryTotal>
    <cbc:PayableAmount currencyID="EUR">121.00</cbc:PayableAmount>
  </cac:LegalMonetaryTotal>
</Invoice>
"""


@pytest.mark.unit
def test_parse_ubl_summary_extracts_fields():
    from app.services.peppol_inbound_service import parse_ubl_summary

    summary = parse_ubl_summary(SAMPLE_UBL)
    assert summary["document_type"] == "invoice"
    assert summary["document_number"] == "SUP-42"
    assert str(summary["issue_date"]) == "2026-03-01"
    assert summary["currency"] == "EUR"
    assert summary["total_amount"] == Decimal("121.00")
    assert summary["supplier_peppol_id"] == "0208:0999999999"


@pytest.mark.unit
def test_bridge_base_url_from_access_point():
    from app.services.peppol_inbound_service import bridge_base_url_from_access_point

    assert bridge_base_url_from_access_point("http://peppol-bridge:8088/send") == "http://peppol-bridge:8088"
    assert bridge_base_url_from_access_point("http://peppol-bridge:8088/send/") == "http://peppol-bridge:8088"
    assert bridge_base_url_from_access_point("") is None


@pytest.mark.unit
def test_match_client_by_peppol_id(app):
    from app.services.peppol_inbound_service import match_client_by_peppol_id

    with app.app_context():
        client = Client(name="Matched Supplier", email="sup@example.com")
        client.set_custom_field("peppol_endpoint_id", "0999999999")
        client.set_custom_field("peppol_scheme_id", "0208")
        db.session.add(client)
        db.session.commit()

        found = match_client_by_peppol_id("0208:0999999999")
        assert found is not None
        assert found.id == client.id
        assert match_client_by_peppol_id("0208:0000000000") is None


@pytest.mark.unit
def test_upsert_document_is_idempotent(app):
    from app.services.peppol_inbound_service import PeppolInboundService

    with app.app_context():
        svc = PeppolInboundService()
        payload = {
            "id": "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
            "direction": "INCOMING",
            "type": "INVOICE",
            "ownerPeppolId": "0208:0123456789",
            "partnerPeppolId": "0208:0999999999",
            "ubl": SAMPLE_UBL,
            "processedStatus": "delivered",
        }
        row1, created1 = svc.upsert_document(payload, provider="letspeppol")
        db.session.commit()
        assert created1 is True
        assert row1.document_number == "SUP-42"
        assert row1.total_amount == Decimal("121.00")

        row2, created2 = svc.upsert_document(payload, provider="letspeppol")
        db.session.commit()
        assert created2 is False
        assert row2.id == row1.id
        assert PeppolInboundDocument.query.count() == 1


@pytest.mark.unit
@responses.activate
def test_poll_and_import_acks_after_store(app, monkeypatch):
    from app.services.peppol_inbound_service import PeppolInboundService

    with app.app_context():
        settings = Settings.get_settings()
        settings.peppol_enabled = True
        settings.peppol_inbox_enabled = True
        settings.peppol_access_point_url = "http://peppol-bridge:8088/send"
        settings.peppol_provider = "letspeppol"
        db.session.commit()

        client = Client(name="Inbox Supplier", email="inbox-sup@example.com")
        client.set_custom_field("peppol_endpoint_id", "0999999999")
        client.set_custom_field("peppol_scheme_id", "0208")
        db.session.add(client)
        db.session.commit()

        doc_id = "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb"
        responses.add(
            responses.GET,
            "http://peppol-bridge:8088/inbox",
            json={
                "ok": True,
                "provider": "letspeppol",
                "documents": [
                    {
                        "id": doc_id,
                        "direction": "INCOMING",
                        "type": "INVOICE",
                        "ownerPeppolId": "0208:0123456789",
                        "partnerPeppolId": "0208:0999999999",
                        "ubl": SAMPLE_UBL,
                    }
                ],
            },
            status=200,
        )
        responses.add(
            responses.POST,
            "http://peppol-bridge:8088/inbox/ack",
            json={"ok": True, "acked": 1},
            status=200,
        )

        result = PeppolInboundService().poll_and_import()
        assert result["ok"] is True
        assert result["created"] == 1
        assert result["acked"] == 1

        row = PeppolInboundDocument.query.filter_by(external_id=doc_id).one()
        assert row.status == "acknowledged"
        assert row.matched_client_id == client.id
        assert row.document_number == "SUP-42"

        # Second poll with same document updates + re-acks without duplicating.
        responses.add(
            responses.GET,
            "http://peppol-bridge:8088/inbox",
            json={
                "ok": True,
                "documents": [
                    {
                        "id": doc_id,
                        "direction": "INCOMING",
                        "type": "INVOICE",
                        "ownerPeppolId": "0208:0123456789",
                        "partnerPeppolId": "0208:0999999999",
                        "ubl": SAMPLE_UBL,
                    }
                ],
            },
            status=200,
        )
        responses.add(
            responses.POST,
            "http://peppol-bridge:8088/inbox/ack",
            json={"ok": True, "acked": 1},
            status=200,
        )
        result2 = PeppolInboundService().poll_and_import()
        assert result2["created"] == 0
        assert result2["updated"] == 1
        assert PeppolInboundDocument.query.count() == 1


@pytest.mark.unit
def test_poll_skipped_when_inbox_disabled(app, monkeypatch):
    from app.services.peppol_inbound_service import PeppolInboundService

    with app.app_context():
        settings = Settings.get_settings()
        settings.peppol_enabled = True
        settings.peppol_inbox_enabled = False
        db.session.commit()
        monkeypatch.setenv("PEPPOL_ENABLED", "true")

        result = PeppolInboundService().poll_and_import()
        assert result.get("skipped") is True


@pytest.mark.unit
def test_poll_ack_failure_keeps_imported_row(app, monkeypatch):
    from app.services import peppol_inbound_service as mod

    with app.app_context():
        settings = Settings.get_settings()
        settings.peppol_enabled = True
        settings.peppol_inbox_enabled = True
        settings.peppol_access_point_url = "http://peppol-bridge:8088/send"
        db.session.commit()

        svc = mod.PeppolInboundService()
        svc.fetch_inbox = MagicMock(
            return_value=[
                {
                    "id": "cccccccc-cccc-cccc-cccc-cccccccccccc",
                    "direction": "INCOMING",
                    "type": "INVOICE",
                    "partnerPeppolId": "0208:0999999999",
                    "ubl": SAMPLE_UBL,
                }
            ]
        )
        svc.ack_downloaded = MagicMock(side_effect=RuntimeError("ack down"))

        result = svc.poll_and_import()
        assert result["created"] == 1
        assert result["acked"] == 0
        assert any("ack:" in e for e in result["errors"])
        row = PeppolInboundDocument.query.filter_by(external_id="cccccccc-cccc-cccc-cccc-cccccccccccc").one()
        assert row.document_number == "SUP-42"
        assert row.status == "new"
