"""
Microsoft Teams integration connector.
Send notifications and sync with Microsoft Teams.
"""

from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
from app.integrations.base import BaseConnector
import requests
import os


def _env_if_allowed(name: str) -> str:
    """Prevent global env fallbacks for tenant-scoped credentials in SaaS multi-tenant mode."""
    try:
        from flask import current_app

        if bool(current_app.config.get("SAAS_MODE")) and (current_app.config.get("TENANCY_MODE") == "multi"):
            return ""
    except Exception:
        pass
    return os.getenv(name) or ""


class MicrosoftTeamsConnector(BaseConnector):
    """Microsoft Teams integration connector using Microsoft Graph API."""

    display_name = "Microsoft Teams"
    description = "Send notifications and sync with Microsoft Teams"
    icon = "microsoft-teams"

    # Microsoft Graph API endpoints
    GRAPH_BASE_URL = "https://graph.microsoft.com/v1.0"
    AUTH_BASE_URL = "https://login.microsoftonline.com"

    # OAuth 2.0 scopes required
    SCOPES = ["ChannelMessage.Send", "Chat.ReadWrite", "offline_access", "User.Read"]

    @property
    def provider_name(self) -> str:
        return "microsoft_teams"

    def _get_tenant_id(self) -> str:
        """Get tenant ID from settings or use 'common' for multi-tenant."""
        from app.models import Settings

        settings = Settings.get_settings()
        creds = settings.get_integration_credentials("microsoft_teams")
        tenant_id = creds.get("tenant_id") or (_env_if_allowed("MICROSOFT_TEAMS_TENANT_ID") or "common")
        return tenant_id

    def get_authorization_url(self, redirect_uri: str, state: str = None) -> str:
        """Get Microsoft OAuth authorization URL."""
        from app.models import Settings

        settings = Settings.get_settings()
        creds = settings.get_integration_credentials("microsoft_teams")
        client_id = creds.get("client_id") or _env_if_allowed("MICROSOFT_TEAMS_CLIENT_ID")
        tenant_id = self._get_tenant_id()

        if not client_id:
            raise ValueError("Microsoft Teams OAuth credentials not configured")

        auth_url = f"{self.AUTH_BASE_URL}/{tenant_id}/oauth2/v2.0/authorize"

        params = {
            "client_id": client_id,
            "response_type": "code",
            "redirect_uri": redirect_uri,
            "response_mode": "query",
            "scope": " ".join(self.SCOPES),
            "state": state or "",
            "prompt": "consent",
        }

        query_string = "&".join([f"{k}={v}" for k, v in params.items()])
        return f"{auth_url}?{query_string}"

    def exchange_code_for_tokens(self, code: str, redirect_uri: str) -> Dict[str, Any]:
        """Exchange authorization code for tokens."""
        from app.models import Settings

        settings = Settings.get_settings()
        creds = settings.get_integration_credentials("microsoft_teams")
        client_id = creds.get("client_id") or _env_if_allowed("MICROSOFT_TEAMS_CLIENT_ID")
        client_secret = creds.get("client_secret") or _env_if_allowed("MICROSOFT_TEAMS_CLIENT_SECRET")
        tenant_id = self._get_tenant_id()

        if not client_id or not client_secret:
            raise ValueError("Microsoft Teams OAuth credentials not configured")

        token_url = f"{self.AUTH_BASE_URL}/{tenant_id}/oauth2/v2.0/token"

        response = requests.post(
            token_url,
            data={
                "client_id": client_id,
                "client_secret": client_secret,
                "code": code,
                "redirect_uri": redirect_uri,
                "grant_type": "authorization_code",
                "scope": " ".join(self.SCOPES),
            },
        )

        response.raise_for_status()
        data = response.json()

        expires_at = None
        if "expires_in" in data:
            expires_at = datetime.utcnow() + timedelta(seconds=data["expires_in"])

        # Get user info
        user_info = {}
        if "access_token" in data:
            try:
                user_response = requests.get(
                    f"{self.GRAPH_BASE_URL}/me", headers={"Authorization": f"Bearer {data['access_token']}"}
                )
                if user_response.status_code == 200:
                    user_data = user_response.json()
                    user_info = {
                        "id": user_data.get("id"),
                        "displayName": user_data.get("displayName"),
                        "mail": user_data.get("mail"),
                    }
            except Exception as e:
                # Log error but don't fail - user info is optional
                import logging
                logger = logging.getLogger(__name__)
                logger.debug(f"Could not fetch Microsoft Teams user info: {e}")

        return {
            "access_token": data.get("access_token"),
            "refresh_token": data.get("refresh_token"),
            "expires_at": expires_at.isoformat() if expires_at else None,
            "token_type": data.get("token_type", "Bearer"),
            "scope": data.get("scope"),
            "extra_data": user_info,
        }

    def refresh_access_token(self) -> Dict[str, Any]:
        """Refresh access token using refresh token."""
        if not self.credentials or not self.credentials.refresh_token:
            raise ValueError("No refresh token available")

        from app.models import Settings

        settings = Settings.get_settings()
        creds = settings.get_integration_credentials("microsoft_teams")
        client_id = creds.get("client_id") or _env_if_allowed("MICROSOFT_TEAMS_CLIENT_ID")
        client_secret = creds.get("client_secret") or _env_if_allowed("MICROSOFT_TEAMS_CLIENT_SECRET")
        tenant_id = self._get_tenant_id()

        if not client_id or not client_secret:
            raise ValueError("Microsoft Teams OAuth credentials not configured")

        token_url = f"{self.AUTH_BASE_URL}/{tenant_id}/oauth2/v2.0/token"

        response = requests.post(
            token_url,
            data={
                "client_id": client_id,
                "client_secret": client_secret,
                "refresh_token": self.credentials.refresh_token,
                "grant_type": "refresh_token",
                "scope": " ".join(self.SCOPES),
            },
        )

        response.raise_for_status()
        data = response.json()

        expires_at = None
        if "expires_in" in data:
            expires_at = datetime.utcnow() + timedelta(seconds=data["expires_in"])

        # Update credentials
        self.credentials.access_token = data.get("access_token")
        if "refresh_token" in data:
            self.credentials.refresh_token = data.get("refresh_token")
        if expires_at:
            self.credentials.expires_at = expires_at
        from app.utils.db import safe_commit

        safe_commit("refresh_microsoft_teams_token", {"integration_id": self.integration.id})

        return {
            "access_token": data.get("access_token"),
            "expires_at": expires_at.isoformat() if expires_at else None,
        }

    def test_connection(self) -> Dict[str, Any]:
        """Test connection to Microsoft Teams."""
        token = self.get_access_token()
        if not token:
            return {"success": False, "message": "No access token available"}

        try:
            # Get user info
            response = requests.get(f"{self.GRAPH_BASE_URL}/me", headers={"Authorization": f"Bearer {token}"})

            if response.status_code == 200:
                user_data = response.json()
                return {
                    "success": True,
                    "message": f"Connected to Microsoft Teams as {user_data.get('displayName', 'Unknown')}",
                }
            else:
                return {"success": False, "message": f"API returned status {response.status_code}"}
        except Exception as e:
            return {"success": False, "message": f"Connection test failed: {str(e)}"}

    def send_message(self, channel_id: str, message: str) -> Dict[str, Any]:
        """Send a message to a Teams channel."""
        token = self.get_access_token()
        if not token:
            return {"success": False, "message": "No access token available"}

        try:
            # Send message to channel
            response = requests.post(
                f"{self.GRAPH_BASE_URL}/teams/{channel_id}/channels/{channel_id}/messages",
                headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
                json={"body": {"contentType": "text", "content": message}},
            )

            if response.status_code in [200, 201]:
                return {"success": True, "message": "Message sent successfully"}
            else:
                return {"success": False, "message": f"API returned status {response.status_code}"}
        except Exception as e:
            return {"success": False, "message": f"Error sending message: {str(e)}"}

    def sync_data(self, sync_type: str = "full") -> Dict[str, Any]:
        """Sync data from Microsoft Teams (channels, teams, etc.)."""
        token = self.get_access_token()
        if not token:
            return {"success": False, "message": "No access token available"}

        try:
            # Get teams
            response = requests.get(
                f"{self.GRAPH_BASE_URL}/me/joinedTeams", headers={"Authorization": f"Bearer {token}"}
            )

            if response.status_code == 200:
                teams = response.json().get("value", [])
                return {
                    "success": True,
                    "message": f"Sync completed. Found {len(teams)} teams.",
                    "synced_items": len(teams),
                }
            else:
                return {"success": False, "message": f"API returned status {response.status_code}"}
        except Exception as e:
            return {"success": False, "message": f"Sync failed: {str(e)}"}

    def get_config_schema(self) -> Dict[str, Any]:
        """Get configuration schema."""
        return {
            "fields": [
                {
                    "name": "default_channel_id",
                    "type": "string",
                    "label": "Default Channel ID",
                    "required": False,
                    "placeholder": "19:channel-id@thread.tacv2",
                    "description": "Default Teams channel ID for notifications",
                    "help": "Find channel ID in Teams channel settings or API",
                },
                {
                    "name": "sync_direction",
                    "type": "select",
                    "label": "Sync Direction",
                    "options": [
                        {"value": "teams_to_timetracker", "label": "Teams → TimeTracker (Import only)"},
                        {"value": "timetracker_to_teams", "label": "TimeTracker → Teams (Export only)"},
                        {"value": "bidirectional", "label": "Bidirectional (Two-way sync)"},
                    ],
                    "default": "timetracker_to_teams",
                    "description": "Choose how data flows between Microsoft Teams and TimeTracker",
                },
                {
                    "name": "sync_items",
                    "type": "array",
                    "label": "Items to Sync",
                    "options": [
                        {"value": "channels", "label": "Channels"},
                        {"value": "teams", "label": "Teams"},
                        {"value": "messages", "label": "Messages (as tasks)"},
                    ],
                    "default": [],
                    "description": "Select which items to synchronize",
                },
                {
                    "name": "notify_on_time_entry_start",
                    "type": "boolean",
                    "label": "Notify on Time Entry Start",
                    "default": False,
                    "description": "Send Teams notification when a time entry starts",
                },
                {
                    "name": "notify_on_time_entry_complete",
                    "type": "boolean",
                    "label": "Notify on Time Entry Complete",
                    "default": False,
                    "description": "Send Teams notification when a time entry is completed",
                },
                {
                    "name": "notify_on_task_complete",
                    "type": "boolean",
                    "label": "Notify on Task Complete",
                    "default": False,
                    "description": "Send Teams notification when a task is completed",
                },
                {
                    "name": "notify_on_invoice_sent",
                    "type": "boolean",
                    "label": "Notify on Invoice Sent",
                    "default": True,
                    "description": "Send Teams notification when an invoice is sent",
                },
                {
                    "name": "notify_on_project_create",
                    "type": "boolean",
                    "label": "Notify on Project Create",
                    "default": False,
                    "description": "Send Teams notification when a project is created",
                },
                {
                    "name": "auto_sync",
                    "type": "boolean",
                    "label": "Auto Sync",
                    "default": False,
                    "description": "Automatically sync when webhooks are received from Teams",
                },
                {
                    "name": "sync_interval",
                    "type": "select",
                    "label": "Sync Schedule",
                    "options": [
                        {"value": "manual", "label": "Manual only"},
                        {"value": "hourly", "label": "Every hour"},
                        {"value": "daily", "label": "Daily"},
                    ],
                    "default": "manual",
                    "description": "How often to automatically sync data",
                },
            ],
            "required": [],
            "sections": [
                {
                    "title": "Channel Settings",
                    "description": "Configure Teams channel for notifications",
                    "fields": ["default_channel_id"],
                },
                {
                    "title": "Sync Settings",
                    "description": "Configure what and how to sync",
                    "fields": ["sync_direction", "sync_items", "auto_sync", "sync_interval"],
                },
                {
                    "title": "Notification Settings",
                    "description": "Configure when to send Teams notifications",
                    "fields": ["notify_on_time_entry_start", "notify_on_time_entry_complete", "notify_on_task_complete", "notify_on_invoice_sent", "notify_on_project_create"],
                },
            ],
            "sync_settings": {
                "enabled": True,
                "auto_sync": False,
                "sync_interval": "manual",
                "sync_direction": "timetracker_to_teams",
                "sync_items": [],
            },
        }
