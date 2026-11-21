"""Helpers for the optional Legal entities module (billing entities and payment accounts).

- which entity and payment account a new invoice defaults to;
- the invoice number from an entity's number format;
- copying the seller details and payment text into an invoice;
- a Settings view for the PDF generators that prints the invoice's own seller.
"""

import html
import re
from datetime import date

from app import db

MODULE_ID = "billing_entities"
_TOKEN = re.compile(r"\{(YYYY|YY|MM|DD|SEQ)\}")


def module_on(user=None):
    """True when the Legal entities module is enabled (for the given or current user)."""
    try:
        from app.models import Settings
        from app.utils.module_registry import ModuleRegistry

        return ModuleRegistry.is_enabled(MODULE_ID, Settings.get_settings(), user)
    except Exception:
        return False


def active_entities():
    from app.models import BillingEntity

    return BillingEntity.query.filter_by(status="active").order_by(BillingEntity.short_name).all()


def default_entity_ids_by_client():
    """{client_id: billing_entity_id of that client's latest invoice that has one}."""
    from app.models import Invoice

    rows = (
        db.session.query(Invoice.client_id, Invoice.billing_entity_id)
        .filter(Invoice.client_id.isnot(None), Invoice.billing_entity_id.isnot(None))
        .order_by(Invoice.issue_date.asc(), Invoice.id.asc())
        .all()
    )
    out = {}
    for client_id, entity_id in rows:  # later rows win
        out[client_id] = entity_id
    return out


def default_entity_for_client(client_id):
    from app.models import BillingEntity

    entity_id = default_entity_ids_by_client().get(client_id)
    entity = BillingEntity.query.get(entity_id) if entity_id else None
    if entity and entity.is_active:
        return entity
    return None


def billing_period(issue_date=None):
    """The month an invoice is for: the month before the issue date (invoices go out after month end)."""
    d = issue_date or date.today()
    if d.month == 1:
        return d.year - 1, 12
    return d.year, d.month - 1


def format_invoice_number(entity, issue_date=None, seq=None):
    """Fill an entity's number format. {YYYY}/{YY}/{MM} are the billing period, {DD} the issue day."""
    fmt = (entity.number_format or "").strip()
    if not fmt:
        return None
    d = issue_date or date.today()
    year, month = billing_period(d)
    values = {
        "YYYY": f"{year:04d}",
        "YY": f"{year % 100:02d}",
        "MM": f"{month:02d}",
        "DD": f"{d.day:02d}",
        "SEQ": str(seq if seq is not None else (entity.number_counter or 0) + 1),
    }
    return _TOKEN.sub(lambda m: values[m.group(1)], fmt)


def _number_taken(number, exclude_invoice_id=None):
    from app.models import Invoice

    q = db.session.query(Invoice.id).filter(Invoice.invoice_number == number)
    if exclude_invoice_id:
        q = q.filter(Invoice.id != exclude_invoice_id)
    return q.first() is not None


def unique_number(number, exclude_invoice_id=None):
    """number, or number-2, number-3, … whichever is free."""
    if not _number_taken(number, exclude_invoice_id):
        return number
    n = 2
    while _number_taken(f"{number}-{n}", exclude_invoice_id):
        n += 1
    return f"{number}-{n}"


def preview_invoice_number(entity, issue_date=None):
    number = format_invoice_number(entity, issue_date)
    return unique_number(number) if number else None


def allocate_invoice_number(entity, issue_date=None):
    """Next number for an invoice from ``entity``, or None if the entity has no format.

    Bumps the entity's counter when the format uses {SEQ}. The caller commits.
    """
    fmt = (entity.number_format or "").strip()
    if not fmt:
        return None
    if "{SEQ}" in fmt:
        entity.number_counter = (entity.number_counter or 0) + 1
        number = format_invoice_number(entity, issue_date, seq=entity.number_counter)
    else:
        number = format_invoice_number(entity, issue_date)
    return unique_number(number)


def entity_defaults(entity):
    """Form defaults for a new invoice from this entity."""
    return {
        "vat_category": entity.default_vat_category or "",
        "tax_rate": str(entity.default_tax_rate) if entity.default_tax_rate is not None else "",
        "vat_exemption_code": entity.default_vat_exemption_code or "",
        "vat_exemption_reason": entity.default_vat_exemption_reason or "",
        "terms": entity.default_terms or "",
        "notes": entity.default_notes or "",
    }


def form_context(projects, settings):
    """Data the invoice create form needs for From / Pay to (empty when the module is off)."""
    if not module_on():
        return {"billing_enabled": False}
    entities = active_entities()
    if not entities:
        return {"billing_enabled": False}
    by_client = default_entity_ids_by_client()
    data = {}
    for e in entities:
        data[e.id] = {
            "name": e.short_name,
            "number": preview_invoice_number(e) or "",
            "defaults": entity_defaults(e),
            "accounts": [
                {"id": a.id, "currency": a.currency, "label": a.label, "text": a.printed_text}
                for a in e.active_payment_accounts()
            ],
            "seller": e.seller_snapshot(),
        }
    return {
        "billing_enabled": True,
        "billing_entities": entities,
        "billing_entity_data": data,
        "billing_entity_by_client": {str(k): v for k, v in by_client.items()},
        "billing_project_clients": {str(p.id): p.client_id for p in (projects or [])},
    }


def resolve_from_form(form, currency_code):
    """(entity, account, error) from the posted billing_entity_id / payment_account_id."""
    from app.models import BillingEntity, PaymentAccount

    entity_id = form.get("billing_entity_id", type=int) if hasattr(form, "get") else None
    if not entity_id:
        return None, None, None
    entity = BillingEntity.query.get(entity_id)
    if not entity or not entity.is_active:
        return None, None, "Selected legal entity not found"
    account_id = form.get("payment_account_id", type=int)
    account = PaymentAccount.query.get(account_id) if account_id else None
    if account and (account.billing_entity_id != entity.id or not account.is_active):
        return None, None, "Selected payment account does not belong to the legal entity"
    if account and currency_code and account.currency != currency_code:
        return None, None, "Payment account currency does not match the invoice currency"
    return entity, account, None


def apply_to_invoice(invoice, entity, account):
    """Link the invoice to its seller and payment account and copy their texts into it."""
    invoice.billing_entity_id = entity.id if entity else None
    invoice.payment_account_id = account.id if account else None
    invoice.seller_snapshot = entity.seller_snapshot() if entity else None
    invoice.payment_details_text = account.printed_text if account else None


class SellerSettings:
    """Settings as seen by the PDF generators for one invoice: the seller comes from the invoice.

    Everything not about the seller (currency, templates, PEPPOL, …) is read from the real Settings.
    """

    def __init__(self, settings, snapshot, payment_text, iban):
        self._settings = settings
        self._snapshot = snapshot or {}
        self._payment_text = payment_text or ""
        self.payment_text = self._payment_text  # as typed, for HTML templates (company_bank_info is escaped)
        self._iban = iban or ""

    def __getattr__(self, name):
        snap = self._snapshot
        if name == "company_name":
            return snap.get("legal_name") or ""
        if name == "company_address":
            return snap.get("address") or ""
        if name == "company_email":
            return snap.get("email") or ""
        if name == "company_phone":
            return snap.get("phone") or ""
        if name == "company_website":
            return snap.get("website") or ""
        if name == "company_tax_id":
            return snap.get("vat_number") or snap.get("registration_number") or ""
        if name == "company_country":
            return snap.get("country") or ""
        if name in ("company_street", "company_postcode", "company_city", "company_bic"):
            return ""
        if name == "company_iban":
            return self._iban
        if name == "company_bank_info":
            # Printed as HTML / ReportLab markup by the generators: escape, keep line breaks.
            return html.escape(self._payment_text).replace("\n", "<br/>")
        if name == "company_logo_filename":
            return self._snapshot.get("logo_filename") or ""
        return getattr(self._settings, name)

    def _logo_path(self):
        from app.models import BillingEntity

        return BillingEntity.logo_path(self._snapshot.get("logo_filename"))

    def has_logo(self):
        return self._logo_path() is not None

    def get_logo_path(self):
        return self._logo_path()

    def get_logo_url(self):
        name = self._snapshot.get("logo_filename")
        return f"/uploads/logos/{name}" if name and self._logo_path() else None


def seller_settings_for(invoice, settings):
    """Settings to render ``invoice`` with: its own seller when it has one, else ``settings``."""
    try:
        if invoice is None or not getattr(invoice, "billing_entity_id", None) or not invoice.seller_snapshot:
            return settings
        iban = invoice.payment_account.iban if getattr(invoice, "payment_account", None) else ""
        return SellerSettings(settings, invoice.seller_snapshot, invoice.payment_details_text, iban)
    except Exception:
        return settings
