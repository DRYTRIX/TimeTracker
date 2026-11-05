"""Exchange rate fetching falls back to the keyless ECB endpoint."""

from datetime import date
from decimal import Decimal
from unittest.mock import MagicMock, patch

import pytest

from app.services.currency_service import CurrencyService


def _response(payload, status=200):
    resp = MagicMock()
    resp.status_code = status
    resp.json.return_value = payload
    return resp


@pytest.mark.unit
def test_fetch_uses_ecb_fallback_when_primary_has_no_rate():
    primary = _response({"success": False, "error": {"code": 101, "type": "missing_access_key"}})
    ecb = _response({"success": True, "base": "USD", "date": "2026-10-15", "rates": {"EUR": 0.8922}})
    with patch("app.services.currency_service.requests.get", side_effect=[primary, ecb]) as get:
        rate = CurrencyService.fetch_exchange_rate("USD", "EUR", date(2026, 10, 15))
    assert rate == Decimal("0.8922")
    assert get.call_args_list[1].args[0] == f"{CurrencyService.ECB_FALLBACK_API_URL}/2026-10-15"


@pytest.mark.unit
def test_fetch_keeps_primary_result_when_available():
    primary = _response({"success": True, "rates": {"EUR": 0.9}})
    with patch("app.services.currency_service.requests.get", side_effect=[primary]) as get:
        rate = CurrencyService.fetch_exchange_rate("USD", "EUR", date(2026, 10, 15))
    assert rate == Decimal("0.9")
    assert get.call_count == 1
