from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional


@dataclass(frozen=True)
class ProviderSendResult:
    message_id: Optional[str]
    raw: Dict[str, Any]


class ProviderError(RuntimeError):
    pass


class ProviderBase:
    name: str

    def test_credentials(self) -> Dict[str, Any]:
        raise NotImplementedError

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
        raise NotImplementedError

    def get_status(self, message_id: str) -> Dict[str, Any]:
        """Return AP-side delivery status for a previously sent message.

        Expected keys: folder (lowercase, e.g. outbox/sent/failed, None if unknown)
        and fatal_rules (list of {id, message}) when the AP reports a failure.
        """
        raise ProviderError(f"Status lookup not supported by provider '{self.name}'")

