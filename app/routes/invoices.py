from flask import Blueprint, Response, render_template, request, redirect, url_for, flash, jsonify, send_file, make_response, current_app
from flask_babel import gettext as _
from flask_login import login_required, current_user
from app import db, log_event, track_event
from app.utils.module_helpers import module_enabled
from app.models import (
    User,
    Project,
    TimeEntry,
    Invoice,
    InvoiceItem,
    Settings,
    RateOverride,
    ProjectCost,
    ExtraGood,
    Expense,
    InvoiceImage,
)
from datetime import datetime, timedelta, date
from decimal import Decimal, InvalidOperation
import io
import csv
import json
import logging
from app.utils.db import safe_commit
from app.utils.excel_export import create_invoices_list_excel
from app.utils.prepaid_hours import PrepaidHoursAllocator
from app.utils.posthog_funnels import (
    track_invoice_page_viewed,
    track_invoice_project_selected,
    track_invoice_previewed,
    track_invoice_generated,
)

invoices_bp = Blueprint("invoices", __name__)
logger = logging.getLogger(__name__)


@invoices_bp.route("/invoices")
@login_required
@module_enabled("invoices")
def list_invoices():
    """List all invoices - REFACTORED to use service layer with eager loading"""
    # Track invoice page viewed
    track_invoice_page_viewed(current_user.id)

    from app.services import InvoiceService

    # Get filter parameters
    status = request.args.get("status", "").strip()
    payment_status = request.args.get("payment_status", "").strip()
    search_query = request.args.get("search", "").strip()

    # Use service layer to get invoices (prevents N+1 queries)
    invoice_service = InvoiceService()
    result = invoice_service.list_invoices(
        status=status if status else None,
        payment_status=payment_status if payment_status else None,
        search=search_query if search_query else None,
        user_id=current_user.id,
        is_admin=current_user.is_admin,
    )

    # Check if this is an AJAX request
    if request.headers.get("X-Requested-With") == "XMLHttpRequest":
        # Return only the invoices list HTML for AJAX requests
        response = make_response(render_template(
            "invoices/_invoices_list.html",
            invoices=result["invoices"],
        ))
        response.headers["Content-Type"] = "text/html; charset=utf-8"
        return response

    return render_template("invoices/list.html", invoices=result["invoices"], summary=result["summary"])


@invoices_bp.route("/invoices/create", methods=["GET", "POST"])
@login_required
def create_invoice():
    """Create a new invoice"""
    if request.method == "POST":
        # Get form data
        project_id = request.form.get("project_id", type=int)
        client_name = request.form.get("client_name", "").strip()
        client_email = request.form.get("client_email", "").strip()
        client_address = request.form.get("client_address", "").strip()
        buyer_reference = (request.form.get("buyer_reference", "") or "").strip() or None
        due_date_str = request.form.get("due_date", "").strip()
        tax_rate = request.form.get("tax_rate", "0").strip()
        notes = request.form.get("notes", "").strip()
        terms = request.form.get("terms", "").strip()

        # Validate required fields
        if not project_id or not client_name or not due_date_str:
            flash(_("Project, client name, and due date are required"), "error")
            return render_template("invoices/create.html")

        try:
            due_date = datetime.strptime(due_date_str, "%Y-%m-%d").date()
        except ValueError:
            flash(_("Invalid due date format"), "error")
            return render_template("invoices/create.html")

        try:
            tax_rate = Decimal(tax_rate)
        except ValueError:
            flash(_("Invalid tax rate format"), "error")
            return render_template("invoices/create.html")

        # Get project
        project = Project.query.get(project_id)
        if not project:
            flash(_("Selected project not found"), "error")
            return render_template("invoices/create.html")

        # Get quote_id from project if it exists
        quote_id = project.quote_id if hasattr(project, "quote_id") else None

        # If quote exists, try to get payment terms and calculate due_date
        quote = None
        if quote_id:
            from app.models import Quote

            quote = Quote.query.get(quote_id)
            if quote and quote.payment_terms:
                # Calculate due_date from payment terms
                calculated_due_date = quote.calculate_due_date_from_payment_terms()
                if calculated_due_date:
                    try:
                        due_date = calculated_due_date
                        # Override if user provided a different due_date
                        if due_date_str:
                            due_date = datetime.strptime(due_date_str, "%Y-%m-%d").date()
                    except ValueError:
                        pass  # Use calculated date if parsing fails

        # Generate invoice number
        invoice_number = Invoice.generate_invoice_number()

        # Track project selected for invoice
        track_invoice_project_selected(
            current_user.id, {"project_id": project_id, "has_email": bool(client_email), "has_tax": tax_rate > 0}
        )

        # Get currency from settings
        settings = Settings.get_settings()
        currency_code = settings.currency if settings else "USD"

        # Create invoice
        invoice = Invoice(
            invoice_number=invoice_number,
            project_id=project_id,
            client_name=client_name,
            due_date=due_date,
            created_by=current_user.id,
            client_id=project.client_id,
            quote_id=quote_id,
            client_email=client_email,
            client_address=client_address,
            buyer_reference=buyer_reference,
            tax_rate=tax_rate,
            notes=notes,
            terms=terms,
            currency_code=currency_code,
        )

        db.session.add(invoice)
        if not safe_commit("create_invoice", {"invoice_number": invoice_number, "project_id": project_id}):
            flash(_("Could not create invoice due to a database error. Please check server logs."), "error")
            return render_template("invoices/create.html")

        # Track invoice created
        track_invoice_generated(
            current_user.id,
            {
                "invoice_id": invoice.id,
                "invoice_number": invoice_number,
                "has_tax": float(tax_rate) > 0,
                "has_notes": bool(notes),
            },
        )

        # Notify client about new invoice
        if invoice.client_id:
            try:
                from app.services.client_notification_service import ClientNotificationService
                notification_service = ClientNotificationService()
                notification_service.notify_invoice_created(invoice.id, invoice.client_id)
            except Exception as e:
                logger.error(f"Failed to send client notification for invoice {invoice.id}: {e}", exc_info=True)

        flash(f"Invoice {invoice_number} created successfully", "success")
        return redirect(url_for("invoices.edit_invoice", invoice_id=invoice.id))

    # GET request - show form (scoped for subcontractors)
    from app.utils.scope_filter import apply_project_scope_to_model
    projects_query = Project.query.filter_by(status="active", billable=True).order_by(Project.name)
    scope_p = apply_project_scope_to_model(Project, current_user)
    if scope_p is not None:
        projects_query = projects_query.filter(scope_p)
    projects = projects_query.all()
    settings = Settings.get_settings()

    # Set default due date to 30 days from now
    default_due_date = (datetime.utcnow() + timedelta(days=30)).strftime("%Y-%m-%d")

    return render_template(
        "invoices/create.html", projects=projects, settings=settings, default_due_date=default_due_date
    )


@invoices_bp.route("/invoices/<int:invoice_id>")
@login_required
def view_invoice(invoice_id):
    """View invoice details"""
    from app.models import InvoiceTemplate

    invoice = Invoice.query.get_or_404(invoice_id)

    # Check access permissions
    if not current_user.is_admin and invoice.created_by != current_user.id:
        flash(_("You do not have permission to view this invoice"), "error")
        return redirect(url_for("invoices.list_invoices"))

    # Track invoice previewed
    track_invoice_previewed(current_user.id, {"invoice_id": invoice.id, "invoice_number": invoice.invoice_number})

    # Get email templates for selection
    email_templates = InvoiceTemplate.query.order_by(InvoiceTemplate.name).all()

    # Get email history
    from app.models import InvoiceEmail

    email_history = InvoiceEmail.query.filter_by(invoice_id=invoice_id).order_by(InvoiceEmail.sent_at.desc()).all()

    # Get Peppol history (best-effort if table exists)
    peppol_history = []
    peppol_enabled_flag = False
    peppol_recipient_ready = False
    try:
        from app.models import InvoicePeppolTransmission
        from app.integrations.peppol import peppol_enabled as _peppol_enabled

        peppol_enabled_flag = bool(_peppol_enabled())
        peppol_history = (
            InvoicePeppolTransmission.query.filter_by(invoice_id=invoice_id)
            .order_by(InvoicePeppolTransmission.created_at.desc())
            .all()
        )
        try:
            client = invoice.client
            peppol_recipient_ready = bool(
                client
                and client.get_custom_field("peppol_endpoint_id")
                and client.get_custom_field("peppol_scheme_id")
            )
        except Exception:
            peppol_recipient_ready = False
    except Exception:
        # Migration might not be applied yet; don't block invoice view.
        peppol_history = []

    # PEPPOL compliance warnings when invoices_peppol_compliant is on
    peppol_compliance_warnings = []
    try:
        settings_obj = Settings.get_settings()
        if getattr(settings_obj, "invoices_peppol_compliant", False):
            if not (getattr(settings_obj, "company_tax_id", None) or "").strip():
                peppol_compliance_warnings.append(_("Company Tax ID (VAT) is missing in Admin → Settings → Company Branding."))
            if not (getattr(settings_obj, "peppol_sender_endpoint_id", None) or "").strip():
                peppol_compliance_warnings.append(_("Sender Endpoint ID is missing in Admin → Settings → Peppol e-Invoicing."))
            if not (getattr(settings_obj, "peppol_sender_scheme_id", None) or "").strip():
                peppol_compliance_warnings.append(_("Sender Scheme ID is missing in Admin → Settings → Peppol e-Invoicing."))
            client = getattr(invoice, "client", None)
            if client:
                if not (client.get_custom_field("peppol_endpoint_id", "") or "").strip():
                    peppol_compliance_warnings.append(_("Client Peppol Endpoint ID is missing. Add peppol_endpoint_id to the client's custom fields."))
                if not (client.get_custom_field("peppol_scheme_id", "") or "").strip():
                    peppol_compliance_warnings.append(_("Client Peppol Scheme ID is missing. Add peppol_scheme_id to the client's custom fields."))
            else:
                peppol_compliance_warnings.append(_("Invoice has no linked client; buyer PEPPOL identifiers cannot be checked."))
    except Exception:
        pass

    # Get approval information
    from app.services.invoice_approval_service import InvoiceApprovalService

    approval_service = InvoiceApprovalService()
    approval = approval_service.get_invoice_approval(invoice_id)

    # Get link templates for payment_reference (for clickable values)
    from app.models import LinkTemplate
    from sqlalchemy.exc import ProgrammingError
    link_templates_by_field = {}
    try:
        for template in LinkTemplate.get_active_templates():
            if template.field_key == 'payment_reference':
                link_templates_by_field['payment_reference'] = template
    except ProgrammingError as e:
        # Handle case where link_templates table doesn't exist (migration not run)
        if "does not exist" in str(e.orig) or "relation" in str(e.orig).lower():
            current_app.logger.warning(
                "link_templates table does not exist. Run migration: flask db upgrade"
            )
            link_templates_by_field = {}
        else:
            raise

    return render_template(
        "invoices/view.html",
        invoice=invoice,
        email_templates=email_templates,
        email_history=email_history,
        peppol_history=peppol_history,
        peppol_enabled=peppol_enabled_flag,
        peppol_recipient_ready=peppol_recipient_ready,
        peppol_compliance_warnings=peppol_compliance_warnings,
        invoices_peppol_compliant=getattr(Settings.get_settings(), "invoices_peppol_compliant", False),
        approval=approval,
        link_templates_by_field=link_templates_by_field,
    )


@invoices_bp.route("/invoices/<int:invoice_id>/edit", methods=["GET", "POST"])
@login_required
def edit_invoice(invoice_id):
    """Edit invoice"""
    invoice = Invoice.query.get_or_404(invoice_id)

    # Check access permissions
    if not current_user.is_admin and invoice.created_by != current_user.id:
        flash(_("You do not have permission to edit this invoice"), "error")
        return redirect(url_for("invoices.list_invoices"))

    if request.method == "POST":
        # Update invoice details
        invoice.client_name = request.form.get("client_name", "").strip()
        invoice.client_email = request.form.get("client_email", "").strip()
        invoice.client_address = request.form.get("client_address", "").strip()
        _br = request.form.get("buyer_reference", "").strip()
        invoice.buyer_reference = _br if _br else None
        invoice.due_date = datetime.strptime(request.form.get("due_date"), "%Y-%m-%d").date()
        invoice.tax_rate = Decimal(request.form.get("tax_rate", "0"))
        invoice.notes = request.form.get("notes", "").strip()
        invoice.terms = request.form.get("terms", "").strip()

        # Update items
        item_ids = request.form.getlist("item_id[]")
        descriptions = request.form.getlist("description[]")
        quantities = request.form.getlist("quantity[]")
        unit_prices = request.form.getlist("unit_price[]")
        item_time_entry_ids_list = request.form.getlist("item_time_entry_ids[]")

        # Remove existing items
        invoice.items.delete()

        # Add new items
        for i in range(len(descriptions)):
            if descriptions[i].strip() and quantities[i] and unit_prices[i]:
                try:
                    quantity = Decimal(quantities[i])
                    unit_price = Decimal(unit_prices[i])

                    # Get time entry ids if provided (for time-based items)
                    time_entry_ids_val = None
                    if i < len(item_time_entry_ids_list) and item_time_entry_ids_list[i].strip():
                        time_entry_ids_val = item_time_entry_ids_list[i].strip()
                        # Recalculate quantity from time entries (defense in depth)
                        try:
                            entry_ids = [int(x.strip()) for x in time_entry_ids_val.split(",") if x.strip()]
                            if entry_ids:
                                entries = TimeEntry.query.filter(TimeEntry.id.in_(entry_ids)).all()
                                total_seconds = sum(e.duration_seconds or 0 for e in entries)
                                quantity = Decimal(str(round(total_seconds / 3600, 2)))
                        except (ValueError, TypeError):
                            pass

                    # Get stock item info if provided
                    stock_item_id = request.form.getlist("item_stock_item_id[]")
                    warehouse_id = request.form.getlist("item_warehouse_id[]")

                    stock_item_id_val = (
                        int(stock_item_id[i])
                        if i < len(stock_item_id) and stock_item_id[i] and stock_item_id[i].strip()
                        else None
                    )
                    warehouse_id_val = (
                        int(warehouse_id[i])
                        if i < len(warehouse_id) and warehouse_id[i] and warehouse_id[i].strip()
                        else None
                    )

                    item = InvoiceItem(
                        invoice_id=invoice.id,
                        description=descriptions[i].strip(),
                        quantity=quantity,
                        unit_price=unit_price,
                        time_entry_ids=time_entry_ids_val,
                        stock_item_id=stock_item_id_val,
                        warehouse_id=warehouse_id_val,
                    )
                    db.session.add(item)
                except ValueError:
                    flash(f"Invalid quantity or price for item {i+1}", "error")
                    continue

        # Update expenses
        expense_ids = request.form.getlist("expense_id[]")

        # Unlink expenses not in the list
        for expense in invoice.expenses.all():
            if str(expense.id) not in expense_ids:
                expense.unmark_as_invoiced()

        # Link expenses in the list
        if expense_ids:
            for expense_id in expense_ids:
                try:
                    expense = Expense.query.get(int(expense_id))
                    if expense and not expense.invoiced:
                        expense.mark_as_invoiced(invoice.id)
                except (ValueError, AttributeError):
                    continue

        # Update extra goods
        good_ids = request.form.getlist("good_id[]")
        good_names = request.form.getlist("good_name[]")
        good_descriptions = request.form.getlist("good_description[]")
        good_categories = request.form.getlist("good_category[]")
        good_quantities = request.form.getlist("good_quantity[]")
        good_unit_prices = request.form.getlist("good_unit_price[]")
        good_skus = request.form.getlist("good_sku[]")

        # Remove existing extra goods
        invoice.extra_goods.delete()

        # Add new extra goods
        for i in range(len(good_names)):
            if good_names[i].strip() and good_quantities[i] and good_unit_prices[i]:
                try:
                    quantity = Decimal(good_quantities[i])
                    unit_price = Decimal(good_unit_prices[i])

                    good = ExtraGood(
                        name=good_names[i].strip(),
                        description=(
                            good_descriptions[i].strip()
                            if i < len(good_descriptions) and good_descriptions[i]
                            else None
                        ),
                        category=good_categories[i] if i < len(good_categories) and good_categories[i] else "product",
                        quantity=quantity,
                        unit_price=unit_price,
                        sku=good_skus[i].strip() if i < len(good_skus) and good_skus[i] else None,
                        invoice_id=invoice.id,
                        created_by=current_user.id,
                        currency_code=invoice.currency_code,
                    )
                    db.session.add(good)
                except ValueError:
                    flash(f"Invalid quantity or price for extra good {i+1}", "error")
                    continue

        # Reserve stock for invoice items with stock items
        from app.models import StockReservation

        for item in invoice.items:
            if item.is_stock_item and item.stock_item_id and item.warehouse_id:
                # Check if reservation already exists
                existing = StockReservation.query.filter_by(
                    stock_item_id=item.stock_item_id,
                    warehouse_id=item.warehouse_id,
                    reservation_type="invoice",
                    reservation_id=invoice.id,
                    status="reserved",
                ).first()

                if not existing:
                    try:
                        StockReservation.create_reservation(
                            stock_item_id=item.stock_item_id,
                            warehouse_id=item.warehouse_id,
                            quantity=item.quantity,
                            reservation_type="invoice",
                            reservation_id=invoice.id,
                            reserved_by=current_user.id,
                            expires_in_days=None,  # Invoice reservations don't expire
                        )
                    except ValueError as e:
                        flash(
                            _(
                                "Warning: Could not reserve stock for item %(item)s: %(error)s",
                                item=item.description,
                                error=str(e),
                            ),
                            "warning",
                        )

        # Calculate totals
        invoice.calculate_totals()
        if not safe_commit("edit_invoice", {"invoice_id": invoice.id}):
            flash(_("Could not update invoice due to a database error. Please check server logs."), "error")
            return render_template(
                "invoices/edit.html",
                invoice=invoice,
                projects=Project.query.filter_by(status="active").order_by(Project.name).all(),
            )

        flash(_("Invoice updated successfully"), "success")
        return redirect(url_for("invoices.view_invoice", invoice_id=invoice.id))

    # GET request - show edit form
    from app.models import InvoiceTemplate, StockItem, Warehouse
    import json

    projects = Project.query.filter_by(status="active").order_by(Project.name).all()
    email_templates = InvoiceTemplate.query.order_by(InvoiceTemplate.name).all()
    stock_items = StockItem.query.filter_by(is_active=True).order_by(StockItem.name).all()
    warehouses = Warehouse.query.filter_by(is_active=True).order_by(Warehouse.code).all()

    # Prepare stock items and warehouses for JavaScript
    stock_items_json = json.dumps(
        [
            {
                "id": item.id,
                "sku": item.sku,
                "name": item.name,
                "default_price": float(item.default_price) if item.default_price else None,
                "default_cost": float(item.default_cost) if item.default_cost else None,
                "unit": item.unit or "pcs",
                "description": item.name,
            }
            for item in stock_items
        ]
    )

    warehouses_json = json.dumps([{"id": wh.id, "code": wh.code, "name": wh.name} for wh in warehouses])

    return render_template(
        "invoices/edit.html",
        invoice=invoice,
        projects=projects,
        email_templates=email_templates,
        stock_items=stock_items,
        warehouses=warehouses,
        stock_items_json=stock_items_json,
        warehouses_json=warehouses_json,
    )


@invoices_bp.route("/invoices/<int:invoice_id>/status", methods=["POST"])
@login_required
def update_invoice_status(invoice_id):
    """Update invoice status"""
    invoice = Invoice.query.get_or_404(invoice_id)

    # Check access permissions
    if not current_user.is_admin and invoice.created_by != current_user.id:
        return jsonify({"error": "Permission denied"}), 403

    new_status = request.form.get("new_status")
    if new_status not in ["draft", "sent", "paid", "cancelled"]:
        return jsonify({"error": "Invalid status"}), 400

    invoice.status = new_status

    # Auto-update payment status if marking as paid
    if new_status == "paid" and invoice.payment_status != "fully_paid":
        invoice.amount_paid = invoice.total_amount
        invoice.payment_status = "fully_paid"
        if not invoice.payment_date:
            invoice.payment_date = datetime.utcnow().date()

    # Mark time entries as paid when invoice is sent (non-external invoices)
    if new_status == "sent":
        from app.services import InvoiceService
        invoice_service = InvoiceService()
        marked_count = invoice_service.mark_time_entries_as_paid(invoice)
        if marked_count > 0:
            current_app.logger.info(
                f"Marked {marked_count} time entr{'y' if marked_count == 1 else 'ies'} as paid for invoice {invoice.invoice_number}"
            )

    # Reduce stock when invoice is sent or paid (if configured)
    from app.models import StockMovement, StockReservation
    import os

    reduce_on_sent = os.getenv("INVENTORY_REDUCE_ON_INVOICE_SENT", "true").lower() == "true"
    reduce_on_paid = os.getenv("INVENTORY_REDUCE_ON_INVOICE_PAID", "false").lower() == "true"

    if (new_status == "sent" and reduce_on_sent) or (new_status == "paid" and reduce_on_paid):
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
                        reason=f"Invoice {invoice.invoice_number}",
                        update_stock=True,
                    )
                except Exception as e:
                    flash(
                        _(
                            "Warning: Could not reduce stock for item %(item)s: %(error)s",
                            item=item.description,
                            error=str(e),
                        ),
                        "warning",
                    )

    if not safe_commit("update_invoice_status", {"invoice_id": invoice.id, "status": new_status}):
        return jsonify({"error": "Database error while updating status"}), 500

    return jsonify({"success": True, "status": new_status})


@invoices_bp.route("/invoices/<int:invoice_id>/delete", methods=["POST"])
@login_required
def delete_invoice(invoice_id):
    """Delete invoice"""
    invoice = Invoice.query.get_or_404(invoice_id)

    # Check access permissions
    if not current_user.is_admin and invoice.created_by != current_user.id:
        flash(_("You do not have permission to delete this invoice"), "error")
        return redirect(url_for("invoices.list_invoices"))

    invoice_number = invoice.invoice_number
    db.session.delete(invoice)
    if not safe_commit("delete_invoice", {"invoice_id": invoice.id}):
        flash(_("Could not delete invoice due to a database error. Please check server logs."), "error")
        return redirect(url_for("invoices.list_invoices"))

    flash(f"Invoice {invoice_number} deleted successfully", "success")
    return redirect(url_for("invoices.list_invoices"))


@invoices_bp.route("/invoices/bulk-delete", methods=["POST"])
@login_required
def bulk_delete_invoices():
    """Delete multiple invoices at once"""
    invoice_ids = request.form.getlist("invoice_ids[]")

    if not invoice_ids:
        flash(_("No invoices selected for deletion"), "warning")
        return redirect(url_for("invoices.list_invoices"))

    deleted_count = 0
    skipped_count = 0
    errors = []

    for invoice_id_str in invoice_ids:
        try:
            invoice_id = int(invoice_id_str)
            invoice = Invoice.query.get(invoice_id)

            if not invoice:
                continue

            # Check permissions
            if not current_user.is_admin and invoice.created_by != current_user.id:
                skipped_count += 1
                errors.append(f"'{invoice.invoice_number}': No permission")
                continue

            invoice_number = invoice.invoice_number
            db.session.delete(invoice)
            deleted_count += 1

        except Exception as e:
            skipped_count += 1
            errors.append(f"ID {invoice_id_str}: {str(e)}")

    # Commit all deletions
    if deleted_count > 0:
        if not safe_commit("bulk_delete_invoices", {"count": deleted_count}):
            flash(_("Could not delete invoices due to a database error. Please check server logs."), "error")
            return redirect(url_for("invoices.list_invoices"))

    # Show appropriate messages
    if deleted_count > 0:
        flash(f'Successfully deleted {deleted_count} invoice{"s" if deleted_count != 1 else ""}', "success")

    if skipped_count > 0:
        flash(f'Skipped {skipped_count} invoice{"s" if skipped_count != 1 else ""}: {"; ".join(errors[:3])}', "warning")

    return redirect(url_for("invoices.list_invoices"))


@invoices_bp.route("/invoices/bulk-status", methods=["POST"])
@login_required
def bulk_update_status():
    """Update status for multiple invoices at once"""
    invoice_ids = request.form.getlist("invoice_ids[]")
    new_status = request.form.get("status", "").strip()
    invoice_reference = request.form.get("invoice_reference", "").strip()

    if not invoice_ids:
        flash(_("No invoices selected"), "warning")
        return redirect(url_for("invoices.list_invoices"))

    # Validate status
    valid_statuses = ["draft", "sent", "paid", "overdue", "cancelled"]
    if not new_status or new_status not in valid_statuses:
        flash(_("Invalid status value"), "error")
        return redirect(url_for("invoices.list_invoices"))

    updated_count = 0
    skipped_count = 0

    for invoice_id_str in invoice_ids:
        try:
            invoice_id = int(invoice_id_str)
            invoice = Invoice.query.get(invoice_id)

            if not invoice:
                continue

            # Check permissions
            if not current_user.is_admin and invoice.created_by != current_user.id:
                skipped_count += 1
                continue

            invoice.status = new_status

            # Auto-update payment status if marking as paid
            if new_status == "paid" and invoice.payment_status != "fully_paid":
                invoice.amount_paid = invoice.total_amount
                invoice.payment_status = "fully_paid"
                if not invoice.payment_date:
                    invoice.payment_date = datetime.utcnow().date()
                # Set invoice reference if provided
                if invoice_reference:
                    invoice.payment_reference = invoice_reference

            updated_count += 1

        except Exception:
            skipped_count += 1

    if updated_count > 0:
        if not safe_commit("bulk_update_invoice_status", {"count": updated_count, "status": new_status}):
            flash(_("Could not update invoices due to a database error"), "error")
            return redirect(url_for("invoices.list_invoices"))

        flash(
            f'Successfully updated {updated_count} invoice{"s" if updated_count != 1 else ""} to {new_status}',
            "success",
        )

    if skipped_count > 0:
        flash(f'Skipped {skipped_count} invoice{"s" if skipped_count != 1 else ""} (no permission)', "warning")

    return redirect(url_for("invoices.list_invoices"))


@invoices_bp.route("/invoices/<int:invoice_id>/generate-from-time", methods=["GET", "POST"])
@login_required
def generate_from_time(invoice_id):
    """Generate invoice items from time entries"""
    invoice = Invoice.query.get_or_404(invoice_id)

    # Check access permissions
    if not current_user.is_admin and invoice.created_by != current_user.id:
        flash(_("You do not have permission to edit this invoice"), "error")
        return redirect(url_for("invoices.list_invoices"))

    if request.method == "POST":
        # Get selected time entries, costs, expenses, and extra goods
        selected_entries = request.form.getlist("time_entries[]")
        selected_costs = request.form.getlist("project_costs[]")
        selected_expenses = request.form.getlist("expenses[]")
        selected_goods = request.form.getlist("extra_goods[]")

        if not selected_entries and not selected_costs and not selected_expenses and not selected_goods:
            flash(_("No time entries, costs, expenses, or extra goods selected"), "error")
            return redirect(url_for("invoices.generate_from_time", invoice_id=invoice.id))

        # Clear existing items
        invoice.items.delete()

        total_prepaid_allocated = Decimal("0")
        prepaid_allocator = None

        # Process time entries
        if selected_entries:
            # Group time entries by task/project and create invoice items
            time_entries = TimeEntry.query.filter(TimeEntry.id.in_(selected_entries)).all()

            prepaid_allocator = PrepaidHoursAllocator(client=invoice.client, invoice=invoice)
            processed_entries = prepaid_allocator.process(time_entries)
            total_prepaid_allocated = prepaid_allocator.total_prepaid_hours_assigned

            grouped_entries = {}
            for processed in processed_entries:
                if processed.billable_hours <= 0:
                    continue

                entry = processed.entry
                if entry.task_id:
                    key = f"task_{entry.task_id}"
                    description = f"Task: {entry.task.name if entry.task else 'Unknown Task'}"
                else:
                    key = f"project_{entry.project_id}"
                    description = f"Project: {entry.project.name}"

                if key not in grouped_entries:
                    grouped_entries[key] = {
                        "description": description,
                        "entries": [],
                        "total_hours": Decimal("0"),
                    }

                grouped_entries[key]["entries"].append(processed)
                grouped_entries[key]["total_hours"] += processed.billable_hours

            # Create invoice items from time entries
            for group in grouped_entries.values():
                if group["total_hours"] <= 0:
                    continue

                hourly_rate = RateOverride.resolve_rate(invoice.project)

                item = InvoiceItem(
                    invoice_id=invoice.id,
                    description=group["description"],
                    quantity=group["total_hours"],
                    unit_price=hourly_rate,
                    time_entry_ids=",".join(str(processed.entry.id) for processed in group["entries"]),
                )
                db.session.add(item)

        # Process project costs
        if selected_costs:
            costs = ProjectCost.query.filter(ProjectCost.id.in_(selected_costs)).all()

            for cost in costs:
                # Create invoice item for each cost
                item = InvoiceItem(
                    invoice_id=invoice.id,
                    description=f"{cost.description} ({cost.category.title()})",
                    quantity=1,  # Costs are typically a single unit
                    unit_price=cost.amount,
                )
                db.session.add(item)

                # Mark cost as invoiced
                cost.mark_as_invoiced(invoice.id)

        # Process expenses
        if selected_expenses:
            expenses = Expense.query.filter(Expense.id.in_(selected_expenses)).all()

            for expense in expenses:
                # Mark expense as invoiced (this links it to the invoice)
                expense.mark_as_invoiced(invoice.id)

        # Process extra goods from project
        if selected_goods:
            goods = ExtraGood.query.filter(ExtraGood.id.in_(selected_goods)).all()

            for good in goods:
                # Create a copy of the good for the invoice
                invoice_good = ExtraGood(
                    name=good.name,
                    description=good.description,
                    category=good.category,
                    quantity=good.quantity,
                    unit_price=good.unit_price,
                    sku=good.sku,
                    invoice_id=invoice.id,
                    created_by=current_user.id,
                    currency_code=good.currency_code,
                )
                db.session.add(invoice_good)

        # Calculate totals
        invoice.calculate_totals()
        if not safe_commit("generate_from_time", {"invoice_id": invoice.id}):
            flash(_("Could not generate items due to a database error. Please check server logs."), "error")
            return redirect(url_for("invoices.edit_invoice", invoice_id=invoice.id))

        # If invoice is already sent (not draft), mark time entries as paid
        if invoice.status != "draft":
            from app.services import InvoiceService
            invoice_service = InvoiceService()
            marked_count = invoice_service.mark_time_entries_as_paid(invoice)
            if marked_count > 0:
                safe_commit("mark_time_entries_paid_from_invoice", {"invoice_id": invoice.id})

        flash(_("Invoice items generated successfully from time entries and costs"), "success")
        if total_prepaid_allocated and total_prepaid_allocated > 0:
            flash(
                _(
                    "Applied %(hours)s prepaid hours for %(client)s before billing overages.",
                    hours=f"{total_prepaid_allocated:.2f}",
                    client=invoice.client_name,
                ),
                "info",
            )
        return redirect(url_for("invoices.edit_invoice", invoice_id=invoice.id))

    # GET request - show time entry and cost selection
    # Get unbilled time entries for this project
    time_entries = (
        TimeEntry.query.filter(
            TimeEntry.project_id == invoice.project_id, TimeEntry.end_time.isnot(None), TimeEntry.billable == True
        )
        .order_by(TimeEntry.start_time.asc())
        .all()
    )

    # Filter out entries already billed in other invoices
    unbilled_entries = []
    for entry in time_entries:
        # Check if this entry is already billed in another invoice
        already_billed = False
        for other_invoice in invoice.project.invoices:
            if other_invoice.id != invoice.id:
                for item in other_invoice.items:
                    if item.time_entry_ids and str(entry.id) in item.time_entry_ids.split(","):
                        already_billed = True
                        break
                if already_billed:
                    break

        if not already_billed:
            unbilled_entries.append(entry)

    # Get uninvoiced billable costs for this project
    unbilled_costs = ProjectCost.get_uninvoiced_costs(invoice.project_id)

    # Get uninvoiced billable expenses for this project
    unbilled_expenses = Expense.get_uninvoiced_expenses(project_id=invoice.project_id)

    # Get billable extra goods for this project (not yet on an invoice)
    project_goods = (
        ExtraGood.query.filter(
            ExtraGood.project_id == invoice.project_id, ExtraGood.invoice_id.is_(None), ExtraGood.billable == True
        )
        .order_by(ExtraGood.created_at.desc())
        .all()
    )

    # Group time entries by day for a clearer selection UI
    grouped_time_entries = []
    current_date = None
    current_bucket = None
    for entry in unbilled_entries:
        entry_date = entry.start_time.date() if entry.start_time else None
        if entry_date != current_date:
            current_date = entry_date
            current_bucket = {"date": current_date, "entries": [], "total_hours": 0.0}
            grouped_time_entries.append(current_bucket)
        current_bucket["entries"].append(entry)
        current_bucket["total_hours"] += float(entry.duration_hours or 0)

    # Calculate totals
    total_available_hours = sum(entry.duration_hours for entry in unbilled_entries)
    total_available_costs = sum(float(cost.amount) for cost in unbilled_costs)
    total_available_expenses = sum(float(expense.total_amount) for expense in unbilled_expenses)
    total_available_goods = sum(float(good.total_amount) for good in project_goods)

    prepaid_summary = []
    prepaid_plan_hours = None
    if invoice.client and invoice.client.prepaid_plan_enabled:
        allocator = PrepaidHoursAllocator(client=invoice.client)
        summaries = allocator.build_summary(unbilled_entries)
        prepaid_summary = []
        for summary in summaries:
            allocation_month = summary.allocation_month
            prepaid_summary.append(
                {
                    "allocation_month": allocation_month,
                    "allocation_month_label": allocation_month.strftime("%Y-%m-%d") if allocation_month else "",
                    "plan_hours": float(summary.plan_hours),
                    "consumed_hours": float(summary.consumed_hours),
                    "remaining_hours": float(summary.remaining_hours),
                }
            )
        prepaid_plan_hours = float(invoice.client.prepaid_hours_decimal)

    # Get currency from settings
    settings = Settings.get_settings()
    currency = settings.currency if settings else "USD"

    return render_template(
        "invoices/generate_from_time.html",
        invoice=invoice,
        time_entries=unbilled_entries,
        grouped_time_entries=grouped_time_entries,
        project_costs=unbilled_costs,
        expenses=unbilled_expenses,
        extra_goods=project_goods,
        total_available_hours=total_available_hours,
        total_available_costs=total_available_costs,
        total_available_expenses=total_available_expenses,
        total_available_goods=total_available_goods,
        currency=currency,
        prepaid_summary=prepaid_summary,
        prepaid_plan_hours=prepaid_plan_hours,
        prepaid_reset_day=invoice.client.prepaid_reset_day if invoice.client else None,
    )


@invoices_bp.route("/invoices/<int:invoice_id>/export/csv")
@login_required
def export_invoice_csv(invoice_id):
    """Export invoice as CSV"""
    invoice = Invoice.query.get_or_404(invoice_id)

    # Check access permissions
    if not current_user.is_admin and invoice.created_by != current_user.id:
        flash(_("You do not have permission to export this invoice"), "error")
        return redirect(url_for("invoices.list_invoices"))

    # Create CSV output
    output = io.StringIO()
    writer = csv.writer(output)

    # Write header
    writer.writerow(["Invoice Number", invoice.invoice_number])
    writer.writerow(["Client", invoice.client_name])
    writer.writerow(["Issue Date", invoice.issue_date.strftime("%Y-%m-%d")])
    writer.writerow(["Due Date", invoice.due_date.strftime("%Y-%m-%d")])
    writer.writerow(["Status", invoice.status])
    writer.writerow([])

    # Write items
    writer.writerow(["Description", "Quantity (Hours)", "Unit Price", "Total Amount"])
    for item in invoice.items:
        writer.writerow([item.description, float(item.quantity), float(item.unit_price), float(item.total_amount)])

    # Write expenses
    for expense in invoice.expenses:
        writer.writerow(
            [f"{expense.title} ({expense.category})", 1, float(expense.total_amount), float(expense.total_amount)]
        )

    # Write goods
    for good in invoice.extra_goods:
        writer.writerow([good.name, float(good.quantity), float(good.unit_price), float(good.total_amount)])

    writer.writerow([])
    writer.writerow(["Subtotal", "", "", float(invoice.subtotal)])
    writer.writerow(["Tax Rate", "", "", f"{float(invoice.tax_rate)}%"])
    writer.writerow(["Tax Amount", "", "", float(invoice.tax_amount)])
    writer.writerow(["Total Amount", "", "", float(invoice.total_amount)])

    output.seek(0)

    # Get invoice prefix from settings, default to "INV"
    settings = Settings.get_settings()
    prefix = getattr(settings, "invoice_prefix", "INV") if settings else "INV"
    if not prefix:
        prefix = "INV"
    filename = f"{prefix}_{invoice.invoice_number}.csv"

    return send_file(
        io.BytesIO(output.getvalue().encode("utf-8")), mimetype="text/csv", as_attachment=True, download_name=filename
    )


@invoices_bp.route("/invoices/<int:invoice_id>/export/ubl")
@login_required
def export_invoice_ubl(invoice_id):
    """Export invoice as PEPPOL UBL 2.1 XML. Requires sender and client PEPPOL ids."""
    invoice = Invoice.query.get_or_404(invoice_id)
    if not current_user.is_admin and invoice.created_by != current_user.id:
        flash(_("You do not have permission to export this invoice"), "error")
        return redirect(request.referrer or url_for("invoices.list_invoices"))
    try:
        from app.services.peppol_service import PeppolService
        from app.integrations.peppol import build_peppol_ubl_invoice_xml

        svc = PeppolService()
        sender = svc._get_sender_party()
        recipient_party, _ign, _ign = svc._get_recipient_party(invoice)
        ubl_xml, _ign = build_peppol_ubl_invoice_xml(invoice=invoice, supplier=sender, customer=recipient_party)
        fn = f"invoice_{invoice.invoice_number}.xml"
        return Response(ubl_xml, mimetype="application/xml", headers={"Content-Disposition": f"attachment; filename={fn}"})
    except ValueError as e:
        flash(_("Cannot generate UBL: %(msg)s", msg=str(e)), "error")
        return redirect(url_for("invoices.view_invoice", invoice_id=invoice_id))
    except Exception as e:
        current_app.logger.exception("UBL export failed for invoice %s", invoice_id)
        flash(_("UBL export failed: %(msg)s", msg=str(e)), "error")
        return redirect(url_for("invoices.view_invoice", invoice_id=invoice_id))


@invoices_bp.route("/invoices/<int:invoice_id>/export/pdf")
@login_required
def export_invoice_pdf(invoice_id):
    """Export invoice as PDF with optional page size selection"""
    current_app.logger.info(f"[PDF_EXPORT] Action: export_request, InvoiceID: {invoice_id}, User: {current_user.username}")
    
    invoice = Invoice.query.get_or_404(invoice_id)
    # Eager-load line item relationships so PDF generator has items, extra_goods, and expenses in session
    # (Invoice uses lazy="dynamic" so joinedload isn't applicable; trigger loads explicitly)
    _ = invoice.items.all() if hasattr(invoice.items, "all") else list(invoice.items) if invoice.items else []
    _ = invoice.extra_goods.all() if hasattr(invoice.extra_goods, "all") else list(invoice.extra_goods) if invoice.extra_goods else []
    if hasattr(invoice, "expenses"):
        _ = invoice.expenses.all() if hasattr(invoice.expenses, "all") else list(invoice.expenses) if invoice.expenses else []
    current_app.logger.info(f"[PDF_EXPORT] Invoice found: {invoice.invoice_number}, Status: {invoice.status}")

    if not current_user.is_admin and invoice.created_by != current_user.id:
        current_app.logger.warning(f"[PDF_EXPORT] Permission denied - InvoiceID: {invoice_id}, User: {current_user.username}")
        flash(_("You do not have permission to export this invoice"), "error")
        return redirect(request.referrer or url_for("invoices.list_invoices"))

    # Get page size from query parameter, default to A4
    page_size_raw = request.args.get("size", "A4")
    current_app.logger.info(f"[PDF_EXPORT] PageSize from query param: '{page_size_raw}', InvoiceID: {invoice_id}")

    # Validate page size
    valid_sizes = ["A4", "Letter", "Legal", "A3", "A5", "Tabloid"]
    if page_size_raw not in valid_sizes:
        current_app.logger.warning(f"[PDF_EXPORT] Invalid page size '{page_size_raw}', defaulting to A4, InvoiceID: {invoice_id}")
        page_size = "A4"
    else:
        page_size = page_size_raw

    current_app.logger.info(f"[PDF_EXPORT] Final validated PageSize: '{page_size}', InvoiceID: {invoice_id}, InvoiceNumber: {invoice.invoice_number}")

    try:
        from app.utils.pdf_generator import InvoicePDFGenerator

        settings = Settings.get_settings()
        current_app.logger.info(f"[PDF_EXPORT] Creating InvoicePDFGenerator - PageSize: '{page_size}', InvoiceID: {invoice_id}")
        pdf_generator = InvoicePDFGenerator(invoice, settings=settings, page_size=page_size)
        current_app.logger.info(f"[PDF_EXPORT] Starting PDF generation - PageSize: '{page_size}', InvoiceID: {invoice_id}")
        pdf_bytes = pdf_generator.generate_pdf()
        pdf_size_bytes = len(pdf_bytes)
        current_app.logger.info(f"[PDF_EXPORT] PDF generation completed successfully - PageSize: '{page_size}', InvoiceID: {invoice_id}, PDFSize: {pdf_size_bytes} bytes")
        # Filename should be template+date+number (invoice number format)
        filename = f"{invoice.invoice_number}.pdf"
        current_app.logger.info(f"[PDF_EXPORT] Returning PDF file - Filename: '{filename}', PageSize: '{page_size}', InvoiceID: {invoice_id}")
        return send_file(io.BytesIO(pdf_bytes), mimetype="application/pdf", as_attachment=True, download_name=filename)
    except Exception as e:
        import traceback

        current_app.logger.error(f"[PDF_EXPORT] Exception in PDF generation - PageSize: '{page_size}', InvoiceID: {invoice_id}, Error: {str(e)}", exc_info=True)
        try:
            current_app.logger.warning(f"[PDF_EXPORT] Falling back to InvoicePDFGeneratorFallback - PageSize: '{page_size}', InvoiceID: {invoice_id}")
            from app.utils.pdf_generator_fallback import InvoicePDFGeneratorFallback

            settings = Settings.get_settings()
            pdf_generator = InvoicePDFGeneratorFallback(invoice, settings=settings)
            pdf_bytes = pdf_generator.generate_pdf()
            pdf_size_bytes = len(pdf_bytes)
            current_app.logger.info(f"[PDF_EXPORT] Fallback PDF generated successfully - PageSize: '{page_size}', InvoiceID: {invoice_id}, PDFSize: {pdf_size_bytes} bytes")
            # Filename should be template+date+number (invoice number format)
            filename = f"{invoice.invoice_number}.pdf"
            return send_file(
                io.BytesIO(pdf_bytes), mimetype="application/pdf", as_attachment=True, download_name=filename
            )
        except Exception as fallback_error:
            current_app.logger.error(f"[PDF_EXPORT] Fallback PDF generation also failed - PageSize: '{page_size}', InvoiceID: {invoice_id}, Error: {str(fallback_error)}", exc_info=True)
            flash(
                _("PDF generation failed: %(err)s. Fallback also failed: %(fb)s", err=str(e), fb=str(fallback_error)),
                "error",
            )
            return redirect(request.referrer or url_for("invoices.view_invoice", invoice_id=invoice.id))


@invoices_bp.route("/invoices/<int:invoice_id>/duplicate")
@login_required
def duplicate_invoice(invoice_id):
    """Duplicate an existing invoice"""
    original_invoice = Invoice.query.get_or_404(invoice_id)

    # Check access permissions
    if not current_user.is_admin and original_invoice.created_by != current_user.id:
        flash(_("You do not have permission to duplicate this invoice"), "error")
        return redirect(url_for("invoices.list_invoices"))

    # Generate new invoice number
    new_invoice_number = Invoice.generate_invoice_number()

    # Create new invoice
    new_invoice = Invoice(
        invoice_number=new_invoice_number,
        project_id=original_invoice.project_id,
        client_name=original_invoice.client_name,
        client_email=original_invoice.client_email,
        client_address=original_invoice.client_address,
        buyer_reference=original_invoice.buyer_reference,
        due_date=original_invoice.due_date + timedelta(days=30),  # 30 days from original due date
        created_by=current_user.id,
        client_id=original_invoice.client_id,
        tax_rate=original_invoice.tax_rate,
        notes=original_invoice.notes,
        terms=original_invoice.terms,
        currency_code=original_invoice.currency_code,
    )

    db.session.add(new_invoice)
    if not safe_commit(
        "duplicate_invoice_create", {"source_invoice_id": original_invoice.id, "new_invoice_number": new_invoice_number}
    ):
        flash(_("Could not duplicate invoice due to a database error. Please check server logs."), "error")
        return redirect(url_for("invoices.list_invoices"))

    # Duplicate items
    for original_item in original_invoice.items:
        new_item = InvoiceItem(
            invoice_id=new_invoice.id,
            description=original_item.description,
            quantity=original_item.quantity,
            unit_price=original_item.unit_price,
        )
        db.session.add(new_item)

    # Duplicate extra goods
    for original_good in original_invoice.extra_goods:
        new_good = ExtraGood(
            name=original_good.name,
            description=original_good.description,
            category=original_good.category,
            quantity=original_good.quantity,
            unit_price=original_good.unit_price,
            sku=original_good.sku,
            invoice_id=new_invoice.id,
            created_by=current_user.id,
            currency_code=original_good.currency_code,
        )
        db.session.add(new_good)

    # Calculate totals
    new_invoice.calculate_totals()
    if not safe_commit("duplicate_invoice_finalize", {"invoice_id": new_invoice.id}):
        flash(_("Could not finalize duplicated invoice due to a database error. Please check server logs."), "error")
        return redirect(url_for("invoices.list_invoices"))

    flash(f"Invoice {new_invoice_number} created as duplicate", "success")
    return redirect(url_for("invoices.edit_invoice", invoice_id=new_invoice.id))


@invoices_bp.route("/invoices/export/excel")
@login_required
def export_invoices_excel():
    """Export invoice list as Excel file"""
    # Get invoices (scope by user unless admin)
    if current_user.is_admin:
        invoices = Invoice.query.order_by(Invoice.created_at.desc()).all()
    else:
        invoices = Invoice.query.filter_by(created_by=current_user.id).order_by(Invoice.created_at.desc()).all()

    # Create Excel file
    output, filename = create_invoices_list_excel(invoices)

    # Track Excel export event
    log_event("export.excel", user_id=current_user.id, export_type="invoices_list", num_rows=len(invoices))
    track_event(current_user.id, "export.excel", {"export_type": "invoices_list", "num_rows": len(invoices)})

    return send_file(
        output,
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        as_attachment=True,
        download_name=filename,
    )


@invoices_bp.route("/invoices/<int:invoice_id>/send-email", methods=["POST"])
@login_required
def send_invoice_email_route(invoice_id):
    """Send invoice via email"""
    invoice = Invoice.query.get_or_404(invoice_id)

    # Check access permissions
    if not current_user.is_admin and invoice.created_by != current_user.id:
        return jsonify({"error": "Permission denied"}), 403

    # Get recipient email from request
    recipient_email = (
        request.form.get("recipient_email", "").strip() or request.json.get("recipient_email", "").strip()
        if request.is_json
        else ""
    )

    if not recipient_email:
        # Try to use invoice client email
        recipient_email = invoice.client_email

    if not recipient_email:
        return jsonify({"error": "Recipient email address is required"}), 400

    # Get custom message if provided
    custom_message = request.form.get("custom_message", "").strip() or (
        request.json.get("custom_message", "").strip() if request.is_json else ""
    )

    # Get email template ID if provided
    email_template_id = request.form.get("email_template_id", type=int) or (
        request.json.get("email_template_id") if request.is_json else None
    )

    try:
        from app.utils.email import send_invoice_email

        success, invoice_email, message = send_invoice_email(
            invoice=invoice,
            recipient_email=recipient_email,
            sender_user=current_user,
            custom_message=custom_message if custom_message else None,
            email_template_id=email_template_id,
        )

        if success:
            flash(f"Invoice email sent successfully to {recipient_email}", "success")
            return jsonify(
                {"success": True, "message": message, "invoice_email_id": invoice_email.id if invoice_email else None}
            )
        else:
            return jsonify({"error": message}), 500

    except Exception as e:
        logger.error(f"Error sending invoice email: {type(e).__name__}: {str(e)}")
        logger.exception("Full error traceback:")
        return jsonify({"error": f"Failed to send email: {str(e)}"}), 500


@invoices_bp.route("/invoices/<int:invoice_id>/send-peppol", methods=["POST"])
@login_required
def send_invoice_peppol_route(invoice_id):
    """Send invoice via Peppol (requires configured access point)."""
    invoice = Invoice.query.get_or_404(invoice_id)

    # Check access permissions
    if not current_user.is_admin and invoice.created_by != current_user.id:
        return jsonify({"error": "Permission denied"}), 403

    try:
        from app.services import PeppolService

        service = PeppolService()
        success, tx, message = service.send_invoice(invoice=invoice, triggered_by_user_id=current_user.id)
        if success:
            flash(message, "success")
            return jsonify({"success": True, "message": message, "peppol_tx_id": tx.id if tx else None})
        return jsonify({"error": message, "peppol_tx_id": tx.id if tx else None}), 400
    except Exception as e:
        logger.error(f"Error sending invoice via Peppol: {type(e).__name__}: {str(e)}")
        logger.exception("Full error traceback:")
        return jsonify({"error": f"Failed to send via Peppol: {str(e)}"}), 500


@invoices_bp.route("/invoices/<int:invoice_id>/email-history", methods=["GET"])
@login_required
def get_invoice_email_history(invoice_id):
    """Get email history for an invoice"""
    invoice = Invoice.query.get_or_404(invoice_id)

    # Check access permissions
    if not current_user.is_admin and invoice.created_by != current_user.id:
        return jsonify({"error": "Permission denied"}), 403

    from app.models import InvoiceEmail

    # Get all email records for this invoice, ordered by most recent first
    email_records = InvoiceEmail.query.filter_by(invoice_id=invoice_id).order_by(InvoiceEmail.sent_at.desc()).all()

    # Convert to list of dictionaries
    email_history = [email.to_dict() for email in email_records]

    return jsonify({"success": True, "email_history": email_history, "count": len(email_history)})


@invoices_bp.route("/invoices/<int:invoice_id>/resend-email/<int:email_id>", methods=["POST"])
@login_required
def resend_invoice_email(invoice_id, email_id):
    """Resend an invoice email"""
    invoice = Invoice.query.get_or_404(invoice_id)

    # Check access permissions
    if not current_user.is_admin and invoice.created_by != current_user.id:
        return jsonify({"error": "Permission denied"}), 403

    from app.models import InvoiceEmail

    original_email = InvoiceEmail.query.get_or_404(email_id)

    # Verify the email belongs to this invoice
    if original_email.invoice_id != invoice_id:
        return jsonify({"error": "Email record does not belong to this invoice"}), 400

    # Get recipient email from request or use original
    recipient_email = (
        request.form.get("recipient_email", "").strip() or request.json.get("recipient_email", "").strip()
        if request.is_json
        else ""
    )
    if not recipient_email:
        recipient_email = original_email.recipient_email

    # Get custom message if provided
    custom_message = request.form.get("custom_message", "").strip() or (
        request.json.get("custom_message", "").strip() if request.is_json else ""
    )

    # Get email template ID if provided
    email_template_id = request.form.get("email_template_id", type=int) or (
        request.json.get("email_template_id") if request.is_json else None
    )

    try:
        from app.utils.email import send_invoice_email

        success, invoice_email, message = send_invoice_email(
            invoice=invoice,
            recipient_email=recipient_email,
            sender_user=current_user,
            custom_message=custom_message if custom_message else None,
            email_template_id=email_template_id,
        )

        if success:
            flash(f"Invoice email resent successfully to {recipient_email}", "success")
            return jsonify(
                {"success": True, "message": message, "invoice_email_id": invoice_email.id if invoice_email else None}
            )
        else:
            return jsonify({"error": message}), 500

    except Exception as e:
        logger.error(f"Error resending invoice email: {type(e).__name__}: {str(e)}")
        logger.exception("Full error traceback:")
        return jsonify({"error": f"Failed to resend email: {str(e)}"}), 500


@invoices_bp.route("/invoices/<int:invoice_id>/images/upload", methods=["POST"])
@login_required
def upload_invoice_image(invoice_id):
    """Upload a decorative image to an invoice"""
    from werkzeug.utils import secure_filename
    import os
    from datetime import datetime
    from decimal import Decimal

    invoice = Invoice.query.get_or_404(invoice_id)

    # Check permissions
    if not current_user.is_admin and invoice.created_by != current_user.id:
        if request.is_json:
            return jsonify({"error": "Permission denied"}), 403
        flash(_("You do not have permission to upload images to this invoice"), "error")
        return redirect(url_for("invoices.view_invoice", invoice_id=invoice_id))

    # File upload configuration - only images
    ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "gif", "webp"}
    UPLOAD_FOLDER = "app/static/uploads/invoice_images"
    MAX_FILE_SIZE = 5 * 1024 * 1024  # 5 MB

    def allowed_file(filename):
        return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS

    if "file" not in request.files:
        if request.is_json:
            return jsonify({"error": "No file provided"}), 400
        flash(_("No file provided"), "error")
        return redirect(url_for("invoices.edit_invoice", invoice_id=invoice_id))

    file = request.files["file"]
    if file.filename == "":
        if request.is_json:
            return jsonify({"error": "No file selected"}), 400
        flash(_("No file selected"), "error")
        return redirect(url_for("invoices.edit_invoice", invoice_id=invoice_id))

    if not allowed_file(file.filename):
        if request.is_json:
            return jsonify({"error": "File type not allowed. Only images (PNG, JPG, JPEG, GIF, WEBP) are allowed"}), 400
        flash(_("File type not allowed. Only images are allowed"), "error")
        return redirect(url_for("invoices.edit_invoice", invoice_id=invoice_id))

    # Check file size
    file.seek(0, os.SEEK_END)
    file_size = file.tell()
    file.seek(0)

    if file_size > MAX_FILE_SIZE:
        if request.is_json:
            return jsonify({"error": f"File size exceeds maximum allowed size ({MAX_FILE_SIZE / (1024*1024):.0f} MB)"}), 400
        flash(_("File size exceeds maximum allowed size (5 MB)"), "error")
        return redirect(url_for("invoices.edit_invoice", invoice_id=invoice_id))

    # Save file
    original_filename = secure_filename(file.filename)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{invoice_id}_{timestamp}_{original_filename}"

    # Ensure upload directory exists
    upload_dir = os.path.join(current_app.root_path, "..", UPLOAD_FOLDER)
    os.makedirs(upload_dir, exist_ok=True)

    file_path = os.path.join(upload_dir, filename)
    file.save(file_path)

    # Get file info
    mime_type = file.content_type or "image/png"
    
    # Get position from form (default to 0,0)
    position_x = Decimal(str(request.form.get("position_x", 0)))
    position_y = Decimal(str(request.form.get("position_y", 0)))
    width = Decimal(str(request.form.get("width", 0))) if request.form.get("width") else None
    height = Decimal(str(request.form.get("height", 0))) if request.form.get("height") else None
    opacity = Decimal(str(request.form.get("opacity", 1.0)))
    z_index = int(request.form.get("z_index", 0))

    # Create image record
    image = InvoiceImage(
        invoice_id=invoice_id,
        filename=filename,
        original_filename=original_filename,
        file_path=os.path.join(UPLOAD_FOLDER, filename),
        file_size=file_size,
        uploaded_by=current_user.id,
        mime_type=mime_type,
        position_x=position_x,
        position_y=position_y,
        width=width,
        height=height,
        opacity=opacity,
        z_index=z_index,
    )

    db.session.add(image)

    if not safe_commit("upload_invoice_image", {"invoice_id": invoice_id, "image_id": image.id}):
        if request.is_json:
            return jsonify({"error": "Database error"}), 500
        flash(_("Could not upload image due to a database error. Please check server logs."), "error")
        # Clean up uploaded file
        try:
            os.remove(file_path)
        except OSError:
            pass
        return redirect(url_for("invoices.edit_invoice", invoice_id=invoice_id))

    log_event(
        "invoice.image.uploaded",
        user_id=current_user.id,
        invoice_id=invoice_id,
        image_id=image.id,
        filename=original_filename,
    )
    track_event(
        current_user.id,
        "invoice.image.uploaded",
        {"invoice_id": invoice_id, "image_id": image.id, "filename": original_filename},
    )

    if request.is_json:
        return jsonify({"success": True, "image": image.to_dict()})
    
    flash(_("Image uploaded successfully"), "success")
    return redirect(url_for("invoices.edit_invoice", invoice_id=invoice_id))


@invoices_bp.route("/invoices/<int:invoice_id>/images/<int:image_id>/position", methods=["POST"])
@login_required
def update_invoice_image_position(invoice_id, image_id):
    """Update the position and properties of a decorative image"""
    from decimal import Decimal

    invoice = Invoice.query.get_or_404(invoice_id)
    image = InvoiceImage.query.filter_by(id=image_id, invoice_id=invoice_id).first_or_404()

    # Check permissions
    if not current_user.is_admin and invoice.created_by != current_user.id:
        return jsonify({"error": "Permission denied"}), 403

    # Get position data from request
    data = request.get_json() if request.is_json else request.form
    
    if "position_x" in data:
        image.position_x = Decimal(str(data["position_x"]))
    if "position_y" in data:
        image.position_y = Decimal(str(data["position_y"]))
    if "width" in data:
        image.width = Decimal(str(data["width"])) if data["width"] else None
    if "height" in data:
        image.height = Decimal(str(data["height"])) if data["height"] else None
    if "opacity" in data:
        image.opacity = Decimal(str(data["opacity"]))
    if "z_index" in data:
        image.z_index = int(data["z_index"])

    if not safe_commit("update_invoice_image_position", {"invoice_id": invoice_id, "image_id": image_id}):
        return jsonify({"error": "Database error"}), 500

    return jsonify({"success": True, "image": image.to_dict()})


@invoices_bp.route("/invoices/<int:invoice_id>/images/<int:image_id>/delete", methods=["POST"])
@login_required
def delete_invoice_image(invoice_id, image_id):
    """Delete a decorative image from an invoice"""
    import os

    invoice = Invoice.query.get_or_404(invoice_id)
    image = InvoiceImage.query.filter_by(id=image_id, invoice_id=invoice_id).first_or_404()

    # Check permissions
    if not current_user.is_admin and invoice.created_by != current_user.id:
        if request.is_json:
            return jsonify({"error": "Permission denied"}), 403
        flash(_("You do not have permission to delete images from this invoice"), "error")
        return redirect(url_for("invoices.edit_invoice", invoice_id=invoice_id))

    # Delete file from disk
    file_path = os.path.join(current_app.root_path, "..", image.file_path)
    if os.path.exists(file_path):
        try:
            os.remove(file_path)
        except OSError as e:
            current_app.logger.warning(f"Failed to delete image file {file_path}: {e}")

    image_id_for_log = image.id
    db.session.delete(image)

    if not safe_commit("delete_invoice_image", {"invoice_id": invoice_id, "image_id": image_id_for_log}):
        if request.is_json:
            return jsonify({"error": "Database error"}), 500
        flash(_("Could not delete image due to a database error. Please check server logs."), "error")
        return redirect(url_for("invoices.edit_invoice", invoice_id=invoice_id))

    log_event(
        "invoice.image.deleted",
        user_id=current_user.id,
        invoice_id=invoice_id,
        image_id=image_id_for_log,
    )
    track_event(
        current_user.id,
        "invoice.image.deleted",
        {"invoice_id": invoice_id, "image_id": image_id_for_log},
    )

    if request.is_json:
        return jsonify({"success": True})
    
    flash(_("Image deleted successfully"), "success")
    return redirect(url_for("invoices.edit_invoice", invoice_id=invoice_id))


@invoices_bp.route("/invoices/<int:invoice_id>/images/<int:image_id>/base64", methods=["GET"])
@login_required
def get_invoice_image_base64(invoice_id, image_id):
    """Get base64-encoded image for PDF embedding or serve image directly"""
    import os
    import base64
    import mimetypes
    from flask import send_file

    invoice = Invoice.query.get_or_404(invoice_id)
    image = InvoiceImage.query.filter_by(id=image_id, invoice_id=invoice_id).first_or_404()

    # Check permissions
    if not current_user.is_admin and invoice.created_by != current_user.id:
        return jsonify({"error": "Permission denied"}), 403

    file_path = os.path.join(current_app.root_path, "..", image.file_path)
    if not os.path.exists(file_path):
        return jsonify({"error": "File not found"}), 404

    # If request wants JSON (for API), return base64 data URI
    if request.args.get("format") == "json" or request.headers.get("Accept") == "application/json":
        try:
            with open(file_path, "rb") as img_file:
                image_data = base64.b64encode(img_file.read()).decode("utf-8")

            # Detect MIME type
            mime_type, _ = mimetypes.guess_type(file_path)
            if not mime_type:
                mime_type = image.mime_type or "image/png"

            return jsonify({
                "success": True,
                "data_uri": f"data:{mime_type};base64,{image_data}",
                "mime_type": mime_type,
            })
        except Exception as e:
            current_app.logger.error(f"Error reading image file: {e}")
            return jsonify({"error": "Error reading image file"}), 500
    
    # Otherwise, serve the image directly (for img src tags)
    try:
        mime_type, _ = mimetypes.guess_type(file_path)
        if not mime_type:
            mime_type = image.mime_type or "image/png"
        
        return send_file(file_path, mimetype=mime_type)
    except Exception as e:
        current_app.logger.error(f"Error serving image file: {e}")
        return jsonify({"error": "Error serving image file"}), 500
