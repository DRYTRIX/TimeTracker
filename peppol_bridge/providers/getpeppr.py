from __future__ import annotations

import base64
import hashlib
import json
import re
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from urllib.parse import quote, urlsplit

import requests

from peppol_bridge.providers.base import ProviderBase, ProviderError, ProviderSendResult

# getpeppr document statuses, grouped by what they say about AP-side delivery.
# `submitted` = accepted by getpeppr, not yet delivered to the recipient's access point.
# `delivered` and the buyer's later responses (including a business `rejected`) mean the
# document reached the recipient's access point.
# `no_action` = the recipient was not found on the network, nothing was delivered.
# `cleared` (tax clearance) says nothing about delivery, so like `unknown` it maps to None.
_OUTBOX_STATUSES = frozenset({"submitted"})
_SENT_STATUSES = frozenset(
    {
        "delivered",
        "acknowledged",
        "in_process",
        "under_query",
        "conditionally_accepted",
        "accepted",
        "rejected",
        "paid",
        "partially_paid",
    }
)
_FAILURE_RULES = {
    "failed": "getpeppr could not deliver document {id} to the recipient's access point",
    "no_action": "The recipient of document {id} was not found on the Peppol network; check its Peppol ID",
}

# Embedded attachments (BG-24) are left out of the idempotency key only. TimeTracker
# regenerates the invoice PDF on every send attempt (it carries its own creation time), and
# sends without it when generation fails, the file is too large or embedding is turned off.
# So one invoice can go out with a different PDF, or none, from one attempt to the next.
_PREFIX = r"(?:[A-Za-z_][\w.-]*:)?"
_DOCUMENT_REFERENCE = re.compile(
    rf"<{_PREFIX}AdditionalDocumentReference\b[^>]*>"
    rf"(?:(?!</{_PREFIX}AdditionalDocumentReference>).)*"
    rf"</{_PREFIX}AdditionalDocumentReference>",
    re.DOTALL,
)
_BETWEEN_TAGS = re.compile(r">\s+<")


def _utc_day() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%d")


def _invoice_fingerprint(ubl_xml: str) -> str:
    def drop_attachment(match: "re.Match[str]") -> str:
        return "" if "EmbeddedDocumentBinaryObject" in match.group(0) else match.group(0)

    return _BETWEEN_TAGS.sub("><", _DOCUMENT_REFERENCE.sub(drop_attachment, ubl_xml)).strip()


def _idempotency_key(*, ubl_xml: str, filename: str, peppol_id: str) -> str:
    canonical = _invoice_fingerprint(ubl_xml)
    digest = hashlib.sha256("\n".join((peppol_id, filename, canonical)).encode("utf-8")).hexdigest()
    return f"timetracker-peppol-bridge-{_utc_day()}-{digest}"


class GetpepprProvider(ProviderBase):
    """
    getpeppr provider adapter.

    Uses:
    - GET /identity to verify credentials (read-only: the key's environment and Peppol identity)
    - POST /invoices/import to send the UBL document as-is (base64), routed to the recipient Peppol ID
    - GET /invoices/{id} to read the document status
    """

    name = "getpeppr"

    def __init__(self, *, base_url: str, api_key: str, timeout_s: float):
        base_url = base_url.rstrip("/")
        parts = urlsplit(base_url)
        if parts.scheme != "https" and not (
            parts.scheme == "http" and parts.hostname in {"localhost", "127.0.0.1", "::1"}
        ):
            raise ProviderError("GETPEPPR_BASE_URL must use https (plain http is accepted for localhost only)")
        self.base_url = base_url
        self.api_key = api_key
        self.timeout_s = timeout_s

    def _headers(self) -> Dict[str, str]:
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Accept": "application/json",
        }

    def _get_json(self, path: str, what: str) -> Dict[str, Any]:
        try:
            resp = requests.get(f"{self.base_url}{path}", headers=self._headers(), timeout=self.timeout_s)
        except Exception as e:
            raise ProviderError(f"Failed to reach getpeppr {what}: {e}") from e
        if resp.status_code >= 400:
            raise ProviderError(f"getpeppr returned HTTP {resp.status_code}: {resp.text[:500]}")
        try:
            data = resp.json()
        except Exception as e:
            raise ProviderError(f"getpeppr returned non-JSON response: {resp.text[:200]}") from e
        if not isinstance(data, dict):
            raise ProviderError("getpeppr returned an unexpected response shape")
        return data

    def test_credentials(self) -> Dict[str, Any]:
        data = self._get_json("/identity", "/identity")
        # Only what an admin needs to confirm the key: environment (sandbox or production)
        # and the sending identity. No address, no internal ids.
        le = data.get("legalEntity")
        identifiers: List[Dict[str, Any]] = []
        for i in data.get("identifiers") or []:
            if isinstance(i, dict):
                identifiers.append({"scheme": i.get("scheme"), "value": i.get("value"), "status": i.get("status")})
        return {
            "environment": data.get("environment"),
            "legal_entity": (
                {"company_name": le.get("companyName"), "country": le.get("country")} if isinstance(le, dict) else None
            ),
            "identifiers": identifiers,
        }

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
        # getpeppr derives the sender from the API key's legal entity (and refuses a UBL whose
        # supplier is not that entity) and the document type from the UBL itself, so the sender
        # and document/process identifiers are accepted for TimeTracker's contract but not sent.
        # The recipient Peppol ID is sent explicitly: getpeppr never derives routing from the UBL.
        filename = f"{document_id or 'invoice'}.xml"
        peppol_id = f"{recipient_scheme_id}:{recipient_endpoint_id}"
        body = {
            "file": base64.b64encode(ubl_xml.encode("utf-8")).decode("ascii"),
            "filename": filename,
            "to": {"peppolId": peppol_id},
        }
        # Peppol does not de-duplicate. The key names the invoice (its UBL without the embedded
        # attachments), its recipient and the UTC day. Sending the same invoice again that
        # day can only replay the original document (identical bytes) or be refused by getpeppr
        # as a key reused for another body: never a second copy. A corrected invoice is a new
        # key, and a deliberate resend on a later day goes out (getpeppr flags it `duplicateOf`).
        headers = {
            **self._headers(),
            "Content-Type": "application/json",
            "Idempotency-Key": _idempotency_key(ubl_xml=ubl_xml, filename=filename, peppol_id=peppol_id),
        }
        try:
            resp = requests.post(
                f"{self.base_url}/invoices/import",
                headers=headers,
                data=json.dumps(body, separators=(",", ":")).encode("utf-8"),
                timeout=self.timeout_s,
            )
        except Exception as e:
            raise ProviderError(f"Failed to call getpeppr /invoices/import: {e}") from e
        if resp.status_code >= 400:
            raise ProviderError(f"getpeppr returned HTTP {resp.status_code}: {resp.text[:500]}")
        try:
            data = resp.json()
        except Exception as e:
            raise ProviderError(f"getpeppr returned non-JSON response: {resp.text[:200]}") from e
        if not isinstance(data, dict):
            raise ProviderError("getpeppr returned an unexpected response shape")

        message_id: Optional[str] = data.get("providerDocumentId") or data.get("id")
        if not message_id:
            raise ProviderError(f"getpeppr did not return a document id: {data}")
        return ProviderSendResult(message_id=str(message_id), raw=data)

    def get_status(self, message_id: str) -> Dict[str, Any]:
        data = self._get_json(f"/invoices/{quote(message_id, safe='')}", "/invoices/{id}")
        status = (data.get("status") or "").strip().lower()
        if status in _OUTBOX_STATUSES:
            folder: Optional[str] = "outbox"
        elif status in _SENT_STATUSES:
            folder = "sent"
        elif status in _FAILURE_RULES:
            folder = "failed"
        else:
            folder = None
        # Only what identifies the document and its state; amounts and names stay at getpeppr.
        raw = {k: data.get(k) for k in ("providerDocumentId", "submissionId", "number", "environment", "updatedAt")}
        out: Dict[str, Any] = {"folder": folder, "status": status or None, "raw": raw}
        if folder == "failed":
            out["fatal_rules"] = [
                {
                    "id": f"getpeppr:{'no_recipient' if status == 'no_action' else 'failed'}",
                    "message": _FAILURE_RULES[status].format(id=message_id),
                }
            ]
        return out
