from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, current_app
from flask_babel import gettext as _
from flask_login import login_required, current_user
from app import db, log_event, track_event
from app.models import PerDiem, PerDiemRate, Project, Client
from datetime import datetime, date, time
from decimal import Decimal
from app.utils.db import safe_commit
from app.utils.permissions import admin_or_permission_required

per_diem_bp = Blueprint('per_diem', __name__)


@per_diem_bp.route('/per-diem')
@login_required
def list_per_diem():
    """List all per diem claims with filters"""
    from app import track_page_view
    track_page_view("per_diem_list")
    
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 25, type=int)
    
    # Filter parameters
    status = request.args.get('status', '').strip()
    project_id = request.args.get('project_id', type=int)
    client_id = request.args.get('client_id', type=int)
    start_date = request.args.get('start_date', '').strip()
    end_date = request.args.get('end_date', '').strip()
    
    # Build query
    query = PerDiem.query
    
    # Non-admin users can only see their own claims
    if not current_user.is_admin:
        query = query.filter(
            db.or_(
                PerDiem.user_id == current_user.id,
                PerDiem.approved_by == current_user.id
            )
        )
    
    # Apply filters
    if status:
        query = query.filter(PerDiem.status == status)
    
    if project_id:
        query = query.filter(PerDiem.project_id == project_id)
    
    if client_id:
        query = query.filter(PerDiem.client_id == client_id)
    
    if start_date:
        try:
            start = datetime.strptime(start_date, '%Y-%m-%d').date()
            query = query.filter(PerDiem.start_date >= start)
        except ValueError:
            pass
    
    if end_date:
        try:
            end = datetime.strptime(end_date, '%Y-%m-%d').date()
            query = query.filter(PerDiem.end_date <= end)
        except ValueError:
            pass
    
    # Paginate
    per_diem_pagination = query.order_by(PerDiem.start_date.desc()).paginate(
        page=page,
        per_page=per_page,
        error_out=False
    )
    
    # Get filter options
    projects = Project.query.filter_by(status='active').order_by(Project.name).all()
    clients = Client.get_active_clients()
    
    # Calculate totals
    total_amount_query = db.session.query(
        db.func.sum(PerDiem.calculated_amount)
    ).filter(PerDiem.status.in_(['approved', 'reimbursed']))
    
    if not current_user.is_admin:
        total_amount_query = total_amount_query.filter(PerDiem.user_id == current_user.id)
    
    total_amount = total_amount_query.scalar() or 0
    
    return render_template(
        'per_diem/list.html',
        per_diem_claims=per_diem_pagination.items,
        pagination=per_diem_pagination,
        projects=projects,
        clients=clients,
        total_amount=float(total_amount),
        status=status,
        project_id=project_id,
        client_id=client_id,
        start_date=start_date,
        end_date=end_date
    )


@per_diem_bp.route('/per-diem/create', methods=['GET', 'POST'])
@login_required
def create_per_diem():
    """Create a new per diem claim"""
    if request.method == 'GET':
        projects = Project.query.filter_by(status='active').order_by(Project.name).all()
        clients = Client.get_active_clients()
        
        return render_template(
            'per_diem/form.html',
            per_diem=None,
            projects=projects,
            clients=clients
        )
    
    try:
        # Get form data
        trip_purpose = request.form.get('trip_purpose', '').strip()
        start_date_str = request.form.get('start_date', '').strip()
        end_date_str = request.form.get('end_date', '').strip()
        country = request.form.get('country', '').strip()
        city = request.form.get('city', '').strip()
        
        # Validate required fields
        if not all([trip_purpose, start_date_str, end_date_str, country]):
            flash(_('Please fill in all required fields'), 'error')
            return redirect(url_for('per_diem.create_per_diem'))
        
        # Parse dates
        try:
            start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
            end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()
        except ValueError:
            flash(_('Invalid date format'), 'error')
            return redirect(url_for('per_diem.create_per_diem'))
        
        if start_date > end_date:
            flash(_('Start date must be before end date'), 'error')
            return redirect(url_for('per_diem.create_per_diem'))
        
        # Parse times if provided
        departure_time = None
        return_time = None
        departure_time_str = request.form.get('departure_time', '').strip()
        return_time_str = request.form.get('return_time', '').strip()
        
        if departure_time_str:
            try:
                departure_time = datetime.strptime(departure_time_str, '%H:%M').time()
            except ValueError:
                pass
        
        if return_time_str:
            try:
                return_time = datetime.strptime(return_time_str, '%H:%M').time()
            except ValueError:
                pass
        
        # Get or calculate full/half days
        auto_calculate = request.form.get('auto_calculate_days') == 'on'
        
        if auto_calculate:
            days_calc = PerDiem.calculate_days_from_dates(start_date, end_date, departure_time, return_time)
            full_days = days_calc['full_days']
            half_days = days_calc['half_days']
        else:
            full_days = int(request.form.get('full_days', 0))
            half_days = int(request.form.get('half_days', 0))
        
        # Get applicable rate
        rate = PerDiemRate.get_rate_for_location(country, city, start_date)
        
        if not rate:
            flash(_('No per diem rate found for this location. Please configure rates first.'), 'error')
            return redirect(url_for('per_diem.create_per_diem'))
        
        # Meal deductions
        breakfast_provided = int(request.form.get('breakfast_provided', 0))
        lunch_provided = int(request.form.get('lunch_provided', 0))
        dinner_provided = int(request.form.get('dinner_provided', 0))
        
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
            description=request.form.get('description'),
            project_id=request.form.get('project_id', type=int),
            client_id=request.form.get('client_id', type=int),
            per_diem_rate_id=rate.id,
            departure_time=departure_time,
            return_time=return_time,
            full_days=full_days,
            half_days=half_days,
            breakfast_provided=breakfast_provided,
            lunch_provided=lunch_provided,
            dinner_provided=dinner_provided,
            breakfast_deduction=rate.breakfast_rate or Decimal('0'),
            lunch_deduction=rate.lunch_rate or Decimal('0'),
            dinner_deduction=rate.dinner_rate or Decimal('0'),
            currency_code=rate.currency_code,
            notes=request.form.get('notes')
        )
        
        db.session.add(per_diem)
        
        # Create expense if requested
        if request.form.get('create_expense') == 'on':
            expense = per_diem.create_expense()
            if expense:
                db.session.add(expense)
        
        if safe_commit(db):
            flash(_('Per diem claim created successfully'), 'success')
            log_event('per_diem_created', user_id=current_user.id, per_diem_id=per_diem.id)
            track_event(current_user.id, 'per_diem.created', {
                'per_diem_id': per_diem.id,
                'amount': float(per_diem.calculated_amount),
                'days': per_diem.total_days
            })
            return redirect(url_for('per_diem.view_per_diem', per_diem_id=per_diem.id))
        else:
            flash(_('Error creating per diem claim'), 'error')
            return redirect(url_for('per_diem.create_per_diem'))
    
    except Exception as e:
        current_app.logger.error(f"Error creating per diem claim: {e}")
        flash(_('Error creating per diem claim'), 'error')
        return redirect(url_for('per_diem.create_per_diem'))


@per_diem_bp.route('/per-diem/<int:per_diem_id>')
@login_required
def view_per_diem(per_diem_id):
    """View per diem claim details"""
    per_diem = PerDiem.query.get_or_404(per_diem_id)
    
    # Check permission
    if not current_user.is_admin and per_diem.user_id != current_user.id and per_diem.approved_by != current_user.id:
        flash(_('You do not have permission to view this per diem claim'), 'error')
        return redirect(url_for('per_diem.list_per_diem'))
    
    from app import track_page_view
    track_page_view("per_diem_detail", properties={'per_diem_id': per_diem_id})
    
    return render_template('per_diem/view.html', per_diem=per_diem)


@per_diem_bp.route('/per-diem/<int:per_diem_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_per_diem(per_diem_id):
    """Edit a per diem claim"""
    per_diem = PerDiem.query.get_or_404(per_diem_id)
    
    # Check permission
    if not current_user.is_admin and per_diem.user_id != current_user.id:
        flash(_('You do not have permission to edit this per diem claim'), 'error')
        return redirect(url_for('per_diem.view_per_diem', per_diem_id=per_diem_id))
    
    # Cannot edit approved or reimbursed claims without admin privileges
    if not current_user.is_admin and per_diem.status in ['approved', 'reimbursed']:
        flash(_('Cannot edit approved or reimbursed per diem claims'), 'error')
        return redirect(url_for('per_diem.view_per_diem', per_diem_id=per_diem_id))
    
    if request.method == 'GET':
        projects = Project.query.filter_by(status='active').order_by(Project.name).all()
        clients = Client.get_active_clients()
        
        return render_template(
            'per_diem/form.html',
            per_diem=per_diem,
            projects=projects,
            clients=clients
        )
    
    try:
        # Update fields
        per_diem.trip_purpose = request.form.get('trip_purpose', '').strip()
        per_diem.description = request.form.get('description', '').strip()
        per_diem.start_date = datetime.strptime(request.form.get('start_date'), '%Y-%m-%d').date()
        per_diem.end_date = datetime.strptime(request.form.get('end_date'), '%Y-%m-%d').date()
        per_diem.country = request.form.get('country', '').strip()
        per_diem.city = request.form.get('city', '').strip()
        per_diem.project_id = request.form.get('project_id', type=int)
        per_diem.client_id = request.form.get('client_id', type=int)
        per_diem.full_days = int(request.form.get('full_days', 0))
        per_diem.half_days = int(request.form.get('half_days', 0))
        per_diem.breakfast_provided = int(request.form.get('breakfast_provided', 0))
        per_diem.lunch_provided = int(request.form.get('lunch_provided', 0))
        per_diem.dinner_provided = int(request.form.get('dinner_provided', 0))
        per_diem.notes = request.form.get('notes')
        per_diem.updated_at = datetime.utcnow()
        
        # Recalculate amount
        per_diem.recalculate_amount()
        
        if safe_commit(db):
            flash(_('Per diem claim updated successfully'), 'success')
            log_event('per_diem_updated', user_id=current_user.id, per_diem_id=per_diem.id)
            track_event(current_user.id, 'per_diem.updated', {'per_diem_id': per_diem.id})
            return redirect(url_for('per_diem.view_per_diem', per_diem_id=per_diem.id))
        else:
            flash(_('Error updating per diem claim'), 'error')
            return redirect(url_for('per_diem.edit_per_diem', per_diem_id=per_diem_id))
    
    except Exception as e:
        current_app.logger.error(f"Error updating per diem claim: {e}")
        flash(_('Error updating per diem claim'), 'error')
        return redirect(url_for('per_diem.edit_per_diem', per_diem_id=per_diem_id))


@per_diem_bp.route('/per-diem/<int:per_diem_id>/delete', methods=['POST'])
@login_required
def delete_per_diem(per_diem_id):
    """Delete a per diem claim"""
    per_diem = PerDiem.query.get_or_404(per_diem_id)
    
    # Check permission
    if not current_user.is_admin and per_diem.user_id != current_user.id:
        flash(_('You do not have permission to delete this per diem claim'), 'error')
        return redirect(url_for('per_diem.view_per_diem', per_diem_id=per_diem_id))
    
    try:
        db.session.delete(per_diem)
        
        if safe_commit(db):
            flash(_('Per diem claim deleted successfully'), 'success')
            log_event('per_diem_deleted', user_id=current_user.id, per_diem_id=per_diem_id)
            track_event(current_user.id, 'per_diem.deleted', {'per_diem_id': per_diem_id})
        else:
            flash(_('Error deleting per diem claim'), 'error')
    
    except Exception as e:
        current_app.logger.error(f"Error deleting per diem claim: {e}")
        flash(_('Error deleting per diem claim'), 'error')
    
    return redirect(url_for('per_diem.list_per_diem'))


@per_diem_bp.route('/per-diem/<int:per_diem_id>/approve', methods=['POST'])
@login_required
def approve_per_diem(per_diem_id):
    """Approve a per diem claim"""
    if not current_user.is_admin:
        flash(_('Only administrators can approve per diem claims'), 'error')
        return redirect(url_for('per_diem.view_per_diem', per_diem_id=per_diem_id))
    
    per_diem = PerDiem.query.get_or_404(per_diem_id)
    
    if per_diem.status != 'pending':
        flash(_('Only pending per diem claims can be approved'), 'error')
        return redirect(url_for('per_diem.view_per_diem', per_diem_id=per_diem_id))
    
    try:
        notes = request.form.get('approval_notes', '').strip()
        per_diem.approve(current_user.id, notes)
        
        if safe_commit(db):
            flash(_('Per diem claim approved successfully'), 'success')
            log_event('per_diem_approved', user_id=current_user.id, per_diem_id=per_diem_id)
            track_event(current_user.id, 'per_diem.approved', {'per_diem_id': per_diem_id})
        else:
            flash(_('Error approving per diem claim'), 'error')
    
    except Exception as e:
        current_app.logger.error(f"Error approving per diem claim: {e}")
        flash(_('Error approving per diem claim'), 'error')
    
    return redirect(url_for('per_diem.view_per_diem', per_diem_id=per_diem_id))


@per_diem_bp.route('/per-diem/<int:per_diem_id>/reject', methods=['POST'])
@login_required
def reject_per_diem(per_diem_id):
    """Reject a per diem claim"""
    if not current_user.is_admin:
        flash(_('Only administrators can reject per diem claims'), 'error')
        return redirect(url_for('per_diem.view_per_diem', per_diem_id=per_diem_id))
    
    per_diem = PerDiem.query.get_or_404(per_diem_id)
    
    if per_diem.status != 'pending':
        flash(_('Only pending per diem claims can be rejected'), 'error')
        return redirect(url_for('per_diem.view_per_diem', per_diem_id=per_diem_id))
    
    try:
        reason = request.form.get('rejection_reason', '').strip()
        if not reason:
            flash(_('Rejection reason is required'), 'error')
            return redirect(url_for('per_diem.view_per_diem', per_diem_id=per_diem_id))
        
        per_diem.reject(current_user.id, reason)
        
        if safe_commit(db):
            flash(_('Per diem claim rejected'), 'success')
            log_event('per_diem_rejected', user_id=current_user.id, per_diem_id=per_diem_id)
            track_event(current_user.id, 'per_diem.rejected', {'per_diem_id': per_diem_id})
        else:
            flash(_('Error rejecting per diem claim'), 'error')
    
    except Exception as e:
        current_app.logger.error(f"Error rejecting per diem claim: {e}")
        flash(_('Error rejecting per diem claim'), 'error')
    
    return redirect(url_for('per_diem.view_per_diem', per_diem_id=per_diem_id))


# Per Diem Rates Management
@per_diem_bp.route('/per-diem/rates')
@login_required
@admin_or_permission_required('per_diem_rates.view')
def list_rates():
    """List all per diem rates"""
    from app import track_page_view
    track_page_view("per_diem_rates_list")
    
    rates = PerDiemRate.query.filter_by(is_active=True).order_by(
        PerDiemRate.country, PerDiemRate.city, PerDiemRate.effective_from.desc()
    ).all()
    
    return render_template('per_diem/rates_list.html', rates=rates)


@per_diem_bp.route('/per-diem/rates/create', methods=['GET', 'POST'])
@login_required
@admin_or_permission_required('per_diem_rates.create')
def create_rate():
    """Create a new per diem rate"""
    if request.method == 'GET':
        return render_template('per_diem/rate_form.html', rate=None)
    
    try:
        country = request.form.get('country', '').strip()
        full_day_rate = request.form.get('full_day_rate', '').strip()
        half_day_rate = request.form.get('half_day_rate', '').strip()
        effective_from = request.form.get('effective_from', '').strip()
        
        if not all([country, full_day_rate, half_day_rate, effective_from]):
            flash(_('Please fill in all required fields'), 'error')
            return redirect(url_for('per_diem.create_rate'))
        
        rate = PerDiemRate(
            country=country,
            city=request.form.get('city'),
            full_day_rate=Decimal(full_day_rate),
            half_day_rate=Decimal(half_day_rate),
            breakfast_rate=request.form.get('breakfast_rate') or None,
            lunch_rate=request.form.get('lunch_rate') or None,
            dinner_rate=request.form.get('dinner_rate') or None,
            incidental_rate=request.form.get('incidental_rate') or None,
            currency_code=request.form.get('currency_code', 'EUR'),
            effective_from=datetime.strptime(effective_from, '%Y-%m-%d').date(),
            effective_to=datetime.strptime(request.form.get('effective_to'), '%Y-%m-%d').date() if request.form.get('effective_to') else None,
            notes=request.form.get('notes')
        )
        
        db.session.add(rate)
        
        if safe_commit(db):
            flash(_('Per diem rate created successfully'), 'success')
            log_event('per_diem_rate_created', user_id=current_user.id, rate_id=rate.id)
            return redirect(url_for('per_diem.list_rates'))
        else:
            flash(_('Error creating per diem rate'), 'error')
            return redirect(url_for('per_diem.create_rate'))
    
    except Exception as e:
        current_app.logger.error(f"Error creating per diem rate: {e}")
        flash(_('Error creating per diem rate'), 'error')
        return redirect(url_for('per_diem.create_rate'))


# API endpoints
@per_diem_bp.route('/api/per-diem', methods=['GET'])
@login_required
def api_list_per_diem():
    """API endpoint to list per diem claims"""
    status = request.args.get('status', '').strip()
    
    query = PerDiem.query
    
    if not current_user.is_admin:
        query = query.filter_by(user_id=current_user.id)
    
    if status:
        query = query.filter(PerDiem.status == status)
    
    claims = query.order_by(PerDiem.start_date.desc()).all()
    
    return jsonify({
        'per_diem': [claim.to_dict() for claim in claims],
        'count': len(claims)
    })


@per_diem_bp.route('/api/per-diem/rates/search', methods=['GET'])
@login_required
def api_search_rates():
    """API endpoint to search for per diem rates"""
    country = request.args.get('country', '').strip()
    city = request.args.get('city', '').strip()
    date_str = request.args.get('date', '').strip()
    
    if not country:
        return jsonify({'error': 'Country is required'}), 400
    
    search_date = datetime.strptime(date_str, '%Y-%m-%d').date() if date_str else date.today()
    
    rate = PerDiemRate.get_rate_for_location(country, city, search_date)
    
    if rate:
        return jsonify(rate.to_dict())
    else:
        return jsonify({'error': 'No rate found for this location'}), 404


@per_diem_bp.route('/api/per-diem/calculate-days', methods=['POST'])
@login_required
def api_calculate_days():
    """API endpoint to calculate full/half days from dates and times"""
    data = request.get_json()
    
    try:
        start_date = datetime.strptime(data['start_date'], '%Y-%m-%d').date()
        end_date = datetime.strptime(data['end_date'], '%Y-%m-%d').date()
        departure_time = datetime.strptime(data.get('departure_time', ''), '%H:%M').time() if data.get('departure_time') else None
        return_time = datetime.strptime(data.get('return_time', ''), '%H:%M').time() if data.get('return_time') else None
        
        result = PerDiem.calculate_days_from_dates(start_date, end_date, departure_time, return_time)
        
        return jsonify(result)
    
    except Exception as e:
        return jsonify({'error': str(e)}), 400

