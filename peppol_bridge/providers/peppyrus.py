from __future__ import annotations

import base64
from typing import Any, Dict

import requests

from peppol_bridge.providers.base import ProviderBase, ProviderError, ProviderSendResult


class PeppyrusProvider(ProviderBase):
    """
    Peppyrus provider adapter.

    Uses:
    - GET /organization/info to verify credentials
    - POST /message to send a base64-encoded UBL invoice (Peppol BIS 3.0)
    """

    name = "peppyrus"

    def __init__(self, *, base_url: str, api_key: str, timeout_s: float):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.timeout_s = timeout_s

    def _headers(self) -> Dict[str, str]:
        return {"X-Api-Key": self.api_key, "Content-Type": "application/json"}

    def test_credentials(self) -> Dict[str, Any]:
        url = f"{self.base_url}/organization/info"
        try:
            resp = requests.get(url, headers=self._headers(), timeout=self.timeout_s)
        except Exception as e:
            raise ProviderError(f"Failed to reach Peppyrus: {e}") from e
        if resp.status_code >= 400:
            raise ProviderError(f"Peppyrus returned HTTP {resp.status_code}: {resp.text}")
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
        url = f"{self.base_url}/message"
        payload = {
            "sender": f"{sender_scheme_id}:{sender_endpoint_id}" if sender_scheme_id else sender_endpoint_id,
            "recipient": f"{recipient_scheme_id}:{recipient_endpoint_id}" if recipient_scheme_id else recipient_endpoint_id,
            "documentType": document_type_id,
            "processType": process_id,
            "fileName": f"{document_id or 'invoice'}.xml",
            "fileContent": base64.b64encode(ubl_xml.encode('utf-8')).decode('ascii'),
        }
        try:
            resp = requests.post(url, headers=self._headers(), json=payload, timeout=self.timeout_s)
        except Exception as e:
            raise ProviderError(f"Failed to call Peppyrus /message: {e}") from e
        if resp.status_code >= 400:
            raise ProviderError(f"Peppyrus returned HTTP {resp.status_code}: {resp.text}")
        try:
            data = resp.json()
        except Exception:
            data = {"raw": resp.text}

        message_id = None
        if isinstance(data, dict):
            message_id = data.get("id") or data.get("message_id") or data.get("messageId")
        return ProviderSendResult(message_id=message_id, raw=data if isinstance(data, dict) else {"data": data})

    def get_status(self, message_id: str) -> Dict[str, Any]:
        # Peppyrus accepts POST /message synchronously but validates/transmits async;
        # the message folder (Outbox -> Sent | Failed) is the real outcome. On Failed,
        # /message/{id}/report carries the validation rule failures.
        url = f"{self.base_url}/message/{message_id}"
        try:
            resp = requests.get(url, headers=self._headers(), timeout=self.timeout_s)
        except Exception as e:
            raise ProviderError(f"Failed to call Peppyrus /message/{{id}}: {e}") from e
        if resp.status_code >= 400:
            raise ProviderError(f"Peppyrus returned HTTP {resp.status_code}: {resp.text}")
        try:
            data = resp.json()
        except Exception:
            raise ProviderError(f"Peppyrus returned non-JSON status: {resp.text[:200]}")
        if isinstance(data, dict):
            data.pop("fileContent", None)
        folder = (data.get("folder") or "").strip().lower() if isinstance(data, dict) else ""
        out: Dict[str, Any] = {"folder": folder or None, "raw": data}
        if folder == "failed":
            try:
                rep = requests.get(f"{url}/report", headers=self._headers(), timeout=self.timeout_s)
                if rep.status_code < 400:
                    rules = (rep.json() or {}).get("validationRules") or []
                    out["fatal_rules"] = [
                        {"id": r.get("id") or "XSD", "message": (r.get("message") or "")[:300]}
                        for r in rules
                        if (r.get("type") or "").upper() == "FATAL"
                    ]
            except Exception:
                pass
        return out

