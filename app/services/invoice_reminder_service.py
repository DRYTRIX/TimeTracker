"""Invoice reminder and late-fee service (Phase 4).

Resolves the reminder policy for each unpaid invoice, checks which policy
levels are due today, fires email reminders, logs sends to
InvoiceReminderSchedule, and optionally applies late fees.
"""

from __future__ import annotations

import logging
from datetime import date, datetime
from decimal import Decimal, ROUND_HALF_UP
from typing import Optional

logger = logging.getLogger(__name__)

# Cap annual interest at 100 % to avoid runaway compound rounding
_MAX_ANNUAL_PERCENT = Decimal("100")


def resolve_policy(invoice):
    """Return the ReminderPolicy for *invoice* (invoice > client > system default).

    Returns None when no policy is configured anywhere.
    """
    from app.models.reminder_policy import ReminderPolicy

    # 1. Per-invoice override
    if getattr(invoice, "reminder_policy_id", None):
        policy = ReminderPolicy.query.get(invoice.reminder_policy_id)
        if policy and policy.active:
            return policy

    # 2. Client-level policy
    client = getattr(invoice, "client", None)
    if client is None and getattr(invoice, "client_id", None):
        from app.models import Client

        client = Client.query.get(invoice.client_id)

    if client and getattr(client, "reminder_policy_id", None):
        policy = ReminderPolicy.query.get(client.reminder_policy_id)
        if policy and policy.active:
            return policy

    # 3. System default
    return ReminderPolicy.get_default()


def process_due_reminders(today: Optional[date] = None) -> int:
    """Find and send all reminder levels that are due today.

    For each unpaid invoice (status in sent/issued/overdue) whose policy has
    a level where ``(today - due_date).days >= days_offset`` and no
    InvoiceReminderSchedule row for that (invoice_id, days_offset) has been
    sent yet, we:

    1. Send an email to the client.
    2. Create / update an InvoiceReminderSchedule row (last_sent_at = now).
    3. Log an InvoiceEmail record.
    4. Optionally apply late fee.

    Returns the total number of reminders sent.
    """
    from app import db
    from app.models import Invoice, InvoiceEmail
    from app.models.payments import InvoiceReminderSchedule

    if today is None:
        try:
            from app.utils.timezone import now_in_app_timezone

            today = now_in_app_timezone().date()
        except Exception:
            today = date.today()

    invoices = Invoice.query.filter(
        Invoice.status.in_(["sent", "issued", "overdue"]),
        Invoice.payment_status != "fully_paid",
    ).all()

    sent_total = 0
    for invoice in invoices:
        try:
            sent_total += _process_invoice(invoice, today, db, InvoiceReminderSchedule, InvoiceEmail)
        except Exception as exc:
            logger.error("Reminder processing failed for invoice %s: %s", invoice.id, exc, exc_info=True)
            try:
                db.session.rollback()
            except Exception:
                pass

    return sent_total


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _process_invoice(invoice, today, db, InvoiceReminderSchedule, InvoiceEmail) -> int:
    """Process reminder levels for a single invoice. Returns # sent."""
    policy = resolve_policy(invoice)
    if policy is None:
        return 0

    levels = [lv for lv in policy.levels if lv.active]
    if not levels:
        return 0

    due_date = invoice.due_date
    if due_date is None:
        return 0

    days_since_due = (today - due_date).days  # negative = before due

    sent = 0
    for level in levels:
        # Level fires when days_since_due >= level.days_offset
        if days_since_due < level.days_offset:
            continue

        # Check whether this level was already sent for this invoice
        existing = InvoiceReminderSchedule.query.filter_by(
            invoice_id=invoice.id,
            days_offset=level.days_offset,
        ).first()

        if existing and existing.last_sent_at is not None:
            continue  # already sent – idempotent

        # Send email
        success = _send_reminder_email(invoice, level)

        # Upsert InvoiceReminderSchedule row
        if existing is None:
            existing = InvoiceReminderSchedule(
                invoice_id=invoice.id,
                days_offset=level.days_offset,
                template_name=level.template_name,
                active=True,
            )
            db.session.add(existing)

        existing.last_sent_at = datetime.utcnow()
        existing.template_name = level.template_name

        # Log InvoiceEmail
        if success:
            recipient = _get_recipient(invoice)
            if recipient:
                ie = InvoiceEmail(
                    invoice_id=invoice.id,
                    recipient_email=recipient,
                    subject=_reminder_subject(invoice, level),
                    sent_by=invoice.created_by,
                    status="sent",
                )
                db.session.add(ie)

        # Apply late fee (once per level, idempotent via last_sent_at check above)
        _apply_late_fee(invoice, level, days_since_due)

        try:
            db.session.commit()
        except Exception as exc:
            logger.error("DB commit failed for invoice %s level %s: %s", invoice.id, level.id, exc)
            db.session.rollback()
            continue

        sent += 1
        logger.info(
            "Sent reminder for invoice %s (offset=%s, policy=%s)",
            invoice.invoice_number,
            level.days_offset,
            policy.name,
        )

    return sent


def _get_recipient(invoice) -> Optional[str]:
    """Return the best email address for the invoice client."""
    if invoice.client_email:
        return invoice.client_email
    client = getattr(invoice, "client", None)
    if client and getattr(client, "email", None):
        return client.email
    return None


def _reminder_subject(invoice, level) -> str:
    days = abs(level.days_offset)
    if level.days_offset >= 0:
        return f"Payment reminder – invoice {invoice.invoice_number} ({days} day{'s' if days != 1 else ''} overdue)"
    return f"Upcoming invoice due – {invoice.invoice_number} (due in {days} day{'s' if days != 1 else ''})"


def _send_reminder_email(invoice, level) -> bool:
    """Send the reminder email. Returns True on success, False on failure."""
    try:
        from flask import current_app

        recipient = _get_recipient(invoice)
        if not recipient:
            logger.warning("No recipient email for invoice %s, skipping reminder", invoice.invoice_number)
            return False

        subject = _reminder_subject(invoice, level)
        days_offset = level.days_offset

        # Try to use send_invoice_email (attaches PDF) first; fall back to plain email
        try:
            from app.utils.email import send_invoice_email

            success, _, message = send_invoice_email(invoice, recipient)
            if not success:
                raise RuntimeError(message)
            return True
        except Exception as exc:
            logger.debug("send_invoice_email failed (%s), falling back to plain reminder", exc)

        # Fallback: plain-text reminder
        try:
            from app.utils.email import send_template_email
            from app.utils.urls import safe_external_url_for

            invoice_url = safe_external_url_for("invoices.view_invoice", invoice_id=invoice.id)
            send_template_email(
                to=recipient,
                subject=subject,
                template="email/invoice_reminder.html",
                invoice=invoice,
                days_offset=days_offset,
                invoice_url=invoice_url,
            )
            return True
        except Exception as exc:
            logger.warning("Fallback reminder email failed for invoice %s: %s", invoice.invoice_number, exc)
            return False

    except Exception as exc:
        logger.error("Unexpected error sending reminder for invoice %s: %s", invoice.invoice_number, exc)
        return False


def _apply_late_fee(invoice, level, days_since_due: int) -> None:
    """Add a late fee to invoice.late_fee_amount based on the level config."""
    if not level.late_fee_type or level.late_fee_value is None:
        return

    fee_value = Decimal(str(level.late_fee_value))
    if fee_value <= 0:
        return

    current_fee = Decimal(str(invoice.late_fee_amount or 0))

    if level.late_fee_type == "fixed":
        invoice.late_fee_amount = current_fee + fee_value

    elif level.late_fee_type == "percent_annual":
        # Daily interest = annual_rate / 365
        # Applied once per level trigger (days_since_due already >= level.days_offset)
        # Outstanding base = total_amount (pre-late-fee) to avoid compounding
        annual_rate = min(fee_value, _MAX_ANNUAL_PERCENT) / Decimal("100")
        daily_rate = annual_rate / Decimal("365")
        base = Decimal(str(invoice.total_amount or 0))
        # Cap application period to actual days overdue (at most days_since_due)
        days = max(days_since_due, 1)
        interest = (base * daily_rate * days).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        invoice.late_fee_amount = current_fee + interest
