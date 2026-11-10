import os

import pytest
import responses


@pytest.fixture()
def bridge_app(monkeypatch):
    # Default to generic_custom provider for local tests
    monkeypatch.setenv("PEPPOL_BRIDGE_PROVIDER", "generic_custom")
    monkeypatch.setenv("GENERIC_FORWARD_URL", "https://forward.example.test/send")
    monkeypatch.setenv("PEPPOL_BRIDGE_TIMEOUT_S", "2")
    monkeypatch.delenv("PEPPOL_BRIDGE_AUTH_TOKEN", raising=False)

    from peppol_bridge.app import create_app

    app = create_app()
    app.config["TESTING"] = True
    return app


@pytest.fixture()
def client(bridge_app):
    return bridge_app.test_client()


def _tt_payload():
    return {
        "recipient": {"endpoint_id": "0123456789", "scheme_id": "0208"},
        "sender": {"endpoint_id": "BE0123456789", "scheme_id": "0208"},
        "document": {
            "id": "INV-1",
            "type_id": "urn:oasis:names:specification:ubl:schema:xsd:Invoice-2::Invoice##x::2.1",
            "process_id": "urn:fdc:peppol.eu:2017:poacc:billing:01:1.0",
        },
        "payload": {"ubl_xml": '<?xml version="1.0" encoding="UTF-8"?><Invoice></Invoice>'},
    }


def test_health_ok(client):
    resp = client.get("/health")
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["ok"] is True
    assert data["service"] == "peppol-bridge"


def test_send_requires_valid_contract(client):
    resp = client.post("/send", json={"foo": "bar"})
    assert resp.status_code == 400
    data = resp.get_json()
    assert data["ok"] is False


@responses.activate
def test_generic_custom_forwards_and_returns_message_id(client):
    responses.add(
        responses.POST,
        "https://forward.example.test/send",
        json={"message_id": "msg_123"},
        status=200,
        content_type="application/json",
    )
    resp = client.post("/send", json=_tt_payload())
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["ok"] is True
    assert data["message_id"] == "msg_123"


def test_send_requires_auth_when_configured(monkeypatch):
    monkeypatch.setenv("PEPPOL_BRIDGE_PROVIDER", "generic_custom")
    monkeypatch.setenv("GENERIC_FORWARD_URL", "https://forward.example.test/send")
    monkeypatch.setenv("PEPPOL_BRIDGE_AUTH_TOKEN", "secret")

    from peppol_bridge.app import create_app

    app = create_app()
    app.config["TESTING"] = True
    c = app.test_client()

    resp = c.post("/send", json=_tt_payload())
    assert resp.status_code == 401


@responses.activate
def test_einvoice_test_credentials(monkeypatch):
    monkeypatch.setenv("PEPPOL_BRIDGE_PROVIDER", "einvoice")
    monkeypatch.setenv("EINVOICE_API_KEY", "k_test")
    monkeypatch.setenv("EINVOICE_BASE_URL", "https://api.e-invoice.be")

    from peppol_bridge.app import create_app

    app = create_app()
    app.config["TESTING"] = True
    c = app.test_client()

    responses.add(
        responses.GET,
        "https://api.e-invoice.be/api/me/",
        json={"id": "me"},
        status=200,
        content_type="application/json",
    )
    resp = c.post("/test")
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["ok"] is True
    assert data["provider"] == "e-invoice.be"


@responses.activate
def test_peppyrus_test_credentials(monkeypatch):
    monkeypatch.setenv("PEPPOL_BRIDGE_PROVIDER", "peppyrus")
    monkeypatch.setenv("PEPPYRUS_API_KEY", "k_test")
    monkeypatch.setenv("PEPPYRUS_BASE_URL", "https://api.peppyrus.be/v1")

    from peppol_bridge.app import create_app

    app = create_app()
    app.config["TESTING"] = True
    c = app.test_client()

    responses.add(
        responses.GET,
        "https://api.peppyrus.be/v1/organization/info",
        json={"org": "x"},
        status=200,
        content_type="application/json",
    )
    resp = c.post("/test")
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["ok"] is True
    assert data["provider"] == "peppyrus"

    assert len(responses.calls) == 1
    req_headers = responses.calls[0].request.headers
    assert req_headers.get("X-Api-Key") == "k_test"
    assert "Authorization" not in req_headers


@responses.activate
def test_peppyrus_send_uses_x_api_key(monkeypatch):
    monkeypatch.setenv("PEPPOL_BRIDGE_PROVIDER", "peppyrus")
    monkeypatch.setenv("PEPPYRUS_API_KEY", "k_test")
    monkeypatch.setenv("PEPPYRUS_BASE_URL", "https://api.peppyrus.be/v1")

    from peppol_bridge.app import create_app

    app = create_app()
    app.config["TESTING"] = True
    c = app.test_client()

    responses.add(
        responses.POST,
        "https://api.peppyrus.be/v1/message",
        json={"id": "msg_123"},
        status=200,
        content_type="application/json",
    )
    resp = c.post("/send", json=_tt_payload())
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["ok"] is True
    assert data["message_id"] == "msg_123"

    assert len(responses.calls) == 1
    req_headers = responses.calls[0].request.headers
    assert req_headers.get("X-Api-Key") == "k_test"
    assert "Authorization" not in req_headers


def _getpeppr_app(monkeypatch):
    monkeypatch.setenv("PEPPOL_BRIDGE_PROVIDER", "getpeppr")
    monkeypatch.setenv("GETPEPPR_API_KEY", "sk_sandbox_test")
    monkeypatch.setenv("GETPEPPR_BASE_URL", "https://api.getpeppr.dev/v1")
    monkeypatch.delenv("PEPPOL_BRIDGE_AUTH_TOKEN", raising=False)

    from peppol_bridge.app import create_app

    app = create_app()
    app.config["TESTING"] = True
    return app.test_client()


@responses.activate
def test_getpeppr_test_credentials_reads_identity(monkeypatch):
    c = _getpeppr_app(monkeypatch)
    responses.add(
        responses.GET,
        "https://api.getpeppr.dev/v1/identity",
        json={
            "environment": "sandbox",
            "legalEntity": {
                "companyName": "Acme BV",
                "country": "BE",
                "address": {"line1": "Street 1", "city": "Gent", "zip": "9000"},
                "createdAt": "2026-11-01T00:00:00.000Z",
            },
            "identifiers": [{"scheme": "0208", "value": "0123456789", "status": "verified", "createdAt": "x"}],
            "sandboxFirstSend": {"status": "ready"},
        },
        status=200,
    )
    resp = c.post("/test")
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["ok"] is True
    assert data["provider"] == "getpeppr"
    assert data["data"] == {
        "environment": "sandbox",
        "legal_entity": {"company_name": "Acme BV", "country": "BE"},
        "identifiers": [{"scheme": "0208", "value": "0123456789", "status": "verified"}],
    }

    assert len(responses.calls) == 1
    req = responses.calls[0].request
    assert req.method == "GET"
    assert req.headers.get("Authorization") == "Bearer sk_sandbox_test"


@responses.activate
def test_getpeppr_test_credentials_rejected_key(monkeypatch):
    c = _getpeppr_app(monkeypatch)
    responses.add(responses.GET, "https://api.getpeppr.dev/v1/identity", json={"error": "Invalid API key"}, status=401)
    resp = c.post("/test")
    assert resp.status_code == 400
    assert resp.get_json()["ok"] is False
    assert len(responses.calls) == 1


def test_getpeppr_requires_api_key(monkeypatch):
    monkeypatch.setenv("PEPPOL_BRIDGE_PROVIDER", "getpeppr")
    monkeypatch.delenv("GETPEPPR_API_KEY", raising=False)

    from peppol_bridge.app import _build_provider
    from peppol_bridge.config import load_config
    from peppol_bridge.providers.base import ProviderError

    with pytest.raises(ProviderError, match="GETPEPPR_API_KEY is not set"):
        _build_provider(load_config())


@pytest.mark.parametrize(
    "base_url,ok",
    [
        ("https://api.getpeppr.dev/v1", True),
        ("http://localhost:3000/api/v1", True),
        ("http://api.getpeppr.dev/v1", False),
        ("ftp://api.getpeppr.dev/v1", False),
    ],
)
def test_getpeppr_base_url_must_be_https(base_url, ok):
    from peppol_bridge.providers.base import ProviderError
    from peppol_bridge.providers.getpeppr import GetpepprProvider

    if ok:
        GetpepprProvider(base_url=base_url, api_key="k", timeout_s=1)
    else:
        with pytest.raises(ProviderError, match="https"):
            GetpepprProvider(base_url=base_url, api_key="k", timeout_s=1)


@responses.activate
def test_getpeppr_send_imports_ubl_with_recipient_routing(monkeypatch):
    import base64
    import json

    c = _getpeppr_app(monkeypatch)
    responses.add(
        responses.POST,
        "https://api.getpeppr.dev/v1/invoices/import",
        json={"id": "doc-guid-1", "providerDocumentId": "doc-guid-1", "submissionId": "sub-1", "status": "submitted"},
        status=201,
    )
    payload = _tt_payload()
    resp = c.post("/send", json=payload)
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["ok"] is True
    assert data["provider"] == "getpeppr"
    assert data["message_id"] == "doc-guid-1"

    assert len(responses.calls) == 1
    req = responses.calls[0].request
    assert req.headers.get("Authorization") == "Bearer sk_sandbox_test"
    body = json.loads(req.body)
    # getpeppr derives the seller and the document type from the API key and the UBL:
    # only the document and the recipient routing travel.
    assert set(body) == {"file", "filename", "to"}
    assert base64.b64decode(body["file"]).decode("utf-8") == payload["payload"]["ubl_xml"]
    assert body["filename"] == "INV-1.xml"
    assert body["to"] == {"peppolId": "0208:0123456789"}
    assert req.headers.get("Idempotency-Key", "").startswith("timetracker-peppol-bridge-")


def _tt_ubl(pdf_bytes, unit_price: str = "100") -> str:
    """UBL from TimeTracker's own generator, with an embedded PDF like PeppolService.send_invoice builds."""
    from datetime import date
    from decimal import Decimal
    from types import SimpleNamespace

    from app.integrations.peppol import PeppolAttachment, PeppolParty, build_peppol_ubl_invoice_xml

    price = Decimal(unit_price)
    item = SimpleNamespace(description="Consulting", quantity=1, unit_price=price, total_amount=price)
    invoice = SimpleNamespace(
        id=1,
        invoice_number="INV-1",
        issue_date=date(2026, 11, 6),
        due_date=None,
        currency_code="EUR",
        subtotal=price,
        tax_rate=Decimal("21"),
        tax_amount=price * Decimal("0.21"),
        total_amount=price * Decimal("1.21"),
        items=[item],
        expenses=[],
        extra_goods=[],
        notes=None,
        buyer_reference="INV-1",
    )
    supplier = PeppolParty(endpoint_id="0123456789", endpoint_scheme_id="0208", name="Seller", tax_id="BE0123456789")
    customer = PeppolParty(endpoint_id="0987654321", endpoint_scheme_id="0208", name="Buyer")
    attachments = None
    if pdf_bytes is not None:
        attachments = [
            PeppolAttachment(document_id="INV-1", filename="INV-1.pdf", mime_code="application/pdf", content=pdf_bytes)
        ]
    xml, _ = build_peppol_ubl_invoice_xml(invoice, supplier, customer, attachments=attachments)
    return xml


@responses.activate
def test_getpeppr_idempotency_key_names_the_invoice_not_the_pdf_bytes(monkeypatch):
    import base64
    import json

    from peppol_bridge.providers import getpeppr as gp

    c = _getpeppr_app(monkeypatch)
    responses.add(
        responses.POST,
        "https://api.getpeppr.dev/v1/invoices/import",
        json={"providerDocumentId": "doc-guid-1"},
        status=201,
    )
    monkeypatch.setattr(gp, "_utc_day", lambda: "20261106")

    def send(ubl_xml):
        payload = _tt_payload()
        payload["payload"]["ubl_xml"] = ubl_xml
        assert c.post("/send", json=payload).status_code == 200

    # A resend regenerates the PDF, and the PDF carries its own creation time.
    first = _tt_ubl(b"%PDF-1.4 CreationDate 20261106095946")
    retry = _tt_ubl(b"%PDF-1.4 CreationDate 20261106095947")
    assert first != retry
    # ... and goes without it when PDF generation fails, is too large or is turned off.
    without_pdf = _tt_ubl(None)
    assert "AdditionalDocumentReference" not in without_pdf
    send(first)
    send(retry)
    send(without_pdf)
    send(_tt_ubl(b"%PDF-1.4 CreationDate 20261106095948", unit_price="120"))
    monkeypatch.setattr(gp, "_utc_day", lambda: "20261107")
    send(first)

    keys = [call.request.headers["Idempotency-Key"] for call in responses.calls]
    assert keys[0] == keys[1], "the same invoice with a regenerated PDF must reuse its key"
    assert keys[2] == keys[0], "the same invoice sent without its PDF must reuse its key"
    assert keys[3] != keys[0], "a changed invoice must never reuse a key"
    assert keys[4] != keys[0], "a deliberate resend on a later day must be a new request"
    assert keys[0].startswith("timetracker-peppol-bridge-20261106-")

    # The key ignores the PDF bytes; the document sent does not.
    sent = base64.b64decode(json.loads(responses.calls[1].request.body)["file"]).decode("utf-8")
    assert sent == retry


def test_getpeppr_fingerprint_keeps_references_without_an_embedded_file():
    from peppol_bridge.providers.getpeppr import _invoice_fingerprint

    ref = "<cac:AdditionalDocumentReference><cbc:ID>{}</cbc:ID></cac:AdditionalDocumentReference>"
    att = (
        "<cac:AdditionalDocumentReference><cbc:ID>A</cbc:ID><cac:Attachment>"
        '<cbc:EmbeddedDocumentBinaryObject mimeCode="application/pdf" filename="a.pdf">QUJD'
        "</cbc:EmbeddedDocumentBinaryObject></cac:Attachment></cac:AdditionalDocumentReference>"
    )
    base = "<Invoice><cbc:ID>INV-1</cbc:ID>{}<cac:AccountingSupplierParty/></Invoice>"
    assert _invoice_fingerprint(base.format(ref.format("PO-1") + att)) == _invoice_fingerprint(
        base.format(ref.format("PO-1"))
    )
    assert _invoice_fingerprint(base.format(ref.format("PO-1"))) != _invoice_fingerprint(
        base.format(ref.format("PO-2"))
    )


@responses.activate
def test_getpeppr_idempotency_key_depends_on_recipient(monkeypatch):
    c = _getpeppr_app(monkeypatch)
    responses.add(
        responses.POST,
        "https://api.getpeppr.dev/v1/invoices/import",
        json={"providerDocumentId": "doc-guid-1"},
        status=201,
    )
    other = _tt_payload()
    other["recipient"] = {"endpoint_id": "0999999999", "scheme_id": "0208"}
    c.post("/send", json=_tt_payload())
    c.post("/send", json=other)
    keys = [call.request.headers["Idempotency-Key"] for call in responses.calls]
    assert keys[0] != keys[1]


@responses.activate
def test_getpeppr_send_accepts_a_replayed_receipt(monkeypatch):
    # A replay of an earlier send can carry only the deprecated `id`.
    c = _getpeppr_app(monkeypatch)
    responses.add(
        responses.POST,
        "https://api.getpeppr.dev/v1/invoices/import",
        json={"id": "doc-guid-1", "status": "submitted", "createdAt": "2026-11-06T09:49:38.590Z"},
        status=201,
    )
    resp = c.post("/send", json=_tt_payload())
    assert resp.status_code == 200
    assert resp.get_json()["message_id"] == "doc-guid-1"


@responses.activate
def test_getpeppr_resend_refused_as_key_reuse_is_a_bridge_error(monkeypatch):
    c = _getpeppr_app(monkeypatch)
    responses.add(
        responses.POST,
        "https://api.getpeppr.dev/v1/invoices/import",
        json={"error": "idempotency_key_reuse"},
        status=422,
    )
    resp = c.post("/send", json=_tt_payload())
    assert resp.status_code == 502
    assert len(responses.calls) == 1


@responses.activate
def test_getpeppr_send_rejection_is_a_bridge_error(monkeypatch):
    c = _getpeppr_app(monkeypatch)
    responses.add(
        responses.POST,
        "https://api.getpeppr.dev/v1/invoices/import",
        json={"error": "validation_failed", "violations": [{"rule": "BR-01"}]},
        status=422,
    )
    resp = c.post("/send", json=_tt_payload())
    assert resp.status_code == 502
    assert resp.get_json()["ok"] is False
    assert len(responses.calls) == 1


@responses.activate
def test_getpeppr_send_without_document_id_is_an_error(monkeypatch):
    c = _getpeppr_app(monkeypatch)
    responses.add(
        responses.POST, "https://api.getpeppr.dev/v1/invoices/import", json={"status": "submitted"}, status=201
    )
    resp = c.post("/send", json=_tt_payload())
    assert resp.status_code == 502
    assert len(responses.calls) == 1


@pytest.mark.parametrize(
    "status,folder,rule",
    [
        ("submitted", "outbox", None),
        ("delivered", "sent", None),
        ("acknowledged", "sent", None),
        ("in_process", "sent", None),
        ("under_query", "sent", None),
        ("conditionally_accepted", "sent", None),
        ("accepted", "sent", None),
        ("rejected", "sent", None),
        ("paid", "sent", None),
        ("partially_paid", "sent", None),
        ("failed", "failed", "getpeppr:failed"),
        ("no_action", "failed", "getpeppr:no_recipient"),
        ("cleared", None, None),
        ("unknown", None, None),
        ("something_new", None, None),
    ],
)
@responses.activate
def test_getpeppr_status_maps_to_bridge_folder(monkeypatch, status, folder, rule):
    c = _getpeppr_app(monkeypatch)
    responses.add(
        responses.GET,
        "https://api.getpeppr.dev/v1/invoices/doc-guid-1",
        json={
            "id": "doc-guid-1",
            "providerDocumentId": "doc-guid-1",
            "submissionId": "sub-1",
            "number": "INV-1",
            "environment": "sandbox",
            "status": status,
            "recipientName": "Buyer BV",
            "totalAmount": 121,
            "accountId": "acc-1",
            "updatedAt": "2026-11-06T09:49:49.133Z",
        },
        status=200,
    )
    resp = c.get("/message/doc-guid-1/status")
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["ok"] is True
    assert data["folder"] == folder
    assert data["status"] == status
    assert set(data["raw"]) == {"providerDocumentId", "submissionId", "number", "environment", "updatedAt"}
    if rule:
        assert [r["id"] for r in data["fatal_rules"]] == [rule]
    else:
        assert "fatal_rules" not in data


@responses.activate
def test_getpeppr_failed_status_marks_the_transmission_failed(monkeypatch):
    # The consumer side: PeppolService reads the bridge folder and the fatal rules.
    from app.services.peppol_service import PeppolService

    c = _getpeppr_app(monkeypatch)
    responses.add(
        responses.GET,
        "https://api.getpeppr.dev/v1/invoices/doc-guid-1",
        json={"providerDocumentId": "doc-guid-1", "status": "no_action"},
        status=200,
    )

    bridge_out = c.get("/message/doc-guid-1/status").get_json()
    responses.add(responses.GET, "http://peppol-bridge:8088/message/doc-guid-1/status", json=bridge_out, status=200)

    folder, rules = PeppolService._poll_ap_status("http://peppol-bridge:8088/send", None, "doc-guid-1", attempts=1)
    assert folder == "failed"
    assert rules[0]["id"] == "getpeppr:no_recipient"


@responses.activate
def test_getpeppr_status_unknown_document(monkeypatch):
    c = _getpeppr_app(monkeypatch)
    responses.add(
        responses.GET, "https://api.getpeppr.dev/v1/invoices/nope", json={"error": "Invoice not found"}, status=404
    )
    resp = c.get("/message/nope/status")
    assert resp.status_code == 502
    assert len(responses.calls) == 1


def _letspeppol_app(monkeypatch):
    monkeypatch.setenv("PEPPOL_BRIDGE_PROVIDER", "letspeppol")
    monkeypatch.setenv("LETSPEPPOL_BASE_URL", "https://be.letspeppol.org")
    monkeypatch.setenv("LETSPEPPOL_CLIENT_ID", "client-id")
    monkeypatch.setenv("LETSPEPPOL_CLIENT_SECRET", "client-secret")
    monkeypatch.setenv("LETSPEPPOL_PEPPOL_ID", "0208:0123456789")
    monkeypatch.delenv("PEPPOL_BRIDGE_AUTH_TOKEN", raising=False)

    from peppol_bridge.app import create_app

    app = create_app()
    app.config["TESTING"] = True
    return app.test_client()


def _mock_letspeppol_token():
    responses.add(
        responses.POST,
        "https://be.letspeppol.org/kyc/auth/oauth2/token",
        json={"access_token": "tok_test", "expires_in": 3600, "token_type": "Bearer"},
        status=200,
    )


@responses.activate
def test_letspeppol_test_credentials(monkeypatch):
    c = _letspeppol_app(monkeypatch)
    _mock_letspeppol_token()
    responses.add(
        responses.GET,
        "https://be.letspeppol.org/proxy/sapi/registry?peppolId=0208%3A0123456789",
        json={"peppolId": "0208:0123456789", "peppolActive": True, "accessPoint": "scrada"},
        status=200,
    )
    resp = c.post("/test")
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["ok"] is True
    assert data["provider"] == "letspeppol"
    assert data["data"]["peppol_active"] is True
    assert responses.calls[0].request.url.endswith("/kyc/auth/oauth2/token")
    assert responses.calls[1].request.headers["Authorization"] == "Bearer tok_test"


@responses.activate
def test_letspeppol_send_creates_and_reschedules(monkeypatch):
    c = _letspeppol_app(monkeypatch)
    _mock_letspeppol_token()
    created = {
        "id": "11111111-1111-1111-1111-111111111111",
        "direction": "OUTGOING",
        "type": "INVOICE",
        "ownerPeppolId": "0208:0123456789",
        "partnerPeppolId": "0208:0123456789",
        "ubl": "<Invoice/>",
    }
    responses.add(
        responses.POST,
        "https://be.letspeppol.org/proxy/sapi/document",
        json=created,
        status=200,
    )
    responses.add(
        responses.PUT,
        "https://be.letspeppol.org/proxy/sapi/document/11111111-1111-1111-1111-111111111111/reschedule",
        json={**created, "processedStatus": "scheduled"},
        status=200,
    )
    resp = c.post("/send", json=_tt_payload())
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["ok"] is True
    assert data["message_id"] == "11111111-1111-1111-1111-111111111111"
    assert len(responses.calls) == 3  # token + create + reschedule
    create_body = responses.calls[1].request.body
    assert b'"direction": "OUTGOING"' in create_body or b'"direction":"OUTGOING"' in create_body


@responses.activate
def test_letspeppol_status_maps_failed(monkeypatch):
    c = _letspeppol_app(monkeypatch)
    _mock_letspeppol_token()
    responses.add(
        responses.POST,
        "https://be.letspeppol.org/proxy/sapi/document/status",
        json=[
            {
                "id": "11111111-1111-1111-1111-111111111111",
                "processedStatus": "failed",
                "partnerPeppolId": "0208:0999999999",
            }
        ],
        status=200,
    )
    resp = c.get("/message/11111111-1111-1111-1111-111111111111/status")
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["folder"] == "failed"
    assert data["fatal_rules"][0]["id"] == "letspeppol:failed"


@responses.activate
def test_letspeppol_inbox_and_ack(monkeypatch):
    c = _letspeppol_app(monkeypatch)
    _mock_letspeppol_token()
    doc = {
        "id": "22222222-2222-2222-2222-222222222222",
        "direction": "INCOMING",
        "type": "INVOICE",
        "ownerPeppolId": "0208:0123456789",
        "partnerPeppolId": "0208:0999999999",
        "ubl": '<?xml version="1.0"?><Invoice xmlns="urn:oasis:names:specification:ubl:schema:xsd:Invoice-2"><cbc:ID xmlns:cbc="urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2">SUP-1</cbc:ID></Invoice>',
    }
    responses.add(
        responses.GET,
        "https://be.letspeppol.org/proxy/sapi/document?size=100",
        json=[doc],
        status=200,
    )
    responses.add(
        responses.PUT,
        "https://be.letspeppol.org/proxy/sapi/document/downloaded",
        status=200,
        body="",
    )

    inbox = c.get("/inbox?size=100")
    assert inbox.status_code == 200
    inbox_data = inbox.get_json()
    assert inbox_data["ok"] is True
    assert len(inbox_data["documents"]) == 1

    ack = c.post("/inbox/ack", json={"ids": [doc["id"]]})
    assert ack.status_code == 200
    assert ack.get_json()["acked"] == 1
