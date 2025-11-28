"""Kiosk Mode Routes - Inventory and Barcode Scanning"""
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, current_app, session
from flask_babel import gettext as _
from flask_login import login_required, current_user, login_user, logout_user
from app import db, log_event
from app.models import (
    User, StockItem, Warehouse, WarehouseStock, StockMovement, 
    Project, TimeEntry, Task, Settings
)
from datetime import datetime
from decimal import Decimal, InvalidOperation
from app.utils.db import safe_commit
from app.utils.permissions import admin_or_permission_required
from sqlalchemy import func, or_

kiosk_bp = Blueprint('kiosk', __name__)


@kiosk_bp.route('/kiosk')
@login_required
def kiosk_dashboard():
    """Main kiosk interface"""
    # Check if kiosk mode is enabled (handle missing columns gracefully)
    try:
        settings = Settings.get_settings()
        kiosk_enabled = getattr(settings, 'kiosk_mode_enabled', False)
    except Exception:
        # Migration not run yet, default to False
        kiosk_enabled = False
    
    if not kiosk_enabled:
        flash(_('Kiosk mode is not enabled. Please contact an administrator.'), 'error')
        return redirect(url_for('main.dashboard'))
    
    # Get active timer
    active_timer = current_user.active_timer
    
    # Get default warehouse (from session or first active)
    default_warehouse = None
    default_warehouse_id = session.get('kiosk_default_warehouse_id')
    if default_warehouse_id:
        default_warehouse = Warehouse.query.get(default_warehouse_id)
    
    if not default_warehouse:
        default_warehouse = Warehouse.query.filter_by(is_active=True).first()
    
    # Get active warehouses
    warehouses = Warehouse.query.filter_by(is_active=True).order_by(Warehouse.code).all()
    
    # Get active projects for timer
    active_projects = Project.query.filter_by(status='active').order_by(Project.name).all()
    
    # Get recent items (last 10 used by this user - stored in session)
    recent_items = []
    recent_item_ids = session.get('kiosk_recent_items', [])
    if recent_item_ids:
        try:
            recent_items = StockItem.query.filter(
                StockItem.id.in_(recent_item_ids[:10]),
                StockItem.is_active == True
            ).all()
        except Exception:
            pass
    
    return render_template('kiosk/dashboard.html',
                         active_timer=active_timer,
                         default_warehouse=default_warehouse,
                         warehouses=warehouses,
                         active_projects=active_projects,
                         recent_items=recent_items)


@kiosk_bp.route('/kiosk/login', methods=['GET', 'POST'])
def kiosk_login():
    """Quick login for kiosk mode"""
    # Check if kiosk mode is enabled (handle missing columns gracefully)
    try:
        settings = Settings.get_settings()
        kiosk_enabled = getattr(settings, 'kiosk_mode_enabled', False)
    except Exception:
        # Migration not run yet, default to False
        kiosk_enabled = False
    
    if not kiosk_enabled:
        flash(_('Kiosk mode is not enabled. Please contact an administrator.'), 'error')
        return redirect(url_for('auth.login'))
    
    if current_user.is_authenticated:
        return redirect(url_for('kiosk.kiosk_dashboard'))
    
    # Get authentication method
    try:
        from app.config import Config
        auth_method = (getattr(Config, 'AUTH_METHOD', 'local') or 'local').strip().lower()
    except Exception:
        auth_method = 'local'
    
    # Determine if password authentication is required (kiosk doesn't support OIDC)
    requires_password = auth_method in ('local', 'both')
    
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        
        if not username:
            flash(_('Username is required'), 'error')
            return redirect(url_for('kiosk.kiosk_login'))
        
        user = User.query.filter_by(username=username, is_active=True).first()
        if not user:
            flash(_('Invalid username or password'), 'error')
            return redirect(url_for('kiosk.kiosk_login'))
        
        # Handle password authentication based on mode
        if requires_password:
            # Password authentication is required
            if user.has_password:
                # User has password set - verify it
                if not password:
                    flash(_('Password is required'), 'error')
                    return redirect(url_for('kiosk.kiosk_login'))
                
                if not user.check_password(password):
                    flash(_('Invalid username or password'), 'error')
                    return redirect(url_for('kiosk.kiosk_login'))
            else:
                # User doesn't have password set - deny access in kiosk mode
                flash(_('No password is set for this account. Please set a password in your profile first.'), 'error')
                return redirect(url_for('kiosk.kiosk_login'))
        
        # For 'none' mode, no password check needed - just log in
        login_user(user, remember=False)  # Don't remember in kiosk mode
        log_event("auth.kiosk_login", user_id=user.id)
        return redirect(url_for('kiosk.kiosk_dashboard'))
    
    # Get list of active users for quick selection
    users = User.query.filter_by(is_active=True).order_by(User.username).all()
    return render_template('kiosk/login.html', users=users, requires_password=requires_password)


@kiosk_bp.route('/kiosk/logout', methods=['GET', 'POST'])
@login_required
def kiosk_logout():
    """Logout from kiosk mode"""
    user_id = current_user.id
    username = current_user.username
    
    # Clear kiosk-specific session data
    session.pop('kiosk_recent_items', None)
    session.pop('kiosk_default_warehouse_id', None)
    
    # Logout user
    logout_user()
    
    # Ensure session keys are cleared for compatibility
    try:
        session.pop('_user_id', None)
        session.pop('user_id', None)
    except Exception:
        pass
    
    log_event("auth.kiosk_logout", user_id=user_id)
    flash(_('You have been logged out'), 'success')
    return redirect(url_for('kiosk.kiosk_login'))


@kiosk_bp.route('/api/kiosk/barcode-lookup', methods=['POST'])
@login_required
def barcode_lookup():
    """Look up stock item by barcode or SKU"""
    data = request.get_json() or {}
    barcode = data.get('barcode', '').strip()
    
    if not barcode:
        return jsonify({'error': 'Barcode required'}), 400
    
    # Search by barcode first
    item = StockItem.query.filter_by(barcode=barcode, is_active=True).first()
    
    # If not found, try SKU (case-insensitive)
    if not item:
        item = StockItem.query.filter(
            func.upper(StockItem.sku) == barcode.upper(),
            StockItem.is_active == True
        ).first()
    
    if not item:
        return jsonify({'error': 'Item not found'}), 404
    
    # Get stock levels across warehouses
    stock_levels = WarehouseStock.query.filter_by(
        stock_item_id=item.id
    ).join(Warehouse).filter(Warehouse.is_active == True).all()
    
    # Update recent items in session
    try:
        recent_item_ids = session.get('kiosk_recent_items', [])
        
        # Add to front, remove duplicates, limit to 20
        if item.id in recent_item_ids:
            recent_item_ids.remove(item.id)
        recent_item_ids.insert(0, item.id)
        recent_item_ids = recent_item_ids[:20]
        
        session['kiosk_recent_items'] = recent_item_ids
        session.permanent = True
    except Exception as e:
        current_app.logger.warning("Failed to update recent items: %s", e)
    
    return jsonify({
        'item': {
            'id': item.id,
            'sku': item.sku,
            'name': item.name,
            'barcode': item.barcode,
            'unit': item.unit,
            'description': item.description,
            'category': item.category,
            'image_url': item.image_url,
            'is_trackable': item.is_trackable
        },
        'stock_levels': [{
            'warehouse_id': stock.warehouse_id,
            'warehouse_name': stock.warehouse.name,
            'warehouse_code': stock.warehouse.code,
            'quantity_on_hand': float(stock.quantity_on_hand),
            'quantity_available': float(stock.quantity_available),
            'quantity_reserved': float(stock.quantity_reserved),
            'location': stock.location
        } for stock in stock_levels]
    })


@kiosk_bp.route('/api/kiosk/adjust-stock', methods=['POST'])
@login_required
def adjust_stock():
    """Quick stock adjustment from kiosk"""
    data = request.get_json() or {}
    
    try:
        stock_item_id = int(data.get('stock_item_id', 0))
        warehouse_id = int(data.get('warehouse_id', 0))
        quantity = Decimal(str(data.get('quantity', 0)))
        reason = data.get('reason', 'Kiosk adjustment').strip() or 'Kiosk adjustment'
        notes = data.get('notes', '').strip() or None
    except (ValueError, InvalidOperation, TypeError) as e:
        return jsonify({'error': f'Invalid input: {str(e)}'}), 400
    
    if not stock_item_id or not warehouse_id:
        return jsonify({'error': 'Item and warehouse required'}), 400
    
    # Validate quantity is not zero
    if quantity == 0:
        return jsonify({'error': 'Quantity cannot be zero'}), 400
    
    # Validate quantity is reasonable (prevent accidental huge adjustments)
    if abs(quantity) > 1000000:
        return jsonify({'error': 'Quantity is too large. Please contact an administrator.'}), 400
    
    # Verify item exists and is active
    item = StockItem.query.get(stock_item_id)
    if not item or not item.is_active:
        return jsonify({'error': 'Item not found or inactive'}), 404
    
    # Verify warehouse exists and is active
    warehouse = Warehouse.query.get(warehouse_id)
    if not warehouse or not warehouse.is_active:
        return jsonify({'error': 'Warehouse not found or inactive'}), 404
    
    # Check permissions
    from app.utils.permissions import has_permission
    if not has_permission(current_user, 'manage_stock_movements'):
        return jsonify({'error': 'Permission denied'}), 403
    
    # Record movement
    try:
        movement, updated_stock = StockMovement.record_movement(
            movement_type='adjustment',
            stock_item_id=stock_item_id,
            warehouse_id=warehouse_id,
            quantity=quantity,
            moved_by=current_user.id,
            reason=reason,
            notes=notes,
            update_stock=True
        )
        
        db.session.commit()
        
        log_event('stock_movement.kiosk_adjustment', {
            'movement_id': movement.id,
            'stock_item_id': stock_item_id,
            'warehouse_id': warehouse_id,
            'quantity': float(quantity)
        })
        
        return jsonify({
            'success': True,
            'movement_id': movement.id,
            'new_quantity': float(updated_stock.quantity_on_hand),
            'message': _('Stock adjustment recorded successfully')
        })
    except Exception as e:
        db.session.rollback()
        current_app.logger.exception("Error recording stock adjustment: %s", e)
        return jsonify({'error': f'Error recording adjustment: {str(e)}'}), 500


@kiosk_bp.route('/api/kiosk/transfer-stock', methods=['POST'])
@login_required
def transfer_stock():
    """Transfer stock between warehouses"""
    data = request.get_json() or {}
    
    try:
        stock_item_id = int(data.get('stock_item_id'))
        from_warehouse_id = int(data.get('from_warehouse_id'))
        to_warehouse_id = int(data.get('to_warehouse_id'))
        quantity = Decimal(str(data.get('quantity', 0)))
        notes = data.get('notes', '').strip() or None
    except (ValueError, InvalidOperation, TypeError) as e:
        return jsonify({'error': f'Invalid input: {str(e)}'}), 400
    
    if not all([stock_item_id, from_warehouse_id, to_warehouse_id]):
        return jsonify({'error': 'Item, source warehouse, and destination warehouse required'}), 400
    
    if from_warehouse_id == to_warehouse_id:
        return jsonify({'error': 'Source and destination warehouses must be different'}), 400
    
    if quantity <= 0:
        return jsonify({'error': 'Quantity must be positive'}), 400
    
    # Validate quantity is reasonable
    if quantity > 1000000:
        return jsonify({'error': 'Quantity is too large. Please contact an administrator.'}), 400
    
    # Verify item exists
    item = StockItem.query.get(stock_item_id)
    if not item or not item.is_active:
        return jsonify({'error': 'Item not found or inactive'}), 404
    
    # Verify warehouses exist
    from_warehouse = Warehouse.query.get(from_warehouse_id)
    to_warehouse = Warehouse.query.get(to_warehouse_id)
    if not from_warehouse or not from_warehouse.is_active:
        return jsonify({'error': 'Source warehouse not found or inactive'}), 404
    if not to_warehouse or not to_warehouse.is_active:
        return jsonify({'error': 'Destination warehouse not found or inactive'}), 404
    
    # Check permissions
    from app.utils.permissions import has_permission
    if not has_permission(current_user, 'transfer_stock'):
        return jsonify({'error': 'Permission denied'}), 403
    
    # Check available stock
    from_stock = WarehouseStock.query.filter_by(
        warehouse_id=from_warehouse_id,
        stock_item_id=stock_item_id
    ).first()
    
    if not from_stock or from_stock.quantity_available < quantity:
        return jsonify({'error': 'Insufficient stock available'}), 400
    
    # Create outbound movement
    try:
        out_movement, out_stock = StockMovement.record_movement(
            movement_type='transfer',
            stock_item_id=stock_item_id,
            warehouse_id=from_warehouse_id,
            quantity=-quantity,  # Negative for removal
            moved_by=current_user.id,
            reason='Transfer out',
            notes=notes,
            update_stock=True
        )
        
        # Create inbound movement
        in_movement, in_stock = StockMovement.record_movement(
            movement_type='transfer',
            stock_item_id=stock_item_id,
            warehouse_id=to_warehouse_id,
            quantity=quantity,  # Positive for addition
            moved_by=current_user.id,
            reason='Transfer in',
            notes=notes,
            update_stock=True
        )
        
        db.session.commit()
        
        log_event('stock_movement.kiosk_transfer', {
            'movement_id': out_movement.id,
            'stock_item_id': stock_item_id,
            'from_warehouse_id': from_warehouse_id,
            'to_warehouse_id': to_warehouse_id,
            'quantity': float(quantity)
        })
        
        return jsonify({
            'success': True,
            'from_quantity': float(out_stock.quantity_on_hand),
            'to_quantity': float(in_stock.quantity_on_hand),
            'message': _('Stock transfer completed successfully')
        })
    except Exception as e:
        db.session.rollback()
        current_app.logger.exception("Error recording stock transfer: %s", e)
        return jsonify({'error': f'Error recording transfer: {str(e)}'}), 500


@kiosk_bp.route('/api/kiosk/start-timer', methods=['POST'])
@login_required
def kiosk_start_timer():
    """Start timer from kiosk interface"""
    data = request.get_json() or {}
    
    try:
        project_id = int(data.get('project_id', 0)) if data.get('project_id') else None
        task_id = int(data.get('task_id')) if data.get('task_id') else None
        notes = data.get('notes', '').strip() or None
    except (ValueError, TypeError) as e:
        return jsonify({'error': f'Invalid input: {str(e)}'}), 400
    
    if not project_id:
        return jsonify({'error': 'Project is required'}), 400
    
    # Check if project exists and is active
    project = Project.query.get(project_id)
    if not project or project.status != 'active':
        return jsonify({'error': 'Invalid or inactive project'}), 400
    
    # Check if user already has an active timer
    active_timer = current_user.active_timer
    if active_timer:
        return jsonify({'error': 'You already have an active timer'}), 400
    
    # Validate task if provided
    if task_id:
        task = Task.query.filter_by(id=task_id, project_id=project_id).first()
        if not task:
            return jsonify({'error': 'Invalid task for selected project'}), 400
    else:
        task = None
    
    # Create new timer
    try:
        from app.models.time_entry import local_now
        new_timer = TimeEntry(
            user_id=current_user.id,
            project_id=project_id,
            task_id=task.id if task else None,
            start_time=local_now(),
            notes=notes,
            source='auto'
        )
        
        db.session.add(new_timer)
        db.session.commit()
        
        log_event("timer.started", user_id=current_user.id, project_id=project_id, task_id=task_id)
        
        return jsonify({
            'success': True,
            'timer_id': new_timer.id,
            'message': _('Timer started successfully')
        })
    except Exception as e:
        db.session.rollback()
        current_app.logger.exception("Error starting timer: %s", e)
        return jsonify({'error': f'Error starting timer: {str(e)}'}), 500


@kiosk_bp.route('/api/kiosk/stop-timer', methods=['POST'])
@login_required
def kiosk_stop_timer():
    """Stop timer from kiosk interface"""
    active_timer = current_user.active_timer
    
    if not active_timer:
        return jsonify({'error': 'No active timer'}), 400
    
    try:
        from app.models.time_entry import local_now
        active_timer.end_time = local_now()
        db.session.commit()
        
        log_event("timer.stopped", user_id=current_user.id, timer_id=active_timer.id)
        
        return jsonify({
            'success': True,
            'message': _('Timer stopped successfully')
        })
    except Exception as e:
        db.session.rollback()
        current_app.logger.exception("Error stopping timer: %s", e)
        return jsonify({'error': f'Error stopping timer: {str(e)}'}), 500


@kiosk_bp.route('/api/kiosk/timer-status', methods=['GET'])
@login_required
def kiosk_timer_status():
    """Get current timer status"""
    active_timer = current_user.active_timer
    
    if not active_timer:
        return jsonify({
            'active': False,
            'timer': None
        })
    
    return jsonify({
        'active': True,
        'timer': {
            'id': active_timer.id,
            'project_id': active_timer.project_id,
            'project_name': active_timer.project.name if active_timer.project else None,
            'task_id': active_timer.task_id,
            'task_name': active_timer.task.name if active_timer.task else None,
            'start_time': active_timer.start_time.isoformat() if active_timer.start_time else None,
            'duration_formatted': active_timer.duration_formatted if hasattr(active_timer, 'duration_formatted') else None
        }
    })


@kiosk_bp.route('/api/kiosk/warehouses', methods=['GET'])
@login_required
def kiosk_warehouses():
    """Get list of active warehouses"""
    warehouses = Warehouse.query.filter_by(is_active=True).order_by(Warehouse.code).all()
    
    return jsonify({
        'warehouses': [{
            'id': w.id,
            'name': w.name,
            'code': w.code
        } for w in warehouses]
    })


@kiosk_bp.route('/api/kiosk/projects', methods=['GET'])
@login_required
def kiosk_projects():
    """Get list of active projects for timer"""
    try:
        from app.models import Client
        from sqlalchemy.orm import joinedload
        
        # Query projects with client relationship eager loaded
        # Note: Client model uses backref='client_obj', not 'client'
        projects = Project.query.options(
            joinedload(Project.client_obj)
        ).filter_by(status='active').order_by(Project.name).all()
        
        projects_data = []
        for p in projects:
            try:
                # Access client via client_obj backref (defined in Client model)
                if hasattr(p, 'client_obj') and p.client_obj:
                    client_name = p.client_obj.name
                elif p.client_id:
                    # Fallback: query client directly if relationship not loaded
                    client = Client.query.get(p.client_id)
                    client_name = client.name if client else None
                else:
                    client_name = None
            except (AttributeError, Exception) as e:
                current_app.logger.warning(f'Error accessing client for project {p.id}: {str(e)}')
                client_name = None
            
            projects_data.append({
                'id': p.id,
                'name': p.name,
                'client_name': client_name
            })
        
        return jsonify({
            'projects': projects_data
        })
    except Exception as e:
        import traceback
        current_app.logger.error(f'Error fetching kiosk projects: {str(e)}\n{traceback.format_exc()}')
        return jsonify({
            'error': 'Failed to fetch projects',
            'projects': []
        }), 500


@kiosk_bp.route('/api/kiosk/settings', methods=['GET'])
@login_required
def kiosk_settings_api():
    """Get kiosk settings for frontend"""
    try:
        settings = Settings.get_settings()
        return jsonify({
            'kiosk_allow_camera_scanning': getattr(settings, 'kiosk_allow_camera_scanning', True),
            'kiosk_auto_logout_minutes': getattr(settings, 'kiosk_auto_logout_minutes', 15)
        })
    except Exception:
        return jsonify({
            'kiosk_allow_camera_scanning': True,
            'kiosk_auto_logout_minutes': 15
        })

