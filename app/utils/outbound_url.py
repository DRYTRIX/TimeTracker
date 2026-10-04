"""Validate outbound URLs to mitigate SSRF (webhooks, admin bridge tests, etc.)."""

from __future__ import annotations

import ipaddress
import socket
from typing import Optional, Tuple
from urllib.parse import urlparse


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


def validate_outbound_url(
    url: Optional[str],
    *,
    allow_http: bool = True,
    resolve_dns: bool = True,
) -> str:
    """
    Validate that url is safe for server-side outbound requests.

    Checks:
    - Non-empty http(s) URL with a host
    - Hostname does not resolve to private / loopback / link-local / metadata IPs
    - Literal IP hosts are checked the same way

    Returns the stripped URL on success.
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
    if lowered in {"metadata", "metadata.google.internal", "kubernetes.default", "localhost"}:
        raise UnsafeOutboundURL("URL host is not allowed")

    # Literal IP in the hostname
    try:
        literal_ip = ipaddress.ip_address(hostname)
    except ValueError:
        literal_ip = None

    if literal_ip is not None:
        if _is_blocked_ip(literal_ip):
            raise UnsafeOutboundURL("URL resolves to a blocked IP address")
        return candidate

    if not resolve_dns:
        return candidate

    try:
        addr_infos = socket.getaddrinfo(hostname, parsed.port or None, type=socket.SOCK_STREAM)
    except socket.gaierror as exc:
        raise UnsafeOutboundURL(f"Could not resolve hostname: {hostname}") from exc

    if not addr_infos:
        raise UnsafeOutboundURL(f"Could not resolve hostname: {hostname}")

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

    return candidate


def is_safe_outbound_url(url: Optional[str], **kwargs) -> Tuple[bool, str]:
    """Return (ok, error_message) for form/API validation."""
    try:
        validate_outbound_url(url, **kwargs)
        return True, ""
    except UnsafeOutboundURL as exc:
        return False, str(exc)
