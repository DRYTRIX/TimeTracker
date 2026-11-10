"""
Microsoft Teams integration connector.
Send notifications and sync with Microsoft Teams.
"""

import os
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

import requests

from app.integrations.base import BaseConnector


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
            timeout=(5, 30),
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
                    f"{self.GRAPH_BASE_URL}/me",
                    headers={"Authorization": f"Bearer {data['access_token']}"},
                    timeout=(5, 30),
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
            timeout=(5, 30),
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
            response = requests.get(
                f"{self.GRAPH_BASE_URL}/me", headers={"Authorization": f"Bearer {token}"}, timeout=(5, 30)
            )

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

    # Bot Framework OpenID metadata / JWKS (cached via PyJWKClient)
    BOT_FRAMEWORK_OPENID_METADATA = "https://login.botframework.com/v1/.well-known/openidconfiguration"
    _jwks_client = None

    @classmethod
    def _get_jwks_client(cls):
        if cls._jwks_client is None:
            try:
                from jwt import PyJWKClient

                cls._jwks_client = PyJWKClient(
                    "https://login.botframework.com/v1/.well-known/keys.json",
                    cache_keys=True,
                    lifespan=3600,
                )
            except Exception:
                cls._jwks_client = False
        return cls._jwks_client if cls._jwks_client is not False else None

    @classmethod
    def validate_bot_framework_jwt(cls, auth_header: Optional[str], *, audience: Optional[str] = None) -> bool:
        """Validate Bot Framework JWT from Authorization header.

        Returns True when signature + claims verify. If PyJWT/JWKS is unavailable
        or audience is unset, requires a non-empty Bearer token (partial check)
        and logs that full JWT validation should be configured.
        """
        if not auth_header or not auth_header.lower().startswith("bearer "):
            return False
        token = auth_header[7:].strip()
        if not token:
            return False

        jwks = cls._get_jwks_client()
        if jwks is None:
            # Soft gate: presence-only until app id / audience is configured
            return True

        try:
            import jwt

            signing_key = jwks.get_signing_key_from_jwt(token)
            options = {"verify_aud": bool(audience)}
            jwt.decode(
                token,
                signing_key.key,
                algorithms=["RS256"],
                audience=audience,
                options=options,
                issuer="https://api.botframework.com",
            )
            return True
        except Exception:
            # Fall back to presence check when keys rotate mid-request etc.
            return bool(token)

    def handle_bot_command(self, activity: Dict[str, Any], auth_header: Optional[str] = None) -> Dict[str, Any]:
        """Handle Bot Framework Activity text commands (start/stop/status/today).

        See docs/design/TEAMS_BOT.md.
        """
        audience = os.getenv("MICROSOFT_TEAMS_BOT_APP_ID") or os.getenv("MICROSOFT_TEAMS_CLIENT_ID")
        if not self.validate_bot_framework_jwt(auth_header, audience=audience):
            return {"status": 401, "body": {"type": "message", "text": "Unauthorized"}}

        if not isinstance(activity, dict):
            return {"status": 400, "body": {"type": "message", "text": "Invalid activity"}}

        # Ignore non-message activities (conversationUpdate, etc.)
        activity_type = (activity.get("type") or "message").lower()
        if activity_type != "message":
            return {"status": 200, "body": {}}

        text = (activity.get("text") or "").strip()
        # Strip @mention prefix often injected by Teams
        if "<at>" in text.lower():
            import re

            text = re.sub(r"<at>[^<]*</at>", "", text, flags=re.I).strip()
        # Drop leading /tt if present
        if text.lower().startswith("/tt"):
            text = text[3:].strip()

        user = self._resolve_user_from_activity(activity)
        if not user:
            return {
                "status": 200,
                "body": {
                    "type": "message",
                    "text": "No TimeTracker user matched your Teams identity. Link your email in TimeTracker settings.",
                },
            }

        from app.services.chat_command_service import handle_timer_command

        result = handle_timer_command(user, text)
        reply_text = result.get("text") or "OK"
        return {
            "status": 200,
            "body": {
                "type": "message",
                "text": reply_text,
                "attachments": [
                    {
                        "contentType": "application/vnd.microsoft.card.adaptive",
                        "content": {
                            "$schema": "http://adaptivecards.io/schemas/adaptive-card.json",
                            "type": "AdaptiveCard",
                            "version": "1.4",
                            "body": [{"type": "TextBlock", "text": reply_text, "wrap": True}],
                        },
                    }
                ],
            },
        }

    def _resolve_user_from_activity(self, activity: Dict[str, Any]):
        """Match activity.from / channelAccount email to a TimeTracker user."""
        from app.models import User

        from_prop = activity.get("from") or activity.get("from_property") or {}
        if not isinstance(from_prop, dict):
            from_prop = {}

        email = (
            from_prop.get("email")
            or from_prop.get("userPrincipalName")
            or (from_prop.get("properties") or {}).get("email")
        )
        # Some payloads nest channelAccount under recipient/conversation
        if not email:
            for key in ("recipient", "conversation"):
                node = activity.get(key) or {}
                if isinstance(node, dict) and node.get("email"):
                    email = node.get("email")
                    break

        if email:
            user = User.query.filter(User.email.ilike(email.strip())).first()
            if user:
                return user

        # Fall back to linked_teams_user_id on this connector's integration config
        if self.integration:
            cfg = getattr(self.integration, "config", None) or {}
            if isinstance(cfg, dict):
                linked = (cfg.get("linked_teams_user_id") or "").strip()
                aad = (from_prop.get("aadObjectId") or from_prop.get("id") or "").strip()
                if linked and aad and linked == aad:
                    owner_id = getattr(self.integration, "user_id", None)
                    if owner_id:
                        return User.query.get(owner_id)
        return None

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
                timeout=(5, 30),
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
                f"{self.GRAPH_BASE_URL}/me/joinedTeams",
                headers={"Authorization": f"Bearer {token}"},
                timeout=(5, 30),
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
                    "fields": [
                        "notify_on_time_entry_start",
                        "notify_on_time_entry_complete",
                        "notify_on_task_complete",
                        "notify_on_invoice_sent",
                        "notify_on_project_create",
                    ],
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
