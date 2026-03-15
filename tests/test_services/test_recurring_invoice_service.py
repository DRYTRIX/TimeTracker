"""
Tests for RecurringInvoiceService.
"""

import pytest
from unittest.mock import MagicMock

pytestmark = [pytest.mark.unit]

from app.services.recurring_invoice_service import RecurringInvoiceService


class TestRecurringInvoiceService:
    """Tests for RecurringInvoiceService."""

    def test_generate_invoice_returns_none_when_should_not_generate(self):
        """When should_generate_today() is False, generate_invoice returns None."""
        service = RecurringInvoiceService()
        recurring = MagicMock()
        recurring.should_generate_today.return_value = False

        result = service.generate_invoice(recurring)

        assert result is None
        recurring.should_generate_today.assert_called_once()
