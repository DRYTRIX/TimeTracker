"""REST API v1 - Client Portal endpoints.

Mounted at /api/v1/portal. Authenticated via API tokens that have
portal scopes and an optional client_id binding.
"""

from flask import Blueprint, g, jsonify, request

from app.models import (
    Client,
    ClientAttachment,
    Invoice,
    Project,
    ProjectAttachment,
    TimeEntry,
)
from app.models.client_time_approval import ClientTimeApproval
from app.utils.api_auth import require_api_token
from app.utils.api_responses import error_response, forbidden_response, validation_error_response

api_v1_client_portal_bp = Blueprint("api_v1_client_portal", __name__, url_prefix="/api/v1/portal")


def _portal_client():
    """Resolve the client for the current portal API token."""
    token = getattr(g, "api_token", None)
    if token and getattr(token, "client_id", None):
        client = Client.query.get(token.client_id)
        if client and client.is_active and client.has_portal_access:
            return client
        return None

    # Fallback: allow admin tokens with explicit client_id query/body
    client_id = request.args.get("client_id", type=int) or (request.get_json(silent=True) or {}).get("client_id")
    if client_id and token and token.has_scope("admin:all"):
        return Client.query.get(client_id)
    return None


def _require_portal_client():
    client = _portal_client()
    if not client:
        return None, forbidden_response("Portal token must be bound to a client, or pass client_id with admin scope")
    return client, None


@api_v1_client_portal_bp.route("/projects", methods=["GET"])
@require_api_token(("portal:read", "portal:all", "read:projects", "admin:all"))
def portal_list_projects():
    client, err = _require_portal_client()
    if err:
        return err
    projects = Project.query.filter_by(client_id=client.id).order_by(Project.name).all()
    return jsonify(
        {
            "projects": [
                {
                    "id": p.id,
                    "name": p.name,
                    "status": p.status,
                    "description": getattr(p, "description", None),
                }
                for p in projects
            ]
        }
    )


@api_v1_client_portal_bp.route("/invoices", methods=["GET"])
@require_api_token(("portal:read", "portal:all", "read:invoices", "admin:all"))
def portal_list_invoices():
    client, err = _require_portal_client()
    if err:
        return err
    invoices = (
        Invoice.query.filter(
            (Invoice.client_id == client.id) | (Invoice.client_name == client.name)
        )
        .order_by(Invoice.created_at.desc())
        .limit(100)
        .all()
    )
    return jsonify(
        {
            "invoices": [
                {
                    "id": inv.id,
                    "invoice_number": inv.invoice_number,
                    "status": inv.status,
                    "total_amount": float(inv.total_amount or 0),
                    "currency_code": getattr(inv, "currency_code", None) or "EUR",
                    "due_date": inv.due_date.isoformat() if inv.due_date else None,
                    "issue_date": inv.issue_date.isoformat() if getattr(inv, "issue_date", None) else None,
                }
                for inv in invoices
            ]
        }
    )


@api_v1_client_portal_bp.route("/invoices/<int:invoice_id>", methods=["GET"])
@require_api_token(("portal:read", "portal:all", "read:invoices", "admin:all"))
def portal_get_invoice(invoice_id):
    client, err = _require_portal_client()
    if err:
        return err
    inv = Invoice.query.get_or_404(invoice_id)
    if inv.client_id != client.id and inv.client_name != client.name:
        return forbidden_response("Invoice does not belong to this client")
    items = []
    for item in getattr(inv, "items", []) or []:
        items.append(
            {
                "description": item.description,
                "quantity": float(item.quantity or 0),
                "unit_price": float(item.unit_price or 0),
            }
        )
    return jsonify(
        {
            "invoice": {
                "id": inv.id,
                "invoice_number": inv.invoice_number,
                "status": inv.status,
                "client_name": inv.client_name,
                "total_amount": float(inv.total_amount or 0),
                "tax_rate": float(inv.tax_rate or 0),
                "currency_code": getattr(inv, "currency_code", None) or "EUR",
                "due_date": inv.due_date.isoformat() if inv.due_date else None,
                "notes": inv.notes,
                "terms": inv.terms,
                "items": items,
            }
        }
    )


@api_v1_client_portal_bp.route("/time-entries", methods=["GET"])
@require_api_token(("portal:read", "portal:all", "read:time_entries", "admin:all"))
def portal_list_time_entries():
    client, err = _require_portal_client()
    if err:
        return err
    project_ids = [p.id for p in Project.query.filter_by(client_id=client.id).all()]
    if not project_ids:
        return jsonify({"time_entries": []})
    q = TimeEntry.query.filter(TimeEntry.project_id.in_(project_ids))
    billable = request.args.get("billable")
    if billable is not None:
        q = q.filter(TimeEntry.billable == (billable.lower() in ("1", "true", "yes")))
    entries = q.order_by(TimeEntry.start_time.desc()).limit(200).all()
    return jsonify(
        {
            "time_entries": [
                {
                    "id": e.id,
                    "project_id": e.project_id,
                    "duration_hours": float(e.duration_hours or 0) if hasattr(e, "duration_hours") else None,
                    "notes": getattr(e, "notes", None) or getattr(e, "description", None),
                    "billable": getattr(e, "billable", None),
                    "start_time": e.start_time.isoformat() if e.start_time else None,
                    "end_time": e.end_time.isoformat() if e.end_time else None,
                }
                for e in entries
            ]
        }
    )


@api_v1_client_portal_bp.route("/messages", methods=["GET"])
@require_api_token(("portal:read", "portal:all", "admin:all"))
def portal_list_messages():
    client, err = _require_portal_client()
    if err:
        return err
    from app.services.client_message_service import ClientMessageService

    after_id = request.args.get("after_id", type=int)
    messages = ClientMessageService().list_messages(client.id, after_id=after_id)
    return jsonify({"messages": [m.to_dict() for m in messages]})


@api_v1_client_portal_bp.route("/messages", methods=["POST"])
@require_api_token(("portal:write", "portal:all", "admin:all"))
def portal_post_message():
    client, err = _require_portal_client()
    if err:
        return err
    from app.services.client_message_service import ClientMessageService

    data = request.get_json() or {}
    body = data.get("body")
    if not body:
        return validation_error_response(errors={"body": ["required"]}, message="body is required")
    msg = ClientMessageService().send(
        client.id,
        sender_type="client",
        body=body,
        sender_id=client.id,
        sender_name=client.name,
        attachments=data.get("attachments"),
    )
    if not msg:
        return error_response("Could not send message", 500)
    return jsonify({"message": msg.to_dict()}), 201


@api_v1_client_portal_bp.route("/approvals/<int:approval_id>/approve", methods=["POST"])
@require_api_token(("portal:write", "portal:all", "admin:all"))
def portal_approve(approval_id):
    client, err = _require_portal_client()
    if err:
        return err
    approval = ClientTimeApproval.query.get_or_404(approval_id)
    if approval.client_id != client.id:
        return forbidden_response("Approval does not belong to this client")
    from app.models import Contact
    from app.services.client_approval_service import ClientApprovalService

    contacts = Contact.get_active_contacts(client.id)
    contact = Contact.get_primary_contact(client.id) or (contacts[0] if contacts else None)
    if not contact:
        return error_response("No contact available to approve", 400)
    data = request.get_json(silent=True) or {}
    result = ClientApprovalService().approve(approval_id, contact.id, comment=data.get("comment"))
    if not result.get("success"):
        return error_response(result.get("message", "Approve failed"), 400)
    return jsonify({"success": True, "approval_id": approval_id, "status": "approved", "result": result})


@api_v1_client_portal_bp.route("/approvals/<int:approval_id>/reject", methods=["POST"])
@require_api_token(("portal:write", "portal:all", "admin:all"))
def portal_reject(approval_id):
    client, err = _require_portal_client()
    if err:
        return err
    approval = ClientTimeApproval.query.get_or_404(approval_id)
    if approval.client_id != client.id:
        return forbidden_response("Approval does not belong to this client")
    from app.models import Contact
    from app.services.client_approval_service import ClientApprovalService

    contacts = Contact.get_active_contacts(client.id)
    contact = Contact.get_primary_contact(client.id) or (contacts[0] if contacts else None)
    if not contact:
        return error_response("No contact available to reject", 400)
    data = request.get_json(silent=True) or {}
    reason = data.get("reason") or "Rejected via API"
    result = ClientApprovalService().reject(approval_id, contact.id, reason=reason)
    if not result.get("success"):
        return error_response(result.get("message", "Reject failed"), 400)
    return jsonify({"success": True, "approval_id": approval_id, "status": "rejected", "result": result})


@api_v1_client_portal_bp.route("/documents", methods=["GET"])
@require_api_token(("portal:read", "portal:all", "admin:all"))
def portal_list_documents():
    client, err = _require_portal_client()
    if err:
        return err
    docs = []
    for att in ClientAttachment.query.filter_by(client_id=client.id).all():
        docs.append(
            {
                "id": att.id,
                "type": "client",
                "filename": att.original_filename,
                "mime_type": att.mime_type,
                "created_at": att.created_at.isoformat() if att.created_at else None,
            }
        )
    project_ids = [p.id for p in Project.query.filter_by(client_id=client.id).all()]
    if project_ids:
        for att in ProjectAttachment.query.filter(ProjectAttachment.project_id.in_(project_ids)).all():
            docs.append(
                {
                    "id": att.id,
                    "type": "project",
                    "project_id": att.project_id,
                    "filename": att.original_filename,
                    "mime_type": att.mime_type,
                    "created_at": att.created_at.isoformat() if att.created_at else None,
                }
            )
    return jsonify({"documents": docs})
