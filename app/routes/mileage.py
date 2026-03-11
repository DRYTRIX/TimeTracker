from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, send_file, current_app
from flask_babel import gettext as _
from flask_login import login_required, current_user
from app import db, log_event, track_event
from app.models import Mileage, Project, Client, Expense, Settings
from app.constants import SUPPORTED_CURRENCIES
from datetime import datetime, date, timedelta
from decimal import Decimal
from app.utils.db import safe_commit
from app.utils.module_helpers import module_enabled
import csv
import io

mileage_bp = Blueprint("mileage", __name__)


@mileage_bp.route("/mileage")
@login_required
@module_enabled("mileage")
def list_mileage():
    """List all mileage entries with filters"""
    from app.utils.client_lock import enforce_locked_client_id
    from app import track_page_view

    track_page_view("mileage_list")

    page = request.args.get("page", 1, type=int)
    per_page = request.args.get("per_page", 25, type=int)

    # Filter parameters
    status = request.args.get("status", "").strip()
    project_id = request.args.get("project_id", type=int)
    client_id = request.args.get("client_id", type=int)
    client_id = enforce_locked_client_id(client_id)
    start_date = request.args.get("start_date", "").strip()
    end_date = request.args.get("end_date", "").strip()
    search = request.args.get("search", "").strip()

    # Build query
    query = Mileage.query

    # Non-admin users can only see their own mileage or mileage they approved
    if not current_user.is_admin:
        query = query.filter(db.or_(Mileage.user_id == current_user.id, Mileage.approved_by == current_user.id))

    # Apply filters
    if status:
        query = query.filter(Mileage.status == status)

    if project_id:
        query = query.filter(Mileage.project_id == project_id)

    if client_id:
        query = query.filter(Mileage.client_id == client_id)

    if start_date:
        try:
            start = datetime.strptime(start_date, "%Y-%m-%d").date()
            query = query.filter(Mileage.trip_date >= start)
        except ValueError:
            pass

    if end_date:
        try:
            end = datetime.strptime(end_date, "%Y-%m-%d").date()
            query = query.filter(Mileage.trip_date <= end)
        except ValueError:
            pass

    if search:
        like = f"%{search}%"
        query = query.filter(
            db.or_(
                Mileage.purpose.ilike(like),
                Mileage.description.ilike(like),
                Mileage.start_location.ilike(like),
                Mileage.end_location.ilike(like),
            )
        )

    # Paginate
    mileage_pagination = query.order_by(Mileage.trip_date.desc()).paginate(
        page=page, per_page=per_page, error_out=False
    )

    # Get filter options
    projects = Project.query.filter_by(status="active").order_by(Project.name).all()
    clients = Client.get_active_clients()
    only_one_client = len(clients) == 1
    single_client = clients[0] if only_one_client else None

    # Calculate totals
    start_date_obj = None
    end_date_obj = None

    if start_date:
        try:
            start_date_obj = datetime.strptime(start_date, "%Y-%m-%d").date()
        except ValueError:
            pass

    if end_date:
        try:
            end_date_obj = datetime.strptime(end_date, "%Y-%m-%d").date()
        except ValueError:
            pass

    total_distance = Mileage.get_total_distance(
        user_id=None if current_user.is_admin else current_user.id, start_date=start_date_obj, end_date=end_date_obj
    )

    total_amount_query = db.session.query(
        db.func.sum(Mileage.calculated_amount * db.case((Mileage.is_round_trip, 2), else_=1))
    ).filter(Mileage.status.in_(["approved", "reimbursed"]))

    if not current_user.is_admin:
        total_amount_query = total_amount_query.filter(Mileage.user_id == current_user.id)

    total_amount = total_amount_query.scalar() or 0

    settings = Settings.get_settings()
    currency = settings.currency if settings else "EUR"

    return render_template(
        "mileage/list.html",
        mileage_entries=mileage_pagination.items,
        pagination=mileage_pagination,
        projects=projects,
        clients=clients,
        only_one_client=only_one_client,
        single_client=single_client,
        total_distance=total_distance,
        total_amount=float(total_amount),
        currency=currency,
        # Pass back filter values
        status=status,
        project_id=project_id,
        client_id=client_id,
        start_date=start_date,
        end_date=end_date,
        search=search,
    )


def _mileage_export_query():
    """Build the same filtered query as list_mileage (no pagination). Caller must apply .all()."""
    from app.utils.client_lock import enforce_locked_client_id
    from sqlalchemy.orm import joinedload

    status = request.args.get("status", "").strip()
    project_id = request.args.get("project_id", type=int)
    client_id = request.args.get("client_id", type=int)
    client_id = enforce_locked_client_id(client_id)
    start_date = request.args.get("start_date", "").strip()
    end_date = request.args.get("end_date", "").strip()
    search = request.args.get("search", "").strip()

    query = Mileage.query.options(
        joinedload(Mileage.user),
        joinedload(Mileage.project),
        joinedload(Mileage.client),
    )

    if not current_user.is_admin:
        query = query.filter(db.or_(Mileage.user_id == current_user.id, Mileage.approved_by == current_user.id))

    if status:
        query = query.filter(Mileage.status == status)
    if project_id:
        query = query.filter(Mileage.project_id == project_id)
    if client_id:
        query = query.filter(Mileage.client_id == client_id)
    if start_date:
        try:
            start = datetime.strptime(start_date, "%Y-%m-%d").date()
            query = query.filter(Mileage.trip_date >= start)
        except ValueError:
            pass
    if end_date:
        try:
            end = datetime.strptime(end_date, "%Y-%m-%d").date()
            query = query.filter(Mileage.trip_date <= end)
        except ValueError:
            pass
    if search:
        like = f"%{search}%"
        query = query.filter(
            db.or_(
                Mileage.purpose.ilike(like),
                Mileage.description.ilike(like),
                Mileage.start_location.ilike(like),
                Mileage.end_location.ilike(like),
            )
        )

    return query.order_by(Mileage.trip_date.desc())


@mileage_bp.route("/mileage/export/csv")
@login_required
@module_enabled("mileage")
def export_mileage_csv():
    """Export (filtered) mileage entries as CSV. Uses same filters as list_mileage."""
    query = _mileage_export_query()
    entries = query.all()

    settings = Settings.get_settings()
    delimiter = getattr(settings, "export_delimiter", ",") or ","
    output = io.StringIO()
    writer = csv.writer(output, delimiter=delimiter)

    writer.writerow(
        [
            "ID",
            "Date",
            "User",
            "Purpose",
            "Start Location",
            "End Location",
            "Distance (km)",
            "Rate per km",
            "Amount",
            "Round Trip",
            "Status",
            "Project",
            "Client",
            "Notes",
        ]
    )

    for entry in entries:
        multiplier = 2 if entry.is_round_trip else 1
        amount = float(entry.calculated_amount or 0) * multiplier
        writer.writerow(
            [
                entry.id,
                entry.trip_date.isoformat() if entry.trip_date else "",
                (entry.user.display_name if entry.user else ""),
                entry.purpose or "",
                entry.start_location or "",
                entry.end_location or "",
                float(entry.distance_km or 0),
                float(entry.rate_per_km or 0),
                amount,
                "Yes" if entry.is_round_trip else "No",
                entry.status or "",
                (entry.project.name if entry.project else ""),
                (entry.client.name if entry.client else ""),
                entry.notes or "",
            ]
        )

    csv_bytes = output.getvalue().encode("utf-8")
    start_part = request.args.get("start_date", "") or "all"
    end_part = request.args.get("end_date", "") or "all"
    filename = f"mileage_export_{start_part}_to_{end_part}.csv"

    return send_file(
        io.BytesIO(csv_bytes),
        mimetype="text/csv",
        as_attachment=True,
        download_name=filename,
    )


@mileage_bp.route("/mileage/export/pdf")
@login_required
@module_enabled("mileage")
def export_mileage_pdf():
    """Export (filtered) mileage entries as PDF. Uses same filters as list_mileage."""
    query = _mileage_export_query()
    entries = query.all()

    start_date = request.args.get("start_date", "").strip() or None
    end_date = request.args.get("end_date", "").strip() or None

    pdf_filters = {}
    if request.args.get("status"):
        pdf_filters["Status"] = request.args.get("status")
    if request.args.get("project_id", type=int):
        proj = Project.query.get(request.args.get("project_id", type=int))
        if proj:
            pdf_filters["Project"] = proj.name
    if request.args.get("client_id", type=int):
        cli = Client.query.get(request.args.get("client_id", type=int))
        if cli:
            pdf_filters["Client"] = cli.name

    try:
        from app.utils.mileage_pdf import build_mileage_pdf
        pdf_bytes = build_mileage_pdf(
            entries,
            start_date=start_date,
            end_date=end_date,
            filters=pdf_filters if pdf_filters else None,
        )
    except Exception as e:
        current_app.logger.warning("Mileage PDF export failed: %s", e, exc_info=True)
        flash(_("PDF export failed: %(error)s", error=str(e)), "error")
        return redirect(url_for("mileage.list_mileage"))

    start_part = start_date or "all"
    end_part = end_date or "all"
    filename = f"mileage_export_{start_part}_to_{end_part}.pdf"

    return send_file(
        io.BytesIO(pdf_bytes),
        mimetype="application/pdf",
        as_attachment=True,
        download_name=filename,
    )


@mileage_bp.route("/mileage/create", methods=["GET", "POST"])
@login_required
@module_enabled("mileage")
def create_mileage():
    """Create a new mileage entry"""
    if request.method == "GET":
        projects = Project.query.filter_by(status="active").order_by(Project.name).all()
        clients = Client.get_active_clients()
        only_one_client = len(clients) == 1
        single_client = clients[0] if only_one_client else None
        default_rates = Mileage.get_default_rates()

        return render_template(
            "mileage/form.html",
            mileage=None,
            projects=projects,
            clients=clients,
            only_one_client=only_one_client,
            single_client=single_client,
            default_rates=default_rates,
            supported_currencies=SUPPORTED_CURRENCIES,
        )

    try:
        from app.utils.client_lock import enforce_locked_client_id, get_locked_client_id

        # Get form data
        trip_date = request.form.get("trip_date", "").strip()
        purpose = request.form.get("purpose", "").strip()
        description = request.form.get("description", "").strip()
        start_location = request.form.get("start_location", "").strip()
        end_location = request.form.get("end_location", "").strip()
        distance_km = request.form.get("distance_km", "").strip()
        rate_per_km = request.form.get("rate_per_km", "").strip()

        # Validate required fields
        if not all([trip_date, purpose, start_location, end_location, distance_km, rate_per_km]):
            flash(_("Please fill in all required fields"), "error")
            return redirect(url_for("mileage.create_mileage"))

        # Parse date
        try:
            trip_date_obj = datetime.strptime(trip_date, "%Y-%m-%d").date()
        except ValueError:
            flash(_("Invalid date format"), "error")
            return redirect(url_for("mileage.create_mileage"))

        project_id = request.form.get("project_id", type=int)
        client_id = enforce_locked_client_id(request.form.get("client_id", type=int))

        # If a locked client is configured, ensure selected project matches it.
        locked_id = get_locked_client_id()
        if locked_id and project_id:
            project = Project.query.get(project_id)
            if project and getattr(project, "client_id", None) and int(project.client_id) != int(locked_id):
                flash(_("Selected project does not match the locked client."), "error")
                return redirect(url_for("mileage.create_mileage"))

        # Create mileage entry
        mileage = Mileage(
            user_id=current_user.id,
            trip_date=trip_date_obj,
            purpose=purpose,
            start_location=start_location,
            end_location=end_location,
            distance_km=Decimal(distance_km),
            rate_per_km=Decimal(rate_per_km),
            description=description,
            project_id=project_id,
            client_id=client_id,
            start_odometer=request.form.get("start_odometer"),
            end_odometer=request.form.get("end_odometer"),
            vehicle_type=request.form.get("vehicle_type"),
            vehicle_description=request.form.get("vehicle_description"),
            license_plate=request.form.get("license_plate"),
            is_round_trip=request.form.get("is_round_trip") == "on",
            currency_code=request.form.get("currency_code", "EUR"),
            notes=request.form.get("notes"),
        )

        db.session.add(mileage)

        # Create expense if requested
        if request.form.get("create_expense") == "on":
            expense = mileage.create_expense()
            if expense:
                db.session.add(expense)

        if safe_commit(db):
            flash(_("Mileage entry created successfully"), "success")
            log_event("mileage_created", user_id=current_user.id, mileage_id=mileage.id)
            track_event(
                current_user.id,
                "mileage.created",
                {"mileage_id": mileage.id, "distance_km": float(distance_km), "amount": float(mileage.total_amount)},
            )
            return redirect(url_for("mileage.view_mileage", mileage_id=mileage.id))
        else:
            flash(_("Error creating mileage entry"), "error")
            return redirect(url_for("mileage.create_mileage"))

    except Exception as e:
        current_app.logger.error(f"Error creating mileage entry: {e}")
        flash(_("Error creating mileage entry"), "error")
        return redirect(url_for("mileage.create_mileage"))


@mileage_bp.route("/mileage/<int:mileage_id>")
@login_required
@module_enabled("mileage")
def view_mileage(mileage_id):
    """View mileage entry details"""
    mileage = Mileage.query.get_or_404(mileage_id)

    # Check permission
    if not current_user.is_admin and mileage.user_id != current_user.id and mileage.approved_by != current_user.id:
        flash(_("You do not have permission to view this mileage entry"), "error")
        return redirect(url_for("mileage.list_mileage"))

    from app import track_page_view

    track_page_view("mileage_detail", properties={"mileage_id": mileage_id})

    return render_template("mileage/view.html", mileage=mileage)


@mileage_bp.route("/mileage/<int:mileage_id>/edit", methods=["GET", "POST"])
@login_required
@module_enabled("mileage")
def edit_mileage(mileage_id):
    """Edit a mileage entry"""
    mileage = Mileage.query.get_or_404(mileage_id)

    # Check permission
    if not current_user.is_admin and mileage.user_id != current_user.id:
        flash(_("You do not have permission to edit this mileage entry"), "error")
        return redirect(url_for("mileage.view_mileage", mileage_id=mileage_id))

    # Cannot edit approved or reimbursed entries without admin privileges
    if not current_user.is_admin and mileage.status in ["approved", "reimbursed"]:
        flash(_("Cannot edit approved or reimbursed mileage entries"), "error")
        return redirect(url_for("mileage.view_mileage", mileage_id=mileage_id))

    if request.method == "GET":
        projects = Project.query.filter_by(status="active").order_by(Project.name).all()
        clients = Client.get_active_clients()
        only_one_client = len(clients) == 1
        single_client = clients[0] if only_one_client else None
        default_rates = Mileage.get_default_rates()

        return render_template(
            "mileage/form.html",
            mileage=mileage,
            projects=projects,
            clients=clients,
            only_one_client=only_one_client,
            single_client=single_client,
            default_rates=default_rates,
            supported_currencies=SUPPORTED_CURRENCIES,
        )

    try:
        from app.utils.client_lock import enforce_locked_client_id
        # Update fields
        trip_date = request.form.get("trip_date", "").strip()
        mileage.trip_date = datetime.strptime(trip_date, "%Y-%m-%d").date()
        mileage.purpose = request.form.get("purpose", "").strip()
        mileage.description = request.form.get("description", "").strip()
        mileage.start_location = request.form.get("start_location", "").strip()
        mileage.end_location = request.form.get("end_location", "").strip()
        mileage.distance_km = Decimal(request.form.get("distance_km", "0"))
        mileage.rate_per_km = Decimal(request.form.get("rate_per_km", "0"))
        mileage.calculated_amount = mileage.distance_km * mileage.rate_per_km
        mileage.project_id = request.form.get("project_id", type=int)
        mileage.client_id = enforce_locked_client_id(request.form.get("client_id", type=int))
        mileage.vehicle_type = request.form.get("vehicle_type")
        mileage.vehicle_description = request.form.get("vehicle_description")
        mileage.license_plate = request.form.get("license_plate")
        mileage.is_round_trip = request.form.get("is_round_trip") == "on"
        mileage.currency_code = request.form.get("currency_code", "EUR")
        mileage.notes = request.form.get("notes")
        mileage.updated_at = datetime.utcnow()

        if safe_commit(db):
            flash(_("Mileage entry updated successfully"), "success")
            log_event("mileage_updated", user_id=current_user.id, mileage_id=mileage.id)
            track_event(current_user.id, "mileage.updated", {"mileage_id": mileage.id})
            return redirect(url_for("mileage.view_mileage", mileage_id=mileage.id))
        else:
            flash(_("Error updating mileage entry"), "error")
            return redirect(url_for("mileage.edit_mileage", mileage_id=mileage_id))

    except Exception as e:
        current_app.logger.error(f"Error updating mileage entry: {e}")
        flash(_("Error updating mileage entry"), "error")
        return redirect(url_for("mileage.edit_mileage", mileage_id=mileage_id))


@mileage_bp.route("/mileage/<int:mileage_id>/delete", methods=["POST"])
@login_required
@module_enabled("mileage")
def delete_mileage(mileage_id):
    """Delete a mileage entry"""
    mileage = Mileage.query.get_or_404(mileage_id)

    # Check permission
    if not current_user.is_admin and mileage.user_id != current_user.id:
        flash(_("You do not have permission to delete this mileage entry"), "error")
        return redirect(url_for("mileage.view_mileage", mileage_id=mileage_id))

    try:
        db.session.delete(mileage)

        if safe_commit(db):
            flash(_("Mileage entry deleted successfully"), "success")
            log_event("mileage_deleted", user_id=current_user.id, mileage_id=mileage_id)
            track_event(current_user.id, "mileage.deleted", {"mileage_id": mileage_id})
        else:
            flash(_("Error deleting mileage entry"), "error")

    except Exception as e:
        current_app.logger.error(f"Error deleting mileage entry: {e}")
        flash(_("Error deleting mileage entry"), "error")

    return redirect(url_for("mileage.list_mileage"))


@mileage_bp.route("/mileage/bulk-delete", methods=["POST"])
@login_required
@module_enabled("mileage")
def bulk_delete_mileage():
    """Delete multiple mileage entries at once"""
    mileage_ids = request.form.getlist("mileage_ids[]")

    if not mileage_ids:
        flash(_("No mileage entries selected for deletion"), "warning")
        return redirect(url_for("mileage.list_mileage"))

    deleted_count = 0
    skipped_count = 0
    errors = []

    for mileage_id_str in mileage_ids:
        try:
            mileage_id = int(mileage_id_str)
            mileage = Mileage.query.get(mileage_id)

            if not mileage:
                continue

            # Check permissions
            if not current_user.is_admin and mileage.user_id != current_user.id:
                skipped_count += 1
                errors.append(f"Mileage #{mileage_id_str}: No permission")
                continue

            db.session.delete(mileage)
            deleted_count += 1

        except Exception as e:
            skipped_count += 1
            errors.append(f"ID {mileage_id_str}: {str(e)}")

    # Commit all deletions
    if deleted_count > 0:
        if not safe_commit(db):
            flash(_("Could not delete mileage entries due to a database error. Please check server logs."), "error")
            return redirect(url_for("mileage.list_mileage"))

        log_event("mileage_bulk_deleted", user_id=current_user.id, count=deleted_count)
        track_event(current_user.id, "mileage.bulk_deleted", {"count": deleted_count})

    # Show appropriate messages
    if deleted_count > 0:
        flash(
            _(
                "Successfully deleted %(count)d mileage entr%(plural)s",
                count=deleted_count,
                plural="y" if deleted_count == 1 else "ies",
            ),
            "success",
        )

    if skipped_count > 0:
        flash(
            _(
                "Skipped %(count)d mileage entr%(plural)s: %(errors)s",
                count=skipped_count,
                plural="y" if skipped_count == 1 else "ies",
                errors="; ".join(errors[:3]),
            ),
            "warning",
        )

    return redirect(url_for("mileage.list_mileage"))


@mileage_bp.route("/mileage/bulk-status", methods=["POST"])
@login_required
@module_enabled("mileage")
def bulk_update_status():
    """Update status for multiple mileage entries at once"""
    mileage_ids = request.form.getlist("mileage_ids[]")
    new_status = request.form.get("status", "").strip()

    if not mileage_ids:
        flash(_("No mileage entries selected"), "warning")
        return redirect(url_for("mileage.list_mileage"))

    # Validate status
    valid_statuses = ["pending", "approved", "rejected", "reimbursed"]
    if not new_status or new_status not in valid_statuses:
        flash(_("Invalid status value"), "error")
        return redirect(url_for("mileage.list_mileage"))

    updated_count = 0
    skipped_count = 0

    for mileage_id_str in mileage_ids:
        try:
            mileage_id = int(mileage_id_str)
            mileage = Mileage.query.get(mileage_id)

            if not mileage:
                continue

            # Check permissions - non-admin users can only update their own entries
            if not current_user.is_admin and mileage.user_id != current_user.id:
                skipped_count += 1
                continue

            mileage.status = new_status
            updated_count += 1

        except Exception:
            skipped_count += 1

    if updated_count > 0:
        if not safe_commit(db):
            flash(_("Could not update mileage entries due to a database error"), "error")
            return redirect(url_for("mileage.list_mileage"))

        flash(
            _(
                "Successfully updated %(count)d mileage entr%(plural)s to %(status)s",
                count=updated_count,
                plural="y" if updated_count == 1 else "ies",
                status=new_status,
            ),
            "success",
        )

    if skipped_count > 0:
        flash(
            _(
                "Skipped %(count)d mileage entr%(plural)s (no permission)",
                count=skipped_count,
                plural="y" if skipped_count == 1 else "ies",
            ),
            "warning",
        )

    return redirect(url_for("mileage.list_mileage"))


@mileage_bp.route("/mileage/<int:mileage_id>/approve", methods=["POST"])
@login_required
@module_enabled("mileage")
def approve_mileage(mileage_id):
    """Approve a mileage entry"""
    if not current_user.is_admin:
        flash(_("Only administrators can approve mileage entries"), "error")
        return redirect(url_for("mileage.view_mileage", mileage_id=mileage_id))

    mileage = Mileage.query.get_or_404(mileage_id)

    if mileage.status != "pending":
        flash(_("Only pending mileage entries can be approved"), "error")
        return redirect(url_for("mileage.view_mileage", mileage_id=mileage_id))

    try:
        notes = request.form.get("approval_notes", "").strip()
        mileage.approve(current_user.id, notes)

        if safe_commit(db):
            flash(_("Mileage entry approved successfully"), "success")
            log_event("mileage_approved", user_id=current_user.id, mileage_id=mileage_id)
            track_event(current_user.id, "mileage.approved", {"mileage_id": mileage_id})
        else:
            flash(_("Error approving mileage entry"), "error")

    except Exception as e:
        current_app.logger.error(f"Error approving mileage entry: {e}")
        flash(_("Error approving mileage entry"), "error")

    return redirect(url_for("mileage.view_mileage", mileage_id=mileage_id))


@mileage_bp.route("/mileage/<int:mileage_id>/reject", methods=["POST"])
@login_required
@module_enabled("mileage")
def reject_mileage(mileage_id):
    """Reject a mileage entry"""
    if not current_user.is_admin:
        flash(_("Only administrators can reject mileage entries"), "error")
        return redirect(url_for("mileage.view_mileage", mileage_id=mileage_id))

    mileage = Mileage.query.get_or_404(mileage_id)

    if mileage.status != "pending":
        flash(_("Only pending mileage entries can be rejected"), "error")
        return redirect(url_for("mileage.view_mileage", mileage_id=mileage_id))

    try:
        reason = request.form.get("rejection_reason", "").strip()
        if not reason:
            flash(_("Rejection reason is required"), "error")
            return redirect(url_for("mileage.view_mileage", mileage_id=mileage_id))

        mileage.reject(current_user.id, reason)

        if safe_commit(db):
            flash(_("Mileage entry rejected"), "success")
            log_event("mileage_rejected", user_id=current_user.id, mileage_id=mileage_id)
            track_event(current_user.id, "mileage.rejected", {"mileage_id": mileage_id})
        else:
            flash(_("Error rejecting mileage entry"), "error")

    except Exception as e:
        current_app.logger.error(f"Error rejecting mileage entry: {e}")
        flash(_("Error rejecting mileage entry"), "error")

    return redirect(url_for("mileage.view_mileage", mileage_id=mileage_id))


@mileage_bp.route("/mileage/<int:mileage_id>/reimburse", methods=["POST"])
@login_required
@module_enabled("mileage")
def mark_reimbursed(mileage_id):
    """Mark a mileage entry as reimbursed"""
    if not current_user.is_admin:
        flash(_("Only administrators can mark mileage entries as reimbursed"), "error")
        return redirect(url_for("mileage.view_mileage", mileage_id=mileage_id))

    mileage = Mileage.query.get_or_404(mileage_id)

    if mileage.status != "approved":
        flash(_("Only approved mileage entries can be marked as reimbursed"), "error")
        return redirect(url_for("mileage.view_mileage", mileage_id=mileage_id))

    try:
        mileage.mark_as_reimbursed()

        if safe_commit(db):
            flash(_("Mileage entry marked as reimbursed"), "success")
            log_event("mileage_reimbursed", user_id=current_user.id, mileage_id=mileage_id)
            track_event(current_user.id, "mileage.reimbursed", {"mileage_id": mileage_id})
        else:
            flash(_("Error marking mileage entry as reimbursed"), "error")

    except Exception as e:
        current_app.logger.error(f"Error marking mileage entry as reimbursed: {e}")
        flash(_("Error marking mileage entry as reimbursed"), "error")

    return redirect(url_for("mileage.view_mileage", mileage_id=mileage_id))


@mileage_bp.route("/mileage/gps", methods=["GET"])
@login_required
@module_enabled("mileage")
def gps_tracking_page():
    """GPS mileage tracking helper page."""
    projects = Project.query.filter_by(status="active").order_by(Project.name).all()
    clients = Client.get_active_clients()
    return render_template("mileage/gps.html", projects=projects, clients=clients)


@mileage_bp.route("/api/mileage/gps/start", methods=["POST"])
@login_required
@module_enabled("mileage")
def web_gps_start():
    from app.services.gps_tracking_service import GPSTrackingService

    data = request.get_json() or {}
    result = GPSTrackingService().start_tracking(
        user_id=current_user.id,
        latitude=data.get("latitude"),
        longitude=data.get("longitude"),
        location=data.get("location"),
    )
    status_code = 201 if result.get("success") else 400
    return jsonify(result), status_code


@mileage_bp.route("/api/mileage/gps/<int:track_id>/point", methods=["POST"])
@login_required
@module_enabled("mileage")
def web_gps_add_point(track_id):
    from app.services.gps_tracking_service import GPSTrackingService

    data = request.get_json() or {}
    if data.get("latitude") is None or data.get("longitude") is None:
        return jsonify({"success": False, "message": "latitude and longitude are required"}), 400

    result = GPSTrackingService().add_track_point(
        track_id=track_id,
        latitude=data.get("latitude"),
        longitude=data.get("longitude"),
    )
    status_code = 200 if result.get("success") else 400
    return jsonify(result), status_code


@mileage_bp.route("/api/mileage/gps/<int:track_id>/stop", methods=["POST"])
@login_required
@module_enabled("mileage")
def web_gps_stop(track_id):
    from app.services.gps_tracking_service import GPSTrackingService

    data = request.get_json() or {}
    result = GPSTrackingService().stop_tracking(
        track_id=track_id,
        latitude=data.get("latitude"),
        longitude=data.get("longitude"),
        location=data.get("location"),
    )
    status_code = 200 if result.get("success") else 400
    return jsonify(result), status_code


@mileage_bp.route("/api/mileage/gps/<int:track_id>/expense", methods=["POST"])
@login_required
@module_enabled("mileage")
def web_gps_create_expense(track_id):
    from app.services.gps_tracking_service import GPSTrackingService

    data = request.get_json() or {}
    result = GPSTrackingService().create_expense_from_track(
        track_id=track_id,
        project_id=data.get("project_id"),
        rate_per_km=data.get("rate_per_km"),
    )
    status_code = 200 if result.get("success") else 400
    return jsonify(result), status_code


# API endpoints
@mileage_bp.route("/api/mileage", methods=["GET"])
@login_required
@module_enabled("mileage")
def api_list_mileage():
    """API endpoint to list mileage entries"""
    status = request.args.get("status", "").strip()

    query = Mileage.query

    if not current_user.is_admin:
        query = query.filter_by(user_id=current_user.id)

    if status:
        query = query.filter(Mileage.status == status)

    entries = query.order_by(Mileage.trip_date.desc()).all()

    return jsonify({"mileage": [entry.to_dict() for entry in entries], "count": len(entries)})


@mileage_bp.route("/api/mileage/<int:mileage_id>", methods=["GET"])
@login_required
@module_enabled("mileage")
def api_get_mileage(mileage_id):
    """API endpoint to get a single mileage entry"""
    mileage = Mileage.query.get_or_404(mileage_id)

    # Check permission
    if not current_user.is_admin and mileage.user_id != current_user.id:
        return jsonify({"error": "Permission denied"}), 403

    return jsonify(mileage.to_dict())


@mileage_bp.route("/api/mileage/default-rates", methods=["GET"])
@login_required
@module_enabled("mileage")
def api_get_default_rates():
    """API endpoint to get default mileage rates"""
    return jsonify(Mileage.get_default_rates())
