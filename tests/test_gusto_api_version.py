"""Gusto requests pin X-Gusto-API-Version instead of relying on the app's minimum version."""

from types import SimpleNamespace

from app.integrations.gusto import GustoConnector


def _connector(config=None):
    connector = GustoConnector.__new__(GustoConnector)
    connector.integration = SimpleNamespace(config=config)
    return connector


def test_headers_pin_the_default_api_version():
    headers = _connector({})._headers("tok", Accept="application/json")
    assert headers == {
        "Authorization": "Bearer tok",
        "X-Gusto-API-Version": GustoConnector.API_VERSION,
        "Accept": "application/json",
    }


def test_headers_use_the_configured_api_version():
    headers = _connector({"api_version": "2025-06-15"})._headers("tok")
    assert headers["X-Gusto-API-Version"] == "2025-06-15"


def test_headers_cope_with_missing_config():
    assert _connector(None)._headers("tok")["X-Gusto-API-Version"] == GustoConnector.API_VERSION
