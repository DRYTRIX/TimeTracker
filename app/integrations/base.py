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
                if new_tokens.get("access_token"):
                    return new_tokens["access_token"]
            except Exception:
                pass

        return self.credentials.access_token if self.credentials else None

    def sync_data(self, sync_type: str = "full") -> Dict[str, Any]:
        """
        Sync data from the integrated service.

        Args:
            sync_type: Type of sync ('full', 'incremental', etc.)

        Returns:
            Dict with sync results
        """
        # Default implementation - override in subclasses
        return {"success": False, "message": "Sync not implemented for this connector"}

    def handle_webhook(self, payload: Dict[str, Any], headers: Dict[str, str], raw_body: Optional[bytes] = None) -> Dict[str, Any]:
        """
        Handle incoming webhook from the service.

        Args:
            payload: Webhook payload (parsed JSON/dict)
            headers: Request headers
            raw_body: Raw request body bytes (for signature verification)

        Returns:
            Dict with processing results
        """
        # Default implementation - override in subclasses
        return {"success": False, "message": "Webhook handling not implemented for this connector"}

    def get_config_schema(self) -> Dict[str, Any]:
        """
        Get configuration schema for this connector.

        Returns:
            Dict describing configuration fields with structure:
            {
                "fields": [
                    {
                        "name": "field_name",
                        "type": "string|number|boolean|select|array|json|password|url|text",
                        "label": "Display Label",
                        "description": "Help text",
                        "placeholder": "Placeholder text",
                        "default": default_value,
                        "required": True/False,
                        "options": [{"value": "val", "label": "Label"}] for select,
                        "help": "Additional help text",
                        "validation": {"min": 1, "max": 100} for numbers,
                    }
                ],
                "required": ["field_name"],
                "sections": [
                    {
                        "title": "Section Title",
                        "description": "Section description",
                        "fields": ["field_name1", "field_name2"]
                    }
                ],
                "sync_settings": {
                    "enabled": True/False,
                    "auto_sync": True/False,
                    "sync_interval": "hourly|daily|weekly|manual",
                    "sync_direction": "provider_to_timetracker|timetracker_to_provider|bidirectional",
                    "sync_items": ["tasks", "projects", "time_entries"],
                }
            }
        """
        return {
            "fields": [],
            "required": [],
            "sections": [],
            "sync_settings": {
                "enabled": True,
                "auto_sync": False,
                "sync_interval": "manual",
                "sync_direction": "provider_to_timetracker",
                "sync_items": [],
            }
        }

    def validate_config(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate configuration.

        Args:
            config: Configuration dict to validate

        Returns:
            Dict with 'valid' (bool) and 'errors' (list)
        """
        schema = self.get_config_schema()
        errors = []
        
        # Check required fields
        required_fields = schema.get("required", [])
        for field_name in required_fields:
            if field_name not in config or not config[field_name]:
                # Find field label for error message
                field_label = field_name
                for field in schema.get("fields", []):
                    if field.get("name") == field_name:
                        field_label = field.get("label", field_name)
                        break
                errors.append(f"{field_label} is required")
        
        # Validate field types and constraints
        for field in schema.get("fields", []):
            field_name = field.get("name")
            if field_name not in config:
                continue
                
            value = config[field_name]
            field_type = field.get("type", "string")
            
            # Type validation
            if field_type == "number" and value is not None:
                try:
                    float(value)
                    # Check min/max if specified
                    validation = field.get("validation", {})
                    if "min" in validation and float(value) < validation["min"]:
                        errors.append(f"{field.get('label', field_name)} must be at least {validation['min']}")
                    if "max" in validation and float(value) > validation["max"]:
                        errors.append(f"{field.get('label', field_name)} must be at most {validation['max']}")
                except (ValueError, TypeError):
                    errors.append(f"{field.get('label', field_name)} must be a number")
            elif field_type == "boolean" and value is not None:
                if not isinstance(value, bool) and value not in ("true", "false", "1", "0", "on", "off", ""):
                    errors.append(f"{field.get('label', field_name)} must be a boolean")
            elif field_type == "url" and value:
                try:
                    from urllib.parse import urlparse
                    parsed = urlparse(value)
                    if not parsed.scheme or not parsed.netloc:
                        errors.append(f"{field.get('label', field_name)} must be a valid URL")
                except Exception:
                    errors.append(f"{field.get('label', field_name)} must be a valid URL")
            elif field_type == "json" and value:
                try:
                    import json
                    if isinstance(value, str):
                        json.loads(value)
                except json.JSONDecodeError:
                    errors.append(f"{field.get('label', field_name)} must be valid JSON")
        
        return {"valid": len(errors) == 0, "errors": errors}
    
    def get_sync_settings(self) -> Dict[str, Any]:
        """
        Get current sync settings from integration config.
        
        Returns:
            Dict with sync settings
        """
        if not self.integration or not self.integration.config:
            schema = self.get_config_schema()
            return schema.get("sync_settings", {})
        
        config = self.integration.config
        schema = self.get_config_schema()
        default_sync_settings = schema.get("sync_settings", {})
        
        return {
            "enabled": config.get("sync_enabled", default_sync_settings.get("enabled", True)),
            "auto_sync": config.get("auto_sync", default_sync_settings.get("auto_sync", False)),
            "sync_interval": config.get("sync_interval", default_sync_settings.get("sync_interval", "manual")),
            "sync_direction": config.get("sync_direction", default_sync_settings.get("sync_direction", "provider_to_timetracker")),
            "sync_items": config.get("sync_items", default_sync_settings.get("sync_items", [])),
        }
    
    def get_field_mappings(self) -> Dict[str, str]:
        """
        Get field mappings for data translation.
        
        Returns:
            Dict mapping provider fields to TimeTracker fields
        """
        if not self.integration or not self.integration.config:
            return {}
        return self.integration.config.get("field_mappings", {})
    
    def get_status_mappings(self) -> Dict[str, str]:
        """
        Get status mappings for data translation.
        
        Returns:
            Dict mapping provider statuses to TimeTracker statuses
        """
        if not self.integration or not self.integration.config:
            return {}
        return self.integration.config.get("status_mappings", {})
