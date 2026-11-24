import csv
import io
import json
import logging
import time
from datetime import date, datetime, timedelta
from decimal import Decimal, InvalidOperation

from flask import (
    Blueprint,
    Response,
    abort,
    current_app,
    flash,
    jsonify,
    make_response,
    redirect,
    render_template,
    request,
    send_file,
    url_for,
)
from flask_babel import gettext as _
from flask_login import current_user, login_required

from app import db, log_event, track_event
from app.models import (
    Expense,
    ExpenseCategory,
    ExtraGood,
    Invoice,
    InvoiceImage,
    InvoiceItem,
    PeppolInboundDocument,
    Project,
    ProjectCost,
    RateOverride,
    Settings,
    TimeEntry,
    User,
)
from app.utils.db import safe_commit
from app.utils.error_handling import DEFAULT_CLIENT_ERROR, client_error_payload, client_error_response
from app.utils.excel_export import create_invoices_list_excel
from app.utils.module_helpers import module_enabled
from app.utils.posthog_funnels import (
    track_invoice_generated,
    track_invoice_page_viewed,
    track_invoice_previewed,
    track_invoice_project_selected,
)
from app.utils.prepaid_hours import PrepaidHoursAllocator
from app.utils.safe_redirect import safe_redirect, safe_redirect_target

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
    page = request.args.get("page", 1, type=int)
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
        page=page,
    )

    # Filter params for pagination links (page is added by pagination_nav)
    pagination_url_params = {}
    if status:
        pagination_url_params["status"] = status
    if payment_status:
        pagination_url_params["payment_status"] = payment_status
    if search_query:
        pagination_url_params["search"] = search_query

    # Check if this is an AJAX request
    if request.headers.get("X-Requested-With") == "XMLHttpRequest":
        # Return only the invoices list HTML for AJAX requests
        response = make_response(
            render_template(
                "invoices/_invoices_list.html",
                invoices=result["invoices"],
                pagination=result["pagination"],
                pagination_url_params=pagination_url_params,
            )
        )
        response.headers["Content-Type"] = "text/html; charset=utf-8"
        return response

    return render_template(
        "invoices/list.html",
        invoices=result["invoices"],
        summary=result["summary"],
        pagination=result["pagination"],
        pagination_url_params=pagination_url_params,
    )


@invoices_bp.route("/projects/<int:project_id>/invoices")
@login_required
@module_enabled("invoices")
def project_invoices(project_id):
    """List the invoices of one project, with the same table as the Invoices page."""
    from app.services import InvoiceService
    from app.utils.scope_filter import user_can_access_project

    if not user_can_access_project(current_user, project_id):
        abort(403)
    project = Project.query.get_or_404(project_id)

    result = InvoiceService().list_invoices(
        project_id=project.id,
        user_id=current_user.id,
        is_admin=current_user.is_admin,
    )
    return render_template("invoices/project_list.html", project=project, invoices=result["invoices"])


@invoices_bp.route("/invoices/create", methods=["GET", "POST"])
@login_required
def create_invoice():
    """Create a new invoice. The page moved to step 1 (``/invoices/new``); posting here still works."""
    if request.method == "GET":
        return redirect(url_for("invoices.new_invoice", **request.args.to_dict()))
    if request.method == "POST":
        # Get form data
        project_id = request.form.get("project_id", type=int)
        client_name = request.form.get("client_name", "").strip()
        client_email = request.form.get("client_email", "").strip()
        client_address = request.form.get("client_address", "").strip()
        buyer_reference = (request.form.get("buyer_reference", "") or "").strip() or None
        vat_category = (request.form.get("vat_category", "") or "").strip().upper() or None
        if vat_category and vat_category not in ("S", "Z", "E", "AE", "K", "G", "O", "L", "M"):
            vat_category = None
        vat_exemption_reason = (request.form.get("vat_exemption_reason", "") or "").strip() or None
        vat_exemption_code = (request.form.get("vat_exemption_code", "") or "").strip() or None
        cig = (request.form.get("cig", "") or "").strip() or None
        cup = (request.form.get("cup", "") or "").strip() or None
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

        # Invoice-level discount (optional)
        try:
            discount_percent = Decimal(request.form.get("discount_percent", "0") or "0")
        except Exception:
            discount_percent = Decimal("0")
        try:
            discount_amount = Decimal(request.form.get("discount_amount", "0") or "0")
        except Exception:
            discount_amount = Decimal("0")

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
                        # User-supplied due_date invalid; keep calculated date from payment terms.
                        current_app.logger.debug(
                            "Ignoring invalid due_date %r; using quote payment-terms date",
                            due_date_str,
                            exc_info=True,
                        )

        # Currency is needed to check the payment account; resolved again below as before
        # Seller ("From") and payment account (optional Legal entities module)
        from app.utils import billing_entities as billing
        from app.utils.invoice_currency import normalize_currency_code as _norm_cur

        billing_entity = payment_account = None
        if billing.module_on():
            billing_entity, payment_account, billing_error = billing.resolve_from_form(
                request.form, _norm_cur(request.form.get("currency_code"))
            )
            if billing_error:
                flash(_(billing_error), "error")
                return redirect(url_for("invoices.create_invoice"))

        # Generate invoice number: typed by hand, else the entity's format, else the global series.
        # A number another invoice already has is an error on the form, not a silent "-2".
        invoice_number = None
        typed_number = (request.form.get("invoice_number", "") or "").strip()
        preview_number = (request.form.get("invoice_number_preview", "") or "").strip()
        if billing_entity:
            try:
                if typed_number and typed_number != preview_number:
                    billing.check_number(billing_entity, typed_number)
                    billing.claim_number(billing_entity, typed_number)
                    invoice_number = typed_number
                else:
                    invoice_number = billing.allocate_invoice_number(billing_entity)
            except billing.NumberTaken as taken:
                db.session.rollback()
                return _render_create_form(number_error=taken, form_due_date=due_date_str), 409
        if not invoice_number:
            invoice_number = Invoice.generate_invoice_number()
        _invoice_create_t0 = time.monotonic()

        # Track project selected for invoice
        track_invoice_project_selected(
            current_user.id, {"project_id": project_id, "has_email": bool(client_email), "has_tax": tax_rate > 0}
        )

        # Currency: chosen in the form, else the client's latest invoice currency, else settings
        from app.utils.invoice_currency import default_currency_for_client, normalize_currency_code

        settings = Settings.get_settings()
        currency_code = normalize_currency_code(request.form.get("currency_code")) or default_currency_for_client(
            project.client_id, settings
        )

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
            vat_category=vat_category,
            vat_exemption_reason=vat_exemption_reason,
            vat_exemption_code=vat_exemption_code,
            cig=cig,
            cup=cup,
            discount_percent=discount_percent,
            discount_amount=discount_amount,
        )
        if billing_entity:
            billing.apply_to_invoice(invoice, billing_entity, payment_account)

        # "Bill to" legal entity of the client (Client legal entities module)
        from app.utils import client_entities as bill_to

        if bill_to.module_on():
            bill_to_entity, bill_to_error = bill_to.resolve_from_form(request.form, project.client_id)
            if bill_to_error:
                flash(_(bill_to_error), "error")
                return redirect(url_for("invoices.create_invoice", project_id=project_id))
            bill_to.apply_to_invoice(invoice, bill_to_entity)

        db.session.add(invoice)
        if not safe_commit("create_invoice", {"invoice_number": invoice_number, "project_id": project_id}):
            flash(_("Could not create invoice due to a database error. Please check server logs."), "error")
            return render_template("invoices/create.html")

        from app.telemetry.otel_setup import business_span, record_invoice_created, record_invoice_duration_seconds

        with business_span(
            "invoice.create",
            user_id=current_user.id,
            source="web",
            has_tax=float(tax_rate) > 0,
            has_notes=bool(notes),
        ):
            pass
        record_invoice_created()
        record_invoice_duration_seconds(time.monotonic() - _invoice_create_t0, "create")

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

        from app.utils.workflow_bridge import fire_invoice_created_workflow

        fire_invoice_created_workflow(invoice, current_user.id)

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

    # GET request - show form
    return _render_create_form()


def _render_create_form(number_error=None, form_due_date=None):
    """The create form (projects scoped for subcontractors).

    After a rejected POST (``number_error``: the invoice number is taken) the form shows what was
    posted, with the error and "Use next free" under the number.
    """
    from app.utils.scope_filter import apply_project_scope_to_model

    projects_query = Project.query.filter_by(status="active", billable=True).order_by(Project.name)
    scope_p = apply_project_scope_to_model(Project, current_user)
    if scope_p is not None:
        projects_query = projects_query.filter(scope_p)
    projects = projects_query.all()
    settings = Settings.get_settings()
    # "New invoice" on a project's Invoices page passes ?project_id= to preselect it
    selected_project_id = request.args.get("project_id", type=int)
    if number_error is not None:
        selected_project_id = request.form.get("project_id", type=int)

    from app.utils.billing_entities import form_context as billing_form_context
    from app.utils.billing_entities import invoice_ref
    from app.utils.client_entities import form_context as bill_to_form_context
    from app.utils.invoice_currency import currency_choices, default_currencies_by_client, settings_currency
    from app.utils.invoice_defaults import DEFAULT_DUE_DAYS, client_defaults, due_date_for

    # Due date and terms follow the client's latest invoice; the form's script refills them per project
    defaults = client_defaults(sorted({p.client_id for p in projects if p.client_id}))
    selected = next((p for p in projects if p.id == selected_project_id), None)
    default_due_date = form_due_date or due_date_for(selected.client_id if selected else None).strftime("%Y-%m-%d")

    posted = None
    if number_error is not None:
        posted = {
            "number": number_error.number,
            "preview": (request.form.get("invoice_number_preview", "") or "").strip(),
            "taken": invoice_ref(number_error.owner),
            "next_free": number_error.next_free or "",
            "entity_id": request.form.get("billing_entity_id", type=int),
            "account_id": request.form.get("payment_account_id", type=int),
            "client_entity_id": request.form.get("client_entity_id", type=int),
        }

    return render_template(
        "invoices/create.html",
        projects=projects,
        settings=settings,
        default_due_date=default_due_date,
        invoice_defaults={
            "byClient": {str(k): v for k, v in defaults.items()},
            "settingsTerms": settings.invoice_terms or "",
            "defaultDays": DEFAULT_DUE_DAYS,
            "today": date.today().isoformat(),
        },
        posted=posted,
        currency_choices=currency_choices(settings),
        client_currencies=default_currencies_by_client(settings),
        default_currency=settings_currency(settings),
        selected_project_id=selected_project_id,
        **billing_form_context(projects, settings),
        **bill_to_form_context(projects),
    )


# ----------------------------------------------------------------------
# New invoice, step 1: who bills whom, number, period, projects, how hours become lines
# ----------------------------------------------------------------------
_STEP_ONE_VAT_CATEGORIES = ("S", "Z", "E", "AE", "K", "G", "O", "L", "M")


class _StepOneInput:
    """Step 1 values from the posted form or from the page's JSON request, read the same way."""

    def __init__(self, source):
        self.source = source or {}

    def get(self, name, default=""):
        value = self.source.get(name, default)
        if isinstance(value, list):
            value = value[0] if value else default
        return default if value is None else value

    def get_int(self, name):
        try:
            return int(str(self.get(name, "")).strip())
        except (TypeError, ValueError):
            return None

    def get_ids(self, name):
        raw = self.source.getlist(name) if hasattr(self.source, "getlist") else self.source.get(name)
        if raw is None:
            return []
        if not isinstance(raw, (list, tuple)):
            raw = [raw]
        ids = []
        for value in raw:
            try:
                number = int(str(value).strip())
            except (TypeError, ValueError):
                continue
            if number not in ids:
                ids.append(number)
        return ids

    def flag(self, name):
        return str(self.get(name, "")).strip().lower() in ("1", "true", "on", "yes")


def _step_one_projects_query():
    """Projects the user may invoice, as on the old create form (subcontractors: assigned ones only)."""
    from app.utils.scope_filter import apply_project_scope_to_model

    query = Project.query.filter(Project.client_id.isnot(None), Project.billable == True)  # noqa: E712
    scope = apply_project_scope_to_model(Project, current_user)
    return query.filter(scope) if scope is not None else query


def _step_one_clients():
    """Clients the user may invoice from step 1: those with at least one project the user can see."""
    from app.models import Client

    client_ids = _step_one_projects_query().with_entities(Project.client_id).distinct()
    return Client.query.filter(Client.id.in_(client_ids)).order_by(Client.name.asc()).all()


def _step_one_client(client_id):
    """The client, if the user may invoice it (sees at least one of its projects); else None."""
    from app.models import Client

    if not client_id:
        return None
    if _step_one_projects_query().filter(Project.client_id == client_id).first() is None:
        return None
    return Client.query.get(client_id)


def _step_one_selection(data, client, projects, invoice=None):
    """Hours part of step 1 as posted. Raises StepOneError for a wrong period.

    Projects the client does not have, or the user may not see, are dropped. Without the
    ``projects_touched`` flag (the page's first request for a client) the projects with hours in
    the period are selected, or only the one step 1 was opened from.
    """
    from app.services.invoice_step_one_service import InvoiceStepOneService, StepOneSelection, resolve_period
    from app.utils.invoice_currency import normalize_currency_code
    from app.utils.invoice_time_entry_items import normalize_layout

    period = resolve_period(data.get("period"), data.get("period_start"), data.get("period_end"))
    offered = [p.id for p in projects]
    from_project_id = data.get_int("from_project_id")
    allowed = _step_one_client_entries_allowed()
    if data.flag("projects_touched") or invoice is not None:
        project_ids = [pid for pid in data.get_ids("project_ids") if pid in offered]
        client_entries = data.flag("client_entries")
    else:
        by_project = InvoiceStepOneService().hours_by_project(client, offered, period, invoice, allowed)
        if from_project_id in offered:
            project_ids = [from_project_id]
        else:
            project_ids = [pid for pid in offered if by_project.get(pid, (0, 0))[1]] or offered[:1]
        client_entries = from_project_id not in offered and bool(by_project.get(None, (0, 0))[1])
    return StepOneSelection(
        client=client,
        project_ids=[pid for pid in offered if pid in project_ids],
        period=period,
        layout=normalize_layout(data.get("hours_layout")),
        template=(data.get("line_template") or None),
        client_entries=client_entries,
        currency=normalize_currency_code(data.get("currency_code")) or (invoice.currency_code if invoice else None),
        invoice=invoice,
        primary_project_id=from_project_id if invoice is None else invoice.project_id,
        client_entries_allowed=allowed,
    )


def _step_one_client_entries_allowed():
    """Whether the user may bill time logged on a client without a project.

    Not for a user limited to their own or assigned projects: that time is not theirs to see.
    """
    from app.utils.scope_filter import apply_project_scope_to_model

    return apply_project_scope_to_model(Project, current_user) is None


def _step_one_numbers(selection, issue_date):
    """{entity id: next number} for the selection's period and issue date (Legal entities module on)."""
    from app.services.invoice_step_one_service import InvoiceStepOneService
    from app.utils import billing_entities as billing

    if not billing.module_on():
        return {}
    period = InvoiceStepOneService().number_period(selection)
    return {str(e.id): billing.number_preview(e, issue_date, period=period) for e in billing.active_entities()}


def _step_one_header(data, client, period):
    """Invoice fields of step 1 as posted (all but the number, From and Bill to). Raises StepOneError."""
    from app.services.invoice_step_one_service import StepOneError
    from app.utils.invoice_currency import normalize_currency_code
    from app.utils.invoice_defaults import due_date_for

    def text(name):
        return (data.get(name) or "").strip()

    def day(name):
        value = text(name)
        if not value:
            return None
        try:
            return datetime.strptime(value, "%Y-%m-%d").date()
        except ValueError:
            raise StepOneError(_("Invalid date: %(value)s", value=value))

    try:
        tax_rate = Decimal(text("tax_rate") or "0")
    except (InvalidOperation, ValueError):
        raise StepOneError(_("Invalid tax rate format"))
    vat_category = text("vat_category").upper() or None
    if vat_category not in _STEP_ONE_VAT_CATEGORIES:
        vat_category = None
    issue_date = day("issue_date") or period.issue_date()
    due_date = day("due_date") or due_date_for(client.id, issue_date)
    if due_date < issue_date:
        raise StepOneError(_("The due date is before the issue date"))
    return {
        "client_name": text("client_name") or client.name,
        "client_email": text("client_email") or None,
        "client_address": text("client_address") or None,
        "buyer_reference": text("buyer_reference") or None,
        "vat_category": vat_category,
        "vat_exemption_reason": text("vat_exemption_reason") or None,
        "vat_exemption_code": text("vat_exemption_code") or None,
        "cig": text("cig") or None,
        "cup": text("cup") or None,
        "tax_rate": tax_rate,
        "notes": text("notes") or None,
        "terms": text("terms") or None,
        "issue_date": issue_date,
        "due_date": due_date,
        "currency_code": normalize_currency_code(data.get("currency_code")),
    }


def _parse_iso_day(value):
    try:
        return datetime.strptime((value or "").strip(), "%Y-%m-%d").date()
    except ValueError:
        return None


def _hours_label(value):
    return "%.2f" % Decimal(str(value or 0))


def _step_one_warning_texts(summary, currency):
    """Each warning of Before you create as a sentence, with its link or action."""
    from flask_babel import format_date, ngettext

    def day(value):
        try:
            return format_date(value, "medium")
        except Exception:
            return value.isoformat()

    out = []
    for w in summary.warnings:
        kind = w["kind"]
        item = {"kind": kind}
        if kind == "no_rate":
            if w.get("project_id"):
                target = " / ".join(part for part in (w.get("project"), w.get("person")) if part)
                item["link"] = {
                    "label": _("Set rate"),
                    "url": url_for("projects.list_rates", project_id=w["project_id"]),
                }
            else:
                # Logged on the client without a project: the client's default rate applies
                target = _("time logged on the client")
                if w.get("client_id"):
                    item["link"] = {
                        "label": _("Set client rate"),
                        "url": url_for("clients.edit_client", client_id=w["client_id"]),
                    }
            item["text"] = _(
                "No hourly rate for %(target)s: %(hours)s h will be billed at 0.", target=target, hours=w["hours"]
            )
        elif kind == "prepaid_used_up":
            item["text"] = _(
                "%(month)s plan used up on %(invoice)s: these hours are billed at the rate.",
                month=_prepaid_months_text([w["month"]]),
                invoice=w["used_on"],
            )
        elif kind == "prepaid_left":
            item["text"] = _(
                "%(month)s plan: %(left)s h left; %(covers)s h of these hours go to it first.",
                month=_prepaid_months_text([w["month"]]),
                left=_hours_label(w["left"]),
                covers=_hours_label(w["covers"]),
            )
        elif kind == "timer_running":
            item["text"] = ngettext(
                "A timer is running (%(people)s): that entry is not included.",
                "%(num)d timers are running (%(people)s): those entries are not included.",
                w["entries"],
                people=", ".join(w["people"]),
            )
        elif kind == "before_period":
            item["text"] = _(
                "%(hours)s h unbilled before the period, since %(since)s.",
                hours=_hours_label(w["hours"]),
                since=day(w["since"]),
            )
            item["action"] = {"label": _("Include them"), "start": w["since"].isoformat()}
        elif kind == "other_projects":
            names = [p["name"] or _("time logged on the client") for p in w["projects"]]
            item["text"] = _(
                "%(hours)s h in this period on what is not selected: %(names)s.",
                hours=_hours_label(w["hours"]),
                names=", ".join(names),
            )
        elif kind == "after_period":
            item["text"] = ngettext(
                "%(num)d entry (%(hours)s h) after the period, until %(until)s.",
                "%(num)d entries (%(hours)s h) after the period, until %(until)s.",
                w["entries"],
                hours=_hours_label(w["hours"]),
                until=day(w["until"]),
            )
        elif kind == "non_billable":
            item["text"] = ngettext(
                "%(num)d non-billable entry (%(hours)s h) in this period stays off the invoice.",
                "%(num)d non-billable entries (%(hours)s h) in this period stay off the invoice.",
                w["entries"],
                hours=_hours_label(w["hours"]),
            )
        elif kind == "manual_lines":
            item["text"] = ngettext(
                "%(num)d line added by hand. Saving step 1 keeps it unless you remove it.",
                "%(num)d lines added by hand. Saving step 1 keeps them unless you remove them.",
                len(w["lines"]),
            )
            item["lines"] = [
                {
                    "id": line["id"],
                    "text": "%s – %s %s" % (line["description"], "%.2f" % line["amount"], currency or ""),
                }
                for line in w["lines"]
            ]
        else:
            continue
        out.append(item)
    return out


def _step_one_parts(selection, projects, summary, remove_line_ids=()):
    """The step 1 blocks that follow the selection, rendered: projects, hours, warnings, summary."""
    from app.services.invoice_step_one_service import InvoiceStepOneService

    primary = InvoiceStepOneService.primary_project(selection, projects)
    remove = set(remove_line_ids or ())
    context = {
        "remove_line_ids": remove,
        "invoice": selection.invoice,
        "primary_id": primary.id if primary is not None else "",
        "selection": selection,
        "summary": summary,
        "projects": projects,
        "warnings": _step_one_warning_texts(summary, selection.currency),
        "currency": selection.currency or "",
        "hours_label": _hours_label,
        "prepaid_month": lambda month: _prepaid_months_text([month]),
    }
    return {
        "projects": render_template("invoices/_step1_projects.html", **context),
        "hours": render_template("invoices/_step1_hours.html", **context),
        "warnings": render_template("invoices/_step1_warnings.html", **context),
        "summary": render_template("invoices/_step1_summary.html", **context),
    }


def _step_one_payload(selection, projects, summary, remove_line_ids=()):
    period = summary.period
    examples = {}
    for layout, info in summary.examples.items():
        if layout == "none":
            examples[layout] = _("No hours lines")
        elif info["lines"]:
            examples[layout] = info["example"] + (
                "\n" + _("%(count)s lines in all", count=info["lines"]) if info["lines"] > 1 else ""
            )
        else:
            examples[layout] = ""
    return {
        "html": _step_one_parts(selection, projects, summary, remove_line_ids),
        "project_ids": selection.project_ids,
        "client_entries": selection.client_entries,
        "period": {
            "kind": period.kind,
            "start": period.start.isoformat() if period.start else "",
            "end": period.end.isoformat() if period.end else "",
            "issue_date": period.issue_date().isoformat(),
        },
        "layout": summary.layout,
        "template": summary.template,
        "examples": examples,
        "lines": summary.lines,
        "hours": _hours_label(summary.tracked_hours),
    }


def _step_one_values(form=None, invoice=None):
    """Field values the step 1 page starts with: as posted, else from the draft, else empty."""
    names = (
        "client_name",
        "client_email",
        "client_address",
        "buyer_reference",
        "vat_category",
        "vat_exemption_reason",
        "vat_exemption_code",
        "cig",
        "cup",
        "tax_rate",
        "notes",
        "terms",
        "issue_date",
        "due_date",
        "currency_code",
        "invoice_number",
    )
    if form is not None:
        return {name: (form.get(name) or "") for name in names}
    if invoice is None:
        return {name: "" for name in names}
    values = {name: "" if getattr(invoice, name, None) is None else str(getattr(invoice, name)) for name in names}
    values["issue_date"] = invoice.issue_date.isoformat() if invoice.issue_date else ""
    values["due_date"] = invoice.due_date.isoformat() if invoice.due_date else ""
    values["tax_rate"] = str(invoice.tax_rate if invoice.tax_rate is not None else "")
    return values


def _step_one_projects_by_client(clients):
    """{client_id: [projects the user can see]}, in one query."""
    ids = [c.id for c in clients]
    if not ids:
        return {}
    out = {}
    query = _step_one_projects_query().filter(Project.client_id.in_(ids))
    for project in query.order_by(Project.name.asc(), Project.id.asc()).all():
        out.setdefault(project.client_id, []).append(project)
    return out


def _render_step_one(invoice=None, selection=None, form=None, number_error=None, status=200):
    """The step 1 page, for a new invoice or for a draft (``invoice``).

    ``form``: what was posted, shown again after an error; ``number_error``: the number is taken.
    """
    from app.services.invoice_step_one_service import InvoiceStepOneService, StepOneError, resolve_period
    from app.utils.billing_entities import form_context as billing_form_context
    from app.utils.billing_entities import invoice_ref
    from app.utils.client_entities import form_context as bill_to_form_context
    from app.utils.invoice_currency import currency_choices, default_currencies_by_client, settings_currency
    from app.utils.invoice_defaults import DEFAULT_DUE_DAYS, client_defaults, due_date_for
    from app.utils.invoice_time_entry_items import DEFAULT_LINE_TEMPLATES, HOURS_LAYOUT_LABELS, HOURS_LAYOUTS

    service = InvoiceStepOneService()
    settings = Settings.get_settings()
    data = _StepOneInput(form if form is not None else request.args)
    if invoice is not None:
        client = invoice.client
        clients = [client]
        if selection is None:
            selection = service.draft_selection(invoice)
    else:
        clients = _step_one_clients()
        from_project_id = data.get_int("from_project_id") or data.get_int("project_id")
        from_project = Project.query.get(from_project_id) if from_project_id else None
        client_id = data.get_int("client_id") or (from_project.client_id if from_project else None)
        client = next((c for c in clients if c.id == client_id), None)
    projects_by_client = _step_one_projects_by_client(clients)
    projects = service.client_projects(client, current_user, invoice) if client is not None else []

    if client is not None and selection is None:
        source = {key: data.source.getlist(key) for key in data.source} if hasattr(data.source, "getlist") else {}
        if invoice is None and from_project is not None and from_project.client_id == client.id:
            source["from_project_id"] = [str(from_project.id)]
        try:
            selection = _step_one_selection(_StepOneInput(source), client, projects)
        except StepOneError:
            selection = _step_one_selection(_StepOneInput({}), client, projects)
    remove_line_ids = data.get_ids("remove_line_ids") if form is not None else []
    parts = (
        _step_one_parts(selection, projects, service.summary(selection, projects, remove_line_ids), remove_line_ids)
        if selection
        else None
    )

    posted = None
    if number_error is not None:
        posted = {
            "number": number_error.number,
            "preview": (form.get("invoice_number_preview", "") or "").strip(),
            "taken": invoice_ref(number_error.owner),
            "next_free": number_error.next_free or "",
            "entity_id": form.get("billing_entity_id", type=int),
            "account_id": form.get("payment_account_id", type=int),
            "client_entity_id": form.get("client_entity_id", type=int),
        }
    primary = service.primary_project(selection, projects) if selection is not None else None
    # The From / Pay to and Bill to blocks follow #project_id (the invoice's own project), which the
    # page's script keeps in step with the client and the selected projects
    form_projects = [invoice.project] if invoice is not None else [p for ps in projects_by_client.values() for p in ps]
    defaults = client_defaults([c.id for c in clients])
    values = _step_one_values(form, invoice)
    # Dates typed or saved stay; the page's script moves the others with the period
    dates_touched = {name: invoice is not None or bool(values[name]) for name in ("issue_date", "due_date")}
    if client is not None and selection is not None:
        # Issue date: the last day of the period; due date: as many days later as on the client's last invoice
        issued = _parse_iso_day(values["issue_date"]) or selection.period.issue_date()
        values["issue_date"] = values["issue_date"] or issued.isoformat()
        values["due_date"] = values["due_date"] or due_date_for(client.id, issued).isoformat()
    number_issue = _parse_iso_day(values["issue_date"])
    number_period = service.number_period(selection) if selection is not None else None
    return (
        render_template(
            "invoices/new.html",
            invoice=invoice,
            clients=clients,
            client=client,
            projects=projects,
            selection=selection,
            period=selection.period if selection is not None else resolve_period(None),
            primary_project=primary,
            parts=parts,
            values=values,
            dates_touched=dates_touched,
            posted=posted,
            settings=settings,
            currency_choices=currency_choices(settings, extra=[invoice.currency_code] if invoice else ()),
            client_currencies={str(k): v for k, v in default_currencies_by_client(settings).items()},
            default_currency=settings_currency(settings),
            client_details={
                str(c.id): {
                    "name": c.name or "",
                    "email": c.email or "",
                    "address": c.address or "",
                    "project": (projects_by_client.get(c.id) or [None])[0].id if projects_by_client.get(c.id) else None,
                }
                for c in clients
            },
            invoice_defaults={
                "byClient": {str(k): v for k, v in defaults.items()},
                "settingsTerms": settings.invoice_terms or "",
                "defaultDays": DEFAULT_DUE_DAYS,
                "today": date.today().isoformat(),
            },
            hours_layouts=[(layout, HOURS_LAYOUT_LABELS[layout]) for layout in HOURS_LAYOUTS],
            default_line_templates=DEFAULT_LINE_TEMPLATES,
            **billing_form_context(form_projects, settings, issue_date=number_issue, period=number_period),
            **bill_to_form_context(form_projects, invoice=invoice),
        ),
        status,
    )


@invoices_bp.route("/invoices/new", methods=["GET", "POST"])
@login_required
def new_invoice():
    """Step 1 of a new invoice: who bills whom, number, period, projects and how hours become lines.

    Creating it makes a draft with its hours lines in one transaction; the draft page is next.
    ``?client_id=`` preselects a client, ``?project_id=`` a client and only that project.
    """
    if request.method == "GET":
        return _render_step_one()

    from app.services.invoice_step_one_service import InvoiceStepOneService, StepOneError
    from app.services.invoice_time_service import InvoiceTimeError
    from app.utils import billing_entities as billing
    from app.utils import client_entities as bill_to

    form = request.form
    data = _StepOneInput(form)
    service = InvoiceStepOneService()
    client = _step_one_client(data.get_int("client_id"))
    if client is None:
        flash(_("Choose a client"), "error")
        return _render_step_one(form=form, status=400)
    projects = service.client_projects(client, current_user)
    try:
        selection = _step_one_selection(data, client, projects)
        header = _step_one_header(data, client, selection.period)
    except StepOneError as exc:
        flash(str(exc), "error")
        return _render_step_one(form=form, status=400)
    primary = service.primary_project(selection, projects)
    if primary is None:
        flash(_("Select at least one project: the invoice needs one"), "error")
        return _render_step_one(form=form, selection=selection, status=400)

    settings = Settings.get_settings()
    from app.utils.invoice_currency import default_currency_for_client

    currency_code = header.pop("currency_code") or default_currency_for_client(client.id, settings)
    selection.currency = currency_code
    _t0 = time.monotonic()

    billing_entity = payment_account = None
    if billing.module_on():
        billing_entity, payment_account, billing_error = billing.resolve_from_form(form, currency_code)
        if billing_error:
            flash(_(billing_error), "error")
            return _render_step_one(form=form, selection=selection, status=400)

    # The number: typed by hand, else the entity's format, else the global series. A number another
    # invoice already has is an error here, never a silent "-2".
    # {YYYY} and {MM} are the month the invoice bills, {DD} its issue day
    invoice_number = None
    typed_number = (form.get("invoice_number", "") or "").strip()
    preview_number = (form.get("invoice_number_preview", "") or "").strip()
    issue_date = header["issue_date"]
    number_period = service.number_period(selection)
    try:
        if billing_entity:
            if typed_number and typed_number != preview_number:
                billing.check_number(billing_entity, typed_number, issue_date, period=number_period)
                billing.claim_number(billing_entity, typed_number, issue_date, period=number_period)
                invoice_number = typed_number
            else:
                invoice_number = billing.allocate_invoice_number(billing_entity, issue_date, period=number_period)
    except billing.NumberTaken as taken:
        db.session.rollback()
        return _render_step_one(form=form, selection=selection, number_error=taken, status=409)
    if not invoice_number:
        invoice_number = Invoice.generate_invoice_number()

    invoice = Invoice(
        invoice_number=invoice_number,
        project_id=primary.id,
        client_name=header.pop("client_name"),
        due_date=header.pop("due_date"),
        created_by=current_user.id,
        client_id=client.id,
        quote_id=getattr(primary, "quote_id", None),
        currency_code=currency_code,
        **header,
    )
    invoice.period_start = selection.period.start
    invoice.period_end = selection.period.end
    if billing_entity:
        billing.apply_to_invoice(invoice, billing_entity, payment_account)
    if bill_to.module_on():
        bill_to_entity, bill_to_error = bill_to.resolve_from_form(form, client.id)
        if bill_to_error:
            db.session.rollback()
            flash(_(bill_to_error), "error")
            return _render_step_one(form=form, selection=selection, status=400)
        bill_to.apply_to_invoice(invoice, bill_to_entity)

    db.session.add(invoice)
    try:
        db.session.flush()
        lines = service.add_hours(invoice, selection, projects, current_user.id)
    except InvoiceTimeError as exc:
        db.session.rollback()
        flash(_("Could not add the time entries: %(error)s", error=str(exc)), "error")
        return _render_step_one(form=form, selection=selection, status=409)
    invoice.calculate_totals()
    if not safe_commit("new_invoice_step_one", {"invoice_number": invoice_number, "client_id": client.id}):
        flash(_("Could not create invoice due to a database error. Please check server logs."), "error")
        return _render_step_one(form=form, selection=selection, status=500)

    _announce_new_invoice(invoice, _t0)
    count = len(lines.items) if lines is not None else 0
    flash(_("Draft %(number)s created with %(count)s lines", number=invoice.invoice_number, count=count), "success")
    return redirect(url_for("invoices.view_invoice", invoice_id=invoice.id))


def _announce_new_invoice(invoice, started):
    """What creating an invoice also does: metrics, analytics, workflows and the client's notification."""
    from app.telemetry.otel_setup import business_span, record_invoice_created, record_invoice_duration_seconds
    from app.utils.workflow_bridge import fire_invoice_created_workflow

    has_tax = float(invoice.tax_rate or 0) > 0
    with business_span(
        "invoice.create", user_id=current_user.id, source="web", has_tax=has_tax, has_notes=bool(invoice.notes)
    ):
        pass
    record_invoice_created()
    record_invoice_duration_seconds(time.monotonic() - started, "create")
    track_invoice_generated(
        current_user.id,
        {
            "invoice_id": invoice.id,
            "invoice_number": invoice.invoice_number,
            "has_tax": has_tax,
            "has_notes": bool(invoice.notes),
        },
    )
    fire_invoice_created_workflow(invoice, current_user.id)
    if invoice.client_id:
        try:
            from app.services.client_notification_service import ClientNotificationService

            ClientNotificationService().notify_invoice_created(invoice.id, invoice.client_id)
        except Exception as e:
            logger.error(f"Failed to send client notification for invoice {invoice.id}: {e}", exc_info=True)


@invoices_bp.route("/invoices/<int:invoice_id>/step-1", methods=["GET", "POST"])
@login_required
def edit_step_one(invoice_id):
    """Step 1 of a draft, every field filled from the invoice.

    Saving with another period, other projects, another layout or template lets go of the draft's
    hours and collects them again (hours lines are rebuilt, lines added by hand stay, non-billable
    marks stay). Saving with only the header changed leaves the lines as they are.
    """
    from flask_babel import ngettext

    from app.services.invoice_step_one_service import InvoiceStepOneService, StepOneError
    from app.services.invoice_time_service import InvoiceTimeError, InvoiceTimeService
    from app.utils import billing_entities as billing
    from app.utils import client_entities as bill_to

    invoice = Invoice.query.get_or_404(invoice_id)
    if not current_user.is_admin and invoice.created_by != current_user.id:
        flash(_("You do not have permission to edit this invoice"), "error")
        return redirect(url_for("invoices.list_invoices"))
    if invoice.status != "draft":
        flash(
            _(
                "Invoice %(number)s is %(status)s: only a draft goes back to step 1.",
                number=invoice.invoice_number,
                status=invoice.status,
            ),
            "error",
        )
        return redirect(url_for("invoices.view_invoice", invoice_id=invoice.id))
    if request.method == "GET":
        return _render_step_one(invoice)

    form = request.form
    data = _StepOneInput(form)
    service = InvoiceStepOneService()
    client = invoice.client
    projects = service.client_projects(client, current_user, invoice)
    try:
        selection = _step_one_selection(data, client, projects, invoice)
        header = _step_one_header(data, client, selection.period)
    except StepOneError as exc:
        flash(str(exc), "error")
        return _render_step_one(invoice, form=form, status=400)
    primary = service.primary_project(selection, projects)
    if primary is None:
        flash(_("Select at least one project: the invoice needs one"), "error")
        return _render_step_one(invoice, selection=selection, form=form, status=400)
    before = service.draft_selection(invoice)

    # The number may change on a draft; another invoice's number is refused. {YYYY} and {MM} are
    # the month the invoice bills and {DD} its issue day, as for a new invoice
    typed_number = (form.get("invoice_number", "") or "").strip()
    if typed_number and typed_number != invoice.invoice_number:
        entity = invoice.billing_entity if invoice.billing_entity_id else None
        posted_entity_id = form.get("billing_entity_id", type=int)
        if billing.module_on() and posted_entity_id and posted_entity_id != invoice.billing_entity_id:
            from app.models import BillingEntity

            entity = BillingEntity.query.get(posted_entity_id) or entity
        issue_date = header["issue_date"]
        number_period = service.number_period(selection)
        owner = billing.number_owner(typed_number, exclude_invoice_id=invoice.id)
        if owner is not None:
            offer = (
                billing.next_free_number(entity, issue_date, typed_number, period=number_period)
                if entity is not None
                else billing.unique_number(typed_number, invoice.id)
            )
            return _render_step_one(
                invoice,
                selection=selection,
                form=form,
                number_error=billing.NumberTaken(typed_number, owner, offer),
                status=409,
            )
        if entity is not None:
            billing.claim_number(entity, typed_number, issue_date, period=number_period)
        invoice.invoice_number = typed_number

    currency_code = header.pop("currency_code") or invoice.currency_code
    currency_changed = currency_code != invoice.currency_code
    selection.currency = currency_code
    invoice.currency_code = currency_code
    for name, value in header.items():
        setattr(invoice, name, value)
    if billing.module_on() and "billing_entity_id" in form:
        billing_entity, payment_account, billing_error = billing.resolve_from_form(form, currency_code)
        if billing_error:
            db.session.rollback()
            flash(_(billing_error), "error")
            return _render_step_one(invoice, selection=selection, form=form, status=400)
        billing.apply_to_invoice(invoice, billing_entity, payment_account)
    if bill_to.module_on() and "client_entity_id" in form:
        bill_to_entity, bill_to_error = bill_to.resolve_from_form(form, invoice.client_id, invoice.client_entity_id)
        if bill_to_error:
            db.session.rollback()
            flash(_(bill_to_error), "error")
            return _render_step_one(invoice, selection=selection, form=form, status=400)
        bill_to.apply_to_invoice(invoice, bill_to_entity)

    invoice.project_id = primary.id
    collected = service.hours_changed(before, selection)
    try:
        removed = service.remove_manual_lines(invoice, data.get_ids("remove_line_ids"))
        if collected:
            lines = service.recollect(invoice, selection, projects, current_user.id)
        else:
            # Same hours: the lines stay; a draft made before step 1 keeps the period it was shown
            invoice.period_start = selection.period.start
            invoice.period_end = selection.period.end
            if currency_changed:
                # Hours lines name their rate with the currency ("- 40.00 EUR/h"): write them again
                InvoiceTimeService().apply_template(invoice, invoice.line_template, keep_edited=True)
            invoice.calculate_totals()
    except InvoiceTimeError as exc:
        db.session.rollback()
        flash(_("Could not add the time entries: %(error)s", error=str(exc)), "error")
        return _render_step_one(invoice, selection=selection, form=form, status=409)
    if not safe_commit("edit_step_one", {"invoice_id": invoice.id}):
        flash(_("Could not update invoice due to a database error. Please check server logs."), "error")
        return _render_step_one(invoice, selection=selection, form=form, status=500)

    if collected:
        count = len(lines.items) if lines is not None else 0
        flash(_("Hours collected again: %(count)s lines", count=count), "success")
    elif removed:
        flash(_("Invoice details saved; the hours lines did not change"), "success")
    else:
        flash(_("Invoice details saved; the lines did not change"), "success")
    if removed:
        flash(ngettext("%(num)d line added by hand removed", "%(num)d lines added by hand removed", removed), "success")
    return redirect(url_for("invoices.view_invoice", invoice_id=invoice.id))


@invoices_bp.route("/invoices/step-1/summary", methods=["POST"])
@login_required
def step_one_summary():
    """What step 1 shows below the period, for the page's choices (JSON in, JSON with HTML parts out).

    Body: ``client_id`` (or ``invoice_id`` for a draft's step 1), ``period``, ``period_start``,
    ``period_end``, ``project_ids``, ``projects_touched``, ``client_entries``, ``from_project_id``,
    ``hours_layout``, ``line_template``, ``currency_code``. Nothing is written.
    """
    from app.services.invoice_step_one_service import InvoiceStepOneService, StepOneError

    data = _StepOneInput(request.get_json(silent=True) or {})
    service = InvoiceStepOneService()
    invoice = None
    invoice_id = data.get_int("invoice_id")
    if invoice_id:
        invoice = Invoice.query.get_or_404(invoice_id)
        if not current_user.is_admin and invoice.created_by != current_user.id:
            return jsonify({"error": "forbidden"}), 403
        if invoice.status != "draft":
            return jsonify({"error": "invalid_status"}), 409
        client = invoice.client
    else:
        client = _step_one_client(data.get_int("client_id"))
        if client is None:
            return jsonify({"error": "forbidden"}), 403
    projects = service.client_projects(client, current_user, invoice)
    try:
        selection = _step_one_selection(data, client, projects, invoice)
    except StepOneError as exc:
        return jsonify({"error": "invalid_period", "message": str(exc)}), 400
    remove_line_ids = data.get_ids("remove_line_ids")
    summary = service.summary(selection, projects, remove_line_ids)
    payload = _step_one_payload(selection, projects, summary, remove_line_ids)
    if invoice is None:
        payload["numbers"] = _step_one_numbers(
            selection, _parse_iso_day(data.get("issue_date")) or selection.period.issue_date()
        )
    return jsonify(payload)


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
        from app.integrations.peppol import peppol_enabled as _peppol_enabled
        from app.models import InvoicePeppolTransmission

        peppol_enabled_flag = bool(_peppol_enabled())
        peppol_history = (
            InvoicePeppolTransmission.query.filter_by(invoice_id=invoice_id)
            .order_by(InvoicePeppolTransmission.created_at.desc())
            .all()
        )
        try:
            client = invoice.client
            peppol_recipient_ready = bool(
                client and client.get_custom_field("peppol_endpoint_id") and client.get_custom_field("peppol_scheme_id")
            )
        except Exception:
            current_app.logger.debug(
                "Could not determine Peppol recipient readiness for invoice %s",
                invoice_id,
                exc_info=True,
            )
            peppol_recipient_ready = False
    except Exception:
        # Migration might not be applied yet; don't block invoice view.
        current_app.logger.debug(
            "Peppol history unavailable for invoice %s (migration may be pending)",
            invoice_id,
            exc_info=True,
        )
        peppol_history = []

    # SDI / FatturaPA history and readiness
    sdi_history = []
    sdi_enabled_flag = False
    sdi_recipient_ready = False
    try:
        from app.models import InvoiceSdiTransmission
        from app.utils.fatturapa import resolve_codice_destinatario

        settings_for_sdi = Settings.get_settings()
        sdi_enabled_flag = bool(getattr(settings_for_sdi, "sdi_enabled", False))
        sdi_history = (
            InvoiceSdiTransmission.query.filter_by(invoice_id=invoice_id)
            .order_by(InvoiceSdiTransmission.created_at.desc())
            .all()
        )
        try:
            client = invoice.client
            code, pec = resolve_codice_destinatario(client) if client else ("", None)
            sdi_recipient_ready = bool(client and code)
        except Exception:
            current_app.logger.debug(
                "Could not determine SDI recipient readiness for invoice %s",
                invoice_id,
                exc_info=True,
            )
            sdi_recipient_ready = False
    except Exception:
        current_app.logger.debug(
            "SDI history unavailable for invoice %s (migration may be pending)",
            invoice_id,
            exc_info=True,
        )
        sdi_history = []

    # PEPPOL compliance warnings when invoices_peppol_compliant is on
    peppol_compliance_warnings = []
    try:
        settings_obj = Settings.get_settings()
        if getattr(settings_obj, "invoices_peppol_compliant", False):
            if not (getattr(settings_obj, "company_tax_id", None) or "").strip():
                peppol_compliance_warnings.append(
                    _("Company Tax ID (VAT) is missing in Admin → Settings → Company Branding.")
                )
            if not (getattr(settings_obj, "peppol_sender_endpoint_id", None) or "").strip():
                peppol_compliance_warnings.append(
                    _("Sender Endpoint ID is missing in Admin → Settings → Peppol e-Invoicing.")
                )
            if not (getattr(settings_obj, "peppol_sender_scheme_id", None) or "").strip():
                peppol_compliance_warnings.append(
                    _("Sender Scheme ID is missing in Admin → Settings → Peppol e-Invoicing.")
                )
            client = getattr(invoice, "client", None)
            if client:
                if not (client.get_custom_field("peppol_endpoint_id", "") or "").strip():
                    peppol_compliance_warnings.append(
                        _("Client Peppol Endpoint ID is missing. Add peppol_endpoint_id to the client's custom fields.")
                    )
                if not (client.get_custom_field("peppol_scheme_id", "") or "").strip():
                    peppol_compliance_warnings.append(
                        _("Client Peppol Scheme ID is missing. Add peppol_scheme_id to the client's custom fields.")
                    )
            else:
                peppol_compliance_warnings.append(
                    _("Invoice has no linked client; buyer PEPPOL identifiers cannot be checked.")
                )
    except (AttributeError, KeyError, TypeError) as e:
        current_app.logger.warning("PEPPOL compliance check failed (configuration or data): %s", e, exc_info=True)
        peppol_compliance_warnings.append(_("Could not verify PEPPOL compliance; check configuration."))
    except Exception as e:
        current_app.logger.warning("PEPPOL compliance check failed: %s", e, exc_info=True)
        peppol_compliance_warnings.append(_("Could not verify PEPPOL compliance; check configuration."))

    # Get approval information
    from app.services.invoice_approval_service import InvoiceApprovalService

    approval_service = InvoiceApprovalService()
    approval = approval_service.get_invoice_approval(invoice_id)

    # Get link templates for payment_reference (for clickable values)
    from sqlalchemy.exc import ProgrammingError

    from app.models import LinkTemplate

    link_templates_by_field = {}
    try:
        for template in LinkTemplate.get_active_templates():
            if template.field_key == "payment_reference":
                link_templates_by_field["payment_reference"] = template
    except ProgrammingError as e:
        # Handle case where link_templates table doesn't exist (migration not run)
        if "does not exist" in str(e.orig) or "relation" in str(e.orig).lower():
            current_app.logger.warning("link_templates table does not exist. Run migration: flask db upgrade")
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
        sdi_history=sdi_history,
        sdi_enabled=sdi_enabled_flag,
        sdi_recipient_ready=sdi_recipient_ready,
        approval=approval,
        link_templates_by_field=link_templates_by_field,
        **_issue_and_correct_context(invoice),
    )


def _hours_text(value):
    """Hours as the invoice page shows them: 47, 58.5, 0.25."""
    hours = Decimal(str(value or 0)).quantize(Decimal("0.01")).normalize()
    return format(hours, "f")


def _prepaid_months_text(months):
    from flask_babel import format_date

    with_year = len({m.year for m in months}) > 1
    names = []
    for month in months:
        try:
            names.append(format_date(month, "LLLL yyyy" if with_year else "LLLL"))
        except Exception:
            names.append(month.strftime("%B %Y" if with_year else "%B"))
    if len(names) <= 1:
        return "".join(names)
    return _("%(first)s and %(last)s", first=", ".join(names[:-1]), last=names[-1])


def _billing_texts(summary):
    """Sentences about what an invoice bills, for the issue and cancel dialogs and the locked notice."""
    from flask_babel import ngettext

    entries = ngettext("%(num)d time entry", "%(num)d time entries", summary["entries"])
    expenses = ngettext("%(num)d expense", "%(num)d expenses", summary["expenses"])
    project_costs = ngettext("%(num)d project cost", "%(num)d project costs", summary["costs"])
    costs = ngettext("%(num)d cost", "%(num)d costs", summary["costs"])
    tracked = _hours_text(summary["tracked_hours"])
    billed = _hours_text(summary["billed_hours"])
    if summary["entries"]:
        billed_entries = _(
            "%(entries)s (%(tracked)s h tracked, %(billed)s h billed)", entries=entries, tracked=tracked, billed=billed
        )
    else:
        billed_entries = entries

    cancel_effect = _(
        "%(tracked)s h tracked, %(expenses)s and %(costs)s go back to Unbilled",
        tracked=tracked,
        expenses=expenses,
        costs=costs,
    )
    prepaid = summary.get("prepaid") or []
    if prepaid:
        prepaid_hours = _hours_text(sum((hours for _month, hours in prepaid), Decimal("0")))
        months = _prepaid_months_text([month for month, _hours in prepaid])
        if len(prepaid) == 1:
            prepaid_text = _("%(hours)s h go back to the %(months)s prepaid plan", hours=prepaid_hours, months=months)
        else:
            prepaid_text = _("%(hours)s h go back to the %(months)s prepaid plans", hours=prepaid_hours, months=months)
        cancel_effect = cancel_effect + "; " + prepaid_text

    return {
        "issue_confirm": _(
            "Lines and amounts will be locked. %(entries)s, %(expenses)s and %(costs)s will be marked as billed.",
            entries=entries,
            expenses=expenses,
            costs=project_costs,
        ),
        "locked": _(
            "Lines and amounts are locked. %(entries)s, %(expenses)s and %(costs)s are billed on this invoice.",
            entries=billed_entries,
            expenses=expenses,
            costs=project_costs,
        ),
        "cancel_effect": cancel_effect + ".",
    }


def _issue_and_correct_context(invoice):
    """What the invoice page shows about issuing, the locked lines and Cancel and reissue."""
    from app.services.invoice_correction_service import InvoiceCorrectionService
    from app.services.invoice_time_service import ISSUED_STATUSES, InvoiceTimeService

    summary = InvoiceTimeService().invoice_summary(invoice)
    reissue_of = cancellation = None
    try:
        if invoice.status == "draft":
            reissue_of = InvoiceCorrectionService.reissue_of(invoice)
        elif invoice.status == "cancelled":
            cancellation = InvoiceCorrectionService.cancellation(invoice)
    except Exception:
        # The audit trail may be unavailable (migration pending); the page works without these notes
        current_app.logger.debug("Invoice correction notes unavailable for %s", invoice.id, exc_info=True)
        db.session.rollback()
    return {
        "billing_summary": summary,
        "billing_texts": _billing_texts(summary),
        "lines_locked": invoice.status in ISSUED_STATUSES,
        "can_correct": InvoiceCorrectionService.can_correct(invoice),
        "has_payments": InvoiceCorrectionService.can_correct(invoice)
        and InvoiceCorrectionService.has_payments(invoice),
        "reissue_of": reissue_of,
        "cancellation": cancellation,
    }


@invoices_bp.route("/invoices/<int:invoice_id>/correct", methods=["POST"])
@login_required
def correct_invoice(invoice_id):
    """Cancel an issued invoice with a reason, and optionally reissue it as a new draft."""
    from app.services.invoice_correction_service import (
        CancelReasonRequiredError,
        InvoiceCorrectionError,
        InvoiceCorrectionService,
        InvoiceHasPaymentsError,
    )
    from app.services.invoice_time_service import InvoiceTimeError, InvoiceTimeService

    invoice = Invoice.query.get_or_404(invoice_id)
    if not current_user.is_admin and invoice.created_by != current_user.id:
        flash(_("You do not have permission to change this invoice"), "error")
        return redirect(url_for("invoices.list_invoices"))

    action = (request.form.get("action") or "reissue").strip()
    if action not in ("reissue", "cancel"):
        flash(_("Invalid action"), "error")
        return redirect(url_for("invoices.view_invoice", invoice_id=invoice.id))

    previous_status = invoice.status
    cancel_effect = _billing_texts(InvoiceTimeService().invoice_summary(invoice))["cancel_effect"]
    service = InvoiceCorrectionService()
    draft = None
    try:
        if action == "reissue":
            draft = service.reissue(invoice, request.form.get("reason"), current_user.id)
        else:
            service.cancel(invoice, request.form.get("reason"), current_user.id)
    except CancelReasonRequiredError:
        db.session.rollback()
        flash(_("Enter a reason to cancel the invoice."), "error")
        return redirect(url_for("invoices.view_invoice", invoice_id=invoice.id))
    except InvoiceHasPaymentsError:
        db.session.rollback()
        flash(_("This invoice has payments; use a credit note"), "error")
        return redirect(url_for("invoices.view_invoice", invoice_id=invoice.id))
    except (InvoiceCorrectionError, InvoiceTimeError) as exc:
        db.session.rollback()
        flash(_("Could not cancel the invoice: %(error)s", error=str(exc)), "error")
        return redirect(url_for("invoices.view_invoice", invoice_id=invoice.id))

    if not safe_commit("correct_invoice", {"invoice_id": invoice.id, "action": action}):
        flash(_("Could not cancel the invoice due to a database error. Please check server logs."), "error")
        return redirect(url_for("invoices.view_invoice", invoice_id=invoice.id))

    try:
        from app.constants import WebhookEvent
        from app.utils.invoice_events import emit_invoice_event

        emit_invoice_event(
            WebhookEvent.INVOICE_UPDATED.value, invoice, previous_status=previous_status, new_status="cancelled"
        )
        if draft is not None:
            emit_invoice_event(WebhookEvent.INVOICE_CREATED.value, draft)
    except Exception:
        current_app.logger.debug("Failed to emit invoice correction webhooks for %s", invoice.id, exc_info=True)
    try:
        log_event(
            "invoice.status_changed",
            user_id=current_user.id,
            invoice_id=invoice.id,
            previous_status=previous_status,
            new_status="cancelled",
        )
    except Exception:
        current_app.logger.warning("Failed to log invoice.status_changed for invoice %s", invoice.id, exc_info=True)

    if draft is not None:
        flash(
            _(
                "Invoice %(old)s cancelled. Its lines are on the new draft %(new)s.",
                old=invoice.invoice_number,
                new=draft.invoice_number,
            ),
            "success",
        )
        return redirect(url_for("invoices.view_invoice", invoice_id=draft.id))
    flash(_("Invoice %(number)s cancelled: %(effect)s", number=invoice.invoice_number, effect=cancel_effect), "success")
    return redirect(url_for("invoices.view_invoice", invoice_id=invoice.id))


@invoices_bp.route("/invoices/<int:invoice_id>/edit", methods=["GET", "POST"])
@login_required
def edit_invoice(invoice_id):
    """Edit invoice"""
    invoice = Invoice.query.get_or_404(invoice_id)

    # Check access permissions
    if not current_user.is_admin and invoice.created_by != current_user.id:
        flash(_("You do not have permission to edit this invoice"), "error")
        return redirect(url_for("invoices.list_invoices"))

    financial_locked = invoice.status != "draft"

    if request.method == "POST":
        # Non-draft invoices are immutable for financial fields (GoBD-style).
        # Only notes, terms and due date may still be updated; use a credit note
        # for corrections to amounts or line items.
        if financial_locked:
            due_date_str = request.form.get("due_date", "").strip()
            if due_date_str:
                try:
                    invoice.due_date = datetime.strptime(due_date_str, "%Y-%m-%d").date()
                except ValueError:
                    flash(_("Invalid due date"), "error")
                    return redirect(url_for("invoices.edit_invoice", invoice_id=invoice.id))
            invoice.notes = request.form.get("notes", "").strip()
            invoice.terms = request.form.get("terms", "").strip()
            if not safe_commit("edit_invoice_locked", {"invoice_id": invoice.id}):
                flash(_("Could not update invoice due to a database error. Please check server logs."), "error")
                return redirect(url_for("invoices.edit_invoice", invoice_id=invoice.id))
            flash(
                _(
                    "Only notes, terms and due date were updated. Sent invoices cannot change "
                    "amounts or line items — issue a credit note instead."
                ),
                "warning",
            )
            return redirect(url_for("invoices.view_invoice", invoice_id=invoice.id))

        # Update invoice details
        invoice.client_name = request.form.get("client_name", "").strip()
        invoice.client_email = request.form.get("client_email", "").strip()
        invoice.client_address = request.form.get("client_address", "").strip()
        _br = request.form.get("buyer_reference", "").strip()
        invoice.buyer_reference = _br if _br else None
        _vc = (request.form.get("vat_category", "") or "").strip().upper() or None
        if _vc and _vc not in ("S", "Z", "E", "AE", "K", "G", "O", "L", "M"):
            _vc = None
        invoice.vat_category = _vc
        invoice.cig = (request.form.get("cig", "") or "").strip() or None
        invoice.cup = (request.form.get("cup", "") or "").strip() or None
        invoice.vat_exemption_reason = (request.form.get("vat_exemption_reason", "") or "").strip() or None
        invoice.vat_exemption_code = (request.form.get("vat_exemption_code", "") or "").strip() or None
        invoice.due_date = datetime.strptime(request.form.get("due_date"), "%Y-%m-%d").date()
        invoice.tax_rate = Decimal(request.form.get("tax_rate", "0"))
        invoice.notes = request.form.get("notes", "").strip()
        invoice.terms = request.form.get("terms", "").strip()

        # "Bill to" legal entity (Client legal entities module): a draft takes the entity's
        # current details each time it is saved
        from app.utils import client_entities as bill_to

        if bill_to.module_on() and "client_entity_id" in request.form:
            bill_to_entity, bill_to_error = bill_to.resolve_from_form(
                request.form, invoice.client_id, invoice.client_entity_id
            )
            if bill_to_error:
                flash(_(bill_to_error), "error")
                return redirect(url_for("invoices.edit_invoice", invoice_id=invoice.id))
            bill_to.apply_to_invoice(invoice, bill_to_entity)

        from app.utils.invoice_currency import normalize_currency_code

        invoice.currency_code = normalize_currency_code(request.form.get("currency_code")) or invoice.currency_code

        # Seller ("From") and payment account: a draft may change them (Legal entities module)
        from app.utils import billing_entities as billing

        if billing.module_on() and "billing_entity_id" in request.form:
            billing_entity, payment_account, billing_error = billing.resolve_from_form(
                request.form, invoice.currency_code
            )
            if billing_error:
                flash(_(billing_error), "error")
                return redirect(url_for("invoices.edit_invoice", invoice_id=invoice.id))
            # A draft always takes the entity's current details; they freeze once it leaves draft
            billing.apply_to_invoice(invoice, billing_entity, payment_account)

        # Read invoice-level discount (draft only since we're in the full edit path)
        try:
            invoice.discount_percent = Decimal(request.form.get("discount_percent", "0") or "0")
        except Exception:
            invoice.discount_percent = Decimal("0")
        try:
            invoice.discount_amount = Decimal(request.form.get("discount_amount", "0") or "0")
        except Exception:
            invoice.discount_amount = Decimal("0")

        # Update items
        item_ids = request.form.getlist("item_id[]")
        descriptions = request.form.getlist("description[]")
        quantities = request.form.getlist("quantity[]")
        unit_prices = request.form.getlist("unit_price[]")
        item_time_entry_ids_list = request.form.getlist("item_time_entry_ids[]")
        item_tax_rates = request.form.getlist("item_tax_rate[]")
        item_vat_categories = request.form.getlist("item_vat_category[]")
        item_discount_percents = request.form.getlist("item_discount_percent[]")
        item_discount_amounts = request.form.getlist("item_discount_amount[]")
        item_positions = request.form.getlist("item_position[]")

        # Remove existing items. Their time links go with them and come back below for the
        # time entries the submitted lines still list.
        from app.services.invoice_time_service import InvoiceTimeError, InvoiceTimeService, line_entry_ids

        time_links = InvoiceTimeService()
        # Every listed time entry must be one this invoice may bill (as in the picker), on one line only
        submitted_lines = [
            line_entry_ids(item_time_entry_ids_list[i])
            for i in range(len(descriptions))
            if descriptions[i].strip()
            and i < len(quantities)
            and quantities[i]
            and i < len(unit_prices)
            and unit_prices[i]
            and i < len(item_time_entry_ids_list)
        ]
        try:
            time_links.check_line_entries(invoice, submitted_lines)
        except InvoiceTimeError as exc:
            db.session.rollback()
            flash(_("Could not save the invoice: %(error)s", error=str(exc)), "error")
            return redirect(url_for("invoices.edit_invoice", invoice_id=invoice.id))

        # A time line whose description, quantity or price changes is marked as edited by hand
        previous_lines = time_links.snapshot_lines(invoice)
        previous_hours = time_links.detach_lines(invoice)
        invoice.items.delete()
        new_items = []
        new_item_ids = []

        # Add new items
        for i in range(len(descriptions)):
            if descriptions[i].strip() and quantities[i] and unit_prices[i]:
                try:
                    quantity = Decimal(quantities[i])
                    unit_price = Decimal(unit_prices[i])

                    # Get time entry ids if provided (for time-based items). The quantity of a time line
                    # follows its linked hours unless it was changed by hand (see carry_line_state).
                    time_entry_ids_val = None
                    row_item_id = item_ids[i] if i < len(item_ids) else None
                    if i < len(item_time_entry_ids_list) and item_time_entry_ids_list[i].strip():
                        time_entry_ids_val = item_time_entry_ids_list[i].strip()

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

                    # Per-line tax / discount / position
                    _item_tax_rate = None
                    if i < len(item_tax_rates) and item_tax_rates[i].strip():
                        try:
                            _item_tax_rate = Decimal(item_tax_rates[i].strip())
                        except Exception:
                            _item_tax_rate = None

                    _item_vat_cat = None
                    if i < len(item_vat_categories) and item_vat_categories[i].strip():
                        _item_vat_cat = item_vat_categories[i].strip().upper() or None
                        if _item_vat_cat and _item_vat_cat not in ("S", "Z", "E", "AE", "K", "G", "O", "L", "M"):
                            _item_vat_cat = None

                    _disc_pct = Decimal("0")
                    if i < len(item_discount_percents) and item_discount_percents[i].strip():
                        try:
                            _disc_pct = Decimal(item_discount_percents[i].strip())
                        except Exception:
                            _disc_pct = Decimal("0")

                    _disc_amt = Decimal("0")
                    if i < len(item_discount_amounts) and item_discount_amounts[i].strip():
                        try:
                            _disc_amt = Decimal(item_discount_amounts[i].strip())
                        except Exception:
                            _disc_amt = Decimal("0")

                    _position = i  # default to form order
                    if i < len(item_positions) and item_positions[i].strip():
                        try:
                            _position = int(item_positions[i].strip())
                        except Exception:
                            _position = i

                    item = InvoiceItem(
                        invoice_id=invoice.id,
                        description=time_links.normalize_description(descriptions[i]),
                        quantity=quantity,
                        unit_price=unit_price,
                        time_entry_ids=time_entry_ids_val,
                        stock_item_id=stock_item_id_val,
                        warehouse_id=warehouse_id_val,
                        tax_rate=_item_tax_rate,
                        vat_category=_item_vat_cat,
                        discount_percent=_disc_pct,
                        discount_amount=_disc_amt,
                        position=_position,
                    )
                    db.session.add(item)
                    new_items.append(item)
                    new_item_ids.append(row_item_id)
                except ValueError:
                    flash(f"Invalid quantity or price for item {i+1}", "error")
                    continue

        try:
            time_links.link_items(invoice, new_items, hours_by_entry=previous_hours, created_by=current_user.id)
        except InvoiceTimeError as exc:
            db.session.rollback()
            flash(_("Could not save the invoice: %(error)s", error=str(exc)), "error")
            return redirect(url_for("invoices.edit_invoice", invoice_id=invoice.id))
        for item, row_item_id in zip(new_items, new_item_ids):
            time_links.carry_line_state(previous_lines, item, row_item_id)

        # Update expenses (only when the expenses section was submitted)
        if request.form.get("expenses_sync"):
            expense_ids = request.form.getlist("expense_id[]")

            # Unlink expenses removed from this invoice
            for expense in invoice.expenses.all():
                if expense.invoice_id == invoice.id and str(expense.id) not in expense_ids:
                    expense.unmark_as_invoiced()

            # Link new expenses from the list
            for expense_id in expense_ids:
                try:
                    expense = Expense.query.get(int(expense_id))
                    if not expense:
                        continue
                    if expense.invoice_id == invoice.id:
                        continue
                    if not expense.invoiced:
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
        good_stock_item_ids = request.form.getlist("good_stock_item_id[]")

        # Remove existing extra goods
        invoice.extra_goods.delete()

        # Add new extra goods
        for i in range(len(good_names)):
            if good_names[i].strip() and good_quantities[i] and good_unit_prices[i]:
                try:
                    quantity = Decimal(good_quantities[i])
                    unit_price = Decimal(good_unit_prices[i])
                    stock_item_id = None
                    if i < len(good_stock_item_ids) and good_stock_item_ids[i]:
                        try:
                            stock_item_id = int(good_stock_item_ids[i])
                        except (TypeError, ValueError):
                            stock_item_id = None

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
                        stock_item_id=stock_item_id,
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
                financial_locked=False,
                expense_categories=ExpenseCategory.query.order_by(ExpenseCategory.name).all(),
            )

        flash(_("Invoice updated successfully"), "success")
        return redirect(url_for("invoices.view_invoice", invoice_id=invoice.id))

    # GET request - show edit form
    import json

    from app.models import InvoiceTemplate, StockItem, Warehouse

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
        financial_locked=financial_locked,
        currency_choices=_invoice_currency_choices(invoice),
        expense_categories=ExpenseCategory.query.order_by(ExpenseCategory.name).all(),
        **_billing_edit_context(invoice),
        **_bill_to_edit_context(invoice),
    )


def _billing_edit_context(invoice):
    from app.utils.billing_entities import form_context

    return form_context(None, Settings.get_settings())


def _bill_to_edit_context(invoice):
    from app.utils.client_entities import form_context

    return form_context(None, invoice=invoice)


def _invoice_currency_choices(invoice):
    from app.utils.invoice_currency import currency_choices

    return currency_choices(Settings.get_settings(), extra=[invoice.currency_code])


@invoices_bp.route("/invoices/<int:invoice_id>/status", methods=["POST"])
@login_required
def update_invoice_status(invoice_id):
    """Update invoice status"""
    invoice = Invoice.query.get_or_404(invoice_id)

    # Check access permissions
    if not current_user.is_admin and invoice.created_by != current_user.id:
        return jsonify({"error": "Permission denied"}), 403

    new_status = request.form.get("new_status")
    if new_status not in ["draft", "issued", "sent", "paid", "overdue", "cancelled", "void"]:
        return jsonify({"error": "Invalid status"}), 400

    from app.services import InvoiceService

    result = InvoiceService().transition_status(invoice, new_status, actor_id=current_user.id)
    if not result.get("success"):
        return jsonify({"error": result.get("message") or "Invalid status transition"}), 400

    previous_status = result.get("previous_status")
    new_status = result.get("status") or new_status
    marked_count = result.get("marked_count") or 0
    if marked_count > 0:
        current_app.logger.info(
            f"Marked {marked_count} time entr{'y' if marked_count == 1 else 'ies'} as paid for invoice {invoice.invoice_number}"
        )
    for warning in result.get("warnings") or []:
        flash(_("Warning: %(msg)s", msg=warning), "warning")

    if not safe_commit("update_invoice_status", {"invoice_id": invoice.id, "status": new_status}):
        return jsonify({"error": "Database error while updating status"}), 500

    if new_status == "paid":
        from app.utils.workflow_bridge import fire_invoice_paid_workflow

        fire_invoice_paid_workflow(invoice, current_user.id)
        try:
            from app.services.client_survey_service import ClientSurveyService

            ClientSurveyService().on_invoice_paid(invoice)
        except Exception as survey_exc:
            current_app.logger.debug("Client survey on invoice paid skipped: %s", survey_exc)

    try:
        from app.constants import WebhookEvent
        from app.utils.invoice_events import emit_invoice_event

        emit_invoice_event(
            WebhookEvent.INVOICE_UPDATED.value,
            invoice,
            previous_status=previous_status,
            new_status=new_status,
        )
        if new_status == "sent" and previous_status != "sent":
            emit_invoice_event(WebhookEvent.INVOICE_SENT.value, invoice)
        if new_status == "paid" and previous_status != "paid":
            emit_invoice_event(WebhookEvent.INVOICE_PAID.value, invoice)
    except Exception:
        current_app.logger.debug("Failed to emit invoice status webhook for %s", invoice.id, exc_info=True)

    try:
        log_event(
            "invoice.status_changed",
            user_id=current_user.id,
            invoice_id=invoice.id,
            previous_status=previous_status,
            new_status=new_status,
        )
    except Exception:
        current_app.logger.warning("Failed to log invoice.status_changed for invoice %s", invoice.id, exc_info=True)

    return jsonify({"success": True, "status": new_status})


def _back_to_invoice_list():
    """Redirect after a delete or bulk action: back to the list the action came from."""
    return safe_redirect(request.form.get("next"), fallback_endpoint="invoices.list_invoices")


@invoices_bp.route("/invoices/<int:invoice_id>/delete", methods=["POST"])
@login_required
def delete_invoice(invoice_id):
    """Delete invoice"""
    invoice = Invoice.query.get_or_404(invoice_id)

    # Check access permissions
    if not current_user.is_admin and invoice.created_by != current_user.id:
        flash(_("You do not have permission to delete this invoice"), "error")
        return _back_to_invoice_list()

    if invoice.status != "draft":
        flash(_("Only draft invoices can be deleted."), "error")
        return redirect(url_for("invoices.edit_invoice", invoice_id=invoice.id))

    invoice_number = invoice.invoice_number
    invoice_id_for_event = invoice.id
    invoice.release_invoiced_costs_and_expenses()
    db.session.delete(invoice)
    if not safe_commit("delete_invoice", {"invoice_id": invoice_id_for_event}):
        flash(_("Could not delete invoice due to a database error. Please check server logs."), "error")
        return _back_to_invoice_list()

    try:
        from app.constants import WebhookEvent
        from app.utils.event_bus import emit_event

        emit_event(
            WebhookEvent.INVOICE_DELETED.value,
            {"invoice_id": invoice_id_for_event, "invoice_number": invoice_number},
        )
    except Exception:
        current_app.logger.debug("Failed to emit invoice.deleted for %s", invoice_id_for_event, exc_info=True)

    flash(f"Invoice {invoice_number} deleted successfully", "success")
    return _back_to_invoice_list()


@invoices_bp.route("/invoices/bulk-delete", methods=["POST"])
@login_required
def bulk_delete_invoices():
    """Delete multiple invoices at once"""
    invoice_ids = request.form.getlist("invoice_ids[]")

    if not invoice_ids:
        flash(_("No invoices selected for deletion"), "warning")
        return _back_to_invoice_list()

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

            if invoice.status != "draft":
                skipped_count += 1
                errors.append(f"'{invoice.invoice_number}': Not a draft")
                continue

            invoice_number = invoice.invoice_number
            invoice.release_invoiced_costs_and_expenses()
            db.session.delete(invoice)
            deleted_count += 1

        except Exception as e:
            current_app.logger.warning("Skipping invoice %s during bulk delete", invoice_id_str, exc_info=True)
            try:
                db.session.rollback()
            except Exception:
                current_app.logger.debug("Rollback after bulk delete skip also failed", exc_info=True)
            skipped_count += 1
            errors.append(f"ID {invoice_id_str}: {str(e)}")

    # Commit all deletions
    if deleted_count > 0:
        if not safe_commit("bulk_delete_invoices", {"count": deleted_count}):
            flash(_("Could not delete invoices due to a database error. Please check server logs."), "error")
            return _back_to_invoice_list()

    # Show appropriate messages
    if deleted_count > 0:
        flash(f'Successfully deleted {deleted_count} invoice{"s" if deleted_count != 1 else ""}', "success")

    if skipped_count > 0:
        flash(f'Skipped {skipped_count} invoice{"s" if skipped_count != 1 else ""}: {"; ".join(errors[:3])}', "warning")

    return _back_to_invoice_list()


@invoices_bp.route("/invoices/bulk-status", methods=["POST"])
@login_required
def bulk_update_status():
    """Update status for multiple invoices at once"""
    invoice_ids = request.form.getlist("invoice_ids[]")
    new_status = request.form.get("status", "").strip()
    invoice_reference = request.form.get("invoice_reference", "").strip()

    if not invoice_ids:
        flash(_("No invoices selected"), "warning")
        return _back_to_invoice_list()

    # Validate status
    # Mirror the single-update validator so bulk update can also set "issued".
    valid_statuses = ["draft", "issued", "sent", "paid", "overdue", "cancelled"]
    if not new_status or new_status not in valid_statuses:
        flash(_("Invalid status value"), "error")
        return _back_to_invoice_list()

    from app.services import InvoiceService

    invoice_service = InvoiceService()
    updated_count = 0
    skipped_count = 0
    not_allowed_count = 0
    has_payments_count = 0

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

            result = invoice_service.transition_status(
                invoice,
                new_status,
                actor_id=current_user.id,
                payment_reference=invoice_reference or None,
            )
            if not result.get("success"):
                if result.get("error") == "has_payments":
                    has_payments_count += 1
                else:
                    not_allowed_count += 1
                continue

            # Same-status is a no-op success; only count real changes
            if result.get("previous_status") != result.get("status"):
                updated_count += 1
            for warning in result.get("warnings") or []:
                flash(_("Warning: %(msg)s", msg=warning), "warning")

        except Exception:
            current_app.logger.warning("Skipping invoice %s during bulk status update", invoice_id_str, exc_info=True)
            try:
                db.session.rollback()
            except Exception:
                current_app.logger.debug("Rollback after bulk status skip also failed", exc_info=True)
            skipped_count += 1

    if updated_count > 0:
        if not safe_commit("bulk_update_invoice_status", {"count": updated_count, "status": new_status}):
            flash(_("Could not update invoices due to a database error"), "error")
            return _back_to_invoice_list()

        flash(
            f'Successfully updated {updated_count} invoice{"s" if updated_count != 1 else ""} to {new_status}',
            "success",
        )

    if skipped_count > 0:
        flash(f'Skipped {skipped_count} invoice{"s" if skipped_count != 1 else ""} (no permission)', "warning")
    if not_allowed_count > 0:
        flash(
            _(
                "Skipped %(count)d invoice(s): their status cannot change to %(status)s "
                "(a cancelled or paid invoice keeps its status)",
                count=not_allowed_count,
                status=new_status,
            ),
            "warning",
        )
    if has_payments_count > 0:
        flash(
            _(
                "Skipped %(count)d invoice(s) with payments: use Correct → Credit note, "
                "or remove the payments first",
                count=has_payments_count,
            ),
            "warning",
        )

    return _back_to_invoice_list()


@invoices_bp.route("/invoices/<int:invoice_id>/generate-from-time", methods=["GET", "POST"])
@login_required
def generate_from_time(invoice_id):
    """Generate invoice items from time entries"""
    invoice = Invoice.query.get_or_404(invoice_id)

    # Check access permissions
    if not current_user.is_admin and invoice.created_by != current_user.id:
        flash(_("You do not have permission to edit this invoice"), "error")
        return redirect(url_for("invoices.list_invoices"))

    # Hours, costs and goods go onto draft invoices only; a sent invoice keeps its lines
    if invoice.status != "draft":
        flash(
            _(
                "Invoice %(number)s is %(status)s: time and costs can only be added to a draft invoice.",
                number=invoice.invoice_number,
                status=invoice.status,
            ),
            "error",
        )
        return redirect(url_for("invoices.view_invoice", invoice_id=invoice.id))

    if request.method == "POST":
        # Get selected time entries, costs, expenses, and extra goods
        selected_entries = request.form.getlist("time_entries[]")
        selected_costs = request.form.getlist("project_costs[]")
        selected_expenses = request.form.getlist("expenses[]")
        selected_goods = request.form.getlist("extra_goods[]")

        if not selected_entries and not selected_costs and not selected_expenses and not selected_goods:
            flash(_("No time entries, costs, expenses, or extra goods selected"), "error")
            return redirect(url_for("invoices.generate_from_time", invoice_id=invoice.id))

        # The picker hides what is already on this invoice, so keep it: manual and cost
        # lines stay, and time lines are rebuilt from their entries plus the new selection.
        # A time line edited by hand (description, quantity or price) stays as it is, with its entries.
        from app.services.invoice_time_service import InvoiceTimeError, InvoiceTimeService
        from app.utils.invoice_time_entry_items import LAYOUT_NONE, normalize_template, resolve_hours_layout_from_form

        time_links = InvoiceTimeService()
        hours_layout = resolve_hours_layout_from_form(request.form)
        line_template = normalize_template(request.form.get("line_template"))
        if hours_layout == LAYOUT_NONE:
            # "Don't add any hours": the invoice's hours stay as they are. The project's default is not
            # changed (it stays the last layout that added hours).
            selected_entries = []
            if not any(item.kind == "time" for item in invoice.items.all()):
                invoice.hours_layout = LAYOUT_NONE
                invoice.line_template = None
        entry_ids = set()
        for raw_id in selected_entries:
            try:
                entry_ids.add(int(raw_id))
            except (TypeError, ValueError):
                continue
        eligible_ids = set()
        kept_entry_ids = set()
        if selected_entries:
            # Same set the picker offers, decided before this invoice's own links are dropped:
            # running entries and entries marked paid outside an invoice are not taken
            eligible_ids = time_links.eligible_entry_ids(
                invoice, entry_ids | set(time_links.invoice_entry_ids(invoice)), include_prepaid_only=True
            )
            active_links = invoice.time_links.filter_by(released_at=None).all()
            kept_line_ids = {item.id for item in invoice.items.all() if item.kind == "time" and item.is_edited}
            kept_entry_ids = {link.time_entry_id for link in active_links if link.invoice_item_id in kept_line_ids}
            # Entries this invoice already bills, including those fully covered by prepaid hours,
            # which have no line
            line_ids = {link.invoice_item_id for link in active_links if link.invoice_item_id} - kept_line_ids
            for link in active_links:
                if link.time_entry_id not in kept_entry_ids:
                    entry_ids.add(link.time_entry_id)
                    db.session.delete(link)
            db.session.flush()
            for item in invoice.items.all():
                if item.id in line_ids:
                    db.session.delete(item)

        total_prepaid_allocated = Decimal("0")
        prepaid_allocator = None
        missing_rate_warnings = []

        # Process time entries
        if selected_entries:
            time_entries = TimeEntry.query.filter(TimeEntry.id.in_(entry_ids - kept_entry_ids)).all()
            conflicts = time_links.find_conflicts(time_entries, invoice)
            if conflicts:
                db.session.rollback()
                flash(
                    _(
                        "Some time entries are already on another invoice: %(entries)s",
                        entries=", ".join(f"{entry.id} ({other.invoice_number})" for entry, other in conflicts),
                    ),
                    "error",
                )
                return redirect(url_for("invoices.generate_from_time", invoice_id=invoice.id))

            left_out = [entry for entry in time_entries if entry.id not in eligible_ids]
            if left_out:
                flash(
                    _(
                        "%(count)d selected time entry/entries were not added: %(entries)s",
                        count=len(left_out),
                        entries=", ".join(
                            f"{entry.id} ({time_links.ineligible_reason(entry, invoice)})" for entry in left_out
                        ),
                    ),
                    "warning",
                )
                time_entries = [entry for entry in time_entries if entry.id in eligible_ids]

            # Entries of kept (edited) lines stay out of the prepaid allocation: their ledger rows and
            # link hours are left as they are, and the hours they used count as used
            prepaid_allocator = PrepaidHoursAllocator(
                client=invoice.client, invoice=invoice, keep_entry_ids=kept_entry_ids
            )
            processed_entries = prepaid_allocator.process(time_entries)
            total_prepaid_allocated = prepaid_allocator.total_prepaid_hours_assigned

            try:
                lines = time_links.add_entries(
                    invoice, processed_entries, hours_layout, line_template, created_by=current_user.id
                )
                missing_rate_warnings = lines.missing_rates
                # Entries fully covered by prepaid hours get no line, only a link to the invoice
                time_links.link_entries(
                    invoice,
                    None,
                    [
                        (p.entry, p.prepaid_hours)
                        for p in processed_entries
                        if p.prepaid_hours > 0 and p.billable_hours <= 0
                    ],
                    created_by=current_user.id,
                )
            except InvoiceTimeError as exc:
                db.session.rollback()
                flash(_("Could not add the time entries: %(error)s", error=str(exc)), "error")
                return redirect(url_for("invoices.generate_from_time", invoice_id=invoice.id))

        # Process project costs
        if selected_costs:
            costs = ProjectCost.query.filter(ProjectCost.id.in_(selected_costs)).all()
            # A cost already on this invoice keeps its line; a resubmitted form must not add a second one
            costs = [cost for cost in costs if cost.invoice_id != invoice.id]

            for cost in costs:
                # Create invoice item for each cost
                item = InvoiceItem(
                    invoice_id=invoice.id,
                    description=f"{cost.description} ({cost.category_name})",
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

        db.session.refresh(invoice)

        added_parts = []
        if selected_entries or selected_costs:
            added_parts.append(_("time entries and costs"))
        if selected_expenses:
            added_parts.append(_("expenses"))
        if selected_goods:
            added_parts.append(_("extra goods"))
        if added_parts:
            flash(
                _("Successfully added %(parts)s to the invoice.", parts=", ".join(added_parts)),
                "success",
            )
        else:
            flash(_("Invoice updated successfully"), "success")
        for missing in missing_rate_warnings:
            flash(
                _(
                    "%(hours)s h were added at 0: no hourly rate for %(target)s",
                    hours=str(missing.rounded_hours),
                    target=missing.target,
                ),
                "warning",
            )
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
    from app.services import InvoiceService
    from app.services.invoice_time_service import InvoiceTimeService
    from app.utils.invoice_time_entry_items import DEFAULT_LINE_TEMPLATES, HOURS_LAYOUT_LABELS, HOURS_LAYOUTS

    data = InvoiceService().get_unbilled_data_for_invoice(invoice)
    focus = request.args.get("focus", "").strip()
    resolved_hourly_rate = RateOverride.resolve_rate(invoice.project)
    # The invoice's own layout once it has hours, else the project's last one, else the global setting
    own_layout = invoice.hours_layout if invoice.hours_layout not in (None, "none") else None
    hours_layout, line_template = InvoiceTimeService().resolve_layout(
        invoice.project,
        own_layout,
        invoice.line_template if own_layout else None,
    )
    return render_template(
        "invoices/generate_from_time.html",
        invoice=invoice,
        time_entries=data["time_entries"],
        grouped_time_entries=data["grouped_time_entries"],
        project_costs=data["project_costs"],
        expenses=data["expenses"],
        extra_goods=data["extra_goods"],
        total_available_hours=data["total_available_hours"],
        total_available_costs=data["total_available_costs"],
        total_available_expenses=data["total_available_expenses"],
        total_available_goods=data["total_available_goods"],
        currency=data["currency"],
        prepaid_summary=data["prepaid_summary"],
        prepaid_plan_hours=data["prepaid_plan_hours"],
        prepaid_reset_day=data.get("prepaid_reset_day"),
        focus=focus,
        diagnostics=data.get("diagnostics", {}),
        resolved_hourly_rate=resolved_hourly_rate,
        hours_layouts=[(layout, HOURS_LAYOUT_LABELS[layout]) for layout in HOURS_LAYOUTS],
        default_line_templates=DEFAULT_LINE_TEMPLATES,
        hours_layout=hours_layout,
        line_template=line_template,
    )


@invoices_bp.route("/invoices/<int:invoice_id>/hours-layout-preview", methods=["POST"])
@login_required
def hours_layout_preview(invoice_id):
    """Example line for each hours layout, from the time entries selected on generate-from-time.

    JSON body: ``time_entry_ids`` and ``line_template`` (omit it to use each layout's default).
    Only entries the picker offers are used (unbilled entries of the invoice's project); a user limited
    to assigned clients gets nothing for a project outside them. Prepaid hours are not applied.
    """
    from app.services.invoice_time_service import InvoiceTimeService
    from app.utils.invoice_time_entry_items import layout_examples, normalize_template
    from app.utils.scope_filter import user_can_access_project

    invoice = Invoice.query.get_or_404(invoice_id)
    if not current_user.is_admin and invoice.created_by != current_user.id:
        return jsonify({"error": "forbidden"}), 403
    # A user limited to assigned clients (subcontractor) sees nothing outside them
    if getattr(current_user, "is_scope_restricted", False) and not user_can_access_project(
        current_user, invoice.project_id
    ):
        return jsonify({"error": "forbidden"}), 403

    data = request.get_json(silent=True) or {}
    raw_ids = data.get("time_entry_ids") or []
    ids = []
    for raw in raw_ids if isinstance(raw_ids, list) else []:
        try:
            ids.append(int(raw))
        except (TypeError, ValueError):
            continue
    # Same set as the picker: unbilled entries of the invoice's project
    entries = (
        InvoiceTimeService().unbilled_query([invoice.project_id]).filter(TimeEntry.id.in_(ids[:1000])).all()
        if ids
        else []
    )
    template = data.get("line_template")
    examples = layout_examples(
        entries,
        template=normalize_template(template if isinstance(template, str) else None),
        currency=invoice.currency_code,
        project_name=invoice.project.name if invoice.project else None,
    )
    return jsonify({"entry_count": len(entries), "layouts": examples})


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

    filename = f"{invoice.invoice_number}.csv"

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
        return safe_redirect(
            request.referrer, allow_absolute_same_host=True, fallback=url_for("invoices.list_invoices")
        )
    try:
        from app.integrations.peppol import build_peppol_ubl_invoice_xml
        from app.services.peppol_service import PeppolService

        svc = PeppolService()
        sender = svc._get_sender_party()
        recipient_party, _ign, _ign = svc._get_recipient_party(invoice)
        ubl_xml, _ign = build_peppol_ubl_invoice_xml(invoice=invoice, supplier=sender, customer=recipient_party)
        fn = f"{invoice.invoice_number}.xml"
        return Response(
            ubl_xml, mimetype="application/xml", headers={"Content-Disposition": f"attachment; filename={fn}"}
        )
    except ValueError as e:
        flash(_("Cannot generate UBL. Please try again."), "error")
        return redirect(url_for("invoices.view_invoice", invoice_id=invoice_id))
    except Exception as e:
        from app.utils.error_reporting import log_and_capture

        log_and_capture(
            current_app.logger,
            "UBL export failed for invoice %s",
            invoice_id,
            exc=e,
            level="exception",
        )
        flash(_("UBL export failed. Please try again."), "error")
        return redirect(url_for("invoices.view_invoice", invoice_id=invoice_id))


@invoices_bp.route("/invoices/<int:invoice_id>/export/xrechnung")
@login_required
def export_invoice_xrechnung(invoice_id):
    """Export invoice as XRechnung 3.0 UBL XML (CIUS-DE)."""
    from app.models import Settings
    from app.utils.xrechnung import build_xrechnung_ubl_invoice_xml, validate_xrechnung_ready

    invoice = Invoice.query.get_or_404(invoice_id)
    if not current_user.is_admin and invoice.created_by != current_user.id:
        flash(_("You do not have permission to export this invoice"), "error")
        return safe_redirect(
            request.referrer, allow_absolute_same_host=True, fallback=url_for("invoices.list_invoices")
        )

    settings = Settings.get_settings()
    client = getattr(invoice, "client", None)
    errors = validate_xrechnung_ready(invoice, settings, client)
    if errors:
        return Response(
            json.dumps({"error": "xrechnung_not_ready", "messages": errors}),
            status=400,
            mimetype="application/json",
        )

    try:
        xml, _sha = build_xrechnung_ubl_invoice_xml(invoice, settings, client)
        fn = f"{invoice.invoice_number}-xrechnung.xml"
        return Response(xml, mimetype="application/xml", headers={"Content-Disposition": f"attachment; filename={fn}"})
    except Exception as e:
        from app.utils.error_reporting import log_and_capture

        log_and_capture(
            current_app.logger,
            "XRechnung export failed for invoice %s",
            invoice_id,
            exc=e,
            level="exception",
        )
        flash(_("XRechnung export failed. Please try again."), "error")
        return redirect(url_for("invoices.view_invoice", invoice_id=invoice_id))


@invoices_bp.route("/invoices/<int:invoice_id>/export/fatturapa")
@login_required
def export_invoice_fatturapa(invoice_id):
    """Export invoice as FatturaPA 1.2 XML (FPR12 / FPA12)."""
    from app.models import Settings
    from app.utils.fatturapa import build_fatturapa_xml, progressivo_from_id, validate_fatturapa_ready

    invoice = Invoice.query.get_or_404(invoice_id)
    if not current_user.is_admin and invoice.created_by != current_user.id:
        flash(_("You do not have permission to export this invoice"), "error")
        return safe_redirect(
            request.referrer, allow_absolute_same_host=True, fallback=url_for("invoices.list_invoices")
        )

    settings = Settings.get_settings()
    client = getattr(invoice, "client", None)
    errors = validate_fatturapa_ready(invoice, settings, client)
    if errors:
        return Response(
            json.dumps({"error": "fatturapa_not_ready", "messages": errors}),
            status=400,
            mimetype="application/json",
        )

    try:
        progressivo = progressivo_from_id(invoice.id or 1)
        xml, filename, _sha = build_fatturapa_xml(invoice, settings, client, progressivo)
        return Response(
            xml, mimetype="application/xml", headers={"Content-Disposition": f"attachment; filename={filename}"}
        )
    except Exception as e:
        from app.utils.error_reporting import log_and_capture

        log_and_capture(
            current_app.logger,
            "FatturaPA export failed for invoice %s",
            invoice_id,
            exc=e,
            level="exception",
        )
        flash(_("FatturaPA export failed. Please try again."), "error")
        return redirect(url_for("invoices.view_invoice", invoice_id=invoice_id))


@invoices_bp.route("/invoices/<int:invoice_id>/export/pdf")
@login_required
def export_invoice_pdf(invoice_id):
    """Export invoice as PDF with optional page size selection"""
    current_app.logger.info(
        f"[PDF_EXPORT] Action: export_request, InvoiceID: {invoice_id}, User: {current_user.username}"
    )

    invoice = Invoice.query.get_or_404(invoice_id)
    # Eager-load line item relationships so PDF generator has items, extra_goods, and expenses in session
    # (Invoice uses lazy="dynamic" so joinedload isn't applicable; trigger loads explicitly)
    _eager = invoice.items.all() if hasattr(invoice.items, "all") else list(invoice.items) if invoice.items else []
    _eager = (
        invoice.extra_goods.all()
        if hasattr(invoice.extra_goods, "all")
        else list(invoice.extra_goods) if invoice.extra_goods else []
    )
    if hasattr(invoice, "expenses"):
        _eager = (
            invoice.expenses.all()
            if hasattr(invoice.expenses, "all")
            else list(invoice.expenses) if invoice.expenses else []
        )
    current_app.logger.info(f"[PDF_EXPORT] Invoice found: {invoice.invoice_number}, Status: {invoice.status}")

    if not current_user.is_admin and invoice.created_by != current_user.id:
        current_app.logger.warning(
            f"[PDF_EXPORT] Permission denied - InvoiceID: {invoice_id}, User: {current_user.username}"
        )
        flash(_("You do not have permission to export this invoice"), "error")
        return safe_redirect(
            request.referrer, allow_absolute_same_host=True, fallback=url_for("invoices.list_invoices")
        )

    # Get page size from query parameter, default to A4
    page_size_raw = request.args.get("size", "A4")
    current_app.logger.info(f"[PDF_EXPORT] PageSize from query param: '{page_size_raw}', InvoiceID: {invoice_id}")

    # Validate page size
    valid_sizes = ["A4", "Letter", "Legal", "A3", "A5", "Tabloid"]
    if page_size_raw not in valid_sizes:
        current_app.logger.warning(
            f"[PDF_EXPORT] Invalid page size '{page_size_raw}', defaulting to A4, InvoiceID: {invoice_id}"
        )
        page_size = "A4"
    else:
        page_size = page_size_raw

    current_app.logger.info(
        f"[PDF_EXPORT] Final validated PageSize: '{page_size}', InvoiceID: {invoice_id}, InvoiceNumber: {invoice.invoice_number}"
    )

    try:
        from app.utils.pdf_generator import InvoicePDFGenerator

        settings = Settings.get_settings()
        if getattr(settings, "invoices_zugferd_pdf", False):
            from app.utils.invoice_validators import validate_facturx_prerequisites

            ok, fx_issues = validate_facturx_prerequisites(invoice, settings)
            if not ok:
                for msg in fx_issues[:5]:
                    flash(msg, "error")
                return safe_redirect(
                    request.referrer,
                    allow_absolute_same_host=True,
                    fallback=url_for("invoices.view_invoice", invoice_id=invoice.id),
                )

        current_app.logger.info(
            f"[PDF_EXPORT] Creating InvoicePDFGenerator - PageSize: '{page_size}', InvoiceID: {invoice_id}"
        )
        pdf_generator = InvoicePDFGenerator(invoice, settings=settings, page_size=page_size)
        current_app.logger.info(
            f"[PDF_EXPORT] Starting PDF generation - PageSize: '{page_size}', InvoiceID: {invoice_id}"
        )
        from opentelemetry import trace

        from app.telemetry.otel_setup import business_span, record_invoice_duration_seconds

        _pdf_t0 = time.monotonic()
        with business_span("invoice.generate_pdf", user_id=current_user.id, page_size=page_size):
            pdf_bytes = pdf_generator.generate_pdf()
            trace.get_current_span().set_attribute("pdf_size_bytes", len(pdf_bytes))
        record_invoice_duration_seconds(time.monotonic() - _pdf_t0, "pdf")
        from app.utils.invoice_pdf_postprocess import postprocess_invoice_pdf_bytes

        pdf_bytes, embed_err, pdfa_err = postprocess_invoice_pdf_bytes(pdf_bytes, invoice, settings)
        if embed_err:
            current_app.logger.warning(
                f"[PDF_EXPORT] Factur-X embed failed - InvoiceID: {invoice_id}, Error: {embed_err}"
            )
            flash(
                _(
                    "Factur-X embedding is enabled but failed: %(err)s. Export aborted so the PDF does not ship without embedded XML.",
                    err=embed_err,
                ),
                "error",
            )
            return safe_redirect(
                request.referrer,
                allow_absolute_same_host=True,
                fallback=url_for("invoices.view_invoice", invoice_id=invoice.id),
            )
        if pdfa_err:
            current_app.logger.warning(
                f"[PDF_EXPORT] PDF/A-3 conversion failed - InvoiceID: {invoice_id}, Error: {pdfa_err}"
            )
            flash(
                _("PDF/A-3 normalization failed: %(err)s. Export aborted.", err=pdfa_err),
                "error",
            )
            return safe_redirect(
                request.referrer,
                allow_absolute_same_host=True,
                fallback=url_for("invoices.view_invoice", invoice_id=invoice.id),
            )
        pdf_size_bytes = len(pdf_bytes)
        # Optional: run veraPDF and surface summary (does not block)
        if getattr(settings, "invoices_validate_export", False):
            verapdf_path = (getattr(settings, "invoices_verapdf_path", "") or "").strip()
            if verapdf_path:
                from app.utils.invoice_validators import validate_pdfa_verapdf

                passed, msgs = validate_pdfa_verapdf(pdf_bytes, verapdf_path=verapdf_path)
                if not passed and msgs:
                    flash(_("veraPDF validation reported issues: %(summary)s", summary="; ".join(msgs[:3])), "warning")
                elif passed and msgs:
                    flash(_("veraPDF: %(summary)s", summary=msgs[0] if msgs else "check completed"), "info")
        current_app.logger.info(
            f"[PDF_EXPORT] PDF generation completed successfully - PageSize: '{page_size}', InvoiceID: {invoice_id}, PDFSize: {pdf_size_bytes} bytes"
        )
        # Filename should be template+date+number (invoice number format)
        filename = f"{invoice.invoice_number}.pdf"
        current_app.logger.info(
            f"[PDF_EXPORT] Returning PDF file - Filename: '{filename}', PageSize: '{page_size}', InvoiceID: {invoice_id}"
        )
        return send_file(io.BytesIO(pdf_bytes), mimetype="application/pdf", as_attachment=True, download_name=filename)
    except Exception as e:
        import traceback

        current_app.logger.error(
            f"[PDF_EXPORT] Exception in PDF generation - PageSize: '{page_size}', InvoiceID: {invoice_id}, Error: {str(e)}",
            exc_info=True,
        )
        try:
            current_app.logger.warning(
                f"[PDF_EXPORT] Falling back to InvoicePDFGeneratorFallback - PageSize: '{page_size}', InvoiceID: {invoice_id}"
            )
            from app.utils.pdf_generator_fallback import InvoicePDFGeneratorFallback

            settings = Settings.get_settings()
            pdf_generator = InvoicePDFGeneratorFallback(invoice, settings=settings)
            from opentelemetry import trace

            from app.telemetry.otel_setup import business_span, record_invoice_duration_seconds

            _pdf_t0 = time.monotonic()
            with business_span(
                "invoice.generate_pdf", user_id=current_user.id, page_size=page_size, generator="fallback"
            ):
                pdf_bytes = pdf_generator.generate_pdf()
                trace.get_current_span().set_attribute("pdf_size_bytes", len(pdf_bytes))
            record_invoice_duration_seconds(time.monotonic() - _pdf_t0, "pdf")
            from app.utils.invoice_pdf_postprocess import postprocess_invoice_pdf_bytes

            pdf_bytes, embed_err, pdfa_err = postprocess_invoice_pdf_bytes(pdf_bytes, invoice, settings)
            if embed_err:
                current_app.logger.warning(
                    f"[PDF_EXPORT] Factur-X embed failed (fallback path) - InvoiceID: {invoice_id}, Error: {embed_err}"
                )
                flash(
                    _("Factur-X embedding is enabled but failed: %(err)s. Export aborted.", err=embed_err),
                    "error",
                )
                return safe_redirect(
                    request.referrer,
                    allow_absolute_same_host=True,
                    fallback=url_for("invoices.view_invoice", invoice_id=invoice.id),
                )
            if pdfa_err:
                flash(_("PDF/A-3 normalization failed: %(err)s. Export aborted.", err=pdfa_err), "error")
                return safe_redirect(
                    request.referrer,
                    allow_absolute_same_host=True,
                    fallback=url_for("invoices.view_invoice", invoice_id=invoice.id),
                )
            pdf_size_bytes = len(pdf_bytes)
            current_app.logger.info(
                f"[PDF_EXPORT] Fallback PDF generated successfully - PageSize: '{page_size}', InvoiceID: {invoice_id}, PDFSize: {pdf_size_bytes} bytes"
            )
            # Filename should be template+date+number (invoice number format)
            filename = f"{invoice.invoice_number}.pdf"
            return send_file(
                io.BytesIO(pdf_bytes), mimetype="application/pdf", as_attachment=True, download_name=filename
            )
        except Exception as fallback_error:
            current_app.logger.error(
                f"[PDF_EXPORT] Fallback PDF generation also failed - PageSize: '{page_size}', InvoiceID: {invoice_id}, Error: {str(fallback_error)}",
                exc_info=True,
            )
            flash(_("PDF generation failed. Please try again."), "error")
            return safe_redirect(
                request.referrer,
                allow_absolute_same_host=True,
                fallback=url_for("invoices.view_invoice", invoice_id=invoice.id),
            )


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
    query = Invoice.query
    if not current_user.is_admin:
        query = query.filter_by(created_by=current_user.id)
    project_id = request.args.get("project_id", type=int)
    if project_id:
        query = query.filter_by(project_id=project_id)
    invoices = query.order_by(Invoice.created_at.desc()).all()

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

    # Get recipient email from request (form POST or JSON API)
    data = request.get_json(silent=True) or {}
    recipient_email = (request.form.get("recipient_email") or data.get("recipient_email") or "").strip()
    if not recipient_email:
        recipient_email = (invoice.client_email or "").strip()

    if not recipient_email:
        return jsonify({"error": "Recipient email address is required"}), 400

    # Get custom message if provided
    custom_message = (request.form.get("custom_message") or data.get("custom_message") or "").strip()

    # Get email template ID if provided
    email_template_id = request.form.get("email_template_id", type=int) or data.get("email_template_id")

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
                {
                    "success": True,
                    "message": "Invoice email sent successfully",
                    "invoice_email_id": invoice_email.id if invoice_email else None,
                }
            )
        else:
            return client_error_response("Failed to send invoice email", 500)

    except Exception as e:
        logger.error(f"Error sending invoice email: {type(e).__name__}: {str(e)}")
        logger.exception("Full error traceback:")
        return client_error_response(status=500)


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
            flash("Invoice sent via Peppol", "success")
            return jsonify(
                {"success": True, "message": "Invoice sent via Peppol", "peppol_tx_id": tx.id if tx else None}
            )
        return jsonify({"error": "Failed to send invoice via Peppol", "peppol_tx_id": tx.id if tx else None}), 400
    except Exception as e:
        logger.error(f"Error sending invoice via Peppol: {type(e).__name__}: {str(e)}")
        logger.exception("Full error traceback:")
        return client_error_response(status=500)


@invoices_bp.route("/invoices/<int:invoice_id>/send-sdi", methods=["POST"])
@login_required
def send_invoice_sdi_route(invoice_id):
    """Send invoice via SDI intermediary (FatturaPA)."""
    invoice = Invoice.query.get_or_404(invoice_id)

    if not current_user.is_admin and invoice.created_by != current_user.id:
        return jsonify({"error": "Permission denied"}), 403

    try:
        from app.services import SdiService

        service = SdiService()
        success, tx, _message = service.send_invoice(invoice=invoice, triggered_by_user_id=current_user.id)
        if success:
            flash(_("Invoice sent via SDI"), "success")
            return jsonify({"success": True, "message": "Invoice sent via SDI", "sdi_tx_id": tx.id if tx else None})
        # Static client copy only — do not echo service/exception text (CodeQL).
        return jsonify({"error": "Failed to send invoice via SDI", "sdi_tx_id": tx.id if tx else None}), 400
    except Exception as e:
        logger.error(f"Error sending invoice via SDI: {type(e).__name__}: {str(e)}")
        logger.exception("Full error traceback:")
        return client_error_response(status=500)


@invoices_bp.route("/invoices/sdi/<int:tx_id>/refresh", methods=["POST"])
@login_required
def refresh_sdi_transmission(tx_id):
    """Refresh status of an SDI transmission from the intermediary."""
    from app.models import InvoiceSdiTransmission
    from app.services import SdiService

    tx = InvoiceSdiTransmission.query.get_or_404(tx_id)
    invoice = Invoice.query.get_or_404(tx.invoice_id)
    if not current_user.is_admin and invoice.created_by != current_user.id:
        return jsonify({"error": "Permission denied"}), 403

    result = SdiService().refresh_status(tx)
    if not result.get("ok"):
        # Do not forward intermediary/exception detail to the browser (CodeQL).
        return jsonify({"error": "Refresh failed"}), 400
    return jsonify({"success": True, "status": result.get("status"), "transmission": tx.to_dict()})


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
                {
                    "success": True,
                    "message": "Invoice email resent successfully",
                    "invoice_email_id": invoice_email.id if invoice_email else None,
                }
            )
        else:
            return client_error_response("Failed to resend invoice email", 500)

    except Exception as e:
        logger.error(f"Error resending invoice email: {type(e).__name__}: {str(e)}")
        logger.exception("Full error traceback:")
        return client_error_response(status=500)


@invoices_bp.route("/invoices/<int:invoice_id>/images/upload", methods=["POST"])
@login_required
def upload_invoice_image(invoice_id):
    """Upload a decorative image to an invoice"""
    import os
    from datetime import datetime
    from decimal import Decimal

    from werkzeug.utils import secure_filename

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
            return (
                jsonify({"error": f"File size exceeds maximum allowed size ({MAX_FILE_SIZE / (1024*1024):.0f} MB)"}),
                400,
            )
        flash(_("File size exceeds maximum allowed size (5 MB)"), "error")
        return redirect(url_for("invoices.edit_invoice", invoice_id=invoice_id))

    # Save file
    from app.utils.paths import PathEscapeError, safe_path_under

    original_filename = secure_filename(file.filename)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = secure_filename(f"{invoice_id}_{timestamp}_{original_filename}")
    if not filename:
        if request.is_json:
            return jsonify({"error": "Invalid filename"}), 400
        flash(_("Invalid filename"), "error")
        return redirect(url_for("invoices.edit_invoice", invoice_id=invoice_id))

    # Ensure upload directory exists
    upload_dir = os.path.join(current_app.root_path, "..", UPLOAD_FOLDER)
    os.makedirs(upload_dir, exist_ok=True)

    try:
        file_path = safe_path_under(upload_dir, filename)
        file.save(file_path)
    except PathEscapeError:
        if request.is_json:
            return jsonify({"error": "Invalid upload path"}), 400
        flash(_("Invalid upload path"), "error")
        return redirect(url_for("invoices.edit_invoice", invoice_id=invoice_id))

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
            # Best-effort cleanup of orphaned upload after DB failure.
            current_app.logger.debug("Could not remove orphaned invoice image %s", file_path, exc_info=True)
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

    from app.utils.paths import PathEscapeError, resolve_stored_upload_path

    try:
        file_path = resolve_stored_upload_path(current_app.root_path, image.file_path)
        if os.path.exists(file_path):
            os.remove(file_path)
    except (PathEscapeError, OSError) as e:
        current_app.logger.warning(f"Failed to delete image file: {e}")

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
    import base64
    import mimetypes
    import os

    from flask import send_file

    invoice = Invoice.query.get_or_404(invoice_id)
    image = InvoiceImage.query.filter_by(id=image_id, invoice_id=invoice_id).first_or_404()

    # Check permissions
    if not current_user.is_admin and invoice.created_by != current_user.id:
        return jsonify({"error": "Permission denied"}), 403

    from app.utils.paths import PathEscapeError, resolve_stored_upload_path

    try:
        file_path = resolve_stored_upload_path(current_app.root_path, image.file_path)
    except PathEscapeError:
        return jsonify({"error": "File not found"}), 404
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

            return jsonify(
                {
                    "success": True,
                    "data_uri": f"data:{mime_type};base64,{image_data}",
                    "mime_type": mime_type,
                }
            )
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


@invoices_bp.route("/invoices/peppol-inbox")
@login_required
@module_enabled("invoices")
def peppol_inbox():
    """List inbound Peppol documents received via the bridge inbox."""
    status = (request.args.get("status") or "").strip().lower()
    query = PeppolInboundDocument.query.order_by(PeppolInboundDocument.created_at.desc())
    if status in {"new", "acknowledged", "error"}:
        query = query.filter(PeppolInboundDocument.status == status)
    documents = query.limit(200).all()
    settings = Settings.get_settings()
    inbox_enabled = bool(getattr(settings, "peppol_inbox_enabled", False))
    return render_template(
        "invoices/peppol_inbox.html",
        documents=documents,
        status_filter=status,
        inbox_enabled=inbox_enabled,
    )


@invoices_bp.route("/invoices/peppol-inbox/<int:doc_id>")
@login_required
@module_enabled("invoices")
def peppol_inbox_detail(doc_id: int):
    doc = PeppolInboundDocument.query.get_or_404(doc_id)
    return render_template("invoices/peppol_inbox_detail.html", document=doc)


@invoices_bp.route("/invoices/peppol-inbox/<int:doc_id>/ubl")
@login_required
@module_enabled("invoices")
def peppol_inbox_download_ubl(doc_id: int):
    doc = PeppolInboundDocument.query.get_or_404(doc_id)
    if not doc.ubl_xml:
        flash(_("No UBL XML is stored for this document."), "error")
        return redirect(url_for("invoices.peppol_inbox_detail", doc_id=doc.id))
    filename = f"{doc.document_number or doc.external_id or 'inbound'}.xml"
    return Response(
        doc.ubl_xml,
        mimetype="application/xml",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@invoices_bp.route("/invoices/peppol-inbox/poll", methods=["POST"])
@login_required
@module_enabled("invoices")
def peppol_inbox_poll_now():
    """Manually trigger an inbox poll (admins / invoice managers)."""
    if not (getattr(current_user, "is_admin", False) or current_user.has_permission("manage_invoices")):
        flash(_("You do not have permission to poll the Peppol inbox."), "error")
        return redirect(url_for("invoices.peppol_inbox"))
    try:
        from app.services.peppol_inbound_service import PeppolInboundService

        result = PeppolInboundService().poll_and_import()
        if result.get("skipped"):
            flash(_("Peppol inbox polling is disabled. Enable it in Peppol settings."), "warning")
        elif result.get("ok"):
            flash(
                _("Peppol inbox poll finished: %(fetched)s fetched, %(created)s new, %(updated)s updated.")
                % {
                    "fetched": result.get("fetched", 0),
                    "created": result.get("created", 0),
                    "updated": result.get("updated", 0),
                },
                "success",
            )
        else:
            flash(_("Peppol inbox poll completed with errors."), "warning")
    except Exception:
        current_app.logger.exception("Manual Peppol inbox poll failed")
        flash(_("Failed to poll Peppol inbox."), "error")
    return redirect(url_for("invoices.peppol_inbox"))
