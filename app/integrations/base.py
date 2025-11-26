"""
Base connector interface for integrations.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List
from datetime import datetime


class BaseConnector(ABC):
    """
    Base class for all integration connectors.
    
    All connectors must implement these methods to provide
    a consistent interface for integration management.
    """

    def __init__(self, integration, credentials):
        """
        Initialize connector with integration and credentials.
        
        Args:
            integration: Integration model instance
            credentials: IntegrationCredential model instance
        """
        self.integration = integration
        self.credentials = credentials

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Return the provider name (e.g., 'jira', 'slack', 'github')."""
        pass

    @property
    @abstractmethod
    def display_name(self) -> str:
        """Return the display name for the provider."""
        pass

    @abstractmethod
    def get_authorization_url(self, redirect_uri: str, state: str = None) -> str:
        """
        Get OAuth authorization URL.
        
        Args:
            redirect_uri: OAuth callback URL
            state: Optional state parameter for CSRF protection
        
        Returns:
            Authorization URL
        """
        pass

    @abstractmethod
    def exchange_code_for_tokens(self, code: str, redirect_uri: str) -> Dict[str, Any]:
        """
        Exchange authorization code for access tokens.
        
        Args:
            code: Authorization code from OAuth callback
            redirect_uri: OAuth callback URL
        
        Returns:
            Dict with access_token, refresh_token, expires_at, etc.
        """
        pass

    @abstractmethod
    def refresh_access_token(self) -> Dict[str, Any]:
        """
        Refresh access token using refresh token.
        
        Returns:
            Dict with new access_token, expires_at, etc.
        """
        pass

    @abstractmethod
    def test_connection(self) -> Dict[str, Any]:
        """
        Test the connection to the service.
        
        Returns:
            Dict with 'success' (bool) and 'message' (str)
        """
        pass

    def get_access_token(self) -> Optional[str]:
        """
        Get current access token, refreshing if needed.
        
        Returns:
            Access token string or None
        """
        if not self.credentials:
            return None
        
        # Check if token needs refresh
        if self.credentials.needs_refresh():
            try:
                new_tokens = self.refresh_access_token()
                if new_tokens.get('access_token'):
                    return new_tokens['access_token']
            except Exception:
                pass
        
        return self.credentials.access_token if self.credentials else None

    def sync_data(self, sync_type: str = 'full') -> Dict[str, Any]:
        """
        Sync data from the integrated service.
        
        Args:
            sync_type: Type of sync ('full', 'incremental', etc.)
        
        Returns:
            Dict with sync results
        """
        # Default implementation - override in subclasses
        return {
            'success': False,
            'message': 'Sync not implemented for this connector'
        }

    def handle_webhook(self, payload: Dict[str, Any], headers: Dict[str, str]) -> Dict[str, Any]:
        """
        Handle incoming webhook from the service.
        
        Args:
            payload: Webhook payload
            headers: Request headers
        
        Returns:
            Dict with processing results
        """
        # Default implementation - override in subclasses
        return {
            'success': False,
            'message': 'Webhook handling not implemented for this connector'
        }

    def get_config_schema(self) -> Dict[str, Any]:
        """
        Get configuration schema for this connector.
        
        Returns:
            Dict describing configuration fields
        """
        return {
            'fields': [],
            'required': []
        }

    def validate_config(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate configuration.
        
        Args:
            config: Configuration dict to validate
        
        Returns:
            Dict with 'valid' (bool) and 'errors' (list)
        """
        return {
            'valid': True,
            'errors': []
        }

