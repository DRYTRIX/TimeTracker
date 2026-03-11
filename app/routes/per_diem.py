from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, send_file, current_app
from flask_babel import gettext as _
from flask_login import login_required, current_user
from app import db, log_event, track_event
from app.models import PerDiem, PerDiemRate, Project, Client, Settings
from app.constants import SUPPORTED_CURRENCIES
from datetime import datetime, date, time
from decimal import Decimal
from app.utils.db import safe_commit
from app.utils.permissions import admin_or_permission_required
from app.utils.module_helpers import module_enabled
import csv
import io

per_diem_bp = Blueprint("per_diem", __name__)


@per_diem_bp.route("/per-diem")
@login_required
@module_enabled("per_diem")
def list_per_diem():
    """List all per diem claims with filters"""
    from app import track_page_view
    from app.utils.client_lock import enforce_locked_client_id

    track_page_view("per_diem_list")

    page = request.args.get("page", 1, type=int)
    per_page = request.args.get("per_page", 25, type=int)

    # Filter parameters
    status = request.args.get("status", "").strip()
    project_id = request.args.get("project_id", type=int)
    client_id = request.args.get("client_id", type=int)
    client_id = enforce_locked_client_id(client_id)
    start_date = request.args.get("start_date", "").strip()
    end_date = request.args.get("end_date", "").strip()

    # Build query
    query = PerDiem.query

    # Non-admin users can only see their own claims
    if not current_user.is_admin:
        query = query.filter(db.or_(PerDiem.user_id == current_user.id, PerDiem.approved_by == current_user.id))

    # Apply filters
    if status:
        query = query.filter(PerDiem.status == status)

    if project_id:
        query = query.filter(PerDiem.project_id == project_id)

    if client_id:
        query = query.filter(PerDiem.client_id == client_id)

    if start_date:
        try:
            start = datetime.strptime(start_date, "%Y-%m-%d").date()
            query = query.filter(PerDiem.start_date >= start)
        except ValueError:
            pass

    if end_date:
        try:
            end = datetime.strptime(end_date, "%Y-%m-%d").date()
            query = query.filter(PerDiem.end_date <= end)
        except ValueError:
            pass

    # Paginate
    per_diem_pagination = query.order_by(PerDiem.start_date.desc()).paginate(
        page=page, per_page=per_page, error_out=False
    )

    # Get filter options
    projects = Project.query.filter_by(status="active").order_by(Project.name).all()
    clients = Client.get_active_clients()
    only_one_client = len(clients) == 1
    single_client = clients[0] if only_one_client else None

    # Calculate totals
    total_amount_query = db.session.query(db.func.sum(PerDiem.calculated_amount)).filter(
        PerDiem.status.in_(["approved", "reimbursed"])
    )

    if not current_user.is_admin:
        total_amount_query = total_amount_query.filter(PerDiem.user_id == current_user.id)

    total_amount = total_amount_query.scalar() or 0

    settings = Settings.get_settings()
    currency = settings.currency if settings else "EUR"

    return render_template(
        "per_diem/list.html",
        per_diem_claims=per_diem_pagination.items,
        pagination=per_diem_pagination,
        projects=projects,
        clients=clients,
        only_one_client=only_one_client,
        single_client=single_client,
        total_amount=float(total_amount),
        currency=currency,
        status=status,
        project_id=project_id,
        client_id=client_id,
        start_date=start_date,
        end_date=end_date,
    )


def _per_diem_export_query():
    """Build the same filtered query as list_per_diem (no pagination)."""
    from sqlalchemy.orm import joinedload
    from app.utils.client_lock import enforce_locked_client_id

    status = request.args.get("status", "").strip()
    project_id = request.args.get("project_id", type=int)
    client_id = request.args.get("client_id", type=int)
    client_id = enforce_locked_client_id(client_id)
    start_date = request.args.get("start_date", "").strip()
    end_date = request.args.get("end_date", "").strip()

    query = PerDiem.query.options(
        joinedload(PerDiem.user),
        joinedload(PerDiem.project),
        joinedload(PerDiem.client),
    )

    if not current_user.is_admin:
        query = query.filter(db.or_(PerDiem.user_id == current_user.id, PerDiem.approved_by == current_user.id))

    if status:
        query = query.filter(PerDiem.status == status)
    if project_id:
        query = query.filter(PerDiem.project_id == project_id)
    if client_id:
        query = query.filter(PerDiem.client_id == client_id)
    if start_date:
        try:
            start = datetime.strptime(start_date, "%Y-%m-%d").date()
            query = query.filter(PerDiem.start_date >= start)
        except ValueError:
            pass
    if end_date:
        try:
            end = datetime.strptime(end_date, "%Y-%m-%d").date()
            query = query.filter(PerDiem.end_date <= end)
        except ValueError:
            pass

    return query.order_by(PerDiem.start_date.desc())


@per_diem_bp.route("/per-diem/export/csv")
@login_required
@module_enabled("per_diem")
def export_per_diem_csv():
    """Export (filtered) per diem claims as CSV. Uses same filters as list_per_diem."""
    query = _per_diem_export_query()
    entries = query.all()

    settings = Settings.get_settings()
    delimiter = getattr(settings, "export_delimiter", ",") or ","
    output = io.StringIO()
    writer = csv.writer(output, delimiter=delimiter)

    writer.writerow(
        [
            "ID",
            "User",
            "Trip Purpose",
            "Start Date",
            "End Date",
            "Country",
            "City",
            "Full Days",
            "Half Days",
            "Amount",
            "Status",
            "Project",
            "Client",
            "Notes",
        ]
    )

    for entry in entries:
        writer.writerow(
            [
                entry.id,
                (entry.user.display_name if entry.user else ""),
                entry.trip_purpose or "",
                entry.start_date.isoformat() if entry.start_date else "",
                entry.end_date.isoformat() if entry.end_date else "",
                entry.country or "",
                entry.city or "",
                entry.full_days or 0,
                entry.half_days or 0,
                float(entry.calculated_amount or 0),
                entry.status or "",
                (entry.project.name if entry.project else ""),
                (entry.client.name if entry.client else ""),
                entry.notes or "",
            ]
        )

    csv_bytes = output.getvalue().encode("utf-8")
    start_part = request.args.get("start_date", "") or "all"
    end_part = request.args.get("end_date", "") or "all"
    filename = f"per_diem_export_{start_part}_to_{end_part}.csv"

    return send_file(
        io.BytesIO(csv_bytes),
        mimetype="text/csv",
        as_attachment=True,
        download_name=filename,
    )


@per_diem_bp.route("/per-diem/export/pdf")
@login_required
@module_enabled("per_diem")
def export_per_diem_pdf():
    """Export (filtered) per diem claims as PDF. Uses same filters as list_per_diem."""
    query = _per_diem_export_query()
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
        from app.utils.per_diem_pdf import build_per_diem_pdf
        pdf_bytes = build_per_diem_pdf(
            entries,
            start_date=start_date,
            end_date=end_date,
            filters=pdf_filters if pdf_filters else None,
        )
    except Exception as e:
        current_app.logger.warning("Per diem PDF export failed: %s", e, exc_info=True)
        flash(_("PDF export failed: %(error)s", error=str(e)), "error")
        return redirect(url_for("per_diem.list_per_diem"))

    start_part = start_date or "all"
    end_part = end_date or "all"
    filename = f"per_diem_export_{start_part}_to_{end_part}.pdf"

    return send_file(
        io.BytesIO(pdf_bytes),
        mimetype="application/pdf",
        as_attachment=True,
        download_name=filename,
    )


@per_diem_bp.route("/per-diem/create", methods=["GET", "POST"])
@login_required
@module_enabled("per_diem")
def create_per_diem():
    """Create a new per diem claim"""
    if request.method == "GET":
        projects = Project.query.filter_by(status="active").order_by(Project.name).all()
        clients = Client.get_active_clients()
        only_one_client = len(clients) == 1
        single_client = clients[0] if only_one_client else None

        return render_template(
            "per_diem/form.html",
            per_diem=None,
            projects=projects,
            clients=clients,
            only_one_client=only_one_client,
            single_client=single_client,
        )

    try:
        from app.utils.client_lock import enforce_locked_client_id, get_locked_client_id
        # Get form data
        trip_purpose = request.form.get("trip_purpose", "").strip()
        start_date_str = request.form.get("start_date", "").strip()
        end_date_str = request.form.get("end_date", "").strip()
        country = request.form.get("country", "").strip()
        city = request.form.get("city", "").strip()

        # Validate required fields
        if not all([trip_purpose, start_date_str, end_date_str, country]):
            flash(_("Please fill in all required fields"), "error")
            return redirect(url_for("per_diem.create_per_diem"))

        # Parse dates
        try:
            start_date = datetime.strptime(start_date_str, "%Y-%m-%d").date()
            end_date = datetime.strptime(end_date_str, "%Y-%m-%d").date()
        except ValueError:
            flash(_("Invalid date format"), "error")
            return redirect(url_for("per_diem.create_per_diem"))

        if start_date > end_date:
            flash(_("Start date must be before end date"), "error")
            return redirect(url_for("per_diem.create_per_diem"))

        # Parse times if provided
        departure_time = None
        return_time = None
        departure_time_str = request.form.get("departure_time", "").strip()
        return_time_str = request.form.get("return_time", "").strip()

        if departure_time_str:
            try:
                departure_time = datetime.strptime(departure_time_str, "%H:%M").time()
            except ValueError:
                pass

        if return_time_str:
            try:
                return_time = datetime.strptime(return_time_str, "%H:%M").time()
            except ValueError:
                pass

        # Get or calculate full/half days
        auto_calculate = request.form.get("auto_calculate_days") == "on"

        if auto_calculate:
            days_calc = PerDiem.calculate_days_from_dates(start_date, end_date, departure_time, return_time)
            full_days = days_calc["full_days"]
            half_days = days_calc["half_days"]
        else:
            full_days = int(request.form.get("full_days", 0))
            half_days = int(request.form.get("half_days", 0))

        # Get applicable rate
        rate = PerDiemRate.get_rate_for_location(country, city, start_date)

        if not rate:
            flash(_("No per diem rate found for this location. Please configure rates first."), "error")
            return redirect(url_for("per_diem.create_per_diem"))

        # Meal deductions
        breakfast_provided = int(request.form.get("breakfast_provided", 0))
        lunch_provided = int(request.form.get("lunch_provided", 0))
        dinner_provided = int(request.form.get("dinner_provided", 0))

        project_id = request.form.get("project_id", type=int)
        client_id = enforce_locked_client_id(request.form.get("client_id", type=int))

        # If a locked client is configured, ensure selected project matches it.
        locked_id = get_locked_client_id()
        if locked_id and project_id:
            project = Project.query.get(project_id)
            if project and getattr(project, "client_id", None) and int(project.client_id) != int(locked_id):
                flash(_("Selected project does not match the locked client."), "error")
                return redirect(url_for("per_diem.create_per_diem"))

        # Create per diem claim
        per_diem = PerDiem(
            user_id=current_user.id,
            trip_purpose=trip_purpose,
            start_date=start_date,
            end_date=end_date,
            country=country,
            city=city,
            full_day_rate=rate.full_day_rate,
            half_day_rate=rate.half_day_rate,
            description=request.form.get("description"),
            project_id=project_id,
            client_id=client_id,
            per_diem_rate_id=rate.id,
            departure_time=departure_time,
            return_time=return_time,
            full_days=full_days,
            half_days=half_days,
            breakfast_provided=breakfast_provided,
            lunch_provided=lunch_provided,
            dinner_provided=dinner_provided,
            breakfast_deduction=rate.breakfast_rate or Decimal("0"),
            lunch_deduction=rate.lunch_rate or Decimal("0"),
            dinner_deduction=rate.dinner_rate or Decimal("0"),
            currency_code=rate.currency_code,
            notes=request.form.get("notes"),
        )

        db.session.add(per_diem)

        # Create expense if requested
        if request.form.get("create_expense") == "on":
            expense = per_diem.create_expense()
            if expense:
                db.session.add(expense)

        if safe_commit(db):
            flash(_("Per diem claim created successfully"), "success")
            log_event("per_diem_created", user_id=current_user.id, per_diem_id=per_diem.id)
            track_event(
                current_user.id,
                "per_diem.created",
                {"per_diem_id": per_diem.id, "amount": float(per_diem.calculated_amount), "days": per_diem.total_days},
            )
            return redirect(url_for("per_diem.view_per_diem", per_diem_id=per_diem.id))
        else:
            flash(_("Error creating per diem claim"), "error")
            return redirect(url_for("per_diem.create_per_diem"))

    except Exception as e:
        current_app.logger.error(f"Error creating per diem claim: {e}")
        flash(_("Error creating per diem claim"), "error")
        return redirect(url_for("per_diem.create_per_diem"))


@per_diem_bp.route("/per-diem/<int:per_diem_id>")
@login_required
@module_enabled("per_diem")
def view_per_diem(per_diem_id):
    """View per diem claim details"""
    per_diem = PerDiem.query.get_or_404(per_diem_id)

    # Check permission
    if not current_user.is_admin and per_diem.user_id != current_user.id and per_diem.approved_by != current_user.id:
        flash(_("You do not have permission to view this per diem claim"), "error")
        return redirect(url_for("per_diem.list_per_diem"))

    from app import track_page_view

    track_page_view("per_diem_detail", properties={"per_diem_id": per_diem_id})

    return render_template("per_diem/view.html", per_diem=per_diem)


@per_diem_bp.route("/per-diem/<int:per_diem_id>/edit", methods=["GET", "POST"])
@login_required
@module_enabled("per_diem")
def edit_per_diem(per_diem_id):
    """Edit a per diem claim"""
    per_diem = PerDiem.query.get_or_404(per_diem_id)

    # Check permission
    if not current_user.is_admin and per_diem.user_id != current_user.id:
        flash(_("You do not have permission to edit this per diem claim"), "error")
        return redirect(url_for("per_diem.view_per_diem", per_diem_id=per_diem_id))

    # Cannot edit approved or reimbursed claims without admin privileges
    if not current_user.is_admin and per_diem.status in ["approved", "reimbursed"]:
        flash(_("Cannot edit approved or reimbursed per diem claims"), "error")
        return redirect(url_for("per_diem.view_per_diem", per_diem_id=per_diem_id))

    if request.method == "GET":
        projects = Project.query.filter_by(status="active").order_by(Project.name).all()
        clients = Client.get_active_clients()
        only_one_client = len(clients) == 1
        single_client = clients[0] if only_one_client else None

        return render_template(
            "per_diem/form.html",
            per_diem=per_diem,
            projects=projects,
            clients=clients,
            only_one_client=only_one_client,
            single_client=single_client,
        )

    try:
        from app.utils.client_lock import enforce_locked_client_id
        # Update fields
        per_diem.trip_purpose = request.form.get("trip_purpose", "").strip()
        per_diem.description = request.form.get("description", "").strip()
        per_diem.start_date = datetime.strptime(request.form.get("start_date"), "%Y-%m-%d").date()
        per_diem.end_date = datetime.strptime(request.form.get("end_date"), "%Y-%m-%d").date()
        per_diem.country = request.form.get("country", "").strip()
        per_diem.city = request.form.get("city", "").strip()
        per_diem.project_id = request.form.get("project_id", type=int)
        per_diem.client_id = enforce_locked_client_id(request.form.get("client_id", type=int))
        per_diem.full_days = int(request.form.get("full_days", 0))
        per_diem.half_days = int(request.form.get("half_days", 0))
        per_diem.breakfast_provided = int(request.form.get("breakfast_provided", 0))
        per_diem.lunch_provided = int(request.form.get("lunch_provided", 0))
        per_diem.dinner_provided = int(request.form.get("dinner_provided", 0))
        per_diem.notes = request.form.get("notes")
        per_diem.updated_at = datetime.utcnow()

        # Recalculate amount
        per_diem.recalculate_amount()

        if safe_commit(db):
            flash(_("Per diem claim updated successfully"), "success")
            log_event("per_diem_updated", user_id=current_user.id, per_diem_id=per_diem.id)
            track_event(current_user.id, "per_diem.updated", {"per_diem_id": per_diem.id})
            return redirect(url_for("per_diem.view_per_diem", per_diem_id=per_diem.id))
        else:
            flash(_("Error updating per diem claim"), "error")
            return redirect(url_for("per_diem.edit_per_diem", per_diem_id=per_diem_id))

    except Exception as e:
        current_app.logger.error(f"Error updating per diem claim: {e}")
        flash(_("Error updating per diem claim"), "error")
        return redirect(url_for("per_diem.edit_per_diem", per_diem_id=per_diem_id))


@per_diem_bp.route("/per-diem/<int:per_diem_id>/delete", methods=["POST"])
@login_required
@module_enabled("per_diem")
def delete_per_diem(per_diem_id):
    """Delete a per diem claim"""
    per_diem = PerDiem.query.get_or_404(per_diem_id)

    # Check permission
    if not current_user.is_admin and per_diem.user_id != current_user.id:
        flash(_("You do not have permission to delete this per diem claim"), "error")
        return redirect(url_for("per_diem.view_per_diem", per_diem_id=per_diem_id))

    try:
        db.session.delete(per_diem)

        if safe_commit(db):
            flash(_("Per diem claim deleted successfully"), "success")
            log_event("per_diem_deleted", user_id=current_user.id, per_diem_id=per_diem_id)
            track_event(current_user.id, "per_diem.deleted", {"per_diem_id": per_diem_id})
        else:
            flash(_("Error deleting per diem claim"), "error")

    except Exception as e:
        current_app.logger.error(f"Error deleting per diem claim: {e}")
        flash(_("Error deleting per diem claim"), "error")

    return redirect(url_for("per_diem.list_per_diem"))


@per_diem_bp.route("/per-diem/bulk-delete", methods=["POST"])
@login_required
@module_enabled("per_diem")
def bulk_delete_per_diem():
    """Delete multiple per diem claims at once"""
    per_diem_ids = request.form.getlist("per_diem_ids[]")

    if not per_diem_ids:
        flash(_("No per diem claims selected for deletion"), "warning")
        return redirect(url_for("per_diem.list_per_diem"))

    deleted_count = 0
    skipped_count = 0
    errors = []

    for per_diem_id_str in per_diem_ids:
        try:
            per_diem_id = int(per_diem_id_str)
            per_diem = PerDiem.query.get(per_diem_id)

            if not per_diem:
                continue

            # Check permissions
            if not current_user.is_admin and per_diem.user_id != current_user.id:
                skipped_count += 1
                errors.append(f"Per diem #{per_diem_id_str}: No permission")
                continue

            db.session.delete(per_diem)
            deleted_count += 1

        except Exception as e:
            skipped_count += 1
            errors.append(f"ID {per_diem_id_str}: {str(e)}")

    # Commit all deletions
    if deleted_count > 0:
        if not safe_commit(db):
            flash(_("Could not delete per diem claims due to a database error. Please check server logs."), "error")
            return redirect(url_for("per_diem.list_per_diem"))

        log_event("per_diem_bulk_deleted", user_id=current_user.id, count=deleted_count)
        track_event(current_user.id, "per_diem.bulk_deleted", {"count": deleted_count})

    # Show appropriate messages
    if deleted_count > 0:
        flash(_("Successfully deleted %(count)d per diem claim(s)", count=deleted_count), "success")

    if skipped_count > 0:
        flash(
            _("Skipped %(count)d per diem claim(s): %(errors)s", count=skipped_count, errors="; ".join(errors[:3])),
            "warning",
        )

    return redirect(url_for("per_diem.list_per_diem"))


@per_diem_bp.route("/per-diem/bulk-status", methods=["POST"])
@login_required
@module_enabled("per_diem")
def bulk_update_status():
    """Update status for multiple per diem claims at once"""
    per_diem_ids = request.form.getlist("per_diem_ids[]")
    new_status = request.form.get("status", "").strip()

    if not per_diem_ids:
        flash(_("No per diem claims selected"), "warning")
        return redirect(url_for("per_diem.list_per_diem"))

    # Validate status
    valid_statuses = ["pending", "approved", "rejected", "reimbursed"]
    if not new_status or new_status not in valid_statuses:
        flash(_("Invalid status value"), "error")
        return redirect(url_for("per_diem.list_per_diem"))

    updated_count = 0
    skipped_count = 0

    for per_diem_id_str in per_diem_ids:
        try:
            per_diem_id = int(per_diem_id_str)
            per_diem = PerDiem.query.get(per_diem_id)

            if not per_diem:
                continue

            # Check permissions - non-admin users can only update their own claims
            if not current_user.is_admin and per_diem.user_id != current_user.id:
                skipped_count += 1
                continue

            per_diem.status = new_status
            updated_count += 1

        except Exception:
            skipped_count += 1

    if updated_count > 0:
        if not safe_commit(db):
            flash(_("Could not update per diem claims due to a database error"), "error")
            return redirect(url_for("per_diem.list_per_diem"))

        flash(
            _("Successfully updated %(count)d per diem claim(s) to %(status)s", count=updated_count, status=new_status),
            "success",
        )

    if skipped_count > 0:
        flash(_("Skipped %(count)d per diem claim(s) (no permission)", count=skipped_count), "warning")

    return redirect(url_for("per_diem.list_per_diem"))


@per_diem_bp.route("/per-diem/<int:per_diem_id>/approve", methods=["POST"])
@login_required
@module_enabled("per_diem")
def approve_per_diem(per_diem_id):
    """Approve a per diem claim"""
    if not current_user.is_admin:
        flash(_("Only administrators can approve per diem claims"), "error")
        return redirect(url_for("per_diem.view_per_diem", per_diem_id=per_diem_id))

    per_diem = PerDiem.query.get_or_404(per_diem_id)

    if per_diem.status != "pending":
        flash(_("Only pending per diem claims can be approved"), "error")
        return redirect(url_for("per_diem.view_per_diem", per_diem_id=per_diem_id))

    try:
        notes = request.form.get("approval_notes", "").strip()
        per_diem.approve(current_user.id, notes)

        if safe_commit(db):
            flash(_("Per diem claim approved successfully"), "success")
            log_event("per_diem_approved", user_id=current_user.id, per_diem_id=per_diem_id)
            track_event(current_user.id, "per_diem.approved", {"per_diem_id": per_diem_id})
        else:
            flash(_("Error approving per diem claim"), "error")

    except Exception as e:
        current_app.logger.error(f"Error approving per diem claim: {e}")
        flash(_("Error approving per diem claim"), "error")

    return redirect(url_for("per_diem.view_per_diem", per_diem_id=per_diem_id))


@per_diem_bp.route("/per-diem/<int:per_diem_id>/reject", methods=["POST"])
@login_required
@module_enabled("per_diem")
def reject_per_diem(per_diem_id):
    """Reject a per diem claim"""
    if not current_user.is_admin:
        flash(_("Only administrators can reject per diem claims"), "error")
        return redirect(url_for("per_diem.view_per_diem", per_diem_id=per_diem_id))

    per_diem = PerDiem.query.get_or_404(per_diem_id)

    if per_diem.status != "pending":
        flash(_("Only pending per diem claims can be rejected"), "error")
        return redirect(url_for("per_diem.view_per_diem", per_diem_id=per_diem_id))

    try:
        reason = request.form.get("rejection_reason", "").strip()
        if not reason:
            flash(_("Rejection reason is required"), "error")
            return redirect(url_for("per_diem.view_per_diem", per_diem_id=per_diem_id))

        per_diem.reject(current_user.id, reason)

        if safe_commit(db):
            flash(_("Per diem claim rejected"), "success")
            log_event("per_diem_rejected", user_id=current_user.id, per_diem_id=per_diem_id)
            track_event(current_user.id, "per_diem.rejected", {"per_diem_id": per_diem_id})
        else:
            flash(_("Error rejecting per diem claim"), "error")

    except Exception as e:
        current_app.logger.error(f"Error rejecting per diem claim: {e}")
        flash(_("Error rejecting per diem claim"), "error")

    return redirect(url_for("per_diem.view_per_diem", per_diem_id=per_diem_id))


# Per Diem Rates Management
@per_diem_bp.route("/per-diem/rates")
@login_required
@module_enabled("per_diem")
@admin_or_permission_required("per_diem_rates.view")
def list_rates():
    """List all per diem rates"""
    from app import track_page_view

    track_page_view("per_diem_rates_list")

    rates = (
        PerDiemRate.query.filter_by(is_active=True)
        .order_by(PerDiemRate.country, PerDiemRate.city, PerDiemRate.effective_from.desc())
        .all()
    )

    return render_template("per_diem/rates_list.html", rates=rates)


@per_diem_bp.route("/per-diem/rates/create", methods=["GET", "POST"])
@login_required
@module_enabled("per_diem")
@admin_or_permission_required("per_diem_rates.create")
def create_rate():
    """Create a new per diem rate"""
    if request.method == "GET":
        return render_template("per_diem/rate_form.html", rate=None, supported_currencies=SUPPORTED_CURRENCIES)

    try:
        country = request.form.get("country", "").strip()
        full_day_rate = request.form.get("full_day_rate", "").strip()
        half_day_rate = request.form.get("half_day_rate", "").strip()
        effective_from = request.form.get("effective_from", "").strip()

        if not all([country, full_day_rate, half_day_rate, effective_from]):
            flash(_("Please fill in all required fields"), "error")
            return redirect(url_for("per_diem.create_rate"))

        rate = PerDiemRate(
            country=country,
            city=request.form.get("city"),
            full_day_rate=Decimal(full_day_rate),
            half_day_rate=Decimal(half_day_rate),
            breakfast_rate=request.form.get("breakfast_rate") or None,
            lunch_rate=request.form.get("lunch_rate") or None,
            dinner_rate=request.form.get("dinner_rate") or None,
            incidental_rate=request.form.get("incidental_rate") or None,
            currency_code=request.form.get("currency_code", "EUR"),
            effective_from=datetime.strptime(effective_from, "%Y-%m-%d").date(),
            effective_to=(
                datetime.strptime(request.form.get("effective_to"), "%Y-%m-%d").date()
                if request.form.get("effective_to")
                else None
            ),
            notes=request.form.get("notes"),
        )

        db.session.add(rate)

        if safe_commit(db):
            flash(_("Per diem rate created successfully"), "success")
            log_event("per_diem_rate_created", user_id=current_user.id, rate_id=rate.id)
            return redirect(url_for("per_diem.list_rates"))
        else:
            flash(_("Error creating per diem rate"), "error")
            return redirect(url_for("per_diem.create_rate"))

    except Exception as e:
        current_app.logger.error(f"Error creating per diem rate: {e}")
        flash(_("Error creating per diem rate"), "error")
        return redirect(url_for("per_diem.create_rate"))


@per_diem_bp.route("/per-diem/rates/<int:rate_id>/edit", methods=["GET", "POST"])
@login_required
@module_enabled("per_diem")
@admin_or_permission_required("per_diem_rates.edit")
def edit_rate(rate_id):
    """Edit an existing per diem rate"""
    rate = PerDiemRate.query.get_or_404(rate_id)

    if request.method == "GET":
        return render_template("per_diem/rate_form.html", rate=rate, supported_currencies=SUPPORTED_CURRENCIES)

    try:
        country = request.form.get("country", "").strip()
        full_day_rate = request.form.get("full_day_rate", "").strip()
        half_day_rate = request.form.get("half_day_rate", "").strip()
        effective_from = request.form.get("effective_from", "").strip()

        if not all([country, full_day_rate, half_day_rate, effective_from]):
            flash(_("Please fill in all required fields"), "error")
            return redirect(url_for("per_diem.edit_rate", rate_id=rate_id))

        # Update rate fields
        rate.country = country
        rate.city = request.form.get("city") or None
        rate.full_day_rate = Decimal(full_day_rate)
        rate.half_day_rate = Decimal(half_day_rate)
        rate.breakfast_rate = (
            Decimal(request.form.get("breakfast_rate")) if request.form.get("breakfast_rate") else None
        )
        rate.lunch_rate = Decimal(request.form.get("lunch_rate")) if request.form.get("lunch_rate") else None
        rate.dinner_rate = Decimal(request.form.get("dinner_rate")) if request.form.get("dinner_rate") else None
        rate.incidental_rate = (
            Decimal(request.form.get("incidental_rate")) if request.form.get("incidental_rate") else None
        )
        rate.currency_code = request.form.get("currency_code", "EUR")
        rate.effective_from = datetime.strptime(effective_from, "%Y-%m-%d").date()
        rate.effective_to = (
            datetime.strptime(request.form.get("effective_to"), "%Y-%m-%d").date()
            if request.form.get("effective_to")
            else None
        )
        rate.notes = request.form.get("notes")
        # updated_at is automatically updated by the model's onupdate

        if safe_commit("edit_per_diem_rate", {"rate_id": rate.id}):
            flash(_("Per diem rate updated successfully"), "success")
            log_event("per_diem_rate_updated", user_id=current_user.id, rate_id=rate.id)
            track_event(current_user.id, "per_diem_rate.updated", {"rate_id": rate.id})
            return redirect(url_for("per_diem.list_rates"))
        else:
            flash(_("Error updating per diem rate"), "error")
            return redirect(url_for("per_diem.edit_rate", rate_id=rate_id))

    except Exception as e:
        current_app.logger.error(f"Error updating per diem rate: {e}")
        flash(_("Error updating per diem rate"), "error")
        return redirect(url_for("per_diem.edit_rate", rate_id=rate_id))


@per_diem_bp.route("/per-diem/rates/<int:rate_id>/delete", methods=["POST"])
@login_required
@module_enabled("per_diem")
@admin_or_permission_required("per_diem_rates.delete")
def delete_rate(rate_id):
    """Delete a per diem rate"""
    rate = PerDiemRate.query.get_or_404(rate_id)

    try:
        # Check if rate is being used by any per diem claims
        from app.models import PerDiem

        claims_using_rate = PerDiem.query.filter_by(per_diem_rate_id=rate_id).count()

        if claims_using_rate > 0:
            flash(
                _(
                    "Cannot delete rate: It is being used by %(count)d per diem claim(s). Deactivate it instead.",
                    count=claims_using_rate,
                ),
                "error",
            )
            return redirect(url_for("per_diem.list_rates"))

        db.session.delete(rate)

        if safe_commit("delete_per_diem_rate", {"rate_id": rate_id}):
            flash(_("Per diem rate deleted successfully"), "success")
            log_event("per_diem_rate_deleted", user_id=current_user.id, rate_id=rate_id)
            track_event(current_user.id, "per_diem_rate.deleted", {"rate_id": rate_id})
        else:
            flash(_("Error deleting per diem rate"), "error")

    except Exception as e:
        current_app.logger.error(f"Error deleting per diem rate: {e}")
        flash(_("Error deleting per diem rate"), "error")

    return redirect(url_for("per_diem.list_rates"))


# API endpoints
@per_diem_bp.route("/api/per-diem", methods=["GET"])
@login_required
@module_enabled("per_diem")
def api_list_per_diem():
    """API endpoint to list per diem claims"""
    status = request.args.get("status", "").strip()

    query = PerDiem.query

    if not current_user.is_admin:
        query = query.filter_by(user_id=current_user.id)

    if status:
        query = query.filter(PerDiem.status == status)

    claims = query.order_by(PerDiem.start_date.desc()).all()

    return jsonify({"per_diem": [claim.to_dict() for claim in claims], "count": len(claims)})


@per_diem_bp.route("/api/per-diem/rates/search", methods=["GET"])
@login_required
@module_enabled("per_diem")
def api_search_rates():
    """API endpoint to search for per diem rates"""
    country = request.args.get("country", "").strip()
    city = request.args.get("city", "").strip()
    date_str = request.args.get("date", "").strip()

    if not country:
        return jsonify({"error": "Country is required"}), 400

    search_date = datetime.strptime(date_str, "%Y-%m-%d").date() if date_str else date.today()

    rate = PerDiemRate.get_rate_for_location(country, city, search_date)

    if rate:
        return jsonify(rate.to_dict())
    else:
        return jsonify({"error": "No rate found for this location"}), 404


@per_diem_bp.route("/api/per-diem/calculate-days", methods=["POST"])
@login_required
@module_enabled("per_diem")
def api_calculate_days():
    """API endpoint to calculate full/half days from dates and times"""
    data = request.get_json()

    try:
        start_date = datetime.strptime(data["start_date"], "%Y-%m-%d").date()
        end_date = datetime.strptime(data["end_date"], "%Y-%m-%d").date()
        departure_time = (
            datetime.strptime(data.get("departure_time", ""), "%H:%M").time() if data.get("departure_time") else None
        )
        return_time = (
            datetime.strptime(data.get("return_time", ""), "%H:%M").time() if data.get("return_time") else None
        )

        result = PerDiem.calculate_days_from_dates(start_date, end_date, departure_time, return_time)

        return jsonify(result)

    except Exception as e:
        return jsonify({"error": str(e)}), 400
