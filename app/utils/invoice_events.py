"""Helpers for emitting invoice-related webhook/domain events."""

from __future__ import annotations

from typing import Any

from app.utils.event_bus import emit_event


def emit_invoice_event(event_name: str, invoice: Any, **extra: Any) -> None:
    """Emit a webhook/domain event for an invoice.

    Builds a standard payload from the invoice model and merges any extra fields.
    Failures are swallowed so callers never break business flows on emit errors.
    """
    try:
        payload = {
            "invoice_id": getattr(invoice, "id", None),
            "invoice_number": getattr(invoice, "invoice_number", None),
            "status": getattr(invoice, "status", None),
            "payment_status": getattr(invoice, "payment_status", None),
            "client_id": getattr(invoice, "client_id", None),
            "project_id": getattr(invoice, "project_id", None),
        }
        payload.update(extra)
        # Drop Nones for cleaner payloads
        payload = {k: v for k, v in payload.items() if v is not None}
        emit_event(event_name, payload)
    except Exception:
        try:
            from flask import current_app

            current_app.logger.debug("emit_invoice_event failed for %s", event_name, exc_info=True)
        except Exception:
            pass


def emit_credit_note_event(event_name: str, credit_note: Any, **extra: Any) -> None:
    """Emit a webhook/domain event for a credit note."""
    try:
        payload = {
            "credit_note_id": getattr(credit_note, "id", None),
            "credit_number": getattr(credit_note, "credit_number", None),
            "invoice_id": getattr(credit_note, "invoice_id", None),
            "amount": float(credit_note.amount) if getattr(credit_note, "amount", None) is not None else None,
            "status": getattr(credit_note, "status", None),
        }
        payload.update(extra)
        payload = {k: v for k, v in payload.items() if v is not None}
        emit_event(event_name, payload)
    except Exception:
        try:
            from flask import current_app

            current_app.logger.debug("emit_credit_note_event failed for %s", event_name, exc_info=True)
        except Exception:
            pass


def emit_payment_event(event_name: str, payment: Any, **extra: Any) -> None:
    """Emit a webhook/domain event for a payment."""
    try:
        payload = {
            "payment_id": getattr(payment, "id", None),
            "invoice_id": getattr(payment, "invoice_id", None),
            "amount": float(payment.amount) if getattr(payment, "amount", None) is not None else None,
            "status": getattr(payment, "status", None),
        }
        payload.update(extra)
        payload = {k: v for k, v in payload.items() if v is not None}
        emit_event(event_name, payload)
    except Exception:
        try:
            from flask import current_app

            current_app.logger.debug("emit_payment_event failed for %s", event_name, exc_info=True)
        except Exception:
            pass
