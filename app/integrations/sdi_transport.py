"""Generic HTTP transport for Italian SDI (FatturaPA) intermediaries."""

from __future__ import annotations

import base64
import logging
from typing import Any, Dict, Optional
import requests

logger = logging.getLogger(__name__)


class SdiTransportError(RuntimeError):
    pass


def bridge_base_url(transport_url: str) -> str:
    """Strip a trailing /send path to get the intermediary base URL."""
    url = (transport_url or "").rstrip("/")
    if url.lower().endswith("/send"):
        url = url[: -len("/send")]
    return url.rstrip("/")


class GenericSdiTransport:
    """
    HTTP adapter for a user-configured SDI intermediary.

    Send contract:
      POST {url}
      Authorization: Bearer {token}
      JSON: {
        filename, formato, recipient: {codice_destinatario, pec},
        xml_base64, sha256
      }
      Response: {message_id, sdi_identifier?}

    Status contract:
      GET {base}/message/{message_id}/status
      Response: {
        status, sdi_identifier?,
        notifications: [{type: RC|NS|MC|NE|DT|AT, date, detail}]
      }
    """

    def __init__(self, url: str, token: Optional[str] = None, timeout: int = 30):
        self.url = (url or "").strip()
        self.token = (token or "").strip() or None
        self.timeout = timeout or 30
        if not self.url:
            raise SdiTransportError("SDI transport URL is not configured")

    def _headers(self) -> Dict[str, str]:
        headers = {"Content-Type": "application/json", "Accept": "application/json"}
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        return headers

    def send(
        self,
        *,
        filename: str,
        formato: str,
        codice_destinatario: str,
        pec: Optional[str],
        xml: str,
        sha256: str,
    ) -> Dict[str, Any]:
        payload = {
            "filename": filename,
            "formato": formato,
            "recipient": {
                "codice_destinatario": codice_destinatario,
                "pec": pec,
            },
            "xml_base64": base64.b64encode(xml.encode("utf-8")).decode("ascii"),
            "sha256": sha256,
        }
        try:
            resp = requests.post(self.url, json=payload, headers=self._headers(), timeout=self.timeout)
        except requests.RequestException as e:
            raise SdiTransportError(f"SDI transport request failed: {e}") from e

        if resp.status_code >= 400:
            raise SdiTransportError(f"SDI transport returned HTTP {resp.status_code}: {resp.text[:500]}")

        try:
            data = resp.json()
        except Exception as e:
            raise SdiTransportError(f"SDI transport returned non-JSON response: {e}") from e

        if not isinstance(data, dict):
            raise SdiTransportError("SDI transport response must be a JSON object")
        if not data.get("message_id"):
            raise SdiTransportError("SDI transport response missing message_id")
        return data

    def get_status(self, message_id: str) -> Dict[str, Any]:
        base = bridge_base_url(self.url)
        status_url = f"{base}/message/{message_id}/status"
        try:
            resp = requests.get(status_url, headers=self._headers(), timeout=self.timeout)
        except requests.RequestException as e:
            raise SdiTransportError(f"SDI status request failed: {e}") from e

        if resp.status_code >= 400:
            raise SdiTransportError(f"SDI status returned HTTP {resp.status_code}: {resp.text[:500]}")

        try:
            data = resp.json()
        except Exception as e:
            raise SdiTransportError(f"SDI status returned non-JSON response: {e}") from e

        if not isinstance(data, dict):
            raise SdiTransportError("SDI status response must be a JSON object")
        return data
