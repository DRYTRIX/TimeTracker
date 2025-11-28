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
    SCOPES = [
        'https://www.googleapis.com/auth/calendar',
        'https://www.googleapis.com/auth/calendar.events'
    ]

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
                    "redirect_uris": [redirect_uri]
                }
            },
            scopes=self.SCOPES,
            redirect_uri=redirect_uri
        )

        if state:
            flow.state = state

        authorization_url, _ = flow.authorization_url(
            access_type='offline',
            include_granted_scopes='true',
            prompt='consent'  # Force consent to get refresh token
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
                    "redirect_uris": [redirect_uri]
                }
            },
            scopes=self.SCOPES,
            redirect_uri=redirect_uri
        )

        flow.fetch_token(code=code)

        credentials = flow.credentials

        # Get user info
        user_info = {}
        try:
            service = build('oauth2', 'v2', credentials=credentials)
            user_info_response = service.userinfo().get().execute()
            user_info = {
                "email": user_info_response.get("email"),
                "name": user_info_response.get("name"),
                "picture": user_info_response.get("picture")
            }
        except Exception:
            pass

        return {
            "access_token": credentials.token,
            "refresh_token": credentials.refresh_token,
            "expires_at": credentials.expiry.isoformat() if credentials.expiry else None,
            "token_type": "Bearer",
            "scope": " ".join(credentials.scopes) if credentials.scopes else None,
            "extra_data": user_info
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
            client_secret=client_secret
        )

        credentials.refresh(Request())

        # Update credentials
        self.credentials.access_token = credentials.token
        if credentials.expiry:
            self.credentials.expires_at = credentials.expiry
        self.credentials.save()

        return {
            "access_token": credentials.token,
            "expires_at": credentials.expiry.isoformat() if credentials.expiry else None
        }

    def test_connection(self) -> Dict[str, Any]:
        """Test connection to Google Calendar."""
        try:
            service = self._get_calendar_service()
            calendar_list = service.calendarList().list().execute()
            return {
                "success": True,
                "message": f"Connected to Google Calendar. Found {len(calendar_list.get('items', []))} calendars."
            }
        except Exception as e:
            return {
                "success": False,
                "message": f"Connection test failed: {str(e)}"
            }

    def _get_calendar_service(self):
        """Get Google Calendar API service."""
        credentials = Credentials(
            token=self.credentials.access_token,
            refresh_token=self.credentials.refresh_token,
            token_uri="https://oauth2.googleapis.com/token",
            client_id=os.getenv("GOOGLE_CLIENT_ID"),
            client_secret=os.getenv("GOOGLE_CLIENT_SECRET")
        )

        # Refresh if needed
        if credentials.expired:
            credentials.refresh(Request())
            self.credentials.access_token = credentials.token
            if credentials.expiry:
                self.credentials.expires_at = credentials.expiry
            self.credentials.save()

        return build('calendar', 'v3', credentials=credentials)

    def sync_data(self, sync_type: str = "full") -> Dict[str, Any]:
        """Sync time entries with Google Calendar."""
        from app.models import TimeEntry, CalendarSyncEvent
        from app import db
        from datetime import datetime, timedelta

        try:
            service = self._get_calendar_service()

            # Get calendar ID from integration config
            calendar_id = self.integration.config.get("calendar_id", "primary")

            # Get time entries to sync
            if sync_type == "incremental":
                # Get last sync time
                last_sync = CalendarSyncEvent.query.filter_by(
                    integration_id=self.integration.id
                ).order_by(CalendarSyncEvent.synced_at.desc()).first()

                start_date = last_sync.synced_at if last_sync else datetime.utcnow() - timedelta(days=30)
            else:
                start_date = datetime.utcnow() - timedelta(days=90)

            # Get time entries
            time_entries = TimeEntry.query.filter(
                TimeEntry.user_id == self.integration.user_id,
                TimeEntry.start_time >= start_date,
                TimeEntry.end_time.isnot(None)
            ).all()

            synced_count = 0
            errors = []

            for entry in time_entries:
                try:
                    # Check if already synced
                    existing_sync = CalendarSyncEvent.query.filter_by(
                        integration_id=self.integration.id,
                        time_entry_id=entry.id
                    ).first()

                    if existing_sync:
                        # Update existing event
                        event_id = existing_sync.external_event_id
                        self._update_calendar_event(service, calendar_id, event_id, entry)
                    else:
                        # Create new event
                        event_id = self._create_calendar_event(service, calendar_id, entry)

                        # Create sync record
                        sync_event = CalendarSyncEvent(
                            integration_id=self.integration.id,
                            time_entry_id=entry.id,
                            external_event_id=event_id,
                            synced_at=datetime.utcnow()
                        )
                        db.session.add(sync_event)

                    synced_count += 1
                except Exception as e:
                    errors.append(f"Error syncing entry {entry.id}: {str(e)}")

            db.session.commit()

            return {
                "success": True,
                "synced_count": synced_count,
                "errors": errors
            }

        except Exception as e:
            return {
                "success": False,
                "message": f"Sync failed: {str(e)}"
            }

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
        description = "\n\n".join(description_parts) if description_parts else None

        event = {
            'summary': title,
            'description': description,
            'start': {
                'dateTime': time_entry.start_time.isoformat(),
                'timeZone': 'UTC',
            },
            'end': {
                'dateTime': time_entry.end_time.isoformat(),
                'timeZone': 'UTC',
            },
            'colorId': '9' if time_entry.billable else '11',  # Blue for billable, red for non-billable
        }

        created_event = service.events().insert(
            calendarId=calendar_id,
            body=event
        ).execute()

        return created_event['id']

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
        if time_entry.notes:
            description_parts.append(time_entry.notes)
        if time_entry.tags:
            description_parts.append(f"Tags: {time_entry.tags}")
        description = "\n\n".join(description_parts) if description_parts else None

        # Get existing event
        event = service.events().get(calendarId=calendar_id, eventId=event_id).execute()

        # Update event
        event['summary'] = title
        event['description'] = description
        event['start'] = {
            'dateTime': time_entry.start_time.isoformat(),
            'timeZone': 'UTC',
        }
        event['end'] = {
            'dateTime': time_entry.end_time.isoformat(),
            'timeZone': 'UTC',
        }
        event['colorId'] = '9' if time_entry.billable else '11'

        service.events().update(
            calendarId=calendar_id,
            eventId=event_id,
            body=event
        ).execute()

    def get_config_schema(self) -> Dict[str, Any]:
        """Get configuration schema."""
        return {
            "fields": [
                {
                    "name": "calendar_id",
                    "type": "string",
                    "label": "Calendar ID",
                    "default": "primary",
                    "description": "Google Calendar ID to sync with (default: primary)"
                },
                {
                    "name": "sync_direction",
                    "type": "select",
                    "label": "Sync Direction",
                    "options": [
                        {"value": "time_tracker_to_calendar", "label": "TimeTracker → Calendar"},
                        {"value": "calendar_to_time_tracker", "label": "Calendar → TimeTracker"},
                        {"value": "bidirectional", "label": "Bidirectional"}
                    ],
                    "default": "time_tracker_to_calendar"
                },
                {
                    "name": "auto_sync",
                    "type": "boolean",
                    "label": "Auto Sync",
                    "default": True,
                    "description": "Automatically sync when time entries are created/updated"
                }
            ],
            "required": []
        }

