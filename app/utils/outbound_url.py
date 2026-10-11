"""Validate outbound URLs to mitigate SSRF (webhooks, admin bridge tests, etc.)."""

from __future__ import annotations

import ipaddress
import socket
from typing import Optional, Tuple
from urllib.parse import urlparse, urlunparse


class UnsafeOutboundURL(ValueError):
    """Raised when an outbound URL is not safe to fetch."""


_BLOCKED_NETWORKS = (
    ipaddress.ip_network("0.0.0.0/8"),
    ipaddress.ip_network("10.0.0.0/8"),
    ipaddress.ip_network("100.64.0.0/10"),  # CGNAT
    ipaddress.ip_network("127.0.0.0/8"),
    ipaddress.ip_network("169.254.0.0/16"),  # link-local / cloud metadata
    ipaddress.ip_network("172.16.0.0/12"),
    ipaddress.ip_network("192.0.0.0/24"),
    ipaddress.ip_network("192.168.0.0/16"),
    ipaddress.ip_network("198.18.0.0/15"),
    ipaddress.ip_network("::1/128"),
    ipaddress.ip_network("fc00::/7"),
    ipaddress.ip_network("fe80::/10"),
)

_METADATA_HOSTS = frozenset(
    {
        "metadata",
        "metadata.google.internal",
        "kubernetes.default",
        "localhost",
    }
)


def _is_blocked_ip(ip: ipaddress._BaseAddress) -> bool:
    if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved or ip.is_multicast:
        return True
    for network in _BLOCKED_NETWORKS:
        try:
            if ip in network:
                return True
        except TypeError:
            continue
    return False


def _rebuild_url(parsed) -> str:
    """Rebuild a URL from parsed components so request-forgery taint does not flow."""
    scheme = (parsed.scheme or "").lower()
    netloc = parsed.netloc
    path = parsed.path or ""
    params = parsed.params or ""
    query = parsed.query or ""
    fragment = ""  # drop fragments for outbound fetches
    return urlunparse((scheme, netloc, path, params, query, fragment))


def validate_outbound_url(
    url: Optional[str],
    *,
    allow_http: bool = True,
    resolve_dns: bool = True,
    allow_private: bool = False,
) -> str:
    """
    Validate that url is safe for server-side outbound requests.

    Checks:
    - Non-empty http(s) URL with a host
    - Hostname does not resolve to private / loopback / link-local / metadata IPs
      (unless allow_private=True)
    - Literal IP hosts are checked the same way

    Returns a rebuilt URL string on success (breaks taint for CodeQL).
    Raises UnsafeOutboundURL on failure.
    """
    if not url or not isinstance(url, str):
        raise UnsafeOutboundURL("URL is required")

    candidate = url.strip()
    try:
        parsed = urlparse(candidate)
    except Exception as exc:
        raise UnsafeOutboundURL(f"Invalid URL: {exc}") from exc

    allowed_schemes = {"https", "http"} if allow_http else {"https"}
    if parsed.scheme.lower() not in allowed_schemes:
        raise UnsafeOutboundURL(f"URL scheme must be one of: {', '.join(sorted(allowed_schemes))}")
    if not parsed.hostname:
        raise UnsafeOutboundURL("URL must include a hostname")

    hostname = parsed.hostname
    # Reject obvious metadata hostnames even before DNS
    lowered = hostname.lower().rstrip(".")
    if lowered in _METADATA_HOSTS and not allow_private:
        raise UnsafeOutboundURL("URL host is not allowed")
    if lowered in {"metadata", "metadata.google.internal", "kubernetes.default"}:
        raise UnsafeOutboundURL("URL host is not allowed")

    # Literal IP in the hostname
    try:
        literal_ip = ipaddress.ip_address(hostname)
    except ValueError:
        literal_ip = None

    if literal_ip is not None:
        if not allow_private and _is_blocked_ip(literal_ip):
            raise UnsafeOutboundURL("URL resolves to a blocked IP address")
        return _rebuild_url(parsed)

    if not resolve_dns:
        return _rebuild_url(parsed)

    try:
        addr_infos = socket.getaddrinfo(hostname, parsed.port or None, type=socket.SOCK_STREAM)
    except socket.gaierror as exc:
        raise UnsafeOutboundURL(f"Could not resolve hostname: {hostname}") from exc

    if not addr_infos:
        raise UnsafeOutboundURL(f"Could not resolve hostname: {hostname}")

    if not allow_private:
        for info in addr_infos:
            sockaddr = info[4]
            if not sockaddr:
                continue
            try:
                ip = ipaddress.ip_address(sockaddr[0])
            except ValueError:
                continue
            if _is_blocked_ip(ip):
                raise UnsafeOutboundURL("URL resolves to a blocked IP address")

    return _rebuild_url(parsed)


def validate_oidc_issuer_url(url: Optional[str]) -> str:
    """
    Validate an OIDC issuer URL for metadata fetch.

    - https is always allowed
    - http is allowed only for localhost / 127.0.0.1 / ::1
    - private / link-local IPs are allowed (enterprise IdPs)
    - metadata hostnames remain blocked
    """
    if not url or not isinstance(url, str):
        raise UnsafeOutboundURL("Issuer URL is required")

    candidate = url.strip()
    try:
        parsed = urlparse(candidate)
    except Exception as exc:
        raise UnsafeOutboundURL(f"Invalid URL: {exc}") from exc

    scheme = (parsed.scheme or "").lower()
    if scheme not in {"https", "http"}:
        raise UnsafeOutboundURL("Issuer URL scheme must be https (or http for localhost)")
    if not parsed.hostname:
        raise UnsafeOutboundURL("Issuer URL must include a hostname")

    hostname = parsed.hostname.lower().rstrip(".")
    if hostname in {"metadata", "metadata.google.internal", "kubernetes.default"}:
        raise UnsafeOutboundURL("Issuer host is not allowed")

    if scheme == "http":
        if hostname not in {"localhost", "127.0.0.1", "::1"}:
            raise UnsafeOutboundURL("http issuer URLs are only allowed for localhost")

    return _rebuild_url(parsed)


def is_safe_outbound_url(url: Optional[str], **kwargs) -> Tuple[bool, str]:
    """Return (ok, error_message) for form/API validation."""
    try:
        validate_outbound_url(url, **kwargs)
        return True, ""
    except UnsafeOutboundURL as exc:
        return False, str(exc)
