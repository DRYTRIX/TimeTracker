"""Helpers for the optional Client legal entities module.

- which legal entity of the client a new invoice is billed to by default;
- the data the invoice form needs for its "Bill to" field;
- copying the entity's details into the invoice;
- the extra "Bill to" lines (registration number, VAT) the built-in PDFs print.
"""

from app import db

MODULE_ID = "client_entities"


def module_on(user=None):
    """True when the Client legal entities module is enabled (for the given or current user)."""
    try:
        from app.models import Settings
        from app.utils.module_registry import ModuleRegistry

        return ModuleRegistry.is_enabled(MODULE_ID, Settings.get_settings(), user)
    except Exception:
        return False


def active_entities(client_id):
    from app.models import ClientEntity

    return ClientEntity.query.filter_by(client_id=client_id, status="active").order_by(ClientEntity.legal_name).all()


def _latest_choices(client_ids):
    """Latest invoice's Bill to per client: {client_id: entity id or None}."""
    from app.models import Invoice

    if not client_ids:
        return {}
    rows = (
        db.session.query(Invoice.client_id, Invoice.client_entity_id)
        .filter(Invoice.client_id.in_(client_ids))
        .order_by(Invoice.issue_date.asc(), Invoice.id.asc())
        .all()
    )
    by_client = {}
    for client_id, entity_id in rows:  # later rows win
        by_client[client_id] = entity_id
    return by_client


def default_entity_id(client_id, active_ids, by_client=None):
    """Bill to for a new invoice of this client.

    An invoice is billed to the client's legal entity, whatever the project: the choice of the
    client's latest invoice (an archived entity is skipped), else the client's only active entity,
    else None ("Client details").
    """
    if by_client is None:
        by_client = _latest_choices([client_id])
    if client_id in by_client:
        entity_id = by_client[client_id]
        if entity_id is None:
            return None
        if entity_id in active_ids:
            return entity_id
    if len(active_ids) == 1:
        return next(iter(active_ids))
    return None


def entity_view(entity):
    """What the form needs to show and fill for one entity."""
    return {
        "id": entity.id,
        "legal_name": entity.legal_name,
        "registration_number": entity.registration_number or "",
        "vat_number": entity.vat_number or "",
        "country": entity.country or "",
        "address": entity.address or "",
        "email": entity.email or "",
        "active": entity.is_active,
    }


def form_context(projects, invoice=None):
    """Data the invoice form needs for "Bill to" (empty when the module is off).

    Create: ``projects`` are the selectable projects. Edit: ``invoice`` is the draft being edited;
    its current entity is offered even if it was archived since.
    """
    from app.models import ClientEntity

    if not module_on():
        return {"client_entities_enabled": False}
    if invoice is not None:
        project_clients = {str(invoice.project_id): invoice.client_id}
    else:
        project_clients = {str(p.id): p.client_id for p in projects or []}
    client_ids = sorted({c for c in project_clients.values() if c})
    entities = (
        ClientEntity.query.filter(ClientEntity.client_id.in_(client_ids)).order_by(ClientEntity.legal_name).all()
        if client_ids
        else []
    )
    current_id = invoice.client_entity_id if invoice is not None else None
    by_client = {}
    for e in entities:
        if e.is_active or e.id == current_id:
            by_client.setdefault(str(e.client_id), []).append(entity_view(e))

    defaults = {}
    if invoice is None and by_client:
        by_client_latest = _latest_choices(client_ids)
        for project_id, client_id in project_clients.items():
            active_ids = {e["id"] for e in by_client.get(str(client_id), []) if e["active"]}
            if active_ids:
                defaults[project_id] = default_entity_id(client_id, active_ids, by_client_latest)
    from app.models import Client

    client_details = {
        str(c.id): {"name": c.name, "email": c.email or "", "address": c.address or ""}
        for c in (Client.query.filter(Client.id.in_([int(k) for k in by_client])).all() if by_client else [])
    }
    return {
        "client_entities_enabled": True,
        "client_entity_data": {
            "byClient": by_client,
            "clients": client_details,
            "projectClients": project_clients,
            "defaults": defaults,
            "current": current_id,
        },
    }


def resolve_from_form(form, client_id, current_entity_id=None):
    """(entity or None, error) from the posted client_entity_id for an invoice of this client."""
    from app.models import ClientEntity

    raw = form.get("client_entity_id") if hasattr(form, "get") else None
    if not raw:
        return None, None
    try:
        entity = ClientEntity.query.get(int(raw))
    except (TypeError, ValueError):
        entity = None
    if entity is None or entity.client_id != client_id:
        return None, "The Bill to legal entity does not belong to the invoice's client"
    if not entity.is_active and entity.id != current_entity_id:
        return None, "The Bill to legal entity is archived"
    return entity, None


def apply_to_invoice(invoice, entity):
    """Link the invoice to its Bill to entity and copy the entity's details into it."""
    invoice.client_entity_id = entity.id if entity else None
    invoice.buyer_snapshot = entity.buyer_snapshot() if entity else None


def buyer_lines(invoice):
    """[(label, value)] the built-in PDFs print under the client name: registration number, VAT."""
    from flask_babel import gettext as _

    snap = getattr(invoice, "buyer_snapshot", None) or {}
    lines = []
    if snap.get("registration_number"):
        lines.append((_("Registration number"), snap["registration_number"]))
    if snap.get("vat_number"):
        lines.append((_("VAT"), snap["vat_number"]))
    return lines
