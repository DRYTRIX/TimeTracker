"""Credit Notes blueprint — Phase 3 web UI + PDF + e-invoicing download routes."""

from __future__ import annotations

import io
import logging

from flask import (
    Blueprint,
    Response,
    abort,
    current_app,
    flash,
    jsonify,
    redirect,
    render_template,
    request,
    send_file,
    url_for,
)
from flask_babel import gettext as _
from flask_login import current_user, login_required

from app import db
from app.models import Invoice
from app.models.payments import CreditNote
from app.utils.module_helpers import module_enabled

credit_notes_bp = Blueprint("credit_notes", __name__, url_prefix="/credit-notes")
logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _check_access(invoice):
    """Raise 403 if the current user doesn't own or admin the invoice."""
    if not current_user.is_admin and invoice.created_by != current_user.id:
        abort(403)


def _get_cn_or_404(cn_id):
    return CreditNote.query.get_or_404(cn_id)


# ---------------------------------------------------------------------------
# List (optional simple view)
# ---------------------------------------------------------------------------


@credit_notes_bp.route("/")
@login_required
@module_enabled("invoices")
def list_credit_notes():
    if current_user.is_admin:
        cns = CreditNote.query.order_by(CreditNote.created_at.desc()).limit(200).all()
    else:
        cns = (
            CreditNote.query.join(Invoice, CreditNote.invoice_id == Invoice.id)
            .filter(Invoice.created_by == current_user.id)
            .order_by(CreditNote.created_at.desc())
            .limit(200)
            .all()
        )
    return render_template("credit_notes/list.html", credit_notes=cns)


# ---------------------------------------------------------------------------
# Create from invoice (POST)
# ---------------------------------------------------------------------------


@credit_notes_bp.route("/create-from-invoice/<int:invoice_id>", methods=["POST"])
@login_required
@module_enabled("invoices")
def create_from_invoice(invoice_id):
    invoice = Invoice.query.get_or_404(invoice_id)
    _check_access(invoice)

    if invoice.status == "draft":
        flash(_("Cannot create credit note for a draft invoice."), "error")
        return redirect(url_for("invoices.view_invoice", invoice_id=invoice_id))

    mode = request.form.get("mode", "full")  # full | amount
    reason = (request.form.get("reason") or "").strip()

    from app.services.credit_note_service import CreditNoteService

    try:
        if mode == "full":
            cn = CreditNoteService.create_full_credit(invoice, current_user.id, reason=reason)
        else:
            raw_amount = request.form.get("amount", "0")
            try:
                from decimal import Decimal

                amount = Decimal(str(raw_amount))
            except Exception:
                flash(_("Invalid amount."), "error")
                return redirect(url_for("invoices.view_invoice", invoice_id=invoice_id))
            description = request.form.get("description") or reason or _("Credit")
            cn = CreditNoteService.create_amount_credit(
                invoice, current_user.id, amount, reason=reason, description=description
            )

        flash(_("Credit note %(cn)s created.", cn=cn.credit_number), "success")
        return redirect(url_for("credit_notes.view_credit_note", cn_id=cn.id))
    except Exception as exc:
        db.session.rollback()
        logger.exception("Failed to create credit note for invoice %s", invoice_id)
        flash(_("Could not create credit note: %(err)s", err=str(exc)), "error")
        return redirect(url_for("invoices.view_invoice", invoice_id=invoice_id))


# ---------------------------------------------------------------------------
# View
# ---------------------------------------------------------------------------


@credit_notes_bp.route("/<int:cn_id>")
@login_required
@module_enabled("invoices")
def view_credit_note(cn_id):
    cn = _get_cn_or_404(cn_id)
    invoice = Invoice.query.get_or_404(cn.invoice_id)
    _check_access(invoice)
    items = cn.items.all() if hasattr(cn.items, "all") else list(cn.items or [])
    items = sorted(items, key=lambda x: x.position)
    return render_template("credit_notes/view.html", cn=cn, invoice=invoice, items=items)


# ---------------------------------------------------------------------------
# Issue (POST)
# ---------------------------------------------------------------------------


@credit_notes_bp.route("/<int:cn_id>/issue", methods=["POST"])
@login_required
@module_enabled("invoices")
def issue_credit_note(cn_id):
    cn = _get_cn_or_404(cn_id)
    invoice = Invoice.query.get_or_404(cn.invoice_id)
    _check_access(invoice)

    if cn.status not in ("draft",):
        flash(_("Credit note is already issued."), "warning")
        return redirect(url_for("credit_notes.view_credit_note", cn_id=cn_id))

    from app.services.credit_note_service import CreditNoteService

    CreditNoteService.issue_credit_note(cn)
    db.session.commit()
    flash(_("Credit note %(cn)s issued.", cn=cn.credit_number), "success")
    return redirect(url_for("credit_notes.view_credit_note", cn_id=cn_id))


# ---------------------------------------------------------------------------
# PDF download
# ---------------------------------------------------------------------------


@credit_notes_bp.route("/<int:cn_id>/pdf")
@login_required
@module_enabled("invoices")
def download_pdf(cn_id):
    cn = _get_cn_or_404(cn_id)
    invoice = Invoice.query.get_or_404(cn.invoice_id)
    _check_access(invoice)

    try:
        from app.utils.credit_note_pdf import generate_credit_note_pdf

        pdf_bytes = generate_credit_note_pdf(cn)
    except Exception as exc:
        logger.exception("Credit note PDF generation failed for cn=%s", cn_id)
        abort(500, description=str(exc))

    filename = f"credit-note-{cn.credit_number}.pdf"
    return send_file(
        io.BytesIO(pdf_bytes),
        mimetype="application/pdf",
        as_attachment=True,
        download_name=filename,
    )


# ---------------------------------------------------------------------------
# E-invoicing XML download routes
# ---------------------------------------------------------------------------


@credit_notes_bp.route("/<int:cn_id>/ubl")
@login_required
@module_enabled("invoices")
def download_ubl(cn_id):
    """Download Peppol UBL CreditNote XML (type 381)."""
    cn = _get_cn_or_404(cn_id)
    invoice = Invoice.query.get_or_404(cn.invoice_id)
    _check_access(invoice)

    try:
        from app.integrations.peppol import PeppolParty, build_peppol_ubl_credit_note_xml
        from app.models import Settings

        settings = Settings.get_settings()
        supplier = PeppolParty(
            endpoint_id=getattr(settings, "peppol_sender_id", "") or "",
            endpoint_scheme_id=getattr(settings, "peppol_sender_scheme", "0088") or "0088",
            name=getattr(settings, "company_name", "Supplier") or "Supplier",
            tax_id=getattr(settings, "company_tax_id", None),
        )
        customer = PeppolParty(
            endpoint_id=getattr(invoice, "buyer_reference", "") or "",
            endpoint_scheme_id="0088",
            name=invoice.client_name or "Customer",
        )
        xml_str, _ = build_peppol_ubl_credit_note_xml(cn, invoice, supplier, customer)
    except Exception as exc:
        logger.exception("UBL credit note XML build failed for cn=%s", cn_id)
        abort(500, description=str(exc))

    filename = f"credit-note-{cn.credit_number}-ubl.xml"
    return Response(
        xml_str,
        mimetype="application/xml",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@credit_notes_bp.route("/<int:cn_id>/fatturapa")
@login_required
@module_enabled("invoices")
def download_fatturapa(cn_id):
    """Download FatturaPA XML (TD04 credit note)."""
    cn = _get_cn_or_404(cn_id)
    invoice = Invoice.query.get_or_404(cn.invoice_id)
    _check_access(invoice)

    try:
        from app.models import Client, Settings
        from app.utils.fatturapa import build_fatturapa_credit_note_xml

        settings = Settings.get_settings()
        client = Client.query.get(invoice.client_id) if invoice.client_id else None
        xml_bytes, filename = build_fatturapa_credit_note_xml(cn, invoice, settings, client)
    except Exception as exc:
        logger.exception("FatturaPA credit note XML build failed for cn=%s", cn_id)
        abort(500, description=str(exc))

    return Response(
        xml_bytes,
        mimetype="application/xml",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
