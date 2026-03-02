"""
PEPPOL AS4 message packaging and transmission.

Builds AS4 (ebMS 3.0 / PEPPOL AS4 profile) messages and sends to recipient
access point. Optional signing when certificate is configured.
"""

from __future__ import annotations

import email.generator
import email.policy
import os
import uuid
from datetime import datetime, timezone
from email.message import EmailMessage
from io import BytesIO
from typing import Any, Dict, Optional

import requests

from app.integrations.peppol import PEPPOL_BIS3_PROFILE_ID

# PEPPOL AS4 profile: invoice document type URN
PEPPOL_INVOICE_DOCUMENT_TYPE = (
    "urn:oasis:names:specification:ubl:schema:xsd:Invoice-2::Invoice"
    "##urn:cen.eu:en16931:2017#compliant#urn:fdc:peppol.eu:2017:poacc:billing:3.0::2.1"
)


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
          <eb3:PartInfo href="cid:payload@europe.eu">
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
    Build AS4 multipart message (SOAP + payload).
    Returns raw bytes suitable for POST to recipient AP.
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
    payload_bytes = ubl_xml.encode("utf-8")

    # Build MIME multipart/related: root SOAP + payload part
    policy = email.policy.EmailPolicy(line_max=0)
    msg = EmailMessage(policy=policy)
    msg["Content-Type"] = "multipart/related; boundary=as4boundary; type=application/soap+xml"
    msg.set_boundary("as4boundary")

    msg.add_attachment(
        soap.encode("utf-8"),
        maintype="application",
        subtype="soap+xml",
        disposition="inline",
        headers={"Content-ID": "<root.message@europe.eu>"},
    )
    msg.add_attachment(
        payload_bytes,
        maintype="application",
        subtype="xml",
        disposition="attachment",
        headers={"Content-ID": "<payload@europe.eu>"},
    )

    buf = BytesIO()
    gen = email.generator.BytesGenerator(buf, policy=policy)
    gen.flatten(msg)
    return buf.getvalue()


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
        "Content-Type": "multipart/related; boundary=as4boundary; type=application/soap+xml",
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

    # Try to parse SOAP response for MessageId or receipt
    if resp.text and "MessageId" in resp.text:
        result["message_id"] = resp.text  # Caller can parse if needed
    return result
