"""Currency choice for invoices created and edited in the web UI.

An invoice keeps its own currency_code. The create form offers a currency list and pre-selects the
currency of the client's latest invoice, falling back to Settings.currency, so a client billed in EUR
keeps getting EUR invoices while the global default stays e.g. USD.
"""

import re

from app import db

_CODE = re.compile(r"^[A-Z]{3}$")
_COMMON = ("EUR", "USD", "GBP", "CHF")


def normalize_currency_code(value):
    """Return an ISO-4217-looking code (3 letters, upper case) or None."""
    code = (value or "").strip().upper()
    return code if _CODE.match(code) else None


def settings_currency(settings):
    return normalize_currency_code(getattr(settings, "currency", None)) or "USD"


def currency_choices(settings, extra=()):
    """Codes for the currency select: active Currency rows, codes already used on invoices,
    the global setting and any extra codes (e.g. the invoice being edited). Sorted, unique."""
    from app.models import Currency, Invoice

    codes = {settings_currency(settings)}
    codes.update(c for c in extra if normalize_currency_code(c))
    try:
        codes.update(code for (code,) in db.session.query(Currency.code).filter(Currency.is_active.is_(True)).all())
    except Exception:
        db.session.rollback()
    codes.update(code for (code,) in db.session.query(Invoice.currency_code).distinct().all() if code)
    if len(codes) < 2:
        codes.update(_COMMON)
    return sorted(c for c in codes if normalize_currency_code(c))


def default_currency_for_client(client_id, settings):
    """Currency of the client's latest invoice, else the global setting."""
    from app.models import Invoice

    if client_id:
        row = (
            db.session.query(Invoice.currency_code)
            .filter(Invoice.client_id == client_id, Invoice.currency_code.isnot(None))
            .order_by(Invoice.issue_date.desc(), Invoice.id.desc())
            .first()
        )
        if row and normalize_currency_code(row[0]):
            return row[0]
    return settings_currency(settings)


def default_currencies_by_client(settings):
    """{client_id: currency of that client's latest invoice} (latest by issue date, then id)."""
    from app.models import Invoice

    rows = (
        db.session.query(Invoice.client_id, Invoice.currency_code)
        .filter(Invoice.client_id.isnot(None), Invoice.currency_code.isnot(None))
        .order_by(Invoice.issue_date.asc(), Invoice.id.asc())
        .all()
    )
    out = {}
    for cid, code in rows:  # later rows win
        if normalize_currency_code(code):
            out[cid] = code
    return out
