"""
Slack integration connector.
"""

from typing import Dict, Any, Optional
from datetime import datetime, timedelta
from app.integrations.base import BaseConnector
import requests
import os


class SlackConnector(BaseConnector):
    """Slack integration connector."""

    display_name = "Slack"
    description = "Send notifications and sync with Slack"
    icon = "slack"

    @property
    def provider_name(self) -> str:
        return "slack"

    def get_authorization_url(self, redirect_uri: str, state: str = None) -> str:
        """Get Slack OAuth authorization URL."""
        from app.models import Settings

        settings = Settings.get_settings()
        creds = settings.get_integration_credentials("slack")
        client_id = creds.get("client_id") or os.getenv("SLACK_CLIENT_ID")
        if not client_id:
            raise ValueError("SLACK_CLIENT_ID not configured")

        scopes = ["chat:write", "chat:write.public", "users:read", "channels:read", "groups:read"]

        auth_url = "https://slack.com/oauth/v2/authorize"
        params = {"client_id": client_id, "redirect_uri": redirect_uri, "scope": ",".join(scopes), "state": state or ""}

        query_string = "&".join([f"{k}={v}" for k, v in params.items()])
        return f"{auth_url}?{query_string}"

    def exchange_code_for_tokens(self, code: str, redirect_uri: str) -> Dict[str, Any]:
        """Exchange authorization code for tokens."""
        from app.models import Settings

        settings = Settings.get_settings()
        creds = settings.get_integration_credentials("slack")
        client_id = creds.get("client_id") or os.getenv("SLACK_CLIENT_ID")
        client_secret = creds.get("client_secret") or os.getenv("SLACK_CLIENT_SECRET")

        if not client_id or not client_secret:
            raise ValueError("Slack OAuth credentials not configured")

        token_url = "https://slack.com/api/oauth.v2.access"

        response = requests.post(
            token_url,
            data={"client_id": client_id, "client_secret": client_secret, "code": code, "redirect_uri": redirect_uri},
        )

        response.raise_for_status()
        data = response.json()

        if not data.get("ok"):
            raise ValueError(f"Slack API error: {data.get('error', 'Unknown error')}")

        access_token = data.get("access_token")
        expires_in = data.get("expires_in", 0)
        expires_at = None
        if expires_in > 0:
            expires_at = datetime.utcnow() + timedelta(seconds=expires_in)

        return {
            "access_token": access_token,
            "refresh_token": data.get("refresh_token"),
            "expires_at": expires_at,
            "token_type": "Bearer",
            "scope": data.get("scope"),
            "extra_data": {
                "team_id": data.get("team", {}).get("id"),
                "team_name": data.get("team", {}).get("name"),
                "authed_user": data.get("authed_user", {}),
            },
        }

    def refresh_access_token(self) -> Dict[str, Any]:
        """Refresh access token."""
        if not self.credentials or not self.credentials.refresh_token:
            raise ValueError("No refresh token available")

        from app.models import Settings

        settings = Settings.get_settings()
        creds = settings.get_integration_credentials("slack")
        client_id = creds.get("client_id") or os.getenv("SLACK_CLIENT_ID")
        client_secret = creds.get("client_secret") or os.getenv("SLACK_CLIENT_SECRET")

        token_url = "https://slack.com/api/oauth.v2.access"

        response = requests.post(
            token_url,
            data={
                "client_id": client_id,
                "client_secret": client_secret,
                "grant_type": "refresh_token",
                "refresh_token": self.credentials.refresh_token,
            },
        )

        response.raise_for_status()
        data = response.json()

        if not data.get("ok"):
            raise ValueError(f"Slack API error: {data.get('error', 'Unknown error')}")

        expires_at = None
        if "expires_in" in data:
            expires_at = datetime.utcnow() + timedelta(seconds=data["expires_in"])

        return {
            "access_token": data.get("access_token"),
            "refresh_token": data.get("refresh_token", self.credentials.refresh_token),
            "expires_at": expires_at,
        }

    def test_connection(self) -> Dict[str, Any]:
        """Test connection to Slack."""
        token = self.get_access_token()
        if not token:
            return {"success": False, "message": "No access token available"}

        api_url = "https://slack.com/api/auth.test"

        try:
            response = requests.post(api_url, headers={"Authorization": f"Bearer {token}"})

            response.raise_for_status()
            data = response.json()

            if data.get("ok"):
                return {"success": True, "message": f"Connected to {data.get('team', 'Unknown Team')}"}
            else:
                return {"success": False, "message": f"Slack API error: {data.get('error', 'Unknown error')}"}
        except Exception as e:
            return {"success": False, "message": f"Connection error: {str(e)}"}

    def sync_data(self, sync_type: str = "full") -> Dict[str, Any]:
        """Sync data from Slack (channels, users, etc.)."""
        token = self.get_access_token()
        if not token:
            return {"success": False, "message": "No access token available"}

        synced_count = 0
        errors = []

        try:
            # Get channels
            channels_response = requests.get(
                "https://slack.com/api/conversations.list",
                headers={"Authorization": f"Bearer {token}"},
                params={"types": "public_channel,private_channel", "exclude_archived": True},
            )

            if channels_response.status_code == 200:
                channels_data = channels_response.json()
                if channels_data.get("ok"):
                    channels = channels_data.get("channels", [])
                    synced_count += len(channels)

                    # Store channels in integration config
                    if not self.integration.config:
                        self.integration.config = {}
                    self.integration.config["channels"] = [
                        {"id": ch.get("id"), "name": ch.get("name"), "is_private": ch.get("is_private", False)}
                        for ch in channels
                    ]
                else:
                    errors.append(f"Slack API error: {channels_data.get('error', 'Unknown error')}")

            # Get users
            users_response = requests.get(
                "https://slack.com/api/users.list", headers={"Authorization": f"Bearer {token}"}
            )

            if users_response.status_code == 200:
                users_data = users_response.json()
                if users_data.get("ok"):
                    users = users_data.get("members", [])
                    synced_count += len(users)

                    # Store users in integration config
                    if not self.integration.config:
                        self.integration.config = {}
                    self.integration.config["users"] = [
                        {
                            "id": u.get("id"),
                            "name": u.get("name"),
                            "real_name": u.get("real_name", ""),
                            "email": u.get("profile", {}).get("email", ""),
                        }
                        for u in users
                        if not u.get("deleted", False)
                    ]
                else:
                    errors.append(f"Slack API error: {users_data.get('error', 'Unknown error')}")

            from app import db
            from app.utils.db import safe_commit

            safe_commit("sync_slack_data", {"integration_id": self.integration.id})

            return {
                "success": True,
                "message": f"Sync completed. Found {synced_count} items.",
                "synced_items": synced_count,
                "errors": errors,
            }
        except Exception as e:
            return {"success": False, "message": f"Sync failed: {str(e)}"}

    def handle_webhook(self, payload: Dict[str, Any], headers: Dict[str, str], raw_body: Optional[bytes] = None) -> Dict[str, Any]:
        """Handle incoming webhook from Slack."""
        import logging
        
        logger = logging.getLogger(__name__)
        
        try:
            # Slack webhooks typically use challenge-response for URL verification
            if payload.get("type") == "url_verification":
                challenge = payload.get("challenge")
                if not challenge:
                    return {"success": False, "message": "URL verification challenge missing"}
                return {"success": True, "challenge": challenge}

            event = payload.get("event", {})
            event_type = event.get("type", "")

            # Handle various Slack events
            if event_type == "message":
                return {"success": True, "message": "Message event received", "event_type": event_type}

            return {"success": True, "message": f"Webhook processed: {event_type}"}
        except KeyError as e:
            logger.error(f"Slack webhook missing required field: {e}")
            return {"success": False, "message": f"Invalid webhook payload: missing field {str(e)}"}
        except Exception as e:
            logger.error(f"Slack webhook processing error: {e}", exc_info=True)
            return {"success": False, "message": f"Error processing webhook: {str(e)}"}

    def send_message(self, channel: str, text: str) -> Dict[str, Any]:
        """Send a message to a Slack channel."""
        token = self.get_access_token()
        if not token:
            return {"success": False, "message": "No access token available"}

        api_url = "https://slack.com/api/chat.postMessage"

        response = requests.post(
            api_url,
            headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
            json={"channel": channel, "text": text},
        )

        response.raise_for_status()
        data = response.json()

        if data.get("ok"):
            return {"success": True, "message": "Message sent successfully"}
        else:
            return {"success": False, "message": f"Slack API error: {data.get('error', 'Unknown error')}"}

    def get_config_schema(self) -> Dict[str, Any]:
        """Get configuration schema."""
        return {
            "fields": [
                {
                    "name": "sync_direction",
                    "type": "select",
                    "label": "Sync Direction",
                    "options": [
                        {"value": "slack_to_timetracker", "label": "Slack → TimeTracker (Import only)"},
                        {"value": "timetracker_to_slack", "label": "TimeTracker → Slack (Export only)"},
                        {"value": "bidirectional", "label": "Bidirectional (Two-way sync)"},
                    ],
                    "default": "slack_to_timetracker",
                    "description": "Choose how data flows between Slack and TimeTracker",
                },
                {
                    "name": "sync_items",
                    "type": "array",
                    "label": "Items to Sync",
                    "options": [
                        {"value": "channels", "label": "Channels"},
                        {"value": "users", "label": "Users"},
                        {"value": "messages", "label": "Messages (as tasks)"},
                    ],
                    "default": ["channels", "users"],
                    "description": "Select which items to synchronize",
                },
                {
                    "name": "notification_channel",
                    "type": "text",
                    "label": "Notification Channel",
                    "required": False,
                    "placeholder": "#general or channel-id",
                    "help": "Channel ID or name where TimeTracker notifications will be sent",
                    "description": "Default channel for notifications",
                },
                {
                    "name": "auto_sync",
                    "type": "boolean",
                    "label": "Auto Sync",
                    "default": False,
                    "description": "Automatically sync when webhooks are received from Slack",
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
                {
                    "name": "notify_on_time_entry",
                    "type": "boolean",
                    "label": "Notify on Time Entry",
                    "default": False,
                    "description": "Send Slack notifications when time entries are created",
                },
                {
                    "name": "notify_on_task_complete",
                    "type": "boolean",
                    "label": "Notify on Task Complete",
                    "default": False,
                    "description": "Send Slack notifications when tasks are completed",
                },
            ],
            "required": [],
            "sections": [
                {
                    "title": "Sync Settings",
                    "description": "Configure what and how to sync",
                    "fields": ["sync_direction", "sync_items", "auto_sync", "sync_interval"],
                },
                {
                    "title": "Notification Settings",
                    "description": "Configure Slack notifications",
                    "fields": ["notification_channel", "notify_on_time_entry", "notify_on_task_complete"],
                },
            ],
            "sync_settings": {
                "enabled": True,
                "auto_sync": False,
                "sync_interval": "manual",
                "sync_direction": "slack_to_timetracker",
                "sync_items": ["channels", "users"],
            },
        }
