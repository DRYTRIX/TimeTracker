"""
PEPPOL AS4 message packaging and transmission.

EXPERIMENTAL: This native AS4 implementation provides basic message
packaging and HTTP POST to a recipient access point. It does NOT
implement full Peppol AS4 compliance:
- No WS-Security / XML digital signatures
- No AS4 receipt handling / reliability
- Payload is gzip-compressed as declared in the SOAP header

For production use, prefer the Generic transport with a standards-compliant
Peppol Access Point provider.
"""

from __future__ import annotations

import gzip
import os
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, Optional

import requests

from app.integrations.peppol import PEPPOL_BIS3_PROFILE_ID

PEPPOL_INVOICE_DOCUMENT_TYPE = (
    "urn:oasis:names:specification:ubl:schema:xsd:Invoice-2::Invoice"
    "##urn:cen.eu:en16931:2017#compliant#urn:fdc:peppol.eu:2017:poacc:billing:3.0::2.1"
)

# Flag surfaced in settings UI so users know this is not production-grade
NATIVE_TRANSPORT_EXPERIMENTAL = True

_BOUNDARY = "as4boundary"


class PeppolAS4Error(RuntimeError):
    """AS4 build or send error."""

    pass


def _soap_envelope(
    message_id: str,
    sender_id: str,
    sender_scheme: str,
    recipient_id: str,
    recipient_scheme: str,
    document_id: str,
    process_id: str,
    document_type_id: str,
) -> str:
    """Build minimal AS4/ebMS 3.0 SOAP envelope (PEPPOL profile)."""
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<soap:Envelope xmlns:soap="http://www.w3.org/2003/05/soap-envelope"
               xmlns:eb3="http://docs.oasis-open.org/ebxml-msg/ebms/v3.0/ns/core/200704/">
  <soap:Header>
    <eb3:Messaging>
      <eb3:UserMessage>
        <eb3:MessageInfo>
          <eb3:MessageId>{message_id}</eb3:MessageId>
          <eb3:Timestamp>{datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')}</eb3:Timestamp>
        </eb3:MessageInfo>
        <eb3:PartyInfo>
          <eb3:From>
            <eb3:PartyId type="{sender_scheme}">{sender_id}</eb3:PartyId>
            <eb3:Role>http://docs.oasis-open.org/ebxml-msg/ebms/v3.0/ns/core/200704/initiator</eb3:Role>
          </eb3:From>
          <eb3:To>
            <eb3:PartyId type="{recipient_scheme}">{recipient_id}</eb3:PartyId>
            <eb3:Role>http://docs.oasis-open.org/ebxml-msg/ebms/v3.0/ns/core/200704/responder</eb3:Role>
          </eb3:To>
        </eb3:PartyInfo>
        <eb3:CollaborationInfo>
          <eb3:AgreementRef>urn:fdc:peppol.eu:2017:agreement</eb3:AgreementRef>
          <eb3:Service type="bdxr-service">urn:fdc:peppol.eu:2017:poacc:billing:01:1.0</eb3:Service>
          <eb3:Action>dispatch</eb3:Action>
          <eb3:ConversationId>{document_id}</eb3:ConversationId>
        </eb3:CollaborationInfo>
        <eb3:PayloadInfo>
          <eb3:PartInfo href="cid:payload@peppol.eu">
            <eb3:Schema location="{document_type_id}"/>
            <eb3:PartProperties>
              <eb3:Property name="MimeType">application/xml</eb3:Property>
              <eb3:Property name="CompressionType">application/gzip</eb3:Property>
            </eb3:PartProperties>
          </eb3:PartInfo>
        </eb3:PayloadInfo>
      </eb3:UserMessage>
    </eb3:Messaging>
  </soap:Header>
  <soap:Body/>
</soap:Envelope>"""


def build_as4_message(
    ubl_xml: str,
    sender_endpoint_id: str,
    sender_scheme_id: str,
    recipient_endpoint_id: str,
    recipient_scheme_id: str,
    document_id: str,
    process_id: str = PEPPOL_BIS3_PROFILE_ID,
    document_type_id: str = PEPPOL_INVOICE_DOCUMENT_TYPE,
) -> bytes:
    """
    Build AS4 multipart/related message (SOAP + gzip-compressed payload).
    Returns raw bytes suitable for POST to recipient AP.

    The payload is gzip-compressed to match the CompressionType declared
    in the SOAP header (application/gzip).
    """
    message_id = f"<{uuid.uuid4().hex}@peppol>"
    soap = _soap_envelope(
        message_id=message_id,
        sender_id=sender_endpoint_id,
        sender_scheme=sender_scheme_id,
        recipient_id=recipient_endpoint_id,
        recipient_scheme=recipient_scheme_id,
        document_id=document_id,
        process_id=process_id,
        document_type_id=document_type_id,
    )
    payload_bytes = gzip.compress(ubl_xml.encode("utf-8"))

    # Build MIME multipart/related manually for cross-Python-version compatibility
    parts = []
    parts.append(
        f"--{_BOUNDARY}\r\n"
        f"Content-Type: application/soap+xml; charset=utf-8\r\n"
        f"Content-ID: <root.message@peppol.eu>\r\n"
        f"\r\n"
    )
    parts.append(soap)
    parts.append(
        f"\r\n--{_BOUNDARY}\r\n"
        f"Content-Type: application/gzip\r\n"
        f"Content-ID: <payload@peppol.eu>\r\n"
        f"Content-Transfer-Encoding: binary\r\n"
        f"\r\n"
    )

    result = b""
    for p in parts:
        result += p.encode("utf-8") if isinstance(p, str) else p
    result += payload_bytes
    result += f"\r\n--{_BOUNDARY}--\r\n".encode("utf-8")

    return result


def send_as4_message(
    recipient_ap_url: str,
    message_bytes: bytes,
    timeout_s: float = 60.0,
    cert_path: Optional[str] = None,
    key_path: Optional[str] = None,
) -> Dict[str, Any]:
    """
    POST AS4 message to recipient access point URL.
    If cert_path and key_path are set, use client certificate for mTLS.
    Returns dict with status_code and optional message_id / error from response.
    """
    url = recipient_ap_url.strip().rstrip("/")
    if not url.startswith("http"):
        raise PeppolAS4Error("Recipient AP URL must be HTTP or HTTPS")

    headers = {
        "Content-Type": f"multipart/related; boundary={_BOUNDARY}; type=application/soap+xml",
        "Accept": "application/xml",
    }
    cert = None
    if cert_path and key_path and os.path.isfile(cert_path) and os.path.isfile(key_path):
        cert = (cert_path, key_path)

    try:
        resp = requests.post(
            url,
            data=message_bytes,
            headers=headers,
            timeout=timeout_s,
            cert=cert,
        )
    except requests.RequestException as e:
        raise PeppolAS4Error(f"AS4 send failed: {e}") from e

    result: Dict[str, Any] = {"status_code": resp.status_code}
    if resp.status_code >= 400:
        result["error"] = resp.text[:2000] if resp.text else f"HTTP {resp.status_code}"
        raise PeppolAS4Error(f"Recipient AP returned {resp.status_code}: {result.get('error', '')}")

    if resp.text and "MessageId" in resp.text:
        result["message_id"] = resp.text
    return result
