from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, send_file, current_app
from flask_babel import gettext as _
from flask_login import login_required, current_user
from app import db, log_event, track_event
from app.models import Mileage, Project, Client, Expense
from datetime import datetime, date, timedelta
from decimal import Decimal
from app.utils.db import safe_commit
import csv
import io

mileage_bp = Blueprint('mileage', __name__)


@mileage_bp.route('/mileage')
@login_required
def list_mileage():
    """List all mileage entries with filters"""
    from app import track_page_view
    track_page_view("mileage_list")
    
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 25, type=int)
    
    # Filter parameters
    status = request.args.get('status', '').strip()
    project_id = request.args.get('project_id', type=int)
    client_id = request.args.get('client_id', type=int)
    start_date = request.args.get('start_date', '').strip()
    end_date = request.args.get('end_date', '').strip()
    search = request.args.get('search', '').strip()
    
    # Build query
    query = Mileage.query
    
    # Non-admin users can only see their own mileage or mileage they approved
    if not current_user.is_admin:
        query = query.filter(
            db.or_(
                Mileage.user_id == current_user.id,
                Mileage.approved_by == current_user.id
            )
        )
    
    # Apply filters
    if status:
        query = query.filter(Mileage.status == status)
    
    if project_id:
        query = query.filter(Mileage.project_id == project_id)
    
    if client_id:
        query = query.filter(Mileage.client_id == client_id)
    
    if start_date:
        try:
            start = datetime.strptime(start_date, '%Y-%m-%d').date()
            query = query.filter(Mileage.trip_date >= start)
        except ValueError:
            pass
    
    if end_date:
        try:
            end = datetime.strptime(end_date, '%Y-%m-%d').date()
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
                Mileage.end_location.ilike(like)
            )
        )
    
    # Paginate
    mileage_pagination = query.order_by(Mileage.trip_date.desc()).paginate(
        page=page,
        per_page=per_page,
        error_out=False
    )
    
    # Get filter options
    projects = Project.query.filter_by(status='active').order_by(Project.name).all()
    clients = Client.get_active_clients()
    
    # Calculate totals
    start_date_obj = None
    end_date_obj = None
    
    if start_date:
        try:
            start_date_obj = datetime.strptime(start_date, '%Y-%m-%d').date()
        except ValueError:
            pass
    
    if end_date:
        try:
            end_date_obj = datetime.strptime(end_date, '%Y-%m-%d').date()
        except ValueError:
            pass
    
    total_distance = Mileage.get_total_distance(
        user_id=None if current_user.is_admin else current_user.id,
        start_date=start_date_obj,
        end_date=end_date_obj
    )
    
    total_amount_query = db.session.query(
        db.func.sum(Mileage.calculated_amount * db.case(
            (Mileage.is_round_trip, 2),
            else_=1
        ))
    ).filter(Mileage.status.in_(['approved', 'reimbursed']))
    
    if not current_user.is_admin:
        total_amount_query = total_amount_query.filter(Mileage.user_id == current_user.id)
    
    total_amount = total_amount_query.scalar() or 0
    
    return render_template(
        'mileage/list.html',
        mileage_entries=mileage_pagination.items,
        pagination=mileage_pagination,
        projects=projects,
        clients=clients,
        total_distance=total_distance,
        total_amount=float(total_amount),
        # Pass back filter values
        status=status,
        project_id=project_id,
        client_id=client_id,
        start_date=start_date,
        end_date=end_date,
        search=search
    )


@mileage_bp.route('/mileage/create', methods=['GET', 'POST'])
@login_required
def create_mileage():
    """Create a new mileage entry"""
    if request.method == 'GET':
        projects = Project.query.filter_by(status='active').order_by(Project.name).all()
        clients = Client.get_active_clients()
        default_rates = Mileage.get_default_rates()
        
        return render_template(
            'mileage/form.html',
            mileage=None,
            projects=projects,
            clients=clients,
            default_rates=default_rates
        )
    
    try:
        # Get form data
        trip_date = request.form.get('trip_date', '').strip()
        purpose = request.form.get('purpose', '').strip()
        description = request.form.get('description', '').strip()
        start_location = request.form.get('start_location', '').strip()
        end_location = request.form.get('end_location', '').strip()
        distance_km = request.form.get('distance_km', '').strip()
        rate_per_km = request.form.get('rate_per_km', '').strip()
        
        # Validate required fields
        if not all([trip_date, purpose, start_location, end_location, distance_km, rate_per_km]):
            flash(_('Please fill in all required fields'), 'error')
            return redirect(url_for('mileage.create_mileage'))
        
        # Parse date
        try:
            trip_date_obj = datetime.strptime(trip_date, '%Y-%m-%d').date()
        except ValueError:
            flash(_('Invalid date format'), 'error')
            return redirect(url_for('mileage.create_mileage'))
        
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
            project_id=request.form.get('project_id', type=int),
            client_id=request.form.get('client_id', type=int),
            start_odometer=request.form.get('start_odometer'),
            end_odometer=request.form.get('end_odometer'),
            vehicle_type=request.form.get('vehicle_type'),
            vehicle_description=request.form.get('vehicle_description'),
            license_plate=request.form.get('license_plate'),
            is_round_trip=request.form.get('is_round_trip') == 'on',
            currency_code=request.form.get('currency_code', 'EUR'),
            notes=request.form.get('notes')
        )
        
        db.session.add(mileage)
        
        # Create expense if requested
        if request.form.get('create_expense') == 'on':
            expense = mileage.create_expense()
            if expense:
                db.session.add(expense)
        
        if safe_commit(db):
            flash(_('Mileage entry created successfully'), 'success')
            log_event('mileage_created', user_id=current_user.id, mileage_id=mileage.id)
            track_event(current_user.id, 'mileage.created', {
                'mileage_id': mileage.id,
                'distance_km': float(distance_km),
                'amount': float(mileage.total_amount)
            })
            return redirect(url_for('mileage.view_mileage', mileage_id=mileage.id))
        else:
            flash(_('Error creating mileage entry'), 'error')
            return redirect(url_for('mileage.create_mileage'))
    
    except Exception as e:
        current_app.logger.error(f"Error creating mileage entry: {e}")
        flash(_('Error creating mileage entry'), 'error')
        return redirect(url_for('mileage.create_mileage'))


@mileage_bp.route('/mileage/<int:mileage_id>')
@login_required
def view_mileage(mileage_id):
    """View mileage entry details"""
    mileage = Mileage.query.get_or_404(mileage_id)
    
    # Check permission
    if not current_user.is_admin and mileage.user_id != current_user.id and mileage.approved_by != current_user.id:
        flash(_('You do not have permission to view this mileage entry'), 'error')
        return redirect(url_for('mileage.list_mileage'))
    
    from app import track_page_view
    track_page_view("mileage_detail", properties={'mileage_id': mileage_id})
    
    return render_template('mileage/view.html', mileage=mileage)


@mileage_bp.route('/mileage/<int:mileage_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_mileage(mileage_id):
    """Edit a mileage entry"""
    mileage = Mileage.query.get_or_404(mileage_id)
    
    # Check permission
    if not current_user.is_admin and mileage.user_id != current_user.id:
        flash(_('You do not have permission to edit this mileage entry'), 'error')
        return redirect(url_for('mileage.view_mileage', mileage_id=mileage_id))
    
    # Cannot edit approved or reimbursed entries without admin privileges
    if not current_user.is_admin and mileage.status in ['approved', 'reimbursed']:
        flash(_('Cannot edit approved or reimbursed mileage entries'), 'error')
        return redirect(url_for('mileage.view_mileage', mileage_id=mileage_id))
    
    if request.method == 'GET':
        projects = Project.query.filter_by(status='active').order_by(Project.name).all()
        clients = Client.get_active_clients()
        default_rates = Mileage.get_default_rates()
        
        return render_template(
            'mileage/form.html',
            mileage=mileage,
            projects=projects,
            clients=clients,
            default_rates=default_rates
        )
    
    try:
        # Update fields
        trip_date = request.form.get('trip_date', '').strip()
        mileage.trip_date = datetime.strptime(trip_date, '%Y-%m-%d').date()
        mileage.purpose = request.form.get('purpose', '').strip()
        mileage.description = request.form.get('description', '').strip()
        mileage.start_location = request.form.get('start_location', '').strip()
        mileage.end_location = request.form.get('end_location', '').strip()
        mileage.distance_km = Decimal(request.form.get('distance_km', '0'))
        mileage.rate_per_km = Decimal(request.form.get('rate_per_km', '0'))
        mileage.calculated_amount = mileage.distance_km * mileage.rate_per_km
        mileage.project_id = request.form.get('project_id', type=int)
        mileage.client_id = request.form.get('client_id', type=int)
        mileage.vehicle_type = request.form.get('vehicle_type')
        mileage.vehicle_description = request.form.get('vehicle_description')
        mileage.license_plate = request.form.get('license_plate')
        mileage.is_round_trip = request.form.get('is_round_trip') == 'on'
        mileage.currency_code = request.form.get('currency_code', 'EUR')
        mileage.notes = request.form.get('notes')
        mileage.updated_at = datetime.utcnow()
        
        if safe_commit(db):
            flash(_('Mileage entry updated successfully'), 'success')
            log_event('mileage_updated', user_id=current_user.id, mileage_id=mileage.id)
            track_event(current_user.id, 'mileage.updated', {'mileage_id': mileage.id})
            return redirect(url_for('mileage.view_mileage', mileage_id=mileage.id))
        else:
            flash(_('Error updating mileage entry'), 'error')
            return redirect(url_for('mileage.edit_mileage', mileage_id=mileage_id))
    
    except Exception as e:
        current_app.logger.error(f"Error updating mileage entry: {e}")
        flash(_('Error updating mileage entry'), 'error')
        return redirect(url_for('mileage.edit_mileage', mileage_id=mileage_id))


@mileage_bp.route('/mileage/<int:mileage_id>/delete', methods=['POST'])
@login_required
def delete_mileage(mileage_id):
    """Delete a mileage entry"""
    mileage = Mileage.query.get_or_404(mileage_id)
    
    # Check permission
    if not current_user.is_admin and mileage.user_id != current_user.id:
        flash(_('You do not have permission to delete this mileage entry'), 'error')
        return redirect(url_for('mileage.view_mileage', mileage_id=mileage_id))
    
    try:
        db.session.delete(mileage)
        
        if safe_commit(db):
            flash(_('Mileage entry deleted successfully'), 'success')
            log_event('mileage_deleted', user_id=current_user.id, mileage_id=mileage_id)
            track_event(current_user.id, 'mileage.deleted', {'mileage_id': mileage_id})
        else:
            flash(_('Error deleting mileage entry'), 'error')
    
    except Exception as e:
        current_app.logger.error(f"Error deleting mileage entry: {e}")
        flash(_('Error deleting mileage entry'), 'error')
    
    return redirect(url_for('mileage.list_mileage'))

@mileage_bp.route('/mileage/bulk-delete', methods=['POST'])
@login_required
def bulk_delete_mileage():
    """Delete multiple mileage entries at once"""
    mileage_ids = request.form.getlist('mileage_ids[]')
    
    if not mileage_ids:
        flash(_('No mileage entries selected for deletion'), 'warning')
        return redirect(url_for('mileage.list_mileage'))
    
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
            flash(_('Could not delete mileage entries due to a database error. Please check server logs.'), 'error')
            return redirect(url_for('mileage.list_mileage'))
        
        log_event('mileage_bulk_deleted', user_id=current_user.id, count=deleted_count)
        track_event(current_user.id, 'mileage.bulk_deleted', {'count': deleted_count})
    
    # Show appropriate messages
    if deleted_count > 0:
        flash(_('Successfully deleted %(count)d mileage entr%(plural)s', count=deleted_count, plural='y' if deleted_count == 1 else 'ies'), 'success')
    
    if skipped_count > 0:
        flash(_('Skipped %(count)d mileage entr%(plural)s: %(errors)s', count=skipped_count, plural='y' if skipped_count == 1 else 'ies', errors="; ".join(errors[:3])), 'warning')
    
    return redirect(url_for('mileage.list_mileage'))

@mileage_bp.route('/mileage/bulk-status', methods=['POST'])
@login_required
def bulk_update_status():
    """Update status for multiple mileage entries at once"""
    mileage_ids = request.form.getlist('mileage_ids[]')
    new_status = request.form.get('status', '').strip()
    
    if not mileage_ids:
        flash(_('No mileage entries selected'), 'warning')
        return redirect(url_for('mileage.list_mileage'))
    
    # Validate status
    valid_statuses = ['pending', 'approved', 'rejected', 'reimbursed']
    if not new_status or new_status not in valid_statuses:
        flash(_('Invalid status value'), 'error')
        return redirect(url_for('mileage.list_mileage'))
    
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
            flash(_('Could not update mileage entries due to a database error'), 'error')
            return redirect(url_for('mileage.list_mileage'))
        
        flash(_('Successfully updated %(count)d mileage entr%(plural)s to %(status)s', count=updated_count, plural='y' if updated_count == 1 else 'ies', status=new_status), 'success')
    
    if skipped_count > 0:
        flash(_('Skipped %(count)d mileage entr%(plural)s (no permission)', count=skipped_count, plural='y' if skipped_count == 1 else 'ies'), 'warning')
    
    return redirect(url_for('mileage.list_mileage'))


@mileage_bp.route('/mileage/<int:mileage_id>/approve', methods=['POST'])
@login_required
def approve_mileage(mileage_id):
    """Approve a mileage entry"""
    if not current_user.is_admin:
        flash(_('Only administrators can approve mileage entries'), 'error')
        return redirect(url_for('mileage.view_mileage', mileage_id=mileage_id))
    
    mileage = Mileage.query.get_or_404(mileage_id)
    
    if mileage.status != 'pending':
        flash(_('Only pending mileage entries can be approved'), 'error')
        return redirect(url_for('mileage.view_mileage', mileage_id=mileage_id))
    
    try:
        notes = request.form.get('approval_notes', '').strip()
        mileage.approve(current_user.id, notes)
        
        if safe_commit(db):
            flash(_('Mileage entry approved successfully'), 'success')
            log_event('mileage_approved', user_id=current_user.id, mileage_id=mileage_id)
            track_event(current_user.id, 'mileage.approved', {'mileage_id': mileage_id})
        else:
            flash(_('Error approving mileage entry'), 'error')
    
    except Exception as e:
        current_app.logger.error(f"Error approving mileage entry: {e}")
        flash(_('Error approving mileage entry'), 'error')
    
    return redirect(url_for('mileage.view_mileage', mileage_id=mileage_id))


@mileage_bp.route('/mileage/<int:mileage_id>/reject', methods=['POST'])
@login_required
def reject_mileage(mileage_id):
    """Reject a mileage entry"""
    if not current_user.is_admin:
        flash(_('Only administrators can reject mileage entries'), 'error')
        return redirect(url_for('mileage.view_mileage', mileage_id=mileage_id))
    
    mileage = Mileage.query.get_or_404(mileage_id)
    
    if mileage.status != 'pending':
        flash(_('Only pending mileage entries can be rejected'), 'error')
        return redirect(url_for('mileage.view_mileage', mileage_id=mileage_id))
    
    try:
        reason = request.form.get('rejection_reason', '').strip()
        if not reason:
            flash(_('Rejection reason is required'), 'error')
            return redirect(url_for('mileage.view_mileage', mileage_id=mileage_id))
        
        mileage.reject(current_user.id, reason)
        
        if safe_commit(db):
            flash(_('Mileage entry rejected'), 'success')
            log_event('mileage_rejected', user_id=current_user.id, mileage_id=mileage_id)
            track_event(current_user.id, 'mileage.rejected', {'mileage_id': mileage_id})
        else:
            flash(_('Error rejecting mileage entry'), 'error')
    
    except Exception as e:
        current_app.logger.error(f"Error rejecting mileage entry: {e}")
        flash(_('Error rejecting mileage entry'), 'error')
    
    return redirect(url_for('mileage.view_mileage', mileage_id=mileage_id))


@mileage_bp.route('/mileage/<int:mileage_id>/reimburse', methods=['POST'])
@login_required
def mark_reimbursed(mileage_id):
    """Mark a mileage entry as reimbursed"""
    if not current_user.is_admin:
        flash(_('Only administrators can mark mileage entries as reimbursed'), 'error')
        return redirect(url_for('mileage.view_mileage', mileage_id=mileage_id))
    
    mileage = Mileage.query.get_or_404(mileage_id)
    
    if mileage.status != 'approved':
        flash(_('Only approved mileage entries can be marked as reimbursed'), 'error')
        return redirect(url_for('mileage.view_mileage', mileage_id=mileage_id))
    
    try:
        mileage.mark_as_reimbursed()
        
        if safe_commit(db):
            flash(_('Mileage entry marked as reimbursed'), 'success')
            log_event('mileage_reimbursed', user_id=current_user.id, mileage_id=mileage_id)
            track_event(current_user.id, 'mileage.reimbursed', {'mileage_id': mileage_id})
        else:
            flash(_('Error marking mileage entry as reimbursed'), 'error')
    
    except Exception as e:
        current_app.logger.error(f"Error marking mileage entry as reimbursed: {e}")
        flash(_('Error marking mileage entry as reimbursed'), 'error')
    
    return redirect(url_for('mileage.view_mileage', mileage_id=mileage_id))


# API endpoints
@mileage_bp.route('/api/mileage', methods=['GET'])
@login_required
def api_list_mileage():
    """API endpoint to list mileage entries"""
    status = request.args.get('status', '').strip()
    
    query = Mileage.query
    
    if not current_user.is_admin:
        query = query.filter_by(user_id=current_user.id)
    
    if status:
        query = query.filter(Mileage.status == status)
    
    entries = query.order_by(Mileage.trip_date.desc()).all()
    
    return jsonify({
        'mileage': [entry.to_dict() for entry in entries],
        'count': len(entries)
    })


@mileage_bp.route('/api/mileage/<int:mileage_id>', methods=['GET'])
@login_required
def api_get_mileage(mileage_id):
    """API endpoint to get a single mileage entry"""
    mileage = Mileage.query.get_or_404(mileage_id)
    
    # Check permission
    if not current_user.is_admin and mileage.user_id != current_user.id:
        return jsonify({'error': 'Permission denied'}), 403
    
    return jsonify(mileage.to_dict())


@mileage_bp.route('/api/mileage/default-rates', methods=['GET'])
@login_required
def api_get_default_rates():
    """API endpoint to get default mileage rates"""
    return jsonify(Mileage.get_default_rates())

