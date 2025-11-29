"""
Currency conversion service with automatic rate fetching
"""

from typing import Dict, Optional, Decimal
from datetime import datetime, date
from decimal import Decimal as D
import requests
import logging
from app import db
from app.models.currency import Currency, ExchangeRate

logger = logging.getLogger(__name__)


class CurrencyService:
    """Service for currency conversion and exchange rate management"""

    EXCHANGE_API_URL = "https://api.exchangerate.host"  # Free API
    FALLBACK_API_URL = "https://api.exchangerate-api.com/v4/latest"  # Alternative

    @staticmethod
    def convert(amount: Decimal, from_currency: str, to_currency: str, conversion_date: date = None) -> Decimal:
        """Convert amount from one currency to another"""
        if from_currency == to_currency:
            return amount

        if not conversion_date:
            conversion_date = date.today()

        # Get exchange rate
        rate = CurrencyService.get_exchange_rate(from_currency, to_currency, conversion_date)
        if not rate:
            logger.warning(f"Exchange rate not found for {from_currency}/{to_currency} on {conversion_date}")
            return amount  # Return original amount if conversion fails

        return amount * rate

    @staticmethod
    def get_exchange_rate(base_currency: str, quote_currency: str, rate_date: date = None) -> Optional[Decimal]:
        """Get exchange rate, fetching if not in database"""
        if not rate_date:
            rate_date = date.today()

        # Try database first
        rate = ExchangeRate.query.filter_by(base_code=base_currency, quote_code=quote_currency, date=rate_date).first()

        if rate:
            return D(str(rate.rate))

        # Try reverse rate
        rate = ExchangeRate.query.filter_by(base_code=quote_currency, quote_code=base_currency, date=rate_date).first()

        if rate:
            # Calculate inverse rate
            return D("1") / D(str(rate.rate))

        # Fetch from API
        fetched_rate = CurrencyService.fetch_exchange_rate(base_currency, quote_currency, rate_date)
        if fetched_rate:
            # Store in database
            CurrencyService.store_exchange_rate(base_currency, quote_currency, rate_date, fetched_rate)
            return fetched_rate

        return None

    @staticmethod
    def fetch_exchange_rate(base_currency: str, quote_currency: str, rate_date: date = None) -> Optional[Decimal]:
        """Fetch exchange rate from external API"""
        if not rate_date:
            rate_date = date.today()

        try:
            # Try primary API (exchangerate.host)
            url = f"{CurrencyService.EXCHANGE_API_URL}/{rate_date}"
            params = {"base": base_currency, "symbols": quote_currency}

            response = requests.get(url, params=params, timeout=10)
            if response.status_code == 200:
                data = response.json()
                if data.get("success") and quote_currency in data.get("rates", {}):
                    rate = D(str(data["rates"][quote_currency]))
                    return rate

            # Try fallback API
            url = f"{CurrencyService.FALLBACK_API_URL}/{base_currency}"
            response = requests.get(url, timeout=10)
            if response.status_code == 200:
                data = response.json()
                if quote_currency in data.get("rates", {}):
                    rate = D(str(data["rates"][quote_currency]))
                    # Store for historical date if needed
                    CurrencyService.store_exchange_rate(base_currency, quote_currency, rate_date, rate)
                    return rate

        except Exception as e:
            logger.error(f"Error fetching exchange rate: {e}")

        return None

    @staticmethod
    def store_exchange_rate(base_currency: str, quote_currency: str, rate_date: date, rate: Decimal):
        """Store exchange rate in database"""
        try:
            exchange_rate = ExchangeRate(
                base_code=base_currency,
                quote_code=quote_currency,
                rate=rate,
                date=rate_date,
                source="exchangerate.host",
            )
            db.session.add(exchange_rate)
            db.session.commit()
        except Exception as e:
            logger.error(f"Error storing exchange rate: {e}")
            db.session.rollback()

    @staticmethod
    def update_exchange_rates(base_currency: str = "EUR", currencies: list = None):
        """Update exchange rates for multiple currencies"""
        if not currencies:
            # Get all active currencies
            currencies = [c.code for c in Currency.query.filter_by(is_active=True).all()]

        updated = 0
        today = date.today()

        for quote_currency in currencies:
            if quote_currency == base_currency:
                continue

            try:
                rate = CurrencyService.fetch_exchange_rate(base_currency, quote_currency, today)
                if rate:
                    updated += 1
            except Exception as e:
                logger.error(f"Error updating rate for {quote_currency}: {e}")

        logger.info(f"Updated {updated} exchange rates")
        return updated

    @staticmethod
    def get_historical_rates(base_currency: str, quote_currency: str, start_date: date, end_date: date) -> list:
        """Get historical exchange rates for a date range"""
        rates = (
            ExchangeRate.query.filter(
                ExchangeRate.base_code == base_currency,
                ExchangeRate.quote_code == quote_currency,
                ExchangeRate.date >= start_date,
                ExchangeRate.date <= end_date,
            )
            .order_by(ExchangeRate.date.asc())
            .all()
        )

        return [{"date": rate.date.isoformat(), "rate": float(rate.rate), "source": rate.source} for rate in rates]

    @staticmethod
    def auto_convert_invoice(invoice) -> Dict[str, Decimal]:
        """Automatically convert invoice amounts to different currencies"""
        if not hasattr(invoice, "currency_code") or not invoice.currency_code:
            return {}

        conversions = {}
        base_currency = invoice.currency_code
        base_amount = invoice.total_amount

        # Get all active currencies
        currencies = Currency.query.filter_by(is_active=True).all()

        for currency in currencies:
            if currency.code != base_currency:
                converted = CurrencyService.convert(base_amount, base_currency, currency.code)
                conversions[currency.code] = converted

        return conversions
