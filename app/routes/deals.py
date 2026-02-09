"""Routes for deal/sales pipeline management"""

from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_babel import gettext as _
from flask_login import login_required, current_user
from app import db
from app.models import Deal, DealActivity, Client, Contact, Lead, Quote, Project
from app.models.audit_log import AuditLog
from app.utils.db import safe_commit
from app.utils.timezone import parse_local_datetime_from_string
from app.utils.module_helpers import module_enabled
from datetime import datetime, date
from decimal import Decimal, InvalidOperation

deals_bp = Blueprint("deals", __name__)

# Pipeline stages
PIPELINE_STAGES = ["prospecting", "qualification", "proposal", "negotiation", "closed_won", "closed_lost"]


@deals_bp.route("/deals")
@login_required
@module_enabled("deals")
def list_deals():
    """List all deals with pipeline view"""
    status = request.args.get("status", "open")
    stage = request.args.get("stage", "")
    owner_id = request.args.get("owner", "")

    query = Deal.query

    if status == "open":
        query = query.filter_by(status="open")
    elif status == "won":
        query = query.filter_by(status="won")
    elif status == "lost":
        query = query.filter_by(status="lost")

    if stage:
        query = query.filter_by(stage=stage)

    if owner_id:
        try:
            query = query.filter_by(owner_id=int(owner_id))
        except (ValueError, TypeError):
            pass

    deals = query.order_by(Deal.expected_close_date, Deal.created_at.desc()).all()

    # Group deals by stage for pipeline view
    deals_by_stage = {}
    for stage_name in PIPELINE_STAGES:
        deals_by_stage[stage_name] = [d for d in deals if d.stage == stage_name]

    return render_template(
        "deals/list.html",
        deals=deals,
        deals_by_stage=deals_by_stage,
        pipeline_stages=PIPELINE_STAGES,
        status=status,
        stage=stage,
        owner_id=owner_id,
    )


@deals_bp.route("/deals/pipeline")
@login_required
def pipeline_view():
    """Visual pipeline view of deals"""
    owner_id = request.args.get("owner", "")

    query = Deal.query.filter_by(status="open")

    if owner_id:
        try:
            query = query.filter_by(owner_id=int(owner_id))
        except (ValueError, TypeError):
            pass

    deals = query.all()

    # Group deals by stage
    deals_by_stage = {}
    for stage_name in PIPELINE_STAGES:
        deals_by_stage[stage_name] = [d for d in deals if d.stage == stage_name]

    return render_template(
        "deals/pipeline.html", deals_by_stage=deals_by_stage, pipeline_stages=PIPELINE_STAGES, owner_id=owner_id
    )


@deals_bp.route("/deals/create", methods=["GET", "POST"])
@login_required
def create_deal():
    """Create a new deal"""
    if request.method == "POST":
        try:
            # Parse value
            value_str = request.form.get("value", "").strip()
            value = None
            if value_str:
                try:
                    value = Decimal(value_str)
                except (InvalidOperation, ValueError):
                    flash(_("Invalid deal value"), "error")
                    return redirect(url_for("deals.create_deal"))

            # Parse expected close date
            close_date_str = request.form.get("expected_close_date", "").strip()
            expected_close_date = None
            if close_date_str:
                try:
                    expected_close_date = datetime.strptime(close_date_str, "%Y-%m-%d").date()
                except ValueError:
                    pass

            deal = Deal(
                name=request.form.get("name", "").strip(),
                created_by=current_user.id,
                client_id=int(request.form.get("client_id")) if request.form.get("client_id") else None,
                contact_id=int(request.form.get("contact_id")) if request.form.get("contact_id") else None,
                lead_id=int(request.form.get("lead_id")) if request.form.get("lead_id") else None,
                description=request.form.get("description", "").strip() or None,
                stage=request.form.get("stage", "prospecting").strip(),
                value=value,
                currency_code=request.form.get("currency_code", "EUR").strip(),
                probability=int(request.form.get("probability", 50)),
                expected_close_date=expected_close_date,
                related_quote_id=(
                    int(request.form.get("related_quote_id")) if request.form.get("related_quote_id") else None
                ),
                related_project_id=(
                    int(request.form.get("related_project_id")) if request.form.get("related_project_id") else None
                ),
                notes=request.form.get("notes", "").strip() or None,
                owner_id=int(request.form.get("owner_id")) if request.form.get("owner_id") else current_user.id,
            )

            db.session.add(deal)

            if safe_commit():
                flash(_("Deal created successfully"), "success")
                return redirect(url_for("deals.view_deal", deal_id=deal.id))
        except Exception as e:
            db.session.rollback()
            flash(_("Error creating deal: %(error)s", error=str(e)), "error")

    # Get data for form
    clients = Client.query.filter_by(status="active").order_by(Client.name).all()
    quotes = Quote.query.filter_by(status="sent").order_by(Quote.created_at.desc()).all()
    leads = Lead.query.filter(~Lead.status.in_(["converted", "lost"])).order_by(Lead.created_at.desc()).all()

    return render_template(
        "deals/form.html", deal=None, clients=clients, quotes=quotes, leads=leads, pipeline_stages=PIPELINE_STAGES
    )


@deals_bp.route("/deals/<int:deal_id>")
@login_required
def view_deal(deal_id):
    """View a deal"""
    deal = Deal.query.get_or_404(deal_id)
    activities = (
        DealActivity.query.filter_by(deal_id=deal_id).order_by(DealActivity.activity_date.desc()).limit(50).all()
    )
    audit_logs = (
        AuditLog.query.filter_by(entity_type="Deal", entity_id=deal_id)
        .order_by(AuditLog.created_at.desc())
        .limit(25)
        .all()
    )
    return render_template("deals/view.html", deal=deal, activities=activities, audit_logs=audit_logs)


@deals_bp.route("/deals/<int:deal_id>/edit", methods=["GET", "POST"])
@login_required
def edit_deal(deal_id):
    """Edit a deal"""
    deal = Deal.query.get_or_404(deal_id)

    if request.method == "POST":
        try:
            # Parse value
            value_str = request.form.get("value", "").strip()
            value = None
            if value_str:
                try:
                    value = Decimal(value_str)
                except (InvalidOperation, ValueError):
                    flash(_("Invalid deal value"), "error")
                    return redirect(url_for("deals.edit_deal", deal_id=deal_id))

            # Parse expected close date
            close_date_str = request.form.get("expected_close_date", "").strip()
            expected_close_date = None
            if close_date_str:
                try:
                    expected_close_date = datetime.strptime(close_date_str, "%Y-%m-%d").date()
                except ValueError:
                    pass

            deal.name = request.form.get("name", "").strip()
            deal.client_id = int(request.form.get("client_id")) if request.form.get("client_id") else None
            deal.contact_id = int(request.form.get("contact_id")) if request.form.get("contact_id") else None
            deal.description = request.form.get("description", "").strip() or None
            deal.stage = request.form.get("stage", "prospecting").strip()
            deal.value = value
            deal.currency_code = request.form.get("currency_code", "EUR").strip()
            deal.probability = int(request.form.get("probability", 50))
            deal.expected_close_date = expected_close_date
            deal.related_quote_id = (
                int(request.form.get("related_quote_id")) if request.form.get("related_quote_id") else None
            )
            deal.related_project_id = (
                int(request.form.get("related_project_id")) if request.form.get("related_project_id") else None
            )
            deal.notes = request.form.get("notes", "").strip() or None
            deal.owner_id = int(request.form.get("owner_id")) if request.form.get("owner_id") else current_user.id
            deal.updated_at = datetime.utcnow()

            if safe_commit():
                flash(_("Deal updated successfully"), "success")
                return redirect(url_for("deals.view_deal", deal_id=deal_id))
        except Exception as e:
            db.session.rollback()
            flash(_("Error updating deal: %(error)s", error=str(e)), "error")

    # Get data for form
    clients = Client.query.filter_by(status="active").order_by(Client.name).all()
    contacts = Contact.query.filter_by(client_id=deal.client_id, is_active=True).all() if deal.client_id else []
    quotes = Quote.query.filter_by(status="sent").order_by(Quote.created_at.desc()).all()

    return render_template(
        "deals/form.html", deal=deal, clients=clients, contacts=contacts, quotes=quotes, pipeline_stages=PIPELINE_STAGES
    )


@deals_bp.route("/deals/<int:deal_id>/close-won", methods=["POST"])
@login_required
def close_won(deal_id):
    """Close deal as won"""
    deal = Deal.query.get_or_404(deal_id)

    try:
        close_date_str = request.form.get("close_date", "").strip()
        close_date = None
        if close_date_str:
            try:
                close_date = datetime.strptime(close_date_str, "%Y-%m-%d").date()
            except ValueError:
                pass

        deal.close_won(close_date)

        if safe_commit():
            flash(_("Deal closed as won"), "success")
    except Exception as e:
        db.session.rollback()
        flash(_("Error closing deal: %(error)s", error=str(e)), "error")

    return redirect(url_for("deals.view_deal", deal_id=deal_id))


@deals_bp.route("/deals/<int:deal_id>/close-lost", methods=["POST"])
@login_required
def close_lost(deal_id):
    """Close deal as lost"""
    deal = Deal.query.get_or_404(deal_id)

    try:
        reason = request.form.get("loss_reason", "").strip() or None

        close_date_str = request.form.get("close_date", "").strip()
        close_date = None
        if close_date_str:
            try:
                close_date = datetime.strptime(close_date_str, "%Y-%m-%d").date()
            except ValueError:
                pass

        deal.close_lost(reason, close_date)

        if safe_commit():
            flash(_("Deal closed as lost"), "success")
    except Exception as e:
        db.session.rollback()
        flash(_("Error closing deal: %(error)s", error=str(e)), "error")

    return redirect(url_for("deals.view_deal", deal_id=deal_id))


@deals_bp.route("/deals/<int:deal_id>/activities/create", methods=["GET", "POST"])
@login_required
def create_activity(deal_id):
    """Create an activity for a deal"""
    deal = Deal.query.get_or_404(deal_id)

    if request.method == "POST":
        try:
            activity_date_str = request.form.get("activity_date", "")
            activity_date = parse_local_datetime_from_string(activity_date_str) if activity_date_str else datetime.utcnow()
            if activity_date is None:
                activity_date = datetime.utcnow()

            due_date_str = request.form.get("due_date", "")
            due_date = parse_local_datetime_from_string(due_date_str) if due_date_str else None

            activity = DealActivity(
                deal_id=deal_id,
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
                return redirect(url_for("deals.view_deal", deal_id=deal_id))
        except Exception as e:
            db.session.rollback()
            flash(_("Error recording activity: %(error)s", error=str(e)), "error")

    return render_template("deals/activity_form.html", deal=deal, activity=None)


@deals_bp.route("/api/deals/<int:deal_id>/contacts")
@login_required
def get_deal_contacts(deal_id):
    """API endpoint to get contacts for a deal's client"""
    deal = Deal.query.get_or_404(deal_id)

    if not deal.client_id:
        return jsonify({"contacts": []})

    contacts = Contact.query.filter_by(client_id=deal.client_id, is_active=True).all()
    return jsonify({"contacts": [c.to_dict() for c in contacts]})
