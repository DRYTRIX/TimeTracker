"""
Routes for integration management.
"""

from flask import Blueprint, render_template, request, redirect, url_for, flash, session, jsonify
from flask_babel import gettext as _
from flask_login import login_required, current_user
from app import db
from app.models import Integration, IntegrationCredential
from app.services.integration_service import IntegrationService
from app.utils.db import safe_commit
import secrets
import logging

logger = logging.getLogger(__name__)

integrations_bp = Blueprint('integrations', __name__)


@integrations_bp.route('/integrations')
@login_required
def list_integrations():
    """List all integrations for the current user."""
    service = IntegrationService()
    integrations = service.list_integrations(current_user.id)
    available_providers = service.get_available_providers()
    
    return render_template(
        'integrations/list.html',
        integrations=integrations,
        available_providers=available_providers
    )


@integrations_bp.route('/integrations/<provider>/connect', methods=['GET', 'POST'])
@login_required
def connect_integration(provider):
    """Start OAuth flow for connecting an integration."""
    service = IntegrationService()
    
    # Check if provider is available
    if provider not in service._connector_registry:
        flash(_('Integration provider not available.'), 'error')
        return redirect(url_for('integrations.list_integrations'))
    
    # Check if integration already exists
    existing = Integration.query.filter_by(
        provider=provider,
        user_id=current_user.id
    ).first()
    
    if existing:
        # Use existing integration (allows reconnecting if credentials were removed)
        integration = existing
    else:
        # Create new integration if it doesn't exist
        result = service.create_integration(provider, current_user.id)
        if not result['success']:
            flash(result['message'], 'error')
            return redirect(url_for('integrations.list_integrations'))
        integration = result['integration']
    
    # Get connector
    connector = service.get_connector(integration)
    if not connector:
        flash(_('Could not initialize connector.'), 'error')
        return redirect(url_for('integrations.list_integrations'))
    
    # Generate state for CSRF protection
    state = secrets.token_urlsafe(32)
    session[f'integration_oauth_state_{integration.id}'] = state
    
    # Get authorization URL
    try:
        redirect_uri = url_for('integrations.oauth_callback', provider=provider, _external=True)
        auth_url = connector.get_authorization_url(redirect_uri, state=state)
        return redirect(auth_url)
    except ValueError as e:
        flash(_('Integration not configured: {error}').format(error=str(e)), 'error')
        return redirect(url_for('integrations.list_integrations'))


@integrations_bp.route('/integrations/<provider>/callback')
@login_required
def oauth_callback(provider):
    """Handle OAuth callback."""
    service = IntegrationService()
    
    code = request.args.get('code')
    state = request.args.get('state')
    error = request.args.get('error')
    
    if error:
        flash(_('Authorization failed: %(error)s', error=error), 'error')
        return redirect(url_for('integrations.list_integrations'))
    
    if not code:
        flash(_('Authorization code not received.'), 'error')
        return redirect(url_for('integrations.list_integrations'))
    
    # Find integration for this user and provider
    integration = Integration.query.filter_by(
        provider=provider,
        user_id=current_user.id
    ).first()
    
    if not integration:
        flash(_('Integration not found.'), 'error')
        return redirect(url_for('integrations.list_integrations'))
    
    # Verify state
    session_key = f'integration_oauth_state_{integration.id}'
    expected_state = session.get(session_key)
    if not expected_state or state != expected_state:
        flash(_('Invalid state parameter. Please try again.'), 'error')
        return redirect(url_for('integrations.list_integrations'))
    
    session.pop(session_key, None)
    
    # Get connector
    connector = service.get_connector(integration)
    if not connector:
        flash(_('Could not initialize connector.'), 'error')
        return redirect(url_for('integrations.list_integrations'))
    
    try:
        # Exchange code for tokens
        redirect_uri = url_for('integrations.oauth_callback', provider=provider, _external=True)
        tokens = connector.exchange_code_for_tokens(code, redirect_uri)
        
        # Save credentials
        service.save_credentials(
            integration_id=integration.id,
            access_token=tokens.get('access_token'),
            refresh_token=tokens.get('refresh_token'),
            expires_at=tokens.get('expires_at'),
            token_type=tokens.get('token_type', 'Bearer'),
            scope=tokens.get('scope'),
            extra_data=tokens.get('extra_data', {})
        )
        
        # Test connection
        test_result = service.test_connection(integration.id, current_user.id)
        if test_result.get('success'):
            flash(_('Integration connected successfully!'), 'success')
        else:
            flash(_('Integration connected but connection test failed: %(message)s', message=test_result.get('message', 'Unknown error')), 'warning')
        
        return redirect(url_for('integrations.view_integration', integration_id=integration.id))
    
    except Exception as e:
        logger.error(f"Error in OAuth callback for {provider}: {e}")
        flash(_('Error connecting integration: %(error)s', error=str(e)), 'error')
        return redirect(url_for('integrations.list_integrations'))


@integrations_bp.route('/integrations/<int:integration_id>')
@login_required
def view_integration(integration_id):
    """View integration details."""
    service = IntegrationService()
    integration = service.get_integration(integration_id, current_user.id)
    
    if not integration:
        flash(_('Integration not found.'), 'error')
        return redirect(url_for('integrations.list_integrations'))
    
    connector = service.get_connector(integration)
    credentials = IntegrationCredential.query.filter_by(integration_id=integration_id).first()
    
    return render_template(
        'integrations/view.html',
        integration=integration,
        connector=connector,
        credentials=credentials
    )


@integrations_bp.route('/integrations/<int:integration_id>/test', methods=['POST'])
@login_required
def test_integration(integration_id):
    """Test integration connection."""
    service = IntegrationService()
    result = service.test_connection(integration_id, current_user.id)
    
    if result.get('success'):
        flash(_('Connection test successful!'), 'success')
    else:
        flash(_('Connection test failed: %(message)s', message=result.get('message', 'Unknown error')), 'error')
    
    return redirect(url_for('integrations.view_integration', integration_id=integration_id))


@integrations_bp.route('/integrations/<int:integration_id>/delete', methods=['POST'])
@login_required
def delete_integration(integration_id):
    """Delete an integration."""
    service = IntegrationService()
    result = service.delete_integration(integration_id, current_user.id)
    
    if result['success']:
        flash(_('Integration deleted successfully.'), 'success')
    else:
        flash(result['message'], 'error')
    
    return redirect(url_for('integrations.list_integrations'))


@integrations_bp.route('/integrations/<int:integration_id>/sync', methods=['POST'])
@login_required
def sync_integration(integration_id):
    """Trigger a sync for an integration."""
    service = IntegrationService()
    integration = service.get_integration(integration_id, current_user.id)
    
    if not integration:
        flash(_('Integration not found.'), 'error')
        return redirect(url_for('integrations.list_integrations'))
    
    connector = service.get_connector(integration)
    if not connector:
        flash(_('Connector not available.'), 'error')
        return redirect(url_for('integrations.view_integration', integration_id=integration_id))
    
    try:
        sync_result = connector.sync_data()
        if sync_result.get('success'):
            flash(_('Sync completed successfully.'), 'success')
        else:
            flash(_('Sync failed: %(message)s', message=sync_result.get('message', 'Unknown error')), 'error')
    except Exception as e:
        logger.error(f"Error syncing integration {integration_id}: {e}")
        flash(_('Error during sync: %(error)s', error=str(e)), 'error')
    
    return redirect(url_for('integrations.view_integration', integration_id=integration_id))

