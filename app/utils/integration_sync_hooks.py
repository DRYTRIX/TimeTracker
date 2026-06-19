"""Event-driven integration sync hooks for accounting connectors."""

import logging
from typing import Optional

logger = logging.getLogger(__name__)


def _get_active_connector(provider: str):
    from app.models import Integration
    from app.services.integration_service import IntegrationService

    integration = Integration.query.filter_by(provider=provider, is_active=True).first()
    if not integration:
        return None, None
    service = IntegrationService()
    connector = service.get_connector(integration)
    return integration, connector


def trigger_invoice_sync(invoice, event: str = "updated") -> None:
    """Push invoice changes to connected accounting systems when auto_sync is enabled."""
    if not invoice or invoice.status not in ("sent", "paid"):
        return

    for provider in ("quickbooks", "xero"):
        try:
            integration, connector = _get_active_connector(provider)
            if not integration or not connector:
                continue
            config = integration.config or {}
            if not config.get("auto_sync", False):
                continue
            from app.integrations.sync_config import export_enabled, should_sync_invoices

            if not export_enabled(config, provider) or not should_sync_invoices(config, "incremental"):
                continue
            result = connector.sync_data(sync_type="incremental")
            if not result.get("success"):
                logger.warning("Auto-sync %s for invoice %s failed: %s", provider, invoice.id, result.get("message"))
        except Exception as exc:
            logger.warning("Auto-sync %s invoice %s error: %s", provider, getattr(invoice, "id", None), exc)


def trigger_expense_sync(expense) -> None:
    """Push approved expenses when auto_sync is enabled."""
    if not expense or expense.status != "approved":
        return

    for provider in ("quickbooks", "xero"):
        try:
            integration, connector = _get_active_connector(provider)
            if not integration or not connector:
                continue
            config = integration.config or {}
            if not config.get("auto_sync", False):
                continue
            from app.integrations.sync_config import export_enabled, should_sync_expenses

            if not export_enabled(config, provider) or not should_sync_expenses(config, "incremental"):
                continue
            connector.sync_data(sync_type="incremental")
        except Exception as exc:
            logger.warning("Auto-sync %s expense %s error: %s", provider, getattr(expense, "id", None), exc)


def trigger_payment_sync(payment) -> None:
    """Notify accounting connectors that a payment was recorded."""
    if not payment or not getattr(payment, "invoice_id", None):
        return
    from app.models import Invoice

    invoice = Invoice.query.get(payment.invoice_id)
    if invoice:
        trigger_invoice_sync(invoice, event="payment")
