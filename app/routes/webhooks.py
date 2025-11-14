"""Routes for webhook management"""
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_babel import gettext as _
from flask_login import login_required, current_user
from app import db
from app.models import Webhook, WebhookDelivery
from app.routes.admin import admin_required
from app.utils.db import safe_commit
from app.utils.webhook_service import WebhookService
from sqlalchemy.exc import IntegrityError

webhooks_bp = Blueprint('webhooks', __name__)


@webhooks_bp.route('/admin/webhooks')
@login_required
@admin_required
def list_webhooks():
    """List all webhooks"""
    # Filter by user if not admin
    if current_user.is_admin:
        webhooks = Webhook.query.order_by(Webhook.created_at.desc()).all()
    else:
        webhooks = Webhook.query.filter_by(user_id=current_user.id).order_by(Webhook.created_at.desc()).all()
    
    return render_template('admin/webhooks/list.html', webhooks=webhooks)


@webhooks_bp.route('/admin/webhooks/create', methods=['GET', 'POST'])
@login_required
@admin_required
def create_webhook():
    """Create a new webhook"""
    if request.method == 'POST':
        data = request.form
        
        # Validate required fields
        if not data.get('name'):
            flash(_('Webhook name is required'), 'error')
            return render_template('admin/webhooks/form.html', 
                                 webhook=None, 
                                 available_events=WebhookService.get_available_events())
        
        if not data.get('url'):
            flash(_('Webhook URL is required'), 'error')
            return render_template('admin/webhooks/form.html', 
                                 webhook=None, 
                                 available_events=WebhookService.get_available_events())
        
        # Parse events
        events = request.form.getlist('events')
        if not events:
            flash(_('At least one event must be selected'), 'error')
            return render_template('admin/webhooks/form.html', 
                                 webhook=None, 
                                 available_events=WebhookService.get_available_events())
        
        # Create webhook
        webhook = Webhook(
            name=data['name'],
            description=data.get('description'),
            url=data['url'],
            events=events,
            http_method=data.get('http_method', 'POST'),
            content_type=data.get('content_type', 'application/json'),
            is_active=data.get('is_active') == 'on',
            user_id=current_user.id,
            max_retries=int(data.get('max_retries', 3)),
            retry_delay_seconds=int(data.get('retry_delay_seconds', 60)),
            timeout_seconds=int(data.get('timeout_seconds', 30)),
        )
        
        # Generate secret
        webhook.set_secret()
        
        try:
            db.session.add(webhook)
            db.session.commit()
            flash(_('Webhook created successfully'), 'success')
            return redirect(url_for('webhooks.view_webhook', webhook_id=webhook.id))
        except IntegrityError:
            db.session.rollback()
            flash(_('Error creating webhook'), 'error')
        except Exception as e:
            db.session.rollback()
            flash(_('Error creating webhook: %(error)s', error=str(e)), 'error')
    
    available_events = WebhookService.get_available_events()
    return render_template('admin/webhooks/form.html', 
                         webhook=None, 
                         available_events=available_events)


@webhooks_bp.route('/admin/webhooks/<int:webhook_id>')
@login_required
@admin_required
def view_webhook(webhook_id):
    """View webhook details and deliveries"""
    webhook = Webhook.query.get_or_404(webhook_id)
    
    # Check permissions
    if not current_user.is_admin and webhook.user_id != current_user.id:
        flash(_('Access denied'), 'error')
        return redirect(url_for('webhooks.list_webhooks'))
    
    # Get recent deliveries
    deliveries = WebhookDelivery.query.filter_by(webhook_id=webhook_id)\
        .order_by(WebhookDelivery.started_at.desc())\
        .limit(50).all()
    
    return render_template('admin/webhooks/view.html', 
                         webhook=webhook, 
                         deliveries=deliveries)


@webhooks_bp.route('/admin/webhooks/<int:webhook_id>/edit', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_webhook(webhook_id):
    """Edit a webhook"""
    webhook = Webhook.query.get_or_404(webhook_id)
    
    # Check permissions
    if not current_user.is_admin and webhook.user_id != current_user.id:
        flash(_('Access denied'), 'error')
        return redirect(url_for('webhooks.list_webhooks'))
    
    if request.method == 'POST':
        data = request.form
        
        # Update fields
        webhook.name = data.get('name', webhook.name)
        webhook.description = data.get('description', webhook.description)
        webhook.url = data.get('url', webhook.url)
        webhook.events = request.form.getlist('events') or webhook.events
        webhook.http_method = data.get('http_method', webhook.http_method)
        webhook.content_type = data.get('content_type', webhook.content_type)
        webhook.is_active = data.get('is_active') == 'on'
        webhook.max_retries = int(data.get('max_retries', webhook.max_retries))
        webhook.retry_delay_seconds = int(data.get('retry_delay_seconds', webhook.retry_delay_seconds))
        webhook.timeout_seconds = int(data.get('timeout_seconds', webhook.timeout_seconds))
        
        # Regenerate secret if requested
        if data.get('regenerate_secret') == 'on':
            webhook.set_secret()
        
        try:
            db.session.commit()
            flash(_('Webhook updated successfully'), 'success')
            return redirect(url_for('webhooks.view_webhook', webhook_id=webhook.id))
        except Exception as e:
            db.session.rollback()
            flash(_('Error updating webhook: %(error)s', error=str(e)), 'error')
    
    available_events = WebhookService.get_available_events()
    return render_template('admin/webhooks/form.html', 
                         webhook=webhook, 
                         available_events=available_events)


@webhooks_bp.route('/admin/webhooks/<int:webhook_id>/delete', methods=['POST'])
@login_required
@admin_required
def delete_webhook(webhook_id):
    """Delete a webhook"""
    webhook = Webhook.query.get_or_404(webhook_id)
    
    # Check permissions
    if not current_user.is_admin and webhook.user_id != current_user.id:
        flash(_('Access denied'), 'error')
        return redirect(url_for('webhooks.list_webhooks'))
    
    try:
        db.session.delete(webhook)
        db.session.commit()
        flash(_('Webhook deleted successfully'), 'success')
    except Exception as e:
        db.session.rollback()
        flash(_('Error deleting webhook: %(error)s', error=str(e)), 'error')
    
    return redirect(url_for('webhooks.list_webhooks'))


@webhooks_bp.route('/admin/webhooks/<int:webhook_id>/test', methods=['POST'])
@login_required
@admin_required
def test_webhook(webhook_id):
    """Test a webhook by sending a test event"""
    webhook = Webhook.query.get_or_404(webhook_id)
    
    # Check permissions
    if not current_user.is_admin and webhook.user_id != current_user.id:
        return jsonify({'error': 'Access denied'}), 403
    
    if not webhook.is_active:
        return jsonify({'error': 'Webhook is not active'}), 400
    
    # Send test event
    try:
        test_payload = {
            'event_type': 'webhook.test',
            'timestamp': db.session.execute(db.text('SELECT CURRENT_TIMESTAMP')).scalar().isoformat(),
            'user': {
                'id': current_user.id,
                'username': current_user.username,
            },
            'message': 'This is a test webhook event',
        }
        
        delivery = WebhookService.deliver_webhook(
            webhook=webhook,
            event_type='webhook.test',
            payload=test_payload,
            event_id=f'test_{webhook_id}_{int(db.session.execute(db.text("SELECT EXTRACT(EPOCH FROM NOW())")).scalar())}'
        )
        
        return jsonify({
            'success': True,
            'delivery': delivery.to_dict(),
            'message': 'Test webhook sent successfully'
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

