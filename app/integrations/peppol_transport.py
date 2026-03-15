"""
PEPPOL transport provider interface and implementations.

- GenericTransport: HTTP JSON adapter (access point URL). Production-ready.
- NativePeppolTransport: SML/SMP discovery + AS4 send. EXPERIMENTAL - lacks
  WS-Security, receipt handling, and full Peppol AS4 compliance. Prefer a
  standards-compliant Access Point provider for production workloads.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Dict, Optional

from app.integrations.peppol import PEPPOL_BIS3_PROFILE_ID, PeppolAccessPointError, send_ubl_via_access_point
from app.integrations.peppol_as4 import PeppolAS4Error, build_as4_message, send_as4_message
from app.integrations.peppol_identifiers import PeppolIdentifierError, validate_participant_identifiers
from app.integrations.peppol_smp import PeppolSMPError, get_recipient_endpoint_url, get_smp_url


class PeppolTransportError(RuntimeError):
    """Transport-level error (wraps AP, SMP, or AS4 errors)."""

    pass


class PeppolTransportProtocol(ABC):
    """Abstract transport for sending UBL invoice to recipient via PEPPOL."""

    @abstractmethod
    def send(
        self,
        ubl_xml: str,
        sender_endpoint_id: str,
        sender_scheme_id: str,
        recipient_endpoint_id: str,
        recipient_scheme_id: str,
        document_id: str,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        """
        Send UBL invoice. Returns dict with at least status_code and optionally
        message_id, data, error. Raises PeppolTransportError on failure.
        """
        pass


class GenericTransport(PeppolTransportProtocol):
    """Existing generic HTTP JSON access point adapter."""

    def __init__(
        self,
        access_point_url: str,
        access_point_token: Optional[str] = None,
        timeout_s: float = 30.0,
    ):
        self.access_point_url = access_point_url.strip()
        self.access_point_token = (access_point_token or "").strip() or None
        self.timeout_s = timeout_s

    def send(
        self,
        ubl_xml: str,
        sender_endpoint_id: str,
        sender_scheme_id: str,
        recipient_endpoint_id: str,
        recipient_scheme_id: str,
        document_id: str,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        if not self.access_point_url:
            raise PeppolTransportError("PEPPOL_ACCESS_POINT_URL is not set")
        try:
            validate_participant_identifiers(
                sender_endpoint_id,
                sender_scheme_id,
                recipient_endpoint_id,
                recipient_scheme_id,
            )
        except PeppolIdentifierError as e:
            raise PeppolTransportError(str(e)) from e
        try:
            return send_ubl_via_access_point(
                ubl_xml=ubl_xml,
                recipient_endpoint_id=recipient_endpoint_id,
                recipient_scheme_id=recipient_scheme_id,
                sender_endpoint_id=sender_endpoint_id,
                sender_scheme_id=sender_scheme_id,
                document_id=document_id,
                access_point_url=self.access_point_url,
                access_point_token=self.access_point_token,
                access_point_timeout_s=self.timeout_s,
            )
        except PeppolAccessPointError as e:
            raise PeppolTransportError(str(e)) from e


class NativePeppolTransport(PeppolTransportProtocol):
    """Native PEPPOL: SML/SMP discovery + AS4 send."""

    def __init__(
        self,
        sml_url: Optional[str] = None,
        timeout_s: float = 60.0,
        cert_path: Optional[str] = None,
        key_path: Optional[str] = None,
    ):
        self.sml_url = (sml_url or "").strip() or None
        self.timeout_s = timeout_s
        self.cert_path = (cert_path or "").strip() or None
        self.key_path = (key_path or "").strip() or None

    def send(
        self,
        ubl_xml: str,
        sender_endpoint_id: str,
        sender_scheme_id: str,
        recipient_endpoint_id: str,
        recipient_scheme_id: str,
        document_id: str,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        try:
            validate_participant_identifiers(
                sender_endpoint_id,
                sender_scheme_id,
                recipient_endpoint_id,
                recipient_scheme_id,
            )
        except PeppolIdentifierError as e:
            raise PeppolTransportError(str(e)) from e

        try:
            smp_url = get_smp_url(recipient_endpoint_id, recipient_scheme_id, self.sml_url)
        except PeppolSMPError as e:
            raise PeppolTransportError(f"SMP lookup failed: {e}") from e

        try:
            recipient_ap_url = get_recipient_endpoint_url(smp_url)
        except PeppolSMPError as e:
            raise PeppolTransportError(f"Recipient endpoint lookup failed: {e}") from e

        message_bytes = build_as4_message(
            ubl_xml=ubl_xml,
            sender_endpoint_id=sender_endpoint_id,
            sender_scheme_id=sender_scheme_id,
            recipient_endpoint_id=recipient_endpoint_id,
            recipient_scheme_id=recipient_scheme_id,
            document_id=document_id,
        )
        try:
            result = send_as4_message(
                recipient_ap_url=recipient_ap_url,
                message_bytes=message_bytes,
                timeout_s=self.timeout_s,
                cert_path=self.cert_path,
                key_path=self.key_path,
            )
        except PeppolAS4Error as e:
            raise PeppolTransportError(f"AS4 send failed: {e}") from e

        return {"status_code": result.get("status_code", 200), "data": result}
