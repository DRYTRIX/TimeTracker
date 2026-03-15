"""
API v1 - Contacts (CRM) sub-blueprint.
Routes under /api/v1/clients/<id>/contacts and /api/v1/contacts.
"""

from flask import Blueprint, jsonify, request, g
from app import db
from app.models import Client, Contact
from app.utils.api_auth import require_api_token
from app.utils.api_responses import error_response, forbidden_response
from app.routes.api_v1_common import _require_module_enabled_for_api

api_v1_contacts_bp = Blueprint("api_v1_contacts", __name__, url_prefix="/api/v1")


@api_v1_contacts_bp.route("/clients/<int:client_id>/contacts", methods=["GET"])
@require_api_token("read:contacts")
def list_contacts(client_id):
    """List contacts for a client."""
    blocked = _require_module_enabled_for_api("contacts")
    if blocked:
        return blocked
    from app.utils.scope_filter import user_can_access_client

    client = Client.query.filter_by(id=client_id).first_or_404()
    if not user_can_access_client(g.api_user, client_id):
        return jsonify({"error": "Access denied", "message": "You do not have access to this client"}), 403
    contacts = Contact.get_active_contacts(client_id)
    return jsonify({"contacts": [c.to_dict() for c in contacts]})


@api_v1_contacts_bp.route("/clients/<int:client_id>/contacts", methods=["POST"])
@require_api_token("write:contacts")
def create_contact(client_id):
    """Create a contact for a client."""
    blocked = _require_module_enabled_for_api("contacts")
    if blocked:
        return blocked
    from app.utils.scope_filter import user_can_access_client

    client = Client.query.filter_by(id=client_id).first_or_404()
    if not user_can_access_client(g.api_user, client_id):
        return forbidden_response("You do not have access to this client")
    data = request.get_json() or {}
    first_name = (data.get("first_name") or "").strip()
    last_name = (data.get("last_name") or "").strip()
    if not first_name or not last_name:
        return error_response("first_name and last_name are required", status_code=400)
    contact = Contact(
        client_id=client_id,
        first_name=first_name,
        last_name=last_name,
        created_by=g.api_user.id,
        email=(data.get("email") or "").strip() or None,
        phone=(data.get("phone") or "").strip() or None,
        mobile=(data.get("mobile") or "").strip() or None,
        title=(data.get("title") or "").strip() or None,
        department=(data.get("department") or "").strip() or None,
        role=(data.get("role") or "contact").strip(),
        is_primary=bool(data.get("is_primary", False)),
        address=(data.get("address") or "").strip() or None,
        notes=(data.get("notes") or "").strip() or None,
        tags=(data.get("tags") or "").strip() or None,
    )
    db.session.add(contact)
    if contact.is_primary:
        Contact.query.filter(
            Contact.client_id == client_id, Contact.id != contact.id, Contact.is_primary == True
        ).update({"is_primary": False})
    db.session.commit()
    return jsonify({"message": "Contact created successfully", "contact": contact.to_dict()}), 201


@api_v1_contacts_bp.route("/contacts/<int:contact_id>", methods=["GET"])
@require_api_token("read:contacts")
def get_contact(contact_id):
    """Get a contact by id."""
    blocked = _require_module_enabled_for_api("contacts")
    if blocked:
        return blocked
    contact = Contact.query.filter_by(id=contact_id).first_or_404()
    return jsonify({"contact": contact.to_dict()})


@api_v1_contacts_bp.route("/contacts/<int:contact_id>", methods=["PUT", "PATCH"])
@require_api_token("write:contacts")
def update_contact(contact_id):
    """Update a contact."""
    blocked = _require_module_enabled_for_api("contacts")
    if blocked:
        return blocked
    contact = Contact.query.filter_by(id=contact_id).first_or_404()
    data = request.get_json() or {}
    for field in (
        "first_name", "last_name", "email", "phone", "mobile", "title",
        "department", "role", "address", "notes", "tags",
    ):
        if field in data and data[field] is not None:
            setattr(
                contact, field,
                str(data[field]).strip() if isinstance(data[field], str) else data[field],
            )
    if "is_primary" in data:
        contact.is_primary = bool(data["is_primary"])
        if contact.is_primary:
            Contact.query.filter(
                Contact.client_id == contact.client_id,
                Contact.id != contact.id,
                Contact.is_primary == True,
            ).update({"is_primary": False})
    db.session.commit()
    return jsonify({"message": "Contact updated successfully", "contact": contact.to_dict()})


@api_v1_contacts_bp.route("/contacts/<int:contact_id>", methods=["DELETE"])
@require_api_token("write:contacts")
def delete_contact(contact_id):
    """Soft-delete a contact (set is_active=False)."""
    blocked = _require_module_enabled_for_api("contacts")
    if blocked:
        return blocked
    contact = Contact.query.filter_by(id=contact_id).first_or_404()
    contact.is_active = False
    db.session.commit()
    return jsonify({"message": "Contact deleted successfully"})
