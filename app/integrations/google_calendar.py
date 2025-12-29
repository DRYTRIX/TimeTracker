"""
Google Calendar integration connector.
Provides two-way sync between TimeTracker and Google Calendar.
"""

from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
from app.integrations.base import BaseConnector
import requests
import os
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError


class GoogleCalendarConnector(BaseConnector):
    """Google Calendar integration connector."""

    display_name = "Google Calendar"
    description = "Two-way sync with Google Calendar"
    icon = "google"

    # OAuth 2.0 scopes required
    SCOPES = ["https://www.googleapis.com/auth/calendar", "https://www.googleapis.com/auth/calendar.events"]

    @property
    def provider_name(self) -> str:
        return "google_calendar"

    def get_authorization_url(self, redirect_uri: str, state: str = None) -> str:
        """Get Google OAuth authorization URL."""
        from app.models import Settings

        settings = Settings.get_settings()
        creds = settings.get_integration_credentials("google_calendar")
        client_id = creds.get("client_id") or os.getenv("GOOGLE_CLIENT_ID")
        client_secret = creds.get("client_secret") or os.getenv("GOOGLE_CLIENT_SECRET")

        if not client_id or not client_secret:
            raise ValueError("Google Calendar OAuth credentials not configured")

        flow = Flow.from_client_config(
            {
                "web": {
                    "client_id": client_id,
                    "client_secret": client_secret,
                    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                    "token_uri": "https://oauth2.googleapis.com/token",
                    "redirect_uris": [redirect_uri],
                }
            },
            scopes=self.SCOPES,
            redirect_uri=redirect_uri,
        )

        if state:
            flow.state = state

        authorization_url, _ = flow.authorization_url(
            access_type="offline", include_granted_scopes="true", prompt="consent"  # Force consent to get refresh token
        )

        return authorization_url

    def exchange_code_for_tokens(self, code: str, redirect_uri: str) -> Dict[str, Any]:
        """Exchange authorization code for tokens."""
        from app.models import Settings

        settings = Settings.get_settings()
        creds = settings.get_integration_credentials("google_calendar")
        client_id = creds.get("client_id") or os.getenv("GOOGLE_CLIENT_ID")
        client_secret = creds.get("client_secret") or os.getenv("GOOGLE_CLIENT_SECRET")

        if not client_id or not client_secret:
            raise ValueError("Google Calendar OAuth credentials not configured")

        flow = Flow.from_client_config(
            {
                "web": {
                    "client_id": client_id,
                    "client_secret": client_secret,
                    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                    "token_uri": "https://oauth2.googleapis.com/token",
                    "redirect_uris": [redirect_uri],
                }
            },
            scopes=self.SCOPES,
            redirect_uri=redirect_uri,
        )

        flow.fetch_token(code=code)

        credentials = flow.credentials

        # Get user info
        user_info = {}
        try:
            service = build("oauth2", "v2", credentials=credentials)
            user_info_response = service.userinfo().get().execute()
            user_info = {
                "email": user_info_response.get("email"),
                "name": user_info_response.get("name"),
                "picture": user_info_response.get("picture"),
            }
        except Exception as e:
            # Log error but don't fail - user info is optional
            import logging
            logger = logging.getLogger(__name__)
            logger.debug(f"Could not fetch Google user info: {e}")

        return {
            "access_token": credentials.token,
            "refresh_token": credentials.refresh_token,
            "expires_at": credentials.expiry.isoformat() if credentials.expiry else None,
            "token_type": "Bearer",
            "scope": " ".join(credentials.scopes) if credentials.scopes else None,
            "extra_data": user_info,
        }

    def refresh_access_token(self) -> Dict[str, Any]:
        """Refresh access token using refresh token."""
        if not self.credentials or not self.credentials.refresh_token:
            raise ValueError("No refresh token available")

        from app.models import Settings

        settings = Settings.get_settings()
        creds = settings.get_integration_credentials("google_calendar")
        client_id = creds.get("client_id") or os.getenv("GOOGLE_CLIENT_ID")
        client_secret = creds.get("client_secret") or os.getenv("GOOGLE_CLIENT_SECRET")

        if not client_id or not client_secret:
            raise ValueError("Google Calendar OAuth credentials not configured")

        credentials = Credentials(
            token=self.credentials.access_token,
            refresh_token=self.credentials.refresh_token,
            token_uri="https://oauth2.googleapis.com/token",
            client_id=client_id,
            client_secret=client_secret,
        )

        credentials.refresh(Request())

        # Update credentials
        from app.utils.db import safe_commit

        self.credentials.access_token = credentials.token
        if credentials.expiry:
            self.credentials.expires_at = credentials.expiry
        safe_commit("refresh_google_calendar_token", {"integration_id": self.integration.id})

        return {
            "access_token": credentials.token,
            "expires_at": credentials.expiry.isoformat() if credentials.expiry else None,
        }

    def test_connection(self) -> Dict[str, Any]:
        """Test connection to Google Calendar."""
        try:
            service = self._get_calendar_service()
            calendar_list = service.calendarList().list().execute()
            calendars = calendar_list.get("items", [])

            # Return calendar list for selection
            calendar_options = [
                {
                    "id": cal.get("id", "primary"),
                    "name": cal.get("summary", "Primary Calendar"),
                    "primary": cal.get("primary", False),
                }
                for cal in calendars
            ]

            return {
                "success": True,
                "message": f"Connected to Google Calendar. Found {len(calendars)} calendars.",
                "calendars": calendar_options,
            }
        except Exception as e:
            return {"success": False, "message": f"Connection test failed: {str(e)}"}

    def _get_calendar_service(self):
        """Get Google Calendar API service."""
        from app.models import Settings
        from app.utils.db import safe_commit

        settings = Settings.get_settings()
        creds = settings.get_integration_credentials("google_calendar")
        client_id = creds.get("client_id") or os.getenv("GOOGLE_CLIENT_ID")
        client_secret = creds.get("client_secret") or os.getenv("GOOGLE_CLIENT_SECRET")

        if not client_id or not client_secret:
            raise ValueError("Google Calendar OAuth credentials not configured")

        credentials = Credentials(
            token=self.credentials.access_token,
            refresh_token=self.credentials.refresh_token,
            token_uri="https://oauth2.googleapis.com/token",
            client_id=client_id,
            client_secret=client_secret,
        )

        # Refresh if needed
        if credentials.expired:
            credentials.refresh(Request())
            self.credentials.access_token = credentials.token
            if credentials.expiry:
                self.credentials.expires_at = credentials.expiry
            safe_commit("refresh_google_calendar_token", {"integration_id": self.integration.id})

        return build("calendar", "v3", credentials=credentials)

    def sync_data(self, sync_type: str = "full") -> Dict[str, Any]:
        """Sync time entries with Google Calendar (bidirectional)."""
        from app.models import TimeEntry
        from app import db
        from datetime import datetime, timedelta
        from app.utils.timezone import now_in_app_timezone

        try:
            service = self._get_calendar_service()

            # Get sync direction from config
            sync_direction = self.integration.config.get("sync_direction", "time_tracker_to_calendar")
            calendar_id = self.integration.config.get("calendar_id", "primary")

            synced_count = 0
            errors = []

            # Sync TimeTracker → Google Calendar
            if sync_direction in ["time_tracker_to_calendar", "bidirectional"]:
                # Get time entries to sync
                if sync_type == "incremental":
                    start_date = (
                        self.integration.last_sync_at
                        if self.integration.last_sync_at
                        else datetime.utcnow() - timedelta(days=30)
                    )
                else:
                    start_date = datetime.utcnow() - timedelta(days=90)

                # Get time entries
                time_entries = TimeEntry.query.filter(
                    TimeEntry.user_id == self.integration.user_id,
                    TimeEntry.start_time >= start_date,
                    TimeEntry.end_time.isnot(None),
                ).all()

                for entry in time_entries:
                    try:
                        # Check if already synced (check metadata)
                        existing_event_id = None
                        if hasattr(entry, "metadata") and entry.metadata:
                            existing_event_id = entry.metadata.get("google_calendar_event_id")

                        if existing_event_id:
                            # Update existing event
                            self._update_calendar_event(service, calendar_id, existing_event_id, entry)
                        else:
                            # Create new event
                            event_id = self._create_calendar_event(service, calendar_id, entry)

                            # Store event ID in time entry metadata
                            if not hasattr(entry, "metadata") or not entry.metadata:
                                entry.metadata = {}
                            entry.metadata = entry.metadata or {}
                            entry.metadata["google_calendar_event_id"] = event_id

                        synced_count += 1
                    except Exception as e:
                        errors.append(f"Error syncing entry {entry.id}: {str(e)}")

            # Sync Google Calendar → TimeTracker
            if sync_direction in ["calendar_to_time_tracker", "bidirectional"]:
                # Get events from Google Calendar
                time_min = datetime.utcnow() - timedelta(days=90)
                if sync_type == "incremental" and self.integration.last_sync_at:
                    time_min = self.integration.last_sync_at

                events_result = (
                    service.events()
                    .list(
                        calendarId=calendar_id,
                        timeMin=time_min.isoformat() + "Z",
                        maxResults=250,
                        singleEvents=True,
                        orderBy="startTime",
                    )
                    .execute()
                )

                events = events_result.get("items", [])

                for event in events:
                    try:
                        # Skip events we created (check description for marker)
                        if event.get("description", "").startswith("TimeTracker:"):
                            continue

                        # Check if we already have this event
                        event_id = event.get("id")
                        existing_entry = TimeEntry.query.filter(
                            TimeEntry.user_id == self.integration.user_id,
                            TimeEntry.metadata.contains({"google_calendar_event_id": event_id}),
                        ).first()

                        if not existing_entry:
                            # Create time entry from calendar event
                            start_str = event["start"].get("dateTime", event["start"].get("date"))
                            end_str = event["end"].get("dateTime", event["end"].get("date"))

                            start_time = datetime.fromisoformat(start_str.replace("Z", "+00:00"))
                            end_time = datetime.fromisoformat(end_str.replace("Z", "+00:00"))

                            # Try to match project/task from event title
                            project = None
                            task = None
                            title = event.get("summary", "")

                            # Simple matching: look for project name in title
                            from app.models import Project, Task

                            projects = Project.query.filter_by(user_id=self.integration.user_id, status="active").all()
                            for p in projects:
                                if p.name in title:
                                    project = p
                                    break

                            time_entry = TimeEntry(
                                user_id=self.integration.user_id,
                                project_id=project.id if project else None,
                                task_id=task.id if task else None,
                                start_time=start_time,
                                end_time=end_time,
                                notes=event.get("description", ""),
                                billable=False,
                            )

                            # Store Google Calendar event ID
                            time_entry.metadata = {"google_calendar_event_id": event_id}

                            db.session.add(time_entry)
                            synced_count += 1
                    except Exception as e:
                        errors.append(f"Error syncing calendar event {event.get('id', 'unknown')}: {str(e)}")

            # Update last sync time
            self.integration.last_sync_at = now_in_app_timezone()
            self.integration.last_sync_status = "success" if not errors else "partial"
            if errors:
                self.integration.last_error = "; ".join(errors[:3])  # Store first 3 errors

            db.session.commit()

            return {
                "success": True,
                "synced_count": synced_count,
                "errors": errors,
                "message": f"Synced {synced_count} items",
            }

        except Exception as e:
            self.integration.last_sync_status = "error"
            self.integration.last_error = str(e)
            db.session.commit()
            return {"success": False, "message": f"Sync failed: {str(e)}"}

    def _create_calendar_event(self, service, calendar_id: str, time_entry) -> str:
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
        description_parts = []
        # Add marker to identify TimeTracker-created events
        description_parts.append("TimeTracker: Created from time entry")
        if time_entry.notes:
            description_parts.append(time_entry.notes)
        if time_entry.tags:
            description_parts.append(f"Tags: {time_entry.tags}")
        description = "\n\n".join(description_parts) if description_parts else "TimeTracker: Created from time entry"

        event = {
            "summary": title,
            "description": description,
            "start": {
                "dateTime": time_entry.start_time.isoformat(),
                "timeZone": "UTC",
            },
            "end": {
                "dateTime": time_entry.end_time.isoformat(),
                "timeZone": "UTC",
            },
            "colorId": "9" if time_entry.billable else "11",  # Blue for billable, red for non-billable
        }

        created_event = service.events().insert(calendarId=calendar_id, body=event).execute()

        return created_event["id"]

    def _update_calendar_event(self, service, calendar_id: str, event_id: str, time_entry):
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
        # Add marker to identify TimeTracker-created events
        description_parts.append("TimeTracker: Created from time entry")
        if time_entry.notes:
            description_parts.append(time_entry.notes)
        if time_entry.tags:
            description_parts.append(f"Tags: {time_entry.tags}")
        description = "\n\n".join(description_parts) if description_parts else "TimeTracker: Created from time entry"

        # Get existing event
        event = service.events().get(calendarId=calendar_id, eventId=event_id).execute()

        # Update event
        event["summary"] = title
        event["description"] = description
        event["start"] = {
            "dateTime": time_entry.start_time.isoformat(),
            "timeZone": "UTC",
        }
        event["end"] = {
            "dateTime": time_entry.end_time.isoformat(),
            "timeZone": "UTC",
        }
        event["colorId"] = "9" if time_entry.billable else "11"

        service.events().update(calendarId=calendar_id, eventId=event_id, body=event).execute()

    def get_config_schema(self) -> Dict[str, Any]:
        """Get configuration schema."""
        return {
            "fields": [
                {
                    "name": "calendar_id",
                    "type": "string",
                    "label": "Calendar ID",
                    "default": "primary",
                    "required": False,
                    "placeholder": "primary",
                    "description": "Google Calendar ID to sync with (default: primary)",
                    "help": "Use 'primary' for your main calendar, or enter a specific calendar ID from Google Calendar settings",
                },
                {
                    "name": "sync_direction",
                    "type": "select",
                    "label": "Sync Direction",
                    "options": [
                        {"value": "time_tracker_to_calendar", "label": "TimeTracker → Calendar (Export only)"},
                        {"value": "calendar_to_time_tracker", "label": "Calendar → TimeTracker (Import only)"},
                        {"value": "bidirectional", "label": "Bidirectional (Two-way sync)"},
                    ],
                    "default": "time_tracker_to_calendar",
                    "description": "Choose how data flows between Google Calendar and TimeTracker",
                },
                {
                    "name": "sync_items",
                    "type": "array",
                    "label": "Items to Sync",
                    "options": [
                        {"value": "time_entries", "label": "Time Entries"},
                        {"value": "events", "label": "Calendar Events"},
                    ],
                    "default": ["time_entries"],
                    "description": "Select which items to synchronize",
                },
                {
                    "name": "auto_sync",
                    "type": "boolean",
                    "label": "Auto Sync",
                    "default": True,
                    "description": "Automatically sync when time entries are created/updated",
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
                    "default": "hourly",
                    "description": "How often to automatically sync data",
                },
                {
                    "name": "event_title_format",
                    "type": "text",
                    "label": "Event Title Format",
                    "default": "{project} - {task}",
                    "placeholder": "{project} - {task}",
                    "description": "Format for calendar event titles. Use {project}, {task}, {notes} as placeholders",
                    "help": "Customize how time entries appear as calendar events",
                },
                {
                    "name": "sync_past_days",
                    "type": "number",
                    "label": "Sync Past Days",
                    "default": 90,
                    "validation": {"min": 1, "max": 365},
                    "description": "Number of days in the past to sync (1-365)",
                    "help": "How far back to sync calendar events",
                },
                {
                    "name": "sync_future_days",
                    "type": "number",
                    "label": "Sync Future Days",
                    "default": 30,
                    "validation": {"min": 1, "max": 365},
                    "description": "Number of days in the future to sync (1-365)",
                    "help": "How far ahead to sync calendar events",
                },
            ],
            "required": [],
            "sections": [
                {
                    "title": "Calendar Settings",
                    "description": "Configure your Google Calendar connection",
                    "fields": ["calendar_id"],
                },
                {
                    "title": "Sync Settings",
                    "description": "Configure what and how to sync",
                    "fields": ["sync_direction", "sync_items", "auto_sync", "sync_interval", "sync_past_days", "sync_future_days"],
                },
                {
                    "title": "Display Settings",
                    "description": "Customize how events appear in the calendar",
                    "fields": ["event_title_format"],
                },
            ],
            "sync_settings": {
                "enabled": True,
                "auto_sync": True,
                "sync_interval": "hourly",
                "sync_direction": "time_tracker_to_calendar",
                "sync_items": ["time_entries"],
            },
        }
