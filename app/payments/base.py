"""Payment provider plugin interface."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any, Dict, Optional


@dataclass
class CheckoutResult:
    success: bool
    url: Optional[str] = None
    session_id: Optional[str] = None
    message: Optional[str] = None
    raw: Dict[str, Any] = field(default_factory=dict)


@dataclass
class WebhookResult:
    valid: bool
    event_type: Optional[str] = None
    transaction_id: Optional[str] = None
    invoice_id: Optional[int] = None
    amount: Optional[Decimal] = None
    currency: Optional[str] = None
    raw: Dict[str, Any] = field(default_factory=dict)
    message: Optional[str] = None


class PaymentProvider(ABC):
    """Abstract payment gateway provider."""

    provider_name: str = "base"

    def __init__(self, config: Dict[str, Any], is_test_mode: bool = False):
        self.config = config
        self.is_test_mode = is_test_mode

    @abstractmethod
    def create_checkout_session(
        self,
        invoice_id: int,
        amount: Decimal,
        currency: str,
        success_url: str,
        cancel_url: str,
        description: Optional[str] = None,
    ) -> CheckoutResult:
        raise NotImplementedError

    @abstractmethod
    def verify_webhook(self, payload: bytes, headers: Dict[str, str]) -> WebhookResult:
        raise NotImplementedError

    def refund(
        self,
        *,
        gateway_transaction_id: str,
        amount: Decimal,
        currency: str,
        reason: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Issue a refund via the gateway.

        Returns a dict with at least ``success`` (bool) and ``message`` (str).
        Default implementation returns a not-supported error so providers that
        don't implement refunds fail gracefully.
        """
        return {"success": False, "message": f"Refunds are not supported by provider '{self.provider_name}'"}
