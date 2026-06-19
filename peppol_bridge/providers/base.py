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

