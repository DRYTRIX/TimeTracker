"""
Service for managing integrations.
"""

from typing import Dict, Any, Optional, List
from datetime import datetime
from app import db
from app.models import Integration, IntegrationCredential, IntegrationEvent, User
from app.utils.db import safe_commit
from app.utils.event_bus import emit_event
from app.constants import WebhookEvent
import logging

logger = logging.getLogger(__name__)


class IntegrationService:
    """
    Service for integration management operations.
    
    Handles:
    - Creating and managing integrations
    - OAuth flow management
    - Token refresh
    - Connection testing
    """

    # Registry of available connectors
    _connector_registry = {}

    @classmethod
    def register_connector(cls, provider: str, connector_class):
        """Register a connector class for a provider."""
        cls._connector_registry[provider] = connector_class

    @classmethod
    def get_connector(cls, integration: Integration) -> Optional[Any]:
        """
        Get connector instance for an integration.
        
        Args:
            integration: Integration model instance
        
        Returns:
            Connector instance or None
        """
        if integration.provider not in cls._connector_registry:
            return None
        
        connector_class = cls._connector_registry[integration.provider]
        credentials = IntegrationCredential.query.filter_by(
            integration_id=integration.id
        ).first()
        
        return connector_class(integration, credentials)

    def create_integration(
        self,
        provider: str,
        user_id: int,
        name: Optional[str] = None,
        config: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """
        Create a new integration.
        
        Args:
            provider: Provider identifier (e.g., 'jira', 'slack')
            user_id: User ID who owns the integration
            name: Optional custom name
            config: Optional configuration dict
        
        Returns:
            Dict with 'success', 'message', and 'integration'
        """
        if provider not in self._connector_registry:
            return {
                'success': False,
                'message': f'Provider {provider} is not available.'
            }
        
        # Check if user already has this integration
        existing = Integration.query.filter_by(
            provider=provider,
            user_id=user_id
        ).first()
        
        if existing:
            return {
                'success': False,
                'message': f'You already have a {provider} integration.'
            }
        
        connector_class = self._connector_registry[provider]
        display_name = connector_class.display_name if hasattr(connector_class, 'display_name') else provider.title()
        
        integration = Integration(
            name=name or display_name,
            provider=provider,
            user_id=user_id,
            config=config or {},
            is_active=False  # Only active when credentials are set up
        )
        
        db.session.add(integration)
        if not safe_commit('create_integration', {'provider': provider, 'user_id': user_id}):
            return {
                'success': False,
                'message': 'Could not create integration due to a database error.'
            }
        
        emit_event(WebhookEvent.INTEGRATION_CREATED, {
            'integration_id': integration.id,
            'provider': provider,
            'user_id': user_id
        })
        
        return {
            'success': True,
            'message': 'Integration created successfully.',
            'integration': integration
        }

    def get_integration(self, integration_id: int, user_id: int) -> Optional[Integration]:
        """Get integration by ID (with user check)."""
        return Integration.query.filter_by(
            id=integration_id,
            user_id=user_id
        ).first()

    def list_integrations(self, user_id: int) -> List[Integration]:
        """List all integrations for a user."""
        integrations = Integration.query.filter_by(user_id=user_id).order_by(Integration.created_at.desc()).all()
        
        # Sync is_active status with credentials existence
        for integration in integrations:
            has_credentials = IntegrationCredential.query.filter_by(
                integration_id=integration.id
            ).first() is not None
            
            # Update is_active if it doesn't match credentials status
            if integration.is_active != has_credentials:
                integration.is_active = has_credentials
                safe_commit('sync_integration_active_status', {'integration_id': integration.id})
        
        return integrations

    def delete_integration(self, integration_id: int, user_id: int) -> Dict[str, Any]:
        """Delete an integration."""
        integration = self.get_integration(integration_id, user_id)
        if not integration:
            return {
                'success': False,
                'message': 'Integration not found.'
            }
        
        db.session.delete(integration)
        if not safe_commit('delete_integration', {'integration_id': integration_id}):
            return {
                'success': False,
                'message': 'Could not delete integration due to a database error.'
            }
        
        emit_event(WebhookEvent.INTEGRATION_DELETED, {
            'integration_id': integration_id,
            'provider': integration.provider
        })
        
        return {
            'success': True,
            'message': 'Integration deleted successfully.'
        }

    def save_credentials(
        self,
        integration_id: int,
        access_token: str,
        refresh_token: Optional[str] = None,
        expires_at: Optional[datetime] = None,
        token_type: str = 'Bearer',
        scope: Optional[str] = None,
        extra_data: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """Save OAuth credentials for an integration."""
        integration = Integration.query.get(integration_id)
        if not integration:
            return {
                'success': False,
                'message': 'Integration not found.'
            }
        
        # Get or create credentials
        credentials = IntegrationCredential.query.filter_by(
            integration_id=integration_id
        ).first()
        
        if not credentials:
            credentials = IntegrationCredential(integration_id=integration_id)
            db.session.add(credentials)
        
        credentials.access_token = access_token
        credentials.refresh_token = refresh_token
        credentials.expires_at = expires_at
        credentials.token_type = token_type
        credentials.scope = scope
        credentials.extra_data = extra_data or {}
        
        # Mark integration as active when credentials are saved
        integration.is_active = True
        
        if not safe_commit('save_integration_credentials', {'integration_id': integration_id}):
            return {
                'success': False,
                'message': 'Could not save credentials due to a database error.'
            }
        
        return {
            'success': True,
            'message': 'Credentials saved successfully.',
            'credentials': credentials
        }

    def test_connection(self, integration_id: int, user_id: int) -> Dict[str, Any]:
        """Test connection to integrated service."""
        integration = self.get_integration(integration_id, user_id)
        if not integration:
            return {
                'success': False,
                'message': 'Integration not found.'
            }
        
        connector = self.get_connector(integration)
        if not connector:
            return {
                'success': False,
                'message': f'Connector for {integration.provider} is not available.'
            }
        
        try:
            result = connector.test_connection()
            
            # Log event
            self._log_event(integration_id, 'test_connection', result.get('success', False), result.get('message'))
            
            return result
        except Exception as e:
            logger.error(f"Error testing connection for integration {integration_id}: {e}")
            return {
                'success': False,
                'message': f'Error testing connection: {str(e)}'
            }

    def _log_event(
        self,
        integration_id: int,
        event_type: str,
        status: bool,
        message: Optional[str] = None,
        metadata: Optional[Dict] = None
    ):
        """Log an integration event."""
        event = IntegrationEvent(
            integration_id=integration_id,
            event_type=event_type,
            status='success' if status else 'error',
            message=message,
            event_metadata=metadata or {}
        )
        db.session.add(event)
        safe_commit('log_integration_event', {'integration_id': integration_id})

    @classmethod
    def get_available_providers(cls) -> List[Dict[str, Any]]:
        """Get list of available integration providers."""
        providers = []
        for provider, connector_class in cls._connector_registry.items():
            providers.append({
                'provider': provider,
                'display_name': getattr(connector_class, 'display_name', provider.title()),
                'description': getattr(connector_class, 'description', ''),
                'icon': getattr(connector_class, 'icon', 'plug')
            })
        return providers

