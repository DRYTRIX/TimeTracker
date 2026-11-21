"""Pages of the Client legal entities module: the legal entities a client is billed through."""

from flask import Blueprint, abort, flash, redirect, render_template, request, url_for
from flask_babel import gettext as _
from flask_login import current_user, login_required

from app import db, log_event
from app.models import Client, ClientEntity
from app.utils.db import safe_commit
from app.utils.module_helpers import module_enabled

client_entities_bp = Blueprint("client_entities", __name__)


def _clean(name, limit=None):
    value = (request.form.get(name, "") or "").strip()
    if limit:
        value = value[:limit]
    return value or None


def _client_for_edit(client_id):
    """The client, if the current user may see and edit it; 403/404 otherwise."""
    from app.utils.permissions import user_can_edit_client
    from app.utils.scope_filter import user_can_access_client

    client = Client.query.get_or_404(client_id)
    if not user_can_access_client(current_user, client_id) or not user_can_edit_client(current_user, client):
        abort(403)
    return client


def _entity_or_404(client, entity_id):
    entity = ClientEntity.query.get_or_404(entity_id)
    if entity.client_id != client.id:
        abort(404)
    return entity


def _fill(entity):
    entity.legal_name = _clean("legal_name", 255) or entity.legal_name
    entity.registration_number = _clean("registration_number", 100)
    entity.vat_number = _clean("vat_number", 100)
    entity.country = (_clean("country", 2) or "").upper() or None
    entity.address = _clean("address")
    entity.email = _clean("email", 200)
    status = request.form.get("status", "active")
    entity.status = status if status in ("active", "archived") else "active"


def _render(client, entity, status=200):
    return (
        render_template("client_entities/edit.html", client=client, entity=entity),
        status,
    )


@client_entities_bp.route("/clients/<int:client_id>/legal-entities/new", methods=["GET", "POST"])
@login_required
@module_enabled("client_entities")
def new_entity(client_id):
    client = _client_for_edit(client_id)
    if request.method == "GET":
        return _render(client, None)
    entity = ClientEntity(client_id=client.id, legal_name=_clean("legal_name", 255) or "")
    _fill(entity)
    if not entity.legal_name:
        flash(_("Legal name is required"), "error")
        return _render(client, entity, 400)
    db.session.add(entity)
    if not safe_commit("client_entity_create", {"client_id": client.id}):
        flash(_("Could not save the legal entity"), "error")
        return _render(client, entity, 400)
    log_event("client_entity.created", user_id=current_user.id, client_id=client.id, client_entity_id=entity.id)
    flash(_("Legal entity added"), "success")
    return redirect(url_for("clients.view_client", client_id=client.id))


@client_entities_bp.route("/clients/<int:client_id>/legal-entities/<int:entity_id>", methods=["GET", "POST"])
@login_required
@module_enabled("client_entities")
def edit_entity(client_id, entity_id):
    client = _client_for_edit(client_id)
    entity = _entity_or_404(client, entity_id)
    if request.method == "GET":
        return _render(client, entity)
    _fill(entity)
    if not safe_commit("client_entity_update", {"client_entity_id": entity.id}):
        flash(_("Could not save the legal entity"), "error")
        return _render(client, entity, 400)
    flash(_("Legal entity saved"), "success")
    return redirect(url_for("clients.view_client", client_id=client.id))


@client_entities_bp.route("/clients/<int:client_id>/legal-entities/<int:entity_id>/archive", methods=["POST"])
@login_required
@module_enabled("client_entities")
def toggle_archive(client_id, entity_id):
    client = _client_for_edit(client_id)
    entity = _entity_or_404(client, entity_id)
    entity.status = "active" if entity.status == "archived" else "archived"
    safe_commit("client_entity_archive", {"client_entity_id": entity.id})
    flash(_("Legal entity archived") if entity.status == "archived" else _("Legal entity restored"), "success")
    return redirect(url_for("clients.view_client", client_id=client.id))


@client_entities_bp.route("/clients/<int:client_id>/legal-entities/<int:entity_id>/delete", methods=["POST"])
@login_required
@module_enabled("client_entities")
def delete_entity(client_id, entity_id):
    client = _client_for_edit(client_id)
    entity = _entity_or_404(client, entity_id)
    if entity.is_used():
        flash(_("Used on invoices, archive it instead"), "error")
        return redirect(url_for("client_entities.edit_entity", client_id=client.id, entity_id=entity.id))
    db.session.delete(entity)
    safe_commit("client_entity_delete", {"client_entity_id": entity_id})
    flash(_("Legal entity deleted"), "success")
    return redirect(url_for("clients.view_client", client_id=client.id))


@client_entities_bp.app_template_global()
def client_entities_card(client):
    """What the client page's Legal entities card shows: None when the module is off."""
    from app.utils.client_entities import module_on
    from app.utils.permissions import user_can_edit_client

    if client is None or not module_on():
        return None
    entities = (
        ClientEntity.query.filter_by(client_id=client.id).order_by(ClientEntity.status, ClientEntity.legal_name).all()
    )
    return {"entities": entities, "can_edit": user_can_edit_client(current_user, client)}
