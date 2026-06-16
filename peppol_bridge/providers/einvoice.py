from __future__ import annotations

import io
from typing import Any, Dict, Optional

import requests

from peppol_bridge.providers.base import ProviderBase, ProviderError, ProviderSendResult


class EInvoiceProvider(ProviderBase):
    """
    e-invoice.be provider adapter.

    Uses:
    - GET /api/me/ to verify credentials
    - POST /api/documents/ubl (multipart file upload) to create a document from UBL
    - POST /api/documents/{document_id}/send to send over Peppol network
    """

    name = "e-invoice.be"

    def __init__(self, *, base_url: str, api_key: str, timeout_s: float):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.timeout_s = timeout_s

    def _headers(self) -> Dict[str, str]:
        return {"Authorization": f"Bearer {self.api_key}"}

    def test_credentials(self) -> Dict[str, Any]:
        url = f"{self.base_url}/api/me/"
        try:
            resp = requests.get(url, headers=self._headers(), timeout=self.timeout_s)
        except Exception as e:
            raise ProviderError(f"Failed to reach e-invoice.be: {e}") from e
        if resp.status_code >= 400:
            raise ProviderError(f"e-invoice.be returned HTTP {resp.status_code}: {resp.text}")
        try:
            return resp.json()
        except Exception:
            return {"raw": resp.text}

    def _create_document_from_ubl(self, *, ubl_xml: str, filename: str) -> Dict[str, Any]:
        url = f"{self.base_url}/api/documents/ubl"
        files = {
            "file": (filename, io.BytesIO(ubl_xml.encode("utf-8")), "application/xml"),
        }
        try:
            resp = requests.post(url, headers=self._headers(), files=files, timeout=self.timeout_s)
        except Exception as e:
            raise ProviderError(f"Failed to call e-invoice.be /api/documents/ubl: {e}") from e
        if resp.status_code >= 400:
            raise ProviderError(f"e-invoice.be returned HTTP {resp.status_code}: {resp.text}")
        try:
            return resp.json()
        except Exception as e:
            raise ProviderError(f"e-invoice.be returned non-JSON response: {e} ({resp.text[:500]})") from e

    def _send_document(self, *, document_id: str) -> Dict[str, Any]:
        url = f"{self.base_url}/api/documents/{document_id}/send"
        try:
            resp = requests.post(url, headers=self._headers(), timeout=self.timeout_s)
        except Exception as e:
            raise ProviderError(f"Failed to call e-invoice.be send: {e}") from e
        if resp.status_code >= 400:
            raise ProviderError(f"e-invoice.be returned HTTP {resp.status_code}: {resp.text}")
        try:
            return resp.json()
        except Exception:
            return {"raw": resp.text}

    def send_ubl(
        self,
        *,
        ubl_xml: str,
        sender_endpoint_id: str,
        sender_scheme_id: str,
        recipient_endpoint_id: str,
        recipient_scheme_id: str,
        document_id: str,
        document_type_id: str,
        process_id: str,
    ) -> ProviderSendResult:
        # The e-invoice API derives routing from the UBL content (Endpoint IDs etc.).
        # We still accept the routing identifiers for compatibility with TimeTracker’s contract.
        filename = f"{document_id or 'invoice'}.xml"
        created = self._create_document_from_ubl(ubl_xml=ubl_xml, filename=filename)
        doc_id: Optional[str] = None
        if isinstance(created, dict):
            doc_id = created.get("id") or created.get("document_id") or created.get("documentId")
        if not doc_id:
            # Best-effort fallback: some APIs nest the created document under 'document'
            doc = created.get("document") if isinstance(created, dict) else None
            if isinstance(doc, dict):
                doc_id = doc.get("id") or doc.get("document_id")
        if not doc_id:
            raise ProviderError(f"e-invoice.be did not return a document id: {created}")

        sent = self._send_document(document_id=str(doc_id))
        message_id = None
        if isinstance(sent, dict):
            message_id = sent.get("message_id") or sent.get("messageId") or sent.get("id") or str(doc_id)
        return ProviderSendResult(message_id=message_id, raw={"created": created, "sent": sent})

