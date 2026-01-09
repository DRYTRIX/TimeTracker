"""
Google Calendar integration connector.
Provides two-way sync between TimeTracker and Google Calendar.
"""

from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta, timezone
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
            state=state,  # Explicitly pass state parameter
            access_type="offline", 
            include_granted_scopes="true", 
            prompt="consent"  # Force consent to get refresh token
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
        from app.models.integration_external_event_link import IntegrationExternalEventLink
        from app import db
        from datetime import datetime, timedelta
        from app.utils.timezone import now_in_app_timezone
        import logging
        
        logger = logging.getLogger(__name__)

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

                logger.info(f"TimeTracker→Calendar sync starting: sync_direction='{sync_direction}', sync_type='{sync_type}'")
                logger.info(f"  Calendar ID: {calendar_id}")
                logger.info(f"  Time range: from {start_date}")

                # Get time entries
                time_entries = TimeEntry.query.filter(
                    TimeEntry.user_id == self.integration.user_id,
                    TimeEntry.start_time >= start_date,
                    TimeEntry.end_time.isnot(None),
                ).all()

                logger.info(f"Found {len(time_entries)} time entries to sync to Google Calendar")

                for entry in time_entries:
                    try:
                        # Check if already synced using IntegrationExternalEventLink
                        existing_link = IntegrationExternalEventLink.query.filter_by(
                            integration_id=self.integration.id,
                            time_entry_id=entry.id
                        ).first()
                        existing_event_id = existing_link.external_uid if existing_link else None

                        if existing_event_id:
                            # Update existing event
                            logger.debug(f"Updating existing calendar event {existing_event_id} for time entry {entry.id}")
                            self._update_calendar_event(service, calendar_id, existing_event_id, entry)
                        else:
                            # Create new event
                            logger.debug(f"Creating new calendar event for time entry {entry.id}")
                            event_id = self._create_calendar_event(service, calendar_id, entry)

                            # Create or update link
                            if existing_link:
                                existing_link.external_uid = event_id
                            else:
                                link = IntegrationExternalEventLink(
                                    integration_id=self.integration.id,
                                    time_entry_id=entry.id,
                                    external_uid=event_id,
                                    external_href=None,  # Google Calendar doesn't use hrefs
                                )
                                db.session.add(link)

                        synced_count += 1
                        logger.debug(f"Synced time entry {entry.id} to Google Calendar")
                    except Exception as e:
                        error_msg = f"Error syncing entry {entry.id}: {str(e)}"
                        errors.append(error_msg)
                        logger.warning(f"{error_msg}", exc_info=True)
                
                logger.info(f"TimeTracker→Calendar sync completed: synced {synced_count} time entries")

            # Sync Google Calendar → TimeTracker
            if sync_direction in ["calendar_to_time_tracker", "bidirectional"]:
                # Get events from Google Calendar
                time_min = datetime.utcnow() - timedelta(days=90)
                if sync_type == "incremental" and self.integration.last_sync_at:
                    time_min = self.integration.last_sync_at

                logger.info(f"Google Calendar sync starting: sync_direction='{sync_direction}', sync_type='{sync_type}'")
                logger.info(f"  Calendar ID: {calendar_id}")
                logger.info(f"  Time range: from {time_min}")

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
                logger.info(f"Fetched {len(events)} events from Google Calendar")

                imported = 0
                skipped = 0
                skipped_reasons = {"time_tracker_created": 0, "already_imported": 0, "invalid_time": 0, "other": 0}

                for event in events:
                    try:
                        event_id = event.get("id")
                        event_summary = event.get("summary", "No title")
                        
                        # Skip events we created (check description for marker)
                        if event.get("description", "").startswith("TimeTracker:"):
                            logger.debug(f"Skipping event {event_id} - created by TimeTracker")
                            skipped += 1
                            skipped_reasons["time_tracker_created"] += 1
                            continue

                        # Check if we already have this event using IntegrationExternalEventLink
                        existing_link = IntegrationExternalEventLink.query.filter_by(
                            integration_id=self.integration.id,
                            external_uid=event_id
                        ).first()

                        if existing_link:
                            logger.debug(f"Event {event_id} ({event_summary}) already imported, skipping")
                            skipped += 1
                            skipped_reasons["already_imported"] += 1
                            continue

                        # Create time entry from calendar event
                        start_str = event["start"].get("dateTime", event["start"].get("date"))
                        end_str = event["end"].get("dateTime", event["end"].get("date"))

                        if not start_str or not end_str:
                            logger.warning(f"Event {event_id} missing start or end time, skipping")
                            skipped += 1
                            skipped_reasons["invalid_time"] += 1
                            continue

                        # Parse datetime strings (Google Calendar returns ISO format with timezone)
                        start_time_utc = datetime.fromisoformat(start_str.replace("Z", "+00:00"))
                        end_time_utc = datetime.fromisoformat(end_str.replace("Z", "+00:00"))

                        # Ensure timezone-aware (assume UTC if naive)
                        if start_time_utc.tzinfo is None:
                            start_time_utc = start_time_utc.replace(tzinfo=timezone.utc)
                        else:
                            start_time_utc = start_time_utc.astimezone(timezone.utc)
                        
                        if end_time_utc.tzinfo is None:
                            end_time_utc = end_time_utc.replace(tzinfo=timezone.utc)
                        else:
                            end_time_utc = end_time_utc.astimezone(timezone.utc)

                        if end_time_utc <= start_time_utc:
                            logger.warning(f"Event {event_id} has invalid time range: start={start_time_utc}, end={end_time_utc}")
                            skipped += 1
                            skipped_reasons["invalid_time"] += 1
                            continue

                        # Convert UTC to local naive datetime (TimeEntry stores local naive datetimes)
                        from app.utils.timezone import utc_to_local
                        start_time_local = utc_to_local(start_time_utc).replace(tzinfo=None)
                        end_time_local = utc_to_local(end_time_utc).replace(tzinfo=None)

                        # Try to match project/task from event title
                        project = None
                        task = None
                        title = event_summary

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
                            start_time=start_time_local,
                            end_time=end_time_local,
                            notes=event.get("description", ""),
                            billable=False,
                            source="auto",
                        )

                        db.session.add(time_entry)
                        db.session.flush()  # Flush to get time_entry.id

                        # Create link to track this import
                        link = IntegrationExternalEventLink(
                            integration_id=self.integration.id,
                            time_entry_id=time_entry.id,
                            external_uid=event_id,
                            external_href=None,  # Google Calendar doesn't use hrefs
                        )
                        db.session.add(link)

                        imported += 1
                        synced_count += 1
                        logger.info(f"Imported event {event_id} ({event_summary}) as time entry {time_entry.id}")
                    except Exception as e:
                        error_msg = f"Error syncing calendar event {event.get('id', 'unknown')}: {str(e)}"
                        errors.append(error_msg)
                        logger.warning(f"{error_msg}", exc_info=True)
                
                if imported > 0 or skipped > 0:
                    logger.info(f"Calendar→TimeTracker sync: imported={imported}, skipped={skipped} (reasons: {skipped_reasons}), total_events={len(events)}")

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
        # Add marker to identify TimeTracker-created events
        description_parts.append("TimeTracker: Created from time entry")
        if time_entry.notes:
            description_parts.append(time_entry.notes)
        if time_entry.tags:
            description_parts.append(f"Tags: {time_entry.tags}")
        description = "\n\n".join(description_parts) if description_parts else "TimeTracker: Created from time entry"

        # Convert local naive datetimes to UTC for Google Calendar API
        from app.utils.timezone import local_to_utc
        start_time_utc = local_to_utc(time_entry.start_time)
        end_time_utc = local_to_utc(time_entry.end_time)

        event = {
            "summary": title,
            "description": description,
            "start": {
                "dateTime": start_time_utc.isoformat(),
                "timeZone": "UTC",
            },
            "end": {
                "dateTime": end_time_utc.isoformat(),
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

        # Convert local naive datetimes to UTC for Google Calendar API
        from app.utils.timezone import local_to_utc
        start_time_utc = local_to_utc(time_entry.start_time)
        end_time_utc = local_to_utc(time_entry.end_time)

        # Update event
        event["summary"] = title
        event["description"] = description
        event["start"] = {
            "dateTime": start_time_utc.isoformat(),
            "timeZone": "UTC",
        }
        event["end"] = {
            "dateTime": end_time_utc.isoformat(),
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
