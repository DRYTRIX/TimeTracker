"""Web UI for bank statement upload and invoice reconciliation."""

from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_babel import gettext as _
from flask_login import current_user, login_required

from app.models.bank_transaction import BankTransaction
from app.services.bank_reconciliation_service import BankReconciliationService
from app.utils.module_helpers import module_enabled

bank_reconciliation_bp = Blueprint("bank_reconciliation", __name__)


def _require_admin():
    if not current_user.is_admin:
        flash(_("Access denied"), "error")
        return False
    return True


@bank_reconciliation_bp.route("/payments/reconciliation", methods=["GET"])
@login_required
@module_enabled("payments")
def reconciliation_queue():
    if not _require_admin():
        return redirect(url_for("payments.list_payments"))

    status = request.args.get("status", BankTransaction.MATCH_PENDING)
    service = BankReconciliationService()
    transactions = service.list_queue(status=status)
    suggestions = {}
    for txn in transactions:
        if txn.match_status == BankTransaction.MATCH_PENDING:
            suggestions[txn.id] = service.suggest_matches(txn, limit=5)

    return render_template(
        "payments/reconciliation_queue.html",
        transactions=transactions,
        suggestions=suggestions,
        status=status,
    )


@bank_reconciliation_bp.route("/payments/reconciliation/upload", methods=["GET", "POST"])
@login_required
@module_enabled("payments")
def reconciliation_upload():
    if not _require_admin():
        return redirect(url_for("payments.list_payments"))

    if request.method == "GET":
        return render_template("payments/reconciliation_upload.html")

    upload = request.files.get("statement")
    account_label = (request.form.get("account_label") or "").strip() or None
    if not upload or not upload.filename:
        flash(_("Please choose a statement file"), "error")
        return redirect(url_for("bank_reconciliation.reconciliation_upload"))

    raw = upload.read()
    try:
        content = raw.decode("utf-8-sig")
    except UnicodeDecodeError:
        content = raw.decode("latin-1")

    service = BankReconciliationService()
    filename = (upload.filename or "").lower()
    try:
        if filename.endswith(".xml") or content.lstrip().startswith("<?xml") or "<Document" in content[:500]:
            parsed = service.parse_camt053(content, account_label=account_label)
        else:
            parsed = service.parse_csv(content, account_label=account_label)
    except ValueError as exc:
        flash(str(exc), "error")
        return redirect(url_for("bank_reconciliation.reconciliation_upload"))

    if not parsed:
        flash(_("No transactions found in file"), "warning")
        return redirect(url_for("bank_reconciliation.reconciliation_upload"))

    created = service.import_rows(parsed)
    flash(_("%(count)s transactions imported", count=len(created)), "success")
    return redirect(url_for("bank_reconciliation.reconciliation_queue"))


@bank_reconciliation_bp.route("/payments/reconciliation/<int:txn_id>/confirm", methods=["POST"])
@login_required
@module_enabled("payments")
def reconciliation_confirm(txn_id):
    if not _require_admin():
        return redirect(url_for("payments.list_payments"))

    invoice_id = request.form.get("invoice_id", type=int)
    if not invoice_id:
        flash(_("Invoice is required"), "error")
        return redirect(url_for("bank_reconciliation.reconciliation_queue"))

    result = BankReconciliationService().confirm_match(
        txn_id, invoice_id, received_by=current_user.id
    )
    if result.get("success"):
        flash(_("Payment recorded and transaction matched"), "success")
    else:
        flash(result.get("message") or _("Could not confirm match"), "error")
    return redirect(url_for("bank_reconciliation.reconciliation_queue"))


@bank_reconciliation_bp.route("/payments/reconciliation/<int:txn_id>/ignore", methods=["POST"])
@login_required
@module_enabled("payments")
def reconciliation_ignore(txn_id):
    if not _require_admin():
        return redirect(url_for("payments.list_payments"))

    result = BankReconciliationService().ignore_transaction(txn_id)
    if result.get("success"):
        flash(_("Transaction ignored"), "success")
    else:
        flash(result.get("message") or _("Could not ignore transaction"), "error")
    return redirect(url_for("bank_reconciliation.reconciliation_queue"))
