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


def number_owner(number, exclude_invoice_id=None):
    """The invoice that already has this number, or None."""
    from app.models import Invoice

    if not number:
        return None
    q = Invoice.query.filter(Invoice.invoice_number == number)
    if exclude_invoice_id:
        q = q.filter(Invoice.id != exclude_invoice_id)
    return q.order_by(Invoice.id.asc()).first()


def _number_taken(number, exclude_invoice_id=None):
    return number_owner(number, exclude_invoice_id) is not None


def unique_number(number, exclude_invoice_id=None):
    """number, or number-2, number-3, … whichever is free."""
    if not _number_taken(number, exclude_invoice_id):
        return number
    n = 2
    while _number_taken(f"{number}-{n}", exclude_invoice_id):
        n += 1
    return f"{number}-{n}"


class NumberTaken(Exception):
    """The invoice number is already used by another invoice.

    ``owner`` is that invoice, ``next_free`` the number the form offers instead.
    """

    def __init__(self, number, owner, next_free):
        super().__init__(number)
        self.number = number
        self.owner = owner
        self.next_free = next_free


def _uses_seq(entity):
    return "{SEQ}" in (entity.number_format or "")


def next_free_number(entity, issue_date=None, number=None):
    """The number to offer when ``number`` (default: the entity's next number) is taken.

    With {SEQ} in the format: the first free number after the entity's counter. Otherwise
    ``number-2``, ``number-3``, … whichever is free.
    """
    if _uses_seq(entity):
        seq = (entity.number_counter or 0) + 1
        while _number_taken(format_invoice_number(entity, issue_date, seq=seq)):
            seq += 1
        return format_invoice_number(entity, issue_date, seq=seq)
    base = number or format_invoice_number(entity, issue_date)
    return unique_number(base) if base else None


def _seq_of(entity, number, issue_date=None):
    """The {SEQ} value if ``number`` is the entity's format filled for this issue date, else None."""
    if not number or not _uses_seq(entity):
        return None
    marker = "\x00"
    pattern = re.escape(format_invoice_number(entity, issue_date, seq=marker)).replace(re.escape(marker), r"(\d+)")
    match = re.fullmatch(pattern, number)
    return int(match.group(1)) if match else None


def check_number(entity, number, issue_date=None, exclude_invoice_id=None):
    """Raise NumberTaken if ``number`` belongs to another invoice."""
    owner = number_owner(number, exclude_invoice_id)
    if owner is not None:
        offer = next_free_number(entity, issue_date, number) if entity else unique_number(number, exclude_invoice_id)
        raise NumberTaken(number, owner, offer)


def claim_number(entity, number, issue_date=None):
    """Move the entity's {SEQ} counter up to ``number`` if it is the format's number past the counter.

    So a number typed by hand, or picked with "Use next free", is not offered again. The caller commits.
    """
    seq = _seq_of(entity, number, issue_date)
    if seq is not None and seq > (entity.number_counter or 0):
        entity.number_counter = seq


def preview_invoice_number(entity, issue_date=None):
    """The entity's next number as the form shows it (it may be taken: see ``number_preview``)."""
    return format_invoice_number(entity, issue_date)


def allocate_invoice_number(entity, issue_date=None):
    """Next number for an invoice from ``entity``, or None if the entity has no format.

    Raises NumberTaken when that number already belongs to another invoice. Bumps the entity's
    counter when the format uses {SEQ}, so it moves only together with the invoice. The caller commits.
    """
    fmt = (entity.number_format or "").strip()
    if not fmt:
        return None
    if _uses_seq(entity):
        seq = (entity.number_counter or 0) + 1
        number = format_invoice_number(entity, issue_date, seq=seq)
    else:
        seq = None
        number = format_invoice_number(entity, issue_date)
    check_number(entity, number, issue_date)
    if seq is not None:
        entity.number_counter = seq
    return number


def invoice_ref(invoice):
    """What the form shows about an invoice (or a row with its number, client name, issue date)."""
    from flask import current_app

    fmt = current_app.jinja_env.filters.get("format_date")
    issued = invoice.issue_date
    return {
        "number": invoice.invoice_number,
        "client": invoice.client_name or "",
        "date": (fmt(issued) if fmt else issued.isoformat()) if issued else "",
    }


def number_preview(entity, issue_date=None):
    """The entity's next number for the form, with the invoice holding it and the next free one."""
    number = preview_invoice_number(entity, issue_date)
    owner = number_owner(number) if number else None
    return {
        "number": number or "",
        "taken": invoice_ref(owner) if owner else None,
        "next_free": next_free_number(entity, issue_date, number) if owner else "",
    }


def _ref_columns(Invoice):
    return (Invoice.invoice_number, Invoice.client_name, Invoice.issue_date)


def latest_invoice_by_entity():
    """{billing_entity_id: number, client and issue date of its latest invoice}."""
    from app.models import Invoice

    rows = (
        db.session.query(Invoice.billing_entity_id, *_ref_columns(Invoice))
        .filter(Invoice.billing_entity_id.isnot(None))
        .order_by(Invoice.issue_date.asc(), Invoice.id.asc())
        .all()
    )
    out = {}
    for row in rows:  # later rows win
        out[row.billing_entity_id] = row
    return out


def latest_invoice_by_client(client_ids):
    """{client_id: number, client and issue date of that client's latest invoice}."""
    from app.models import Invoice

    if not client_ids:
        return {}
    rows = (
        db.session.query(Invoice.client_id, *_ref_columns(Invoice))
        .filter(Invoice.client_id.in_(client_ids))
        .order_by(Invoice.issue_date.asc(), Invoice.id.asc())
        .all()
    )
    out = {}
    for row in rows:  # later rows win
        out[row.client_id] = row
    return out


def entity_defaults(entity):
    """Form defaults for a new invoice from this entity (Notes have none: they differ on every invoice)."""
    return {
        "vat_category": entity.default_vat_category or "",
        "tax_rate": str(entity.default_tax_rate) if entity.default_tax_rate is not None else "",
        "vat_exemption_code": entity.default_vat_exemption_code or "",
        "vat_exemption_reason": entity.default_vat_exemption_reason or "",
        "terms": entity.default_terms or "",
    }


def form_context(projects, settings):
    """Data the invoice create form needs for From / Pay to (empty when the module is off)."""
    if not module_on():
        return {"billing_enabled": False}
    entities = active_entities()
    if not entities:
        return {"billing_enabled": False}
    by_client = default_entity_ids_by_client()
    latest_by_entity = latest_invoice_by_entity()
    data = {}
    for e in entities:
        previous = latest_by_entity.get(e.id)
        data[e.id] = {
            "name": e.short_name,
            **number_preview(e),
            "previous": invoice_ref(previous) if previous else None,
            "defaults": entity_defaults(e),
            "accounts": [
                {"id": a.id, "currency": a.currency, "label": a.label, "text": a.printed_text}
                for a in e.active_payment_accounts()
            ],
            "seller": e.seller_snapshot(),
        }
    project_clients = {str(p.id): p.client_id for p in (projects or [])}
    latest_by_client = latest_invoice_by_client(sorted({c for c in project_clients.values() if c}))
    return {
        "billing_enabled": True,
        "billing_entities": entities,
        "billing_entity_data": data,
        "billing_entity_by_client": {str(k): v for k, v in by_client.items()},
        "billing_project_clients": project_clients,
        "billing_last_by_client": {str(k): invoice_ref(v) for k, v in latest_by_client.items()},
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
