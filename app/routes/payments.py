from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_babel import gettext as _
from flask_login import login_required, current_user
from app import db, log_event, track_event
from app.models import Payment, Invoice, User, Client
from datetime import datetime, date
from decimal import Decimal, InvalidOperation
from sqlalchemy import func, and_, or_
from flask import send_file
from app.utils.db import safe_commit
from app.utils.excel_export import create_payments_list_excel

payments_bp = Blueprint("payments", __name__)


@payments_bp.route("/payments")
@login_required
def list_payments():
    """List all payments"""
    # Get filter parameters
    status_filter = request.args.get("status", "")
    method_filter = request.args.get("method", "")
    date_from = request.args.get("date_from", "")
    date_to = request.args.get("date_to", "")
    invoice_id = request.args.get("invoice_id", type=int)

    # Base query
    query = Payment.query

    # Apply filters based on user role
    if not current_user.is_admin:
        # Regular users can only see payments for their own invoices
        query = query.join(Invoice).filter(Invoice.created_by == current_user.id)

    # Apply status filter
    if status_filter:
        query = query.filter(Payment.status == status_filter)

    # Apply payment method filter
    if method_filter:
        query = query.filter(Payment.method == method_filter)

    # Apply date range filter
    if date_from:
        try:
            date_from_obj = datetime.strptime(date_from, "%Y-%m-%d").date()
            query = query.filter(Payment.payment_date >= date_from_obj)
        except ValueError:
            flash(_("Invalid from date format"), "error")

    if date_to:
        try:
            date_to_obj = datetime.strptime(date_to, "%Y-%m-%d").date()
            query = query.filter(Payment.payment_date <= date_to_obj)
        except ValueError:
            flash(_("Invalid to date format"), "error")

    # Apply invoice filter
    if invoice_id:
        query = query.filter(Payment.invoice_id == invoice_id)

    # Get payments
    payments = query.order_by(Payment.payment_date.desc(), Payment.created_at.desc()).all()

    # Calculate summary statistics
    total_payments = len(payments)
    total_amount = sum(payment.amount for payment in payments)
    total_fees = sum(payment.gateway_fee or Decimal("0") for payment in payments)
    total_net = sum(payment.net_amount or payment.amount for payment in payments)

    # Status breakdown
    completed_payments = [p for p in payments if p.status == "completed"]
    pending_payments = [p for p in payments if p.status == "pending"]
    failed_payments = [p for p in payments if p.status == "failed"]
    refunded_payments = [p for p in payments if p.status == "refunded"]

    summary = {
        "total_payments": total_payments,
        "total_amount": float(total_amount),
        "total_fees": float(total_fees),
        "total_net": float(total_net),
        "completed_count": len(completed_payments),
        "completed_amount": float(sum(p.amount for p in completed_payments)),
        "pending_count": len(pending_payments),
        "pending_amount": float(sum(p.amount for p in pending_payments)),
        "failed_count": len(failed_payments),
        "refunded_count": len(refunded_payments),
        "refunded_amount": float(sum(p.amount for p in refunded_payments)),
    }

    # Get unique payment methods for filter dropdown
    payment_methods = db.session.query(Payment.method).distinct().filter(Payment.method.isnot(None)).all()
    payment_methods = [method[0] for method in payment_methods]

    # Track event
    track_event(
        current_user.id,
        "payments_viewed",
        properties={
            "total_payments": total_payments,
            "filters_applied": bool(status_filter or method_filter or date_from or date_to or invoice_id),
        },
    )

    return render_template(
        "payments/list.html",
        payments=payments,
        summary=summary,
        payment_methods=payment_methods,
        filters={
            "status": status_filter,
            "method": method_filter,
            "date_from": date_from,
            "date_to": date_to,
            "invoice_id": invoice_id,
        },
    )


@payments_bp.route("/payments/<int:payment_id>")
@login_required
def view_payment(payment_id):
    """View payment details"""
    payment = Payment.query.get_or_404(payment_id)

    # Check access permissions
    if not current_user.is_admin and payment.invoice.created_by != current_user.id:
        flash(_("You do not have permission to view this payment"), "error")
        return redirect(url_for("payments.list_payments"))

    return render_template("payments/view.html", payment=payment)


@payments_bp.route("/payments/create", methods=["GET", "POST"])
@login_required
def create_payment():
    """Create a new payment"""
    if request.method == "POST":
        # Get form data
        invoice_id = request.form.get("invoice_id", type=int)
        amount_str = request.form.get("amount", "0").strip()
        currency = request.form.get("currency", "").strip()
        payment_date_str = request.form.get("payment_date", "").strip()
        method = request.form.get("method", "").strip()
        reference = request.form.get("reference", "").strip()
        notes = request.form.get("notes", "").strip()
        status = request.form.get("status", "completed").strip()
        gateway_transaction_id = request.form.get("gateway_transaction_id", "").strip()
        gateway_fee_str = request.form.get("gateway_fee", "0").strip()

        # Validate required fields
        if not invoice_id or not amount_str or not payment_date_str:
            flash(_("Invoice, amount, and payment date are required"), "error")
            invoices = get_user_invoices()
            return render_template("payments/create.html", invoices=invoices)

        # Get invoice
        invoice = Invoice.query.get(invoice_id)
        if not invoice:
            flash(_("Selected invoice not found"), "error")
            invoices = get_user_invoices()
            return render_template("payments/create.html", invoices=invoices)

        # Check access permissions
        if not current_user.is_admin and invoice.created_by != current_user.id:
            flash(_("You do not have permission to add payments to this invoice"), "error")
            return redirect(url_for("payments.list_payments"))

        # Validate and parse amount
        try:
            amount = Decimal(amount_str)
            if amount <= 0:
                flash(_("Payment amount must be greater than zero"), "error")
                invoices = get_user_invoices()
                return render_template("payments/create.html", invoices=invoices)
        except (ValueError, InvalidOperation):
            flash(_("Invalid payment amount"), "error")
            invoices = get_user_invoices()
            return render_template("payments/create.html", invoices=invoices)

        # Validate and parse payment date
        try:
            payment_date = datetime.strptime(payment_date_str, "%Y-%m-%d").date()
        except ValueError:
            flash(_("Invalid payment date format"), "error")
            invoices = get_user_invoices()
            return render_template("payments/create.html", invoices=invoices)

        # Parse gateway fee if provided
        gateway_fee = None
        if gateway_fee_str:
            try:
                gateway_fee = Decimal(gateway_fee_str)
                if gateway_fee < 0:
                    flash(_("Gateway fee cannot be negative"), "error")
                    invoices = get_user_invoices()
                    return render_template("payments/create.html", invoices=invoices)
            except (ValueError, InvalidOperation):
                flash(_("Invalid gateway fee amount"), "error")
                invoices = get_user_invoices()
                return render_template("payments/create.html", invoices=invoices)

        # Create payment
        payment = Payment(
            invoice_id=invoice_id,
            amount=amount,
            currency=currency if currency else invoice.currency_code,
            payment_date=payment_date,
            method=method if method else None,
            reference=reference if reference else None,
            notes=notes if notes else None,
            status=status,
            received_by=current_user.id,
            gateway_transaction_id=gateway_transaction_id if gateway_transaction_id else None,
            gateway_fee=gateway_fee,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )

        # Calculate net amount
        payment.calculate_net_amount()

        db.session.add(payment)

        # Update invoice payment tracking if payment is completed
        if status == "completed":
            invoice.amount_paid = (invoice.amount_paid or Decimal("0")) + amount
            invoice.update_payment_status()

            # Update invoice status if fully paid
            if invoice.payment_status == "fully_paid":
                invoice.status = "paid"

                # Reduce stock when invoice is fully paid (if configured)
                from app.models import StockMovement, StockReservation
                import os

                reduce_on_paid = os.getenv("INVENTORY_REDUCE_ON_INVOICE_PAID", "false").lower() == "true"
                if reduce_on_paid:
                    for item in invoice.items:
                        if item.is_stock_item and item.stock_item_id and item.warehouse_id:
                            try:
                                # Fulfill any existing reservations
                                reservation = StockReservation.query.filter_by(
                                    stock_item_id=item.stock_item_id,
                                    warehouse_id=item.warehouse_id,
                                    reservation_type="invoice",
                                    reservation_id=invoice.id,
                                    status="reserved",
                                ).first()

                                if reservation:
                                    reservation.fulfill()

                                # Create stock movement (sale)
                                StockMovement.record_movement(
                                    movement_type="sale",
                                    stock_item_id=item.stock_item_id,
                                    warehouse_id=item.warehouse_id,
                                    quantity=-item.quantity,  # Negative for removal
                                    moved_by=current_user.id,
                                    reference_type="invoice",
                                    reference_id=invoice.id,
                                    unit_cost=item.stock_item.default_cost if item.stock_item else None,
                                    reason=f"Invoice {invoice.invoice_number} payment",
                                    update_stock=True,
                                )
                            except Exception as e:
                                pass  # Don't fail payment creation on stock errors

        if not safe_commit("create_payment", {"invoice_id": invoice_id, "amount": float(amount)}):
            flash(_("Could not create payment due to a database error. Please check server logs."), "error")
            invoices = get_user_invoices()
            return render_template("payments/create.html", invoices=invoices)

        # Track event
        track_event(
            current_user.id,
            "payment_created",
            properties={
                "payment_id": payment.id,
                "invoice_id": invoice_id,
                "amount": float(amount),
                "method": method,
                "status": status,
            },
        )

        flash(f"Payment of {amount} {currency or invoice.currency_code} recorded successfully", "success")
        return redirect(url_for("payments.view_payment", payment_id=payment.id))

    # GET request - show form
    invoices = get_user_invoices()

    # Pre-select invoice if provided in query params
    selected_invoice_id = request.args.get("invoice_id", type=int)
    selected_invoice = None
    if selected_invoice_id:
        selected_invoice = Invoice.query.get(selected_invoice_id)
        if selected_invoice and (current_user.is_admin or selected_invoice.created_by == current_user.id):
            pass
        else:
            selected_invoice = None

    today = date.today().strftime("%Y-%m-%d")

    return render_template("payments/create.html", invoices=invoices, selected_invoice=selected_invoice, today=today)


@payments_bp.route("/payments/<int:payment_id>/edit", methods=["GET", "POST"])
@login_required
def edit_payment(payment_id):
    """Edit payment"""
    payment = Payment.query.get_or_404(payment_id)

    # Check access permissions
    if not current_user.is_admin and payment.invoice.created_by != current_user.id:
        flash(_("You do not have permission to edit this payment"), "error")
        return redirect(url_for("payments.list_payments"))

    if request.method == "POST":
        # Store old amount for invoice update
        old_amount = payment.amount
        old_status = payment.status

        # Get form data
        amount_str = request.form.get("amount", "0").strip()
        currency = request.form.get("currency", "").strip()
        payment_date_str = request.form.get("payment_date", "").strip()
        method = request.form.get("method", "").strip()
        reference = request.form.get("reference", "").strip()
        notes = request.form.get("notes", "").strip()
        status = request.form.get("status", "completed").strip()
        gateway_transaction_id = request.form.get("gateway_transaction_id", "").strip()
        gateway_fee_str = request.form.get("gateway_fee", "0").strip()

        # Validate and parse amount
        try:
            amount = Decimal(amount_str)
            if amount <= 0:
                flash(_("Payment amount must be greater than zero"), "error")
                return render_template("payments/edit.html", payment=payment)
        except (ValueError, InvalidOperation):
            flash(_("Invalid payment amount"), "error")
            return render_template("payments/edit.html", payment=payment)

        # Validate and parse payment date
        try:
            payment_date = datetime.strptime(payment_date_str, "%Y-%m-%d").date()
        except ValueError:
            flash(_("Invalid payment date format"), "error")
            return render_template("payments/edit.html", payment=payment)

        # Parse gateway fee if provided
        gateway_fee = None
        if gateway_fee_str:
            try:
                gateway_fee = Decimal(gateway_fee_str)
                if gateway_fee < 0:
                    flash(_("Gateway fee cannot be negative"), "error")
                    return render_template("payments/edit.html", payment=payment)
            except (ValueError, InvalidOperation):
                flash(_("Invalid gateway fee amount"), "error")
                return render_template("payments/edit.html", payment=payment)

        # Update payment
        payment.amount = amount
        payment.currency = currency if currency else payment.invoice.currency_code
        payment.payment_date = payment_date
        payment.method = method if method else None
        payment.reference = reference if reference else None
        payment.notes = notes if notes else None
        payment.status = status
        payment.gateway_transaction_id = gateway_transaction_id if gateway_transaction_id else None
        payment.gateway_fee = gateway_fee
        payment.updated_at = datetime.utcnow()

        # Calculate net amount
        payment.calculate_net_amount()

        # Update invoice payment tracking
        invoice = payment.invoice

        # Adjust invoice amount_paid based on old and new amounts and statuses
        if old_status == "completed":
            invoice.amount_paid = (invoice.amount_paid or Decimal("0")) - old_amount

        if status == "completed":
            invoice.amount_paid = (invoice.amount_paid or Decimal("0")) + amount

        invoice.update_payment_status()

        # Update invoice status
        if invoice.payment_status == "fully_paid":
            invoice.status = "paid"
        elif invoice.status == "paid" and invoice.payment_status != "fully_paid":
            invoice.status = "sent"

        if not safe_commit("edit_payment", {"payment_id": payment_id}):
            flash(_("Could not update payment due to a database error. Please check server logs."), "error")
            return render_template("payments/edit.html", payment=payment)

        # Track event
        track_event(
            current_user.id,
            "payment_updated",
            properties={"payment_id": payment.id, "amount": float(amount), "status": status},
        )

        flash(_("Payment updated successfully"), "success")
        return redirect(url_for("payments.view_payment", payment_id=payment.id))

    # GET request - show edit form
    return render_template("payments/edit.html", payment=payment)


@payments_bp.route("/payments/<int:payment_id>/delete", methods=["POST"])
@login_required
def delete_payment(payment_id):
    """Delete payment"""
    payment = Payment.query.get_or_404(payment_id)

    # Check access permissions
    if not current_user.is_admin and payment.invoice.created_by != current_user.id:
        flash(_("You do not have permission to delete this payment"), "error")
        return redirect(url_for("payments.list_payments"))

    # Store info for invoice update
    invoice = payment.invoice
    amount = payment.amount
    status = payment.status

    # Update invoice payment tracking if payment was completed
    if status == "completed":
        invoice.amount_paid = max(Decimal("0"), (invoice.amount_paid or Decimal("0")) - amount)
        invoice.update_payment_status()

        # Update invoice status if no longer paid
        if invoice.status == "paid" and invoice.payment_status != "fully_paid":
            invoice.status = "sent"

    db.session.delete(payment)

    if not safe_commit("delete_payment", {"payment_id": payment_id}):
        flash(_("Could not delete payment due to a database error. Please check server logs."), "error")
        return redirect(url_for("payments.view_payment", payment_id=payment_id))

    # Track event
    track_event(current_user.id, "payment_deleted", properties={"payment_id": payment_id, "invoice_id": invoice.id})

    flash(_("Payment deleted successfully"), "success")
    return redirect(url_for("invoices.view_invoice", invoice_id=invoice.id))


@payments_bp.route("/payments/bulk-delete", methods=["POST"])
@login_required
def bulk_delete_payments():
    """Delete multiple payments at once"""
    payment_ids = request.form.getlist("payment_ids[]")

    if not payment_ids:
        flash(_("No payments selected for deletion"), "warning")
        return redirect(url_for("payments.list_payments"))

    deleted_count = 0
    skipped_count = 0
    errors = []

    for payment_id_str in payment_ids:
        try:
            payment_id = int(payment_id_str)
            payment = Payment.query.get(payment_id)

            if not payment:
                continue

            # Check permissions
            if not current_user.is_admin and payment.invoice.created_by != current_user.id:
                skipped_count += 1
                errors.append(f"Payment #{payment_id_str}: No permission")
                continue

            # Store info for invoice update
            invoice = payment.invoice
            amount = payment.amount
            status = payment.status

            # Update invoice payment tracking if payment was completed
            if status == "completed":
                invoice.amount_paid = max(Decimal("0"), (invoice.amount_paid or Decimal("0")) - amount)
                invoice.update_payment_status()

                # Update invoice status if no longer paid
                if invoice.status == "paid" and invoice.payment_status != "fully_paid":
                    invoice.status = "sent"

            db.session.delete(payment)
            deleted_count += 1

        except Exception as e:
            skipped_count += 1
            errors.append(f"ID {payment_id_str}: {str(e)}")

    # Commit all deletions
    if deleted_count > 0:
        if not safe_commit("bulk_delete_payments", {"count": deleted_count}):
            flash(_("Could not delete payments due to a database error. Please check server logs."), "error")
            return redirect(url_for("payments.list_payments"))

    # Show appropriate messages
    if deleted_count > 0:
        flash(f'Successfully deleted {deleted_count} payment{"s" if deleted_count != 1 else ""}', "success")

    if skipped_count > 0:
        flash(f'Skipped {skipped_count} payment{"s" if skipped_count != 1 else ""}: {"; ".join(errors[:3])}', "warning")

    return redirect(url_for("payments.list_payments"))


@payments_bp.route("/payments/bulk-status", methods=["POST"])
@login_required
def bulk_update_status():
    """Update status for multiple payments at once"""
    payment_ids = request.form.getlist("payment_ids[]")
    new_status = request.form.get("status", "").strip()

    if not payment_ids:
        flash(_("No payments selected"), "warning")
        return redirect(url_for("payments.list_payments"))

    # Validate status
    valid_statuses = ["completed", "pending", "failed", "refunded"]
    if not new_status or new_status not in valid_statuses:
        flash(_("Invalid status value"), "error")
        return redirect(url_for("payments.list_payments"))

    updated_count = 0
    skipped_count = 0

    for payment_id_str in payment_ids:
        try:
            payment_id = int(payment_id_str)
            payment = Payment.query.get(payment_id)

            if not payment:
                continue

            # Check permissions
            if not current_user.is_admin and payment.invoice.created_by != current_user.id:
                skipped_count += 1
                continue

            old_status = payment.status
            payment.status = new_status

            # Update invoice payment tracking if status changed to/from completed
            invoice = payment.invoice
            if old_status == "completed" and new_status != "completed":
                # Payment was completed but now isn't - subtract from invoice
                invoice.amount_paid = max(Decimal("0"), (invoice.amount_paid or Decimal("0")) - payment.amount)
                invoice.update_payment_status()
            elif old_status != "completed" and new_status == "completed":
                # Payment is now completed - add to invoice
                invoice.amount_paid = (invoice.amount_paid or Decimal("0")) + payment.amount
                invoice.update_payment_status()

            # Update invoice status if no longer paid
            if old_status == "completed" and new_status != "completed":
                if invoice.status == "paid" and invoice.payment_status != "fully_paid":
                    invoice.status = "sent"

            updated_count += 1

        except Exception:
            skipped_count += 1

    if updated_count > 0:
        if not safe_commit("bulk_update_payment_status", {"count": updated_count, "status": new_status}):
            flash(_("Could not update payments due to a database error"), "error")
            return redirect(url_for("payments.list_payments"))

        flash(
            f'Successfully updated {updated_count} payment{"s" if updated_count != 1 else ""} to {new_status}',
            "success",
        )

    if skipped_count > 0:
        flash(f'Skipped {skipped_count} payment{"s" if skipped_count != 1 else ""} (no permission)', "warning")

    return redirect(url_for("payments.list_payments"))


@payments_bp.route("/api/payments/stats")
@login_required
def payment_stats():
    """Get payment statistics"""
    # Base query based on user role
    query = Payment.query
    if not current_user.is_admin:
        query = query.join(Invoice).filter(Invoice.created_by == current_user.id)

    # Get date range from request
    date_from = request.args.get("date_from", "")
    date_to = request.args.get("date_to", "")

    if date_from:
        try:
            date_from_obj = datetime.strptime(date_from, "%Y-%m-%d").date()
            query = query.filter(Payment.payment_date >= date_from_obj)
        except ValueError:
            pass

    if date_to:
        try:
            date_to_obj = datetime.strptime(date_to, "%Y-%m-%d").date()
            query = query.filter(Payment.payment_date <= date_to_obj)
        except ValueError:
            pass

    payments = query.all()

    # Calculate statistics
    stats = {
        "total_payments": len(payments),
        "total_amount": float(sum(p.amount for p in payments)),
        "total_fees": float(sum(p.gateway_fee or Decimal("0") for p in payments)),
        "total_net": float(sum(p.net_amount or p.amount for p in payments)),
        "by_method": {},
        "by_status": {},
        "by_month": {},
    }

    # Group by payment method
    for payment in payments:
        method = payment.method or "Unknown"
        if method not in stats["by_method"]:
            stats["by_method"][method] = {"count": 0, "amount": 0}
        stats["by_method"][method]["count"] += 1
        stats["by_method"][method]["amount"] += float(payment.amount)

    # Group by status
    for payment in payments:
        status = payment.status
        if status not in stats["by_status"]:
            stats["by_status"][status] = {"count": 0, "amount": 0}
        stats["by_status"][status]["count"] += 1
        stats["by_status"][status]["amount"] += float(payment.amount)

    # Group by month
    for payment in payments:
        month_key = payment.payment_date.strftime("%Y-%m")
        if month_key not in stats["by_month"]:
            stats["by_month"][month_key] = {"count": 0, "amount": 0}
        stats["by_month"][month_key]["count"] += 1
        stats["by_month"][month_key]["amount"] += float(payment.amount)

    return jsonify(stats)


@payments_bp.route("/payments/export/excel")
@login_required
def export_payments_excel():
    """Export payments list as Excel file"""
    # Get filter parameters
    status_filter = request.args.get("status", "")
    method_filter = request.args.get("method", "")
    date_from = request.args.get("date_from", "")
    date_to = request.args.get("date_to", "")
    invoice_id = request.args.get("invoice_id", type=int)

    # Base query
    query = Payment.query

    # Apply filters based on user role
    if not current_user.is_admin:
        # Regular users can only see payments for their own invoices
        query = query.join(Invoice).filter(Invoice.created_by == current_user.id)

    # Apply additional filters
    if status_filter:
        query = query.filter(Payment.status == status_filter)

    if method_filter:
        query = query.filter(Payment.method == method_filter)

    if date_from:
        try:
            date_from_obj = datetime.strptime(date_from, "%Y-%m-%d").date()
            query = query.filter(Payment.payment_date >= date_from_obj)
        except ValueError:
            pass

    if date_to:
        try:
            date_to_obj = datetime.strptime(date_to, "%Y-%m-%d").date()
            query = query.filter(Payment.payment_date <= date_to_obj)
        except ValueError:
            pass

    if invoice_id:
        query = query.filter(Payment.invoice_id == invoice_id)

    # Get payments
    payments = query.order_by(Payment.payment_date.desc()).all()

    # Create Excel file
    output, filename = create_payments_list_excel(payments)

    # Track Excel export event
    log_event("export.excel", user_id=current_user.id, export_type="payments_list", num_rows=len(payments))
    track_event(current_user.id, "export.excel", {"export_type": "payments_list", "num_rows": len(payments)})

    return send_file(
        output,
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        as_attachment=True,
        download_name=filename,
    )


def get_user_invoices():
    """Get invoices accessible by current user"""
    if current_user.is_admin:
        return Invoice.query.filter(Invoice.status != "cancelled").order_by(Invoice.invoice_number.desc()).all()
    else:
        return (
            Invoice.query.filter(Invoice.created_by == current_user.id, Invoice.status != "cancelled")
            .order_by(Invoice.invoice_number.desc())
            .all()
        )
