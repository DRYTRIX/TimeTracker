"""
PEPPOL SML/SMP participant discovery.

EXPERIMENTAL: Resolves recipient access point URL from the Service Metadata
Locator (SML) and Service Metadata Provider (SMP) for native PEPPOL
transport. This implementation supports basic HTTP-based SML/SMP lookup
only (no DNS-based NAPTR/SRV resolution, no DNSSEC verification).
"""

from __future__ import annotations

import os
import re
from typing import Optional
from xml.etree import ElementTree as ET

import requests

# PEPPOL BIS Billing 3.0 document and process identifiers
PEPPOL_INVOICE_DOCUMENT_TYPE = (
    "urn:oasis:names:specification:ubl:schema:xsd:Invoice-2::Invoice"
    "##urn:cen.eu:en16931:2017#compliant#urn:fdc:peppol.eu:2017:poacc:billing:3.0::2.1"
)
PEPPOL_INVOICE_PROCESS = "urn:fdc:peppol.eu:2017:poacc:billing:01:1.0"


class PeppolSMPError(RuntimeError):
    """SML/SMP lookup or parse error."""

    pass


def _get_sml_base_url() -> str:
    """Return SML base URL from env or default (PEPPOL directory)."""
    url = (os.getenv("PEPPOL_SML_URL") or "").strip()
    if url:
        return url.rstrip("/")
    # Default: PEPPOL directory (production) - use HTTPS
    return "https://edelivery.tech.ec.europa.eu/edelivery-sml"


def _participant_identifier_to_hostname(participant_id: str, scheme_id: str) -> str:
    """
    Build DNS-style hostname for participant (busdox/SML format).
    Format: participant_id.scheme_id.iso6523-actorid-up.iso6523.org (or SML domain).
    """
    # Sanitize: replace invalid chars with hyphen for DNS
    safe_id = re.sub(r"[^a-zA-Z0-9.-]", "-", participant_id).strip(".-") or "unknown"
    safe_scheme = re.sub(r"[^a-zA-Z0-9.-]", "-", scheme_id).strip(".-") or "0000"
    return f"{safe_id}.{safe_scheme}.iso6523-actorid-up.iso6523.org"


def get_smp_url(participant_id: str, scheme_id: str, sml_base_url: Optional[str] = None) -> str:
    """
    Resolve SMP URL for a participant from SML.

    If PEPPOL_SML_URL is set to an HTTP(S) URL, we query that directory.
    Otherwise uses DNS-based lookup (N/A in pure Python without DNSSEC);
    we support fixed SML URL only for now.

    Returns:
        SMP base URL (e.g. https://smp.example.com/...)
    """
    base = (sml_base_url or _get_sml_base_url()).rstrip("/")
    if not base:
        raise PeppolSMPError("PEPPOL_SML_URL is not set; required for native transport")

    # BDXR SMP 1.0 / PEPPOL: participant lookup
    # Path format: /iso6523-actorid-up::{scheme}::{id}
    actor_urn = f"iso6523-actorid-up::{scheme_id}::{participant_id}"
    # URL-encode the URN for path
    import urllib.parse

    path = "/" + urllib.parse.quote(actor_urn, safe="")
    url = base + path

    try:
        resp = requests.get(url, timeout=30, headers={"Accept": "application/xml"})
        resp.raise_for_status()
    except requests.RequestException as e:
        raise PeppolSMPError(f"SML lookup failed for {scheme_id}:{participant_id}: {e}") from e

    # Parse response: ServiceGroup with ServiceMetadataReferenceCollection
    # SMP URL is in the first ServiceMetadataReference or similar
    try:
        root = ET.fromstring(resp.content)
    except ET.ParseError as e:
        raise PeppolSMPError(f"Invalid SML response XML: {e}") from e

    # BDXR: ServiceMetadataReferenceCollection / ServiceMetadataReference / href
    ns = {"bdxr": "http://docs.oasis-open.org/bdxr/ns/SMP/2.0"}
    refs = root.findall(".//bdxr:ServiceMetadataReference", ns)
    if not refs:
        refs = root.findall(".//{http://docs.oasis-open.org/bdxr/ns/SMP/2.0}ServiceMetadataReference")
    if not refs:
        refs = root.findall(".//ServiceMetadataReference")
    if not refs:
        raise PeppolSMPError(f"No ServiceMetadataReference in SML response for {scheme_id}:{participant_id}")

    href = refs[0].get("href") or (refs[0].find("href") is not None and refs[0].find("href").text)
    if not href:
        for child in refs[0]:
            if "href" in child.tag.lower() or child.tag.endswith("}href"):
                href = child.text
                break
    if not href or not str(href).strip().startswith("http"):
        raise PeppolSMPError(f"Invalid SMP href in SML response for {scheme_id}:{participant_id}")
    return str(href).strip().rstrip("/")


def get_recipient_endpoint_url(
    smp_url: str,
    document_type_id: str = PEPPOL_INVOICE_DOCUMENT_TYPE,
    process_id: str = PEPPOL_INVOICE_PROCESS,
) -> str:
    """
    Fetch recipient access point endpoint URL from SMP for the given document and process.

    Returns:
        Receiving access point URL (e.g. https://ap.example.com/as4)
    """
    # SMP 2.0: GET {smp_url}/services/{doc_type}/processes/{process_id}
    import urllib.parse

    doc_encoded = urllib.parse.quote(document_type_id, safe="")
    proc_encoded = urllib.parse.quote(process_id, safe="")
    path = f"/services/{doc_encoded}/processes/{proc_encoded}"
    url = smp_url.rstrip("/") + path

    try:
        resp = requests.get(url, timeout=30, headers={"Accept": "application/xml"})
        resp.raise_for_status()
    except requests.RequestException as e:
        raise PeppolSMPError(f"SMP endpoint lookup failed: {e}") from e

    try:
        root = ET.fromstring(resp.content)
    except ET.ParseError as e:
        raise PeppolSMPError(f"Invalid SMP response XML: {e}") from e

    # Find endpoint URL: ProcessMetadata / ServiceEndpoint / EndpointURI or similar
    ns = {"bdxr": "http://docs.oasis-open.org/bdxr/ns/SMP/2.0"}
    uri_el = root.find(".//bdxr:EndpointURI", ns)
    if uri_el is None:
        uri_el = root.find(".//{http://docs.oasis-open.org/bdxr/ns/SMP/2.0}EndpointURI")
    if uri_el is None:
        uri_el = root.find(".//EndpointURI")
    if uri_el is not None and uri_el.text:
        return uri_el.text.strip()
    # Alternative: RequireCertificate / child with URL
    for el in root.iter():
        if el.text and el.text.strip().startswith("http"):
            return el.text.strip()
    raise PeppolSMPError("No endpoint URL found in SMP response")
