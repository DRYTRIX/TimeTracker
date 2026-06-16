from __future__ import annotations

from typing import Any, Dict, Optional

import requests

from peppol_bridge.providers.base import ProviderBase, ProviderError, ProviderSendResult


class GenericCustomProvider(ProviderBase):
    """
    Generic passthrough provider.

    This mode forwards the exact TimeTracker adapter contract body to a custom URL.
    It's intended as an escape hatch for provider APIs not yet supported by presets.
    """

    name = "generic_custom"

    def __init__(self, *, forward_url: str, bearer_token: Optional[str], timeout_s: float):
        self.forward_url = forward_url.rstrip("/")
        self.bearer_token = (bearer_token or "").strip() or None
        self.timeout_s = timeout_s

    def test_credentials(self) -> Dict[str, Any]:
        if not self.forward_url:
            raise ProviderError("GENERIC_FORWARD_URL is not set")
        return {"ok": True, "forward_url": self.forward_url}

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
        headers: Dict[str, str] = {"Content-Type": "application/json"}
        if self.bearer_token:
            headers["Authorization"] = f"Bearer {self.bearer_token}"
        body = {
            "recipient": {"endpoint_id": recipient_endpoint_id, "scheme_id": recipient_scheme_id},
            "sender": {"endpoint_id": sender_endpoint_id, "scheme_id": sender_scheme_id},
            "document": {"id": document_id, "type_id": document_type_id, "process_id": process_id},
            "payload": {"ubl_xml": ubl_xml},
        }
        try:
            resp = requests.post(self.forward_url, headers=headers, json=body, timeout=self.timeout_s)
        except Exception as e:
            raise ProviderError(f"Forward request failed: {e}") from e
        content_type = (resp.headers.get("content-type") or "").lower()
        if "application/json" in content_type:
            data: Any = resp.json()
        else:
            data = {"raw": resp.text}
        if resp.status_code >= 400:
            raise ProviderError(f"Forward URL returned HTTP {resp.status_code}: {data}")
        message_id = None
        if isinstance(data, dict):
            message_id = data.get("message_id") or data.get("messageId") or data.get("id")
        return ProviderSendResult(message_id=message_id, raw={"forward_response": data, "status_code": resp.status_code})

