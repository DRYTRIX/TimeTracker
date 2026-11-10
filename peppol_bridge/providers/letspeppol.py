from __future__ import annotations

import threading
import time
from typing import Any, Dict, List, Optional
from urllib.parse import quote

import requests

from peppol_bridge.providers.base import ProviderBase, ProviderError, ProviderSendResult

# Transport-oriented status mapping for TimeTracker's post-send verifier.
_OUTBOX_STATUSES = frozenset(
    {
        "pending",
        "scheduled",
        "queued",
        "created",
        "new",
        "to_send",
        "tosend",
        "waiting",
        "retry",
        "retrying",
    }
)
_SENT_STATUSES = frozenset(
    {
        "sent",
        "delivered",
        "processed",
        "success",
        "ok",
        "completed",
        "done",
        "acknowledged",
        "accepted",
    }
)
_FAILED_STATUSES = frozenset(
    {
        "failed",
        "error",
        "fatal",
        "cancelled",
        "canceled",
        "rejected",
        "unregistered",
        "unauthorized",
    }
)


def _peppol_id(scheme_id: str, endpoint_id: str) -> str:
    scheme = (scheme_id or "").strip()
    endpoint = (endpoint_id or "").strip()
    if not scheme:
        return endpoint
    if endpoint.startswith(f"{scheme}:"):
        return endpoint
    return f"{scheme}:{endpoint}"


def _document_type(*, ubl_xml: str, document_type_id: str) -> str:
    type_id = (document_type_id or "").lower()
    root_snip = (ubl_xml or "")[:500].lower()
    if "creditnote" in type_id or "<creditnote" in root_snip:
        return "CREDIT_NOTE"
    if "selfbillingcreditnote" in type_id.replace(":", "").replace("-", ""):
        return "SELF_BILLING_CREDIT_NOTE"
    if "selfbilling" in type_id.replace(":", "").replace("-", "") or "self-billing" in type_id:
        return "SELF_BILLING_INVOICE"
    return "INVOICE"


class LetsPeppolProvider(ProviderBase):
    """
    Let’s Peppol (hosted be.letspeppol.org) provider adapter.

    Uses OAuth2 client-credentials against KYC, then Proxy document APIs:
    - POST /proxy/sapi/document + PUT …/reschedule for outbound send
    - POST /proxy/sapi/document/status for delivery status
    - GET /proxy/sapi/document for inbound inbox polling
    - PUT /proxy/sapi/document/downloaded (batch) to acknowledge downloads
    """

    name = "letspeppol"

    def __init__(
        self,
        *,
        base_url: str,
        client_id: str,
        client_secret: str,
        peppol_id: str,
        timeout_s: float,
        token_url: Optional[str] = None,
    ):
        self.base_url = base_url.rstrip("/")
        self.client_id = client_id
        self.client_secret = client_secret
        self.peppol_id = (peppol_id or "").strip()
        self.timeout_s = timeout_s
        self.token_url = (token_url or f"{self.base_url}/kyc/auth/oauth2/token").rstrip("/")
        self._token: Optional[str] = None
        self._token_expires_at: float = 0.0
        self._token_lock = threading.Lock()

    def _headers(self, *, json_body: bool = True) -> Dict[str, str]:
        headers = {
            "Authorization": f"Bearer {self._access_token()}",
            "Accept": "application/json",
        }
        if json_body:
            headers["Content-Type"] = "application/json"
        return headers

    def _access_token(self) -> str:
        now = time.time()
        with self._token_lock:
            if self._token and now < (self._token_expires_at - 30):
                return self._token
            try:
                resp = requests.post(
                    self.token_url,
                    data={
                        "grant_type": "client_credentials",
                        "scope": "service",
                    },
                    auth=(self.client_id, self.client_secret),
                    headers={"Accept": "application/json"},
                    timeout=self.timeout_s,
                )
            except Exception as e:
                raise ProviderError(f"Failed to reach Let’s Peppol token endpoint: {e}") from e
            if resp.status_code >= 400:
                raise ProviderError(f"Let’s Peppol token HTTP {resp.status_code}: {resp.text[:500]}")
            try:
                data = resp.json()
            except Exception as e:
                raise ProviderError(f"Let’s Peppol token response was not JSON: {e}") from e
            token = data.get("access_token")
            if not isinstance(token, str) or not token.strip():
                raise ProviderError("Let’s Peppol token response missing access_token")
            expires_in = data.get("expires_in")
            try:
                ttl = float(expires_in) if expires_in is not None else 300.0
            except (TypeError, ValueError):
                ttl = 300.0
            self._token = token.strip()
            self._token_expires_at = now + max(ttl, 30.0)
            return self._token

    def _request(
        self,
        method: str,
        path: str,
        *,
        what: str,
        json_body: Any = None,
        params: Optional[Dict[str, Any]] = None,
        expect_json: bool = True,
    ) -> Any:
        url = f"{self.base_url}{path}"
        try:
            resp = requests.request(
                method,
                url,
                headers=self._headers(json_body=json_body is not None),
                json=json_body,
                params=params,
                timeout=self.timeout_s,
            )
        except Exception as e:
            raise ProviderError(f"Failed to call Let’s Peppol {what}: {e}") from e
        if resp.status_code >= 400:
            raise ProviderError(f"Let’s Peppol {what} HTTP {resp.status_code}: {resp.text[:500]}")
        if not expect_json or resp.status_code == 204 or not (resp.text or "").strip():
            return None
        try:
            return resp.json()
        except Exception as e:
            raise ProviderError(f"Let’s Peppol {what} returned non-JSON: {e}") from e

    def test_credentials(self) -> Dict[str, Any]:
        if not self.peppol_id:
            raise ProviderError("LETSPEPPOL_PEPPOL_ID is not set")
        # Force a fresh token so /test fails closed when credentials are wrong.
        with self._token_lock:
            self._token = None
            self._token_expires_at = 0.0
        data = self._request(
            "GET",
            "/proxy/sapi/registry",
            what="registry",
            params={"peppolId": self.peppol_id},
        )
        if not isinstance(data, dict):
            raise ProviderError("Let’s Peppol registry returned an unexpected response shape")
        return {
            "peppol_id": data.get("peppolId") or self.peppol_id,
            "peppol_active": data.get("peppolActive"),
            "access_point": data.get("accessPoint"),
            "default_access_point": data.get("defaultAccessPoint"),
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
        owner = self.peppol_id or _peppol_id(sender_scheme_id, sender_endpoint_id)
        partner = _peppol_id(recipient_scheme_id, recipient_endpoint_id)
        if not owner:
            raise ProviderError("Missing owner Peppol ID (set LETSPEPPOL_PEPPOL_ID or sender identifiers)")
        if not partner:
            raise ProviderError("Missing recipient Peppol ID")

        body = {
            "direction": "OUTGOING",
            "type": _document_type(ubl_xml=ubl_xml, document_type_id=document_type_id),
            "ownerPeppolId": owner,
            "partnerPeppolId": partner,
            "ubl": ubl_xml,
        }
        created = self._request("POST", "/proxy/sapi/document", what="create document", json_body=body)
        if not isinstance(created, dict):
            raise ProviderError("Let’s Peppol create document returned an unexpected response shape")
        doc_id = created.get("id")
        if not doc_id:
            raise ProviderError(f"Let’s Peppol did not return a document id: {created}")

        scheduled = self._request(
            "PUT",
            f"/proxy/sapi/document/{quote(str(doc_id), safe='')}/reschedule",
            what="reschedule document",
            json_body=created,
        )
        raw = scheduled if isinstance(scheduled, dict) else created
        return ProviderSendResult(message_id=str(doc_id), raw=raw if isinstance(raw, dict) else {"id": doc_id})

    def get_status(self, message_id: str) -> Dict[str, Any]:
        data = self._request(
            "POST",
            "/proxy/sapi/document/status",
            what="document status",
            json_body=[message_id],
        )
        docs = data if isinstance(data, list) else []
        match = None
        for item in docs:
            if isinstance(item, dict) and str(item.get("id")) == str(message_id):
                match = item
                break
        if match is None and docs and isinstance(docs[0], dict):
            match = docs[0]
        if not isinstance(match, dict):
            return {"folder": None, "status": None, "raw": {"documents": docs}}

        status = (match.get("processedStatus") or "").strip()
        status_l = status.lower()
        if status_l in _FAILED_STATUSES or status_l.startswith("fail") or status_l.startswith("error"):
            folder: Optional[str] = "failed"
        elif status_l in _SENT_STATUSES:
            folder = "sent"
        elif status_l in _OUTBOX_STATUSES or not status_l:
            folder = "outbox" if status_l else None
        else:
            folder = None

        out: Dict[str, Any] = {
            "folder": folder,
            "status": status or None,
            "raw": {
                "id": match.get("id"),
                "processedOn": match.get("processedOn"),
                "processedStatus": match.get("processedStatus"),
                "partnerPeppolId": match.get("partnerPeppolId"),
                "direction": match.get("direction"),
            },
        }
        if folder == "failed":
            out["fatal_rules"] = [
                {
                    "id": f"letspeppol:{status_l or 'failed'}",
                    "message": f"Let’s Peppol reported status '{status or 'failed'}' for document {message_id}",
                }
            ]
        return out

    def list_inbox(self, *, size: int = 100) -> List[Dict[str, Any]]:
        size = max(1, min(int(size or 100), 500))
        data = self._request(
            "GET",
            "/proxy/sapi/document",
            what="inbox",
            params={"size": size},
        )
        if not isinstance(data, list):
            raise ProviderError("Let’s Peppol inbox returned an unexpected response shape")
        out: List[Dict[str, Any]] = []
        for item in data:
            if isinstance(item, dict):
                out.append(item)
        return out

    def ack_downloaded(self, document_ids: List[str], *, no_archive: bool = False) -> None:
        ids = [str(i).strip() for i in document_ids if str(i).strip()]
        if not ids:
            return
        params = {"noArchive": "true"} if no_archive else None
        # Prefer batch acknowledgement when available.
        self._request(
            "PUT",
            "/proxy/sapi/document/downloaded",
            what="ack downloaded",
            json_body=ids,
            params=params,
            expect_json=False,
        )
