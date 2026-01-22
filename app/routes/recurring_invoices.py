from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_babel import gettext as _
from flask_login import login_required, current_user
from app import db, log_event
from app.models import RecurringInvoice, Project, Client, Settings, Invoice
from datetime import datetime, timedelta
from decimal import Decimal
import logging
from app.utils.db import safe_commit
from app.utils.module_helpers import module_enabled

recurring_invoices_bp = Blueprint("recurring_invoices", __name__)
logger = logging.getLogger(__name__)


@recurring_invoices_bp.route("/recurring-invoices")
@login_required
@module_enabled("recurring_invoices")
def list_recurring_invoices():
    """List all recurring invoices"""
    # Get filter parameters
    is_active = request.args.get("is_active", "").strip()

    # Build query
    if current_user.is_admin:
        query = RecurringInvoice.query
    else:
        query = RecurringInvoice.query.filter_by(created_by=current_user.id)

    # Apply active filter
    if is_active == "true":
        query = query.filter_by(is_active=True)
    elif is_active == "false":
        query = query.filter_by(is_active=False)

    # Get recurring invoices
    recurring_invoices = query.order_by(RecurringInvoice.next_run_date.asc()).all()

    return render_template("recurring_invoices/list.html", recurring_invoices=recurring_invoices)


@recurring_invoices_bp.route("/recurring-invoices/create", methods=["GET", "POST"])
@login_required
@module_enabled("recurring_invoices")
def create_recurring_invoice():
    """Create a new recurring invoice"""
    if request.method == "POST":
        # Get form data
        name = request.form.get("name", "").strip()
        project_id = request.form.get("project_id", type=int)
        client_id = request.form.get("client_id", type=int)
        frequency = request.form.get("frequency", "").strip()
        interval = request.form.get("interval", type=int, default=1)
        next_run_date_str = request.form.get("next_run_date", "").strip()
        end_date_str = request.form.get("end_date", "").strip()
        client_name = request.form.get("client_name", "").strip()
        client_email = request.form.get("client_email", "").strip()
        client_address = request.form.get("client_address", "").strip()
        due_date_days = request.form.get("due_date_days", type=int, default=30)
        tax_rate = request.form.get("tax_rate", "0").strip()
        notes = request.form.get("notes", "").strip()
        terms = request.form.get("terms", "").strip()
        auto_send = request.form.get("auto_send") == "on"
        auto_include_time_entries = request.form.get("auto_include_time_entries") != "off"

        # Validate required fields
        if not name or not project_id or not client_id or not frequency or not next_run_date_str:
            flash(_("Name, project, client, frequency, and next run date are required"), "error")
            return render_template("recurring_invoices/create.html")

        try:
            next_run_date = datetime.strptime(next_run_date_str, "%Y-%m-%d").date()
        except ValueError:
            flash(_("Invalid next run date format"), "error")
            return render_template("recurring_invoices/create.html")

        end_date = None
        if end_date_str:
            try:
                end_date = datetime.strptime(end_date_str, "%Y-%m-%d").date()
            except ValueError:
                flash(_("Invalid end date format"), "error")
                return render_template("recurring_invoices/create.html")

        try:
            tax_rate = Decimal(tax_rate)
        except ValueError:
            flash(_("Invalid tax rate format"), "error")
            return render_template("recurring_invoices/create.html")

        # Get project and client
        project = Project.query.get(project_id)
        client = Client.query.get(client_id)
        if not project or not client:
            flash(_("Selected project or client not found"), "error")
            return render_template("recurring_invoices/create.html")

        # Get currency from settings
        settings = Settings.get_settings()
        currency_code = settings.currency if settings else "EUR"

        # Use client info if not provided
        if not client_name:
            client_name = client.name
        if not client_email:
            client_email = client.email

        # Create recurring invoice
        recurring = RecurringInvoice(
            name=name,
            project_id=project_id,
            client_id=client_id,
            frequency=frequency,
            next_run_date=next_run_date,
            created_by=current_user.id,
            interval=interval,
            end_date=end_date,
            client_name=client_name,
            client_email=client_email,
            client_address=client_address,
            due_date_days=due_date_days,
            tax_rate=tax_rate,
            notes=notes,
            terms=terms,
            currency_code=currency_code,
            auto_send=auto_send,
            auto_include_time_entries=auto_include_time_entries,
        )

        db.session.add(recurring)
        if not safe_commit("create_recurring_invoice", {"name": name, "project_id": project_id}):
            flash(_("Could not create recurring invoice due to a database error. Please check server logs."), "error")
            return render_template("recurring_invoices/create.html")

        flash(f'Recurring invoice "{name}" created successfully', "success")
        return redirect(url_for("recurring_invoices.list_recurring_invoices"))

    # GET request - show form
    projects = Project.query.filter_by(status="active", billable=True).order_by(Project.name).all()
    clients = Client.query.filter_by(status="active").order_by(Client.name).all()
    settings = Settings.get_settings()

    # Set default next run date to tomorrow
    default_next_run_date = (datetime.utcnow() + timedelta(days=1)).strftime("%Y-%m-%d")

    return render_template(
        "recurring_invoices/create.html",
        projects=projects,
        clients=clients,
        settings=settings,
        default_next_run_date=default_next_run_date,
    )


@recurring_invoices_bp.route("/recurring-invoices/<int:recurring_id>")
@login_required
@module_enabled("recurring_invoices")
def view_recurring_invoice(recurring_id):
    """View recurring invoice details"""
    recurring = RecurringInvoice.query.get_or_404(recurring_id)

    # Check access permissions
    if not current_user.is_admin and recurring.created_by != current_user.id:
        flash(_("You do not have permission to view this recurring invoice"), "error")
        return redirect(url_for("recurring_invoices.list_recurring_invoices"))

    # Get generated invoices
    generated_invoices = recurring.generated_invoices.order_by(Invoice.created_at.desc()).limit(10).all()

    return render_template("recurring_invoices/view.html", recurring=recurring, generated_invoices=generated_invoices)


@recurring_invoices_bp.route("/recurring-invoices/<int:recurring_id>/edit", methods=["GET", "POST"])
@login_required
@module_enabled("recurring_invoices")
def edit_recurring_invoice(recurring_id):
    """Edit recurring invoice"""
    recurring = RecurringInvoice.query.get_or_404(recurring_id)

    # Check access permissions
    if not current_user.is_admin and recurring.created_by != current_user.id:
        flash(_("You do not have permission to edit this recurring invoice"), "error")
        return redirect(url_for("recurring_invoices.list_recurring_invoices"))

    if request.method == "POST":
        # Update recurring invoice
        recurring.name = request.form.get("name", "").strip()
        recurring.frequency = request.form.get("frequency", "").strip()
        recurring.interval = request.form.get("interval", type=int, default=1)
        recurring.next_run_date = datetime.strptime(request.form.get("next_run_date"), "%Y-%m-%d").date()

        end_date_str = request.form.get("end_date", "").strip()
        recurring.end_date = datetime.strptime(end_date_str, "%Y-%m-%d").date() if end_date_str else None

        recurring.client_name = request.form.get("client_name", "").strip()
        recurring.client_email = request.form.get("client_email", "").strip()
        recurring.client_address = request.form.get("client_address", "").strip()
        recurring.due_date_days = request.form.get("due_date_days", type=int, default=30)
        recurring.tax_rate = Decimal(request.form.get("tax_rate", "0"))
        recurring.notes = request.form.get("notes", "").strip()
        recurring.terms = request.form.get("terms", "").strip()
        recurring.auto_send = request.form.get("auto_send") == "on"
        recurring.auto_include_time_entries = request.form.get("auto_include_time_entries") != "off"
        recurring.is_active = request.form.get("is_active") == "on"

        if not safe_commit("edit_recurring_invoice", {"recurring_id": recurring.id}):
            flash(_("Could not update recurring invoice due to a database error. Please check server logs."), "error")
            return render_template(
                "recurring_invoices/edit.html",
                recurring=recurring,
                projects=Project.query.filter_by(status="active").order_by(Project.name).all(),
                clients=Client.query.filter_by(status="active").order_by(Client.name).all(),
            )

        flash(_("Recurring invoice updated successfully"), "success")
        return redirect(url_for("recurring_invoices.view_recurring_invoice", recurring_id=recurring.id))

    # GET request - show edit form
    projects = Project.query.filter_by(status="active").order_by(Project.name).all()
    clients = Client.query.filter_by(status="active").order_by(Client.name).all()
    return render_template("recurring_invoices/edit.html", recurring=recurring, projects=projects, clients=clients)


@recurring_invoices_bp.route("/recurring-invoices/<int:recurring_id>/delete", methods=["POST"])
@login_required
@module_enabled("recurring_invoices")
def delete_recurring_invoice(recurring_id):
    """Delete recurring invoice"""
    recurring = RecurringInvoice.query.get_or_404(recurring_id)

    # Check access permissions
    if not current_user.is_admin and recurring.created_by != current_user.id:
        flash(_("You do not have permission to delete this recurring invoice"), "error")
        return redirect(url_for("recurring_invoices.list_recurring_invoices"))

    name = recurring.name
    db.session.delete(recurring)
    if not safe_commit("delete_recurring_invoice", {"recurring_id": recurring.id}):
        flash(_("Could not delete recurring invoice due to a database error. Please check server logs."), "error")
        return redirect(url_for("recurring_invoices.list_recurring_invoices"))

    flash(f'Recurring invoice "{name}" deleted successfully', "success")
    return redirect(url_for("recurring_invoices.list_recurring_invoices"))


@recurring_invoices_bp.route("/recurring-invoices/<int:recurring_id>/generate", methods=["POST"])
@login_required
@module_enabled("recurring_invoices")
def generate_invoice_now(recurring_id):
    """Manually generate an invoice from a recurring template"""
    recurring = RecurringInvoice.query.get_or_404(recurring_id)

    # Check access permissions
    if not current_user.is_admin and recurring.created_by != current_user.id:
        return jsonify({"error": "Permission denied"}), 403

    try:
        # Temporarily set next_run_date to today to allow generation
        original_next_run_date = recurring.next_run_date
        recurring.next_run_date = datetime.utcnow().date()

        invoice = recurring.generate_invoice()
        if invoice:
            db.session.commit()
            flash(f"Invoice {invoice.invoice_number} generated successfully", "success")
            return jsonify({"success": True, "invoice_id": invoice.id, "invoice_number": invoice.invoice_number})
        else:
            recurring.next_run_date = original_next_run_date
            return jsonify({"error": "Failed to generate invoice"}), 400

    except Exception as e:
        logger.error(f"Error generating invoice from recurring template: {e}")
        return jsonify({"error": str(e)}), 500
