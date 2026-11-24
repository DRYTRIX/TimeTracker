"""
Tests for RecurringInvoiceService.
"""

from datetime import date, datetime, timezone
from unittest.mock import MagicMock

import pytest
from freezegun import freeze_time

from app import db
from app.models import Settings
from app.services.recurring_invoice_service import RecurringInvoiceService
from app.utils.timezone import now_in_app_timezone


class TestRecurringInvoiceService:
    """Tests for RecurringInvoiceService."""

    pytestmark = [pytest.mark.unit]

    def test_generate_invoice_returns_none_when_should_not_generate(self):
        """When should_generate_today() is False, generate_invoice returns None."""
        service = RecurringInvoiceService()
        recurring = MagicMock()
        recurring.should_generate_today.return_value = False

        result = service.generate_invoice(recurring)

        assert result is None
        recurring.should_generate_today.assert_called_once()


@pytest.mark.integration
def test_should_generate_today_uses_app_timezone_east_of_utc(app, recurring_invoice):
    """App-local today wins when UTC calendar day still lags (issue #965)."""
    settings = Settings.get_settings()
    settings.timezone = "Asia/Tokyo"
    db.session.commit()

    # 23:00 UTC on 23 Nov is already 08:00 on 24 Nov in Tokyo (UTC+9).
    with freeze_time(datetime(2026, 11, 23, 23, 0, 0, tzinfo=timezone.utc)):
        app_today = now_in_app_timezone().date()
        assert app_today == date(2026, 11, 24)
        assert datetime.utcnow().date() == date(2026, 11, 23)

        recurring_invoice.next_run_date = app_today
        recurring_invoice.is_active = True
        db.session.commit()

        assert recurring_invoice.should_generate_today() is True

        invoice = RecurringInvoiceService().generate_invoice(recurring_invoice)
        assert invoice is not None
        assert invoice.issue_date == app_today
        assert invoice.id is not None
