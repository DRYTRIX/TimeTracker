"""
Microsoft Teams integration connector.
Send notifications and sync with Microsoft Teams.
"""

from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
from app.integrations.base import BaseConnector
import requests
import os


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
        tenant_id = creds.get("tenant_id") or os.getenv("MICROSOFT_TEAMS_TENANT_ID", "common")
        return tenant_id

    def get_authorization_url(self, redirect_uri: str, state: str = None) -> str:
        """Get Microsoft OAuth authorization URL."""
        from app.models import Settings

        settings = Settings.get_settings()
        creds = settings.get_integration_credentials("microsoft_teams")
        client_id = creds.get("client_id") or os.getenv("MICROSOFT_TEAMS_CLIENT_ID")
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
        client_id = creds.get("client_id") or os.getenv("MICROSOFT_TEAMS_CLIENT_ID")
        client_secret = creds.get("client_secret") or os.getenv("MICROSOFT_TEAMS_CLIENT_SECRET")
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
            except Exception:
                pass

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
        client_id = creds.get("client_id") or os.getenv("MICROSOFT_TEAMS_CLIENT_ID")
        client_secret = creds.get("client_secret") or os.getenv("MICROSOFT_TEAMS_CLIENT_SECRET")
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
                    "description": "Default Teams channel ID for notifications",
                },
                {
                    "name": "notify_on_time_entry_start",
                    "type": "boolean",
                    "label": "Notify on Time Entry Start",
                    "default": False,
                },
                {
                    "name": "notify_on_invoice_sent",
                    "type": "boolean",
                    "label": "Notify on Invoice Sent",
                    "default": True,
                },
            ],
            "required": [],
        }
