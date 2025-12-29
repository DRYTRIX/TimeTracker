"""
Outlook Calendar integration connector.
Provides two-way sync between TimeTracker and Outlook Calendar.
"""

from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
from app.integrations.base import BaseConnector
import requests
import os


class OutlookCalendarConnector(BaseConnector):
    """Outlook Calendar integration connector using Microsoft Graph API."""

    display_name = "Outlook Calendar"
    description = "Two-way sync with Outlook Calendar"
    icon = "microsoft"

    # Microsoft Graph API endpoints
    GRAPH_BASE_URL = "https://graph.microsoft.com/v1.0"
    AUTH_BASE_URL = "https://login.microsoftonline.com"

    # OAuth 2.0 scopes required
    SCOPES = ["Calendars.ReadWrite", "offline_access", "User.Read"]

    @property
    def provider_name(self) -> str:
        return "outlook_calendar"

    def _get_tenant_id(self) -> str:
        """Get tenant ID from settings or use 'common' for multi-tenant."""
        from app.models import Settings

        settings = Settings.get_settings()
        creds = settings.get_integration_credentials("outlook_calendar")
        tenant_id = creds.get("tenant_id") or os.getenv("OUTLOOK_TENANT_ID", "common")
        return tenant_id

    def get_authorization_url(self, redirect_uri: str, state: str = None) -> str:
        """Get Microsoft OAuth authorization URL."""
        from app.models import Settings

        settings = Settings.get_settings()
        creds = settings.get_integration_credentials("outlook_calendar")
        client_id = creds.get("client_id") or os.getenv("OUTLOOK_CLIENT_ID")
        tenant_id = self._get_tenant_id()

        if not client_id:
            raise ValueError("Outlook Calendar OAuth credentials not configured")

        auth_url = f"{self.AUTH_BASE_URL}/{tenant_id}/oauth2/v2.0/authorize"

        params = {
            "client_id": client_id,
            "response_type": "code",
            "redirect_uri": redirect_uri,
            "response_mode": "query",
            "scope": " ".join(self.SCOPES),
            "state": state or "",
            "prompt": "consent",  # Force consent to get refresh token
        }

        query_string = "&".join([f"{k}={v}" for k, v in params.items()])
        return f"{auth_url}?{query_string}"

    def exchange_code_for_tokens(self, code: str, redirect_uri: str) -> Dict[str, Any]:
        """Exchange authorization code for tokens."""
        from app.models import Settings

        settings = Settings.get_settings()
        creds = settings.get_integration_credentials("outlook_calendar")
        client_id = creds.get("client_id") or os.getenv("OUTLOOK_CLIENT_ID")
        client_secret = creds.get("client_secret") or os.getenv("OUTLOOK_CLIENT_SECRET")
        tenant_id = self._get_tenant_id()

        if not client_id or not client_secret:
            raise ValueError("Outlook Calendar OAuth credentials not configured")

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
                        "userPrincipalName": user_data.get("userPrincipalName"),
                    }
            except Exception as e:
                # Log error but don't fail - user info is optional
                import logging
                logger = logging.getLogger(__name__)
                logger.debug(f"Could not fetch Outlook user info: {e}")

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
        creds = settings.get_integration_credentials("outlook_calendar")
        client_id = creds.get("client_id") or os.getenv("OUTLOOK_CLIENT_ID")
        client_secret = creds.get("client_secret") or os.getenv("OUTLOOK_CLIENT_SECRET")
        tenant_id = self._get_tenant_id()

        if not client_id or not client_secret:
            raise ValueError("Outlook Calendar OAuth credentials not configured")

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

        safe_commit("refresh_outlook_calendar_token", {"integration_id": self.integration.id})

        return {
            "access_token": data.get("access_token"),
            "expires_at": expires_at.isoformat() if expires_at else None,
        }

    def test_connection(self) -> Dict[str, Any]:
        """Test connection to Outlook Calendar."""
        token = self.get_access_token()
        if not token:
            return {"success": False, "message": "No access token available"}

        try:
            # Get user info and calendars
            response = requests.get(f"{self.GRAPH_BASE_URL}/me/calendars", headers={"Authorization": f"Bearer {token}"})

            if response.status_code == 200:
                calendars = response.json().get("value", [])
                return {"success": True, "message": f"Connected to Outlook Calendar. Found {len(calendars)} calendars."}
            else:
                return {"success": False, "message": f"API returned status {response.status_code}"}
        except Exception as e:
            return {"success": False, "message": f"Connection test failed: {str(e)}"}

    def sync_data(self, sync_type: str = "full") -> Dict[str, Any]:
        """Sync time entries with Outlook Calendar."""
        from app.models import TimeEntry
        from app import db
        from datetime import datetime, timedelta

        try:
            token = self.get_access_token()
            if not token:
                return {"success": False, "message": "No access token available"}

            # Get calendar ID from integration config
            calendar_id = self.integration.config.get("calendar_id", "calendar")

            # Get time entries to sync
            if sync_type == "incremental":
                start_date = datetime.utcnow() - timedelta(days=30)
            else:
                start_date = datetime.utcnow() - timedelta(days=90)

            # Get time entries
            time_entries = TimeEntry.query.filter(
                TimeEntry.user_id == self.integration.user_id,
                TimeEntry.start_time >= start_date,
                TimeEntry.end_time.isnot(None),
            ).all()

            synced_count = 0
            errors = []

            for entry in time_entries:
                try:
                    # Check if already synced
                    existing_event_id = None
                    if hasattr(entry, "metadata") and entry.metadata:
                        existing_event_id = entry.metadata.get("outlook_event_id")

                    if existing_event_id:
                        # Update existing event
                        self._update_calendar_event(token, calendar_id, existing_event_id, entry)
                    else:
                        # Create new event
                        event_id = self._create_calendar_event(token, calendar_id, entry)

                        # Store event ID in time entry metadata
                        if not hasattr(entry, "metadata") or not entry.metadata:
                            entry.metadata = {}
                        entry.metadata = entry.metadata or {}
                        entry.metadata["outlook_event_id"] = event_id

                    synced_count += 1
                except Exception as e:
                    errors.append(f"Error syncing entry {entry.id}: {str(e)}")

            db.session.commit()

            return {"success": True, "synced_count": synced_count, "errors": errors}

        except Exception as e:
            return {"success": False, "message": f"Sync failed: {str(e)}"}

    def _create_calendar_event(self, token: str, calendar_id: str, time_entry) -> str:
        """Create a calendar event from a time entry."""
        from app.models import Project, Task

        project = Project.query.get(time_entry.project_id)
        task = Task.query.get(time_entry.task_id) if time_entry.task_id else None

        # Build event title
        title_parts = []
        if project:
            title_parts.append(project.name)
        if task:
            title_parts.append(task.name)
        if not title_parts:
            title_parts.append("Time Entry")

        title = " - ".join(title_parts)

        # Build description
        description_parts = []
        if time_entry.notes:
            description_parts.append(time_entry.notes)
        if time_entry.tags:
            description_parts.append(f"Tags: {time_entry.tags}")
        description = "\n\n".join(description_parts) if description_parts else None

        event = {
            "subject": title,
            "body": {"contentType": "text", "content": description or ""},
            "start": {"dateTime": time_entry.start_time.isoformat(), "timeZone": "UTC"},
            "end": {"dateTime": time_entry.end_time.isoformat(), "timeZone": "UTC"},
            "isAllDay": False,
        }

        response = requests.post(
            f"{self.GRAPH_BASE_URL}/me/calendars/{calendar_id}/events",
            headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
            json=event,
        )

        response.raise_for_status()
        created_event = response.json()
        return created_event["id"]

    def _update_calendar_event(self, token: str, calendar_id: str, event_id: str, time_entry):
        """Update an existing calendar event."""
        from app.models import Project, Task

        project = Project.query.get(time_entry.project_id)
        task = Task.query.get(time_entry.task_id) if time_entry.task_id else None

        # Build event title
        title_parts = []
        if project:
            title_parts.append(project.name)
        if task:
            title_parts.append(task.name)
        if not title_parts:
            title_parts.append("Time Entry")

        title = " - ".join(title_parts)

        # Build description
        description_parts = []
        if time_entry.notes:
            description_parts.append(time_entry.notes)
        if time_entry.tags:
            description_parts.append(f"Tags: {time_entry.tags}")
        description = "\n\n".join(description_parts) if description_parts else None

        event = {
            "subject": title,
            "body": {"contentType": "text", "content": description or ""},
            "start": {"dateTime": time_entry.start_time.isoformat(), "timeZone": "UTC"},
            "end": {"dateTime": time_entry.end_time.isoformat(), "timeZone": "UTC"},
        }

        response = requests.patch(
            f"{self.GRAPH_BASE_URL}/me/calendars/{calendar_id}/events/{event_id}",
            headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
            json=event,
        )

        response.raise_for_status()

    def get_config_schema(self) -> Dict[str, Any]:
        """Get configuration schema."""
        return {
            "fields": [
                {
                    "name": "calendar_id",
                    "type": "string",
                    "label": "Calendar ID",
                    "default": "calendar",
                    "description": "Outlook Calendar ID to sync with (default: 'calendar' for primary calendar)",
                },
                {
                    "name": "sync_direction",
                    "type": "select",
                    "label": "Sync Direction",
                    "options": [
                        {"value": "time_tracker_to_calendar", "label": "TimeTracker → Calendar"},
                        {"value": "calendar_to_time_tracker", "label": "Calendar → TimeTracker"},
                        {"value": "bidirectional", "label": "Bidirectional"},
                    ],
                    "default": "time_tracker_to_calendar",
                },
                {
                    "name": "auto_sync",
                    "type": "boolean",
                    "label": "Auto Sync",
                    "default": True,
                    "description": "Automatically sync when time entries are created/updated",
                },
            ],
            "required": [],
        }
