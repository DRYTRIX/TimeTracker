"""Defaults a new invoice takes from the client's latest invoice: payment terms and the due date.

Every client has its own payment period and terms, and they repeat from invoice to invoice. So a
new invoice copies them from that client's latest invoice:

- due date: the issue date plus as many days as the latest invoice gave (30 for a new client);
- terms: the latest invoice's terms, else the seller entity's default terms, else Settings.

Notes have no default: they differ on every invoice.
"""

from datetime import date, timedelta

from app import db

DEFAULT_DUE_DAYS = 30


def _latest_by_client(client_ids):
    """{client_id: (terms, issue_date, due_date, client_name) of that client's latest invoice}."""
    from app.models import Invoice

    if not client_ids:
        return {}
    rows = (
        db.session.query(Invoice.client_id, Invoice.terms, Invoice.issue_date, Invoice.due_date, Invoice.client_name)
        .filter(Invoice.client_id.in_(client_ids))
        .order_by(Invoice.issue_date.asc(), Invoice.id.asc())
        .all()
    )
    out = {}
    for client_id, terms, issued, due, name in rows:  # later rows win
        out[client_id] = (terms, issued, due, name)
    return out


def _days(issued, due):
    if not issued or not due or due < issued:
        return None
    return (due - issued).days


def client_defaults(client_ids):
    """{client_id: {"terms", "days", "client"}} for clients that have invoices.

    ``terms`` is "" when the latest invoice has none; ``days`` is None when its dates give no period.
    """
    from app.models import Client

    latest = _latest_by_client(client_ids)
    names = {c.id: c.name for c in Client.query.filter(Client.id.in_(list(latest))).all()} if latest else {}
    out = {}
    for client_id, (terms, issued, due, invoice_client_name) in latest.items():
        out[client_id] = {
            "terms": (terms or "").strip(),
            "days": _days(issued, due),
            "client": names.get(client_id) or invoice_client_name or "",
        }
    return out


def due_days_for(client_id):
    """Days from issue to due date for a new invoice of this client."""
    days = client_defaults([client_id]).get(client_id, {}).get("days") if client_id else None
    return DEFAULT_DUE_DAYS if days is None else days


def due_date_for(client_id, issue_date=None):
    """Due date for a new invoice of this client issued on ``issue_date`` (default: today)."""
    return (issue_date or date.today()) + timedelta(days=due_days_for(client_id))


def terms_for(client_id, entity=None, settings=None):
    """Terms for a new invoice: the client's latest invoice, else the seller entity, else Settings."""
    terms = client_defaults([client_id]).get(client_id, {}).get("terms") if client_id else ""
    if terms:
        return terms
    if entity is not None and (entity.default_terms or "").strip():
        return entity.default_terms.strip()
    if settings is not None and (settings.invoice_terms or "").strip():
        return settings.invoice_terms.strip()
    return None
