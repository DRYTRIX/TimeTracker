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
        "payload": {"ubl_xml": "<?xml version=\"1.0\" encoding=\"UTF-8\"?><Invoice></Invoice>"},
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

