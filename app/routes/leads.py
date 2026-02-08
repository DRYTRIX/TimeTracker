"""Routes for lead management"""

from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_babel import gettext as _
from flask_login import login_required, current_user
from app import db
from app.models import Lead, LeadActivity, Client, Deal
from app.utils.db import safe_commit
from app.utils.timezone import parse_local_datetime
from app.utils.module_helpers import module_enabled
from datetime import datetime
from decimal import Decimal, InvalidOperation

leads_bp = Blueprint("leads", __name__)

# Lead statuses
LEAD_STATUSES = ["new", "contacted", "qualified", "converted", "lost"]

# Pipeline stages for convert-to-deal (must match deals module)
PIPELINE_STAGES = ["prospecting", "qualification", "proposal", "negotiation", "closed_won", "closed_lost"]


@leads_bp.route("/leads")
@login_required
@module_enabled("leads")
def list_leads():
    """List all leads"""
    status = request.args.get("status", "")
    source = request.args.get("source", "")
    owner_id = request.args.get("owner", "")
    search = request.args.get("search", "").strip()

    query = Lead.query

    if status:
        query = query.filter_by(status=status)
    else:
        # Default to active leads (not converted or lost)
        query = query.filter(~Lead.status.in_(["converted", "lost"]))

    if source:
        query = query.filter_by(source=source)

    if owner_id:
        try:
            query = query.filter_by(owner_id=int(owner_id))
        except (ValueError, TypeError):
            pass

    if search:
        like = f"%{search}%"
        query = query.filter(
            db.or_(
                Lead.first_name.ilike(like),
                Lead.last_name.ilike(like),
                Lead.company_name.ilike(like),
                Lead.email.ilike(like),
            )
        )

    leads = query.order_by(Lead.score.desc(), Lead.created_at.desc()).all()

    return render_template(
        "leads/list.html",
        leads=leads,
        lead_statuses=LEAD_STATUSES,
        status=status,
        source=source,
        owner_id=owner_id,
        search=search,
    )


@leads_bp.route("/leads/create", methods=["GET", "POST"])
@login_required
def create_lead():
    """Create a new lead"""
    if request.method == "POST":
        try:
            # Parse estimated value
            value_str = request.form.get("estimated_value", "").strip()
            estimated_value = None
            if value_str:
                try:
                    estimated_value = Decimal(value_str)
                except (InvalidOperation, ValueError):
                    pass

            lead = Lead(
                first_name=request.form.get("first_name", "").strip(),
                last_name=request.form.get("last_name", "").strip(),
                created_by=current_user.id,
                company_name=request.form.get("company_name", "").strip() or None,
                email=request.form.get("email", "").strip() or None,
                phone=request.form.get("phone", "").strip() or None,
                title=request.form.get("title", "").strip() or None,
                source=request.form.get("source", "").strip() or None,
                status=request.form.get("status", "new").strip(),
                score=int(request.form.get("score", 0)),
                estimated_value=estimated_value,
                currency_code=request.form.get("currency_code", "EUR").strip(),
                notes=request.form.get("notes", "").strip() or None,
                tags=request.form.get("tags", "").strip() or None,
                owner_id=int(request.form.get("owner_id")) if request.form.get("owner_id") else current_user.id,
            )

            db.session.add(lead)

            if safe_commit():
                flash(_("Lead created successfully"), "success")
                return redirect(url_for("leads.view_lead", lead_id=lead.id))
        except Exception as e:
            db.session.rollback()
            flash(_("Error creating lead: %(error)s", error=str(e)), "error")

    return render_template("leads/form.html", lead=None, lead_statuses=LEAD_STATUSES)


@leads_bp.route("/leads/<int:lead_id>")
@login_required
def view_lead(lead_id):
    """View a lead"""
    lead = Lead.query.get_or_404(lead_id)
    activities = (
        LeadActivity.query.filter_by(lead_id=lead_id).order_by(LeadActivity.activity_date.desc()).limit(50).all()
    )
    return render_template("leads/view.html", lead=lead, activities=activities)


@leads_bp.route("/leads/<int:lead_id>/edit", methods=["GET", "POST"])
@login_required
def edit_lead(lead_id):
    """Edit a lead"""
    lead = Lead.query.get_or_404(lead_id)

    if request.method == "POST":
        try:
            # Parse estimated value
            value_str = request.form.get("estimated_value", "").strip()
            estimated_value = None
            if value_str:
                try:
                    estimated_value = Decimal(value_str)
                except (InvalidOperation, ValueError):
                    pass

            lead.first_name = request.form.get("first_name", "").strip()
            lead.last_name = request.form.get("last_name", "").strip()
            lead.company_name = request.form.get("company_name", "").strip() or None
            lead.email = request.form.get("email", "").strip() or None
            lead.phone = request.form.get("phone", "").strip() or None
            lead.title = request.form.get("title", "").strip() or None
            lead.source = request.form.get("source", "").strip() or None
            lead.status = request.form.get("status", "new").strip()
            lead.score = int(request.form.get("score", 0))
            lead.estimated_value = estimated_value
            lead.currency_code = request.form.get("currency_code", "EUR").strip()
            lead.notes = request.form.get("notes", "").strip() or None
            lead.tags = request.form.get("tags", "").strip() or None
            lead.owner_id = int(request.form.get("owner_id")) if request.form.get("owner_id") else current_user.id
            lead.updated_at = datetime.utcnow()

            if safe_commit():
                flash(_("Lead updated successfully"), "success")
                return redirect(url_for("leads.view_lead", lead_id=lead_id))
        except Exception as e:
            db.session.rollback()
            flash(_("Error updating lead: %(error)s", error=str(e)), "error")

    return render_template("leads/form.html", lead=lead, lead_statuses=LEAD_STATUSES)


@leads_bp.route("/leads/<int:lead_id>/convert-to-client", methods=["GET", "POST"])
@login_required
def convert_to_client(lead_id):
    """Convert a lead to a client"""
    lead = Lead.query.get_or_404(lead_id)

    if lead.is_converted:
        flash(_("Lead has already been converted"), "error")
        return redirect(url_for("leads.view_lead", lead_id=lead_id))

    if request.method == "POST":
        try:
            # Create new client from lead
            from app.models import Client

            client = Client(
                name=lead.company_name or f"{lead.first_name} {lead.last_name}",
                contact_person=f"{lead.first_name} {lead.last_name}",
                email=lead.email,
                phone=lead.phone,
                description=f"Converted from lead: {lead.display_name}",
                status="active",
            )

            db.session.add(client)
            db.session.flush()  # Get client ID

            # Convert lead
            lead.convert_to_client(client.id, current_user.id)

            # Create primary contact from lead
            from app.models import Contact

            contact = Contact(
                client_id=client.id,
                first_name=lead.first_name,
                last_name=lead.last_name,
                email=lead.email,
                phone=lead.phone,
                title=lead.title,
                is_primary=True,
                created_by=current_user.id,
            )
            db.session.add(contact)

            if safe_commit():
                flash(_("Lead converted to client successfully"), "success")
                return redirect(url_for("clients.view_client", client_id=client.id))
        except Exception as e:
            db.session.rollback()
            flash(_("Error converting lead: %(error)s", error=str(e)), "error")

    return render_template("leads/convert_to_client.html", lead=lead)


@leads_bp.route("/leads/<int:lead_id>/convert-to-deal", methods=["GET", "POST"])
@login_required
def convert_to_deal(lead_id):
    """Convert a lead to a deal"""
    lead = Lead.query.get_or_404(lead_id)

    if lead.is_converted:
        flash(_("Lead has already been converted"), "error")
        return redirect(url_for("leads.view_lead", lead_id=lead_id))

    if request.method == "POST":
        try:
            # Create new deal from lead
            deal = Deal(
                name=request.form.get("name", f"Deal: {lead.display_name}").strip(),
                created_by=current_user.id,
                lead_id=lead_id,
                client_id=int(request.form.get("client_id")) if request.form.get("client_id") else None,
                description=request.form.get("description", "").strip() or None,
                stage=request.form.get("stage", "prospecting").strip(),
                value=lead.estimated_value,
                currency_code=lead.currency_code,
                probability=int(request.form.get("probability", 50)),
                notes=lead.notes,
                owner_id=current_user.id,
            )

            # Parse expected close date
            close_date_str = request.form.get("expected_close_date", "").strip()
            if close_date_str:
                try:
                    deal.expected_close_date = datetime.strptime(close_date_str, "%Y-%m-%d").date()
                except ValueError:
                    pass

            db.session.add(deal)
            db.session.flush()  # Get deal ID

            # Convert lead
            lead.convert_to_deal(deal.id, current_user.id)

            if safe_commit():
                flash(_("Lead converted to deal successfully"), "success")
                return redirect(url_for("deals.view_deal", deal_id=deal.id))
        except Exception as e:
            db.session.rollback()
            flash(_("Error converting lead: %(error)s", error=str(e)), "error")

    # Get clients for selection
    clients = Client.query.filter_by(status="active").order_by(Client.name).all()

    return render_template(
        "leads/convert_to_deal.html",
        lead=lead,
        clients=clients,
        pipeline_stages=PIPELINE_STAGES,
    )


@leads_bp.route("/leads/<int:lead_id>/mark-lost", methods=["POST"])
@login_required
def mark_lost(lead_id):
    """Mark a lead as lost"""
    lead = Lead.query.get_or_404(lead_id)

    try:
        lead.mark_lost()

        if safe_commit():
            flash(_("Lead marked as lost"), "success")
    except Exception as e:
        db.session.rollback()
        flash(_("Error marking lead as lost: %(error)s", error=str(e)), "error")

    return redirect(url_for("leads.view_lead", lead_id=lead_id))


@leads_bp.route("/leads/<int:lead_id>/activities/create", methods=["GET", "POST"])
@login_required
def create_activity(lead_id):
    """Create an activity for a lead"""
    lead = Lead.query.get_or_404(lead_id)

    if request.method == "POST":
        try:
            activity_date_str = request.form.get("activity_date", "")
            activity_date = parse_local_datetime(activity_date_str) if activity_date_str else datetime.utcnow()

            due_date_str = request.form.get("due_date", "")
            due_date = parse_local_datetime(due_date_str) if due_date_str else None

            activity = LeadActivity(
                lead_id=lead_id,
                type=request.form.get("type", "note").strip(),
                created_by=current_user.id,
                subject=request.form.get("subject", "").strip() or None,
                description=request.form.get("description", "").strip() or None,
                activity_date=activity_date,
                due_date=due_date,
                status=request.form.get("status", "completed").strip() or "completed",
            )

            db.session.add(activity)

            if safe_commit():
                flash(_("Activity recorded successfully"), "success")
                return redirect(url_for("leads.view_lead", lead_id=lead_id))
        except Exception as e:
            db.session.rollback()
            flash(_("Error recording activity: %(error)s", error=str(e)), "error")

    return render_template("leads/activity_form.html", lead=lead, activity=None)
