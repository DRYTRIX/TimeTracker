"""Object-level authorization helpers for REST API v1.

Token scopes alone are not sufficient: callers must also pass the same
client/project/owner checks the web UI enforces.
"""

from __future__ import annotations

from typing import Any, Optional, Tuple

from flask import g, jsonify


def api_user():
    return getattr(g, "api_user", None)


def api_user_is_admin() -> bool:
    user = api_user()
    return bool(user and getattr(user, "is_admin", False))


def forbidden(message: str = "Forbidden", status: int = 403):
    return jsonify({"error": "forbidden", "message": message, "error_code": "forbidden"}), status


def not_found(message: str = "Not found"):
    """Return 404 to avoid leaking existence of out-of-scope objects."""
    return jsonify({"error": "not_found", "message": message, "error_code": "not_found"}), 404


def require_client_access(client_id: Optional[int], *, edit: bool = False):
    """Return an error response if the API user cannot access/edit the client, else None."""
    user = api_user()
    if not user or client_id is None:
        return forbidden("Authentication required")
    if api_user_is_admin():
        return None
    from app.utils.scope_filter import user_can_access_client

    if not user_can_access_client(user, client_id):
        return not_found("Client not found")
    if edit:
        from app.models import Client
        from app.utils.permissions import user_can_edit_client

        client = Client.query.get(client_id)
        if not client or not user_can_edit_client(user, client):
            return forbidden("You do not have permission to edit this client")
    return None


def require_project_access(project_id: Optional[int], *, edit: bool = False):
    user = api_user()
    if not user or project_id is None:
        return forbidden("Authentication required")
    if api_user_is_admin():
        return None
    from app.utils.scope_filter import user_can_access_project

    if not user_can_access_project(user, project_id):
        return not_found("Project not found")
    if edit:
        from app.models import Project
        from app.utils.permissions import user_can_edit_project

        project = Project.query.get(project_id)
        if not project or not user_can_edit_project(user, project):
            return forbidden("You do not have permission to edit this project")
    return None


def require_invoice_access(invoice, *, write: bool = False) -> Optional[Tuple[Any, int]]:
    """Enforce creator-or-admin invoice access (matches web + InvoiceService)."""
    user = api_user()
    if not user or invoice is None:
        return not_found("Invoice not found")
    if api_user_is_admin():
        return None
    from app.services.invoice_service import InvoiceService

    if not InvoiceService().user_can_access_invoice(invoice, user.id, False):
        return not_found("Invoice not found")
    return None


def filter_invoices_query(query):
    """Restrict invoice query to those the API user may see."""
    user = api_user()
    if not user or api_user_is_admin():
        return query
    from app.models import Invoice

    return query.filter(Invoice.created_by == user.id)


def filter_payments_query(query):
    """Restrict payment query to payments on invoices the API user owns."""
    user = api_user()
    if not user or api_user_is_admin():
        return query
    from app.models import Invoice, Payment

    return query.join(Invoice, Payment.invoice_id == Invoice.id).filter(Invoice.created_by == user.id)


def filter_credit_notes_query(query):
    user = api_user()
    if not user or api_user_is_admin():
        return query
    from app.models import CreditNote, Invoice

    return query.join(Invoice, CreditNote.invoice_id == Invoice.id).filter(Invoice.created_by == user.id)


def default_app_login_scopes(user) -> str:
    """Scopes minted by /api/v1/auth/login — never grant admin scopes to non-admins.

    Portal-only users get a narrow read set. Regular users get broad read/write
    resource scopes (not wildcards) so object-level checks remain the boundary.
    """
    if not user:
        return "read:projects,read:time_entries"
    if getattr(user, "is_admin", False):
        return "admin:all"
    if getattr(user, "portal_only", False) or getattr(user, "is_client_portal_user", False):
        return "read:invoices,read:payments,read:clients,read:projects"
    # Explicit resource scopes instead of read:*,write:* wildcards
    return (
        "read:projects,write:projects,"
        "read:time_entries,write:time_entries,"
        "read:invoices,write:invoices,"
        "read:clients,write:clients,"
        "read:tasks,write:tasks,"
        "read:payments,write:payments,"
        "read:contacts,write:contacts,"
        "read:expenses,write:expenses,"
        "read:reports"
    )


def cap_scopes_for_user(user, scopes: str) -> str:
    """Strip admin-tier scopes from non-admin users."""
    parts = [s.strip() for s in (scopes or "").replace(" ", ",").split(",") if s.strip()]
    if not parts:
        return ""
    if getattr(user, "is_admin", False):
        return ",".join(parts)
    blocked = {"admin:all", "admin:*", "*"}
    capped = [s for s in parts if s not in blocked and not s.startswith("admin:")]
    if getattr(user, "portal_only", False) or getattr(user, "is_client_portal_user", False):
        allowed_prefixes = ("read:",)
        capped = [s for s in capped if s.startswith(allowed_prefixes) and not s.startswith("write:")]
    return ",".join(capped)


def scopes_allowed_for_token_owner(actor, target_user, scopes: str) -> Tuple[bool, str, str]:
    """Validate scopes when an admin creates a token for ``target_user``.

    Returns (ok, error_message, capped_scopes).
    """
    from app.services.api_token_service import ApiTokenService

    validation = ApiTokenService().validate_scopes(scopes)
    if not validation.get("valid"):
        return False, f"Invalid scopes: {', '.join(validation.get('invalid') or [])}", ""

    capped = cap_scopes_for_user(target_user, scopes)
    if not capped:
        return False, "No permitted scopes remain for this user", ""

    # Non-super-admins cannot mint admin:all even for themselves via this helper
    raw_parts = {s.strip() for s in scopes.replace(" ", ",").split(",") if s.strip()}
    if ("admin:all" in raw_parts or "*" in raw_parts) and not getattr(actor, "is_admin", False):
        return False, "Only admins can create tokens with admin scopes", capped

    if capped != ",".join(s.strip() for s in scopes.replace(" ", ",").split(",") if s.strip()):
        # Silently cap rather than fail when stripping admin scopes from non-admins
        pass
    return True, "", capped
