"""Unit tests for SSRF-oriented outbound URL validation."""

from __future__ import annotations

import socket

import pytest

from app.utils.outbound_url import UnsafeOutboundURL, validate_outbound_url

pytestmark = [pytest.mark.unit, pytest.mark.security]


@pytest.mark.parametrize(
    "url",
    [
        "http://127.0.0.1/",
        "http://localhost/",
        "http://169.254.169.254/",
        "http://10.0.0.1/",
    ],
)
def test_validate_outbound_url_rejects_private_and_metadata(url):
    with pytest.raises(UnsafeOutboundURL):
        validate_outbound_url(url)


def test_validate_outbound_url_accepts_public_https(monkeypatch):
    def _fake_getaddrinfo(host, port, *args, **kwargs):
        # sockaddr is info[4]; first element is the IP string
        return [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("93.184.216.34", port or 443))]

    monkeypatch.setattr(socket, "getaddrinfo", _fake_getaddrinfo)
    assert validate_outbound_url("https://example.com") == "https://example.com"


def test_validate_outbound_url_allow_http_false_rejects_http(monkeypatch):
    def _fake_getaddrinfo(host, port, *args, **kwargs):
        return [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("93.184.216.34", port or 80))]

    monkeypatch.setattr(socket, "getaddrinfo", _fake_getaddrinfo)
    with pytest.raises(UnsafeOutboundURL):
        validate_outbound_url("http://example.com", allow_http=False)
    # HTTPS still allowed
    assert validate_outbound_url("https://example.com", allow_http=False) == "https://example.com"
