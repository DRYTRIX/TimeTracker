"""
Tests for CalDAV calendar integration.
"""

import pytest
from datetime import datetime, timedelta, timezone
from unittest.mock import Mock, patch, MagicMock
from flask import url_for

from app import db
from app.models import Integration, IntegrationCredential, IntegrationExternalEventLink, TimeEntry, Project, User
from app.integrations.caldav_calendar import CalDAVCalendarConnector, CalDAVClient, CalDAVCalendar
from app.services.integration_service import IntegrationService


@pytest.fixture
def test_user(db_session):
    """Create a test user"""
    user = User(username="testuser", email="test@example.com", role="admin")
    user.set_password("testpass")
    db_session.add(user)
    db_session.commit()
    return user


@pytest.fixture
def test_project(db_session, test_user):
    """Create a test project"""
    from app.models import Client

    client = Client(name="Test Client", email="client@example.com")
    db_session.add(client)
    db_session.commit()

    project = Project(name="Test Project", client_id=client.id, status="active")
    db_session.add(project)
    db_session.commit()
    return project


@pytest.fixture
def caldav_integration(db_session, test_user, test_project):
    """Create a CalDAV integration"""
    integration = Integration(
        name="CalDAV Calendar",
        provider="caldav_calendar",
        user_id=test_user.id,
        is_global=False,
        is_active=True,
        config={
            "server_url": "https://mail.example.com/dav",
            "calendar_url": "https://mail.example.com/dav/user@example.com/Calendar/",
            "calendar_name": "My Calendar",
            "default_project_id": test_project.id,
            "sync_direction": "calendar_to_time_tracker",
            "lookback_days": 90,
            "verify_ssl": True,
        },
    )
    db_session.add(integration)
    db_session.commit()

    credentials = IntegrationCredential(
        integration_id=integration.id,
        access_token="test_password",
        token_type="Basic",
        scope="caldav",
        extra_data={"username": "user@example.com"},
    )
    db_session.add(credentials)
    db_session.commit()

    return integration


class TestCalDAVClient:
    """Test CalDAV client functionality"""

    def test_client_initialization(self):
        """Test CalDAV client can be initialized"""
        client = CalDAVClient(username="user@example.com", password="pass", verify_ssl=True)
        assert client.username == "user@example.com"
        assert client.password == "pass"
        assert client.verify_ssl is True

    @patch("app.integrations.caldav_calendar.requests.request")
    def test_discover_calendars(self, mock_request):
        """Test calendar discovery"""
        # Mock PROPFIND responses
        mock_resp1 = Mock()
        mock_resp1.text = """<?xml version="1.0"?>
        <d:multistatus xmlns:d="DAV:">
            <d:response>
                <d:propstat>
                    <d:prop>
                        <d:current-user-principal>
                            <d:href>/dav/user@example.com</d:href>
                        </d:current-user-principal>
                    </d:prop>
                </d:propstat>
            </d:response>
        </d:multistatus>"""
        mock_resp1.raise_for_status = Mock()

        mock_resp2 = Mock()
        mock_resp2.text = """<?xml version="1.0"?>
        <d:multistatus xmlns:d="DAV:" xmlns:cs="urn:ietf:params:xml:ns:caldav">
            <d:response>
                <d:propstat>
                    <d:prop>
                        <cs:calendar-home-set>
                            <d:href>/dav/user@example.com/Calendar/</d:href>
                        </cs:calendar-home-set>
                    </d:prop>
                </d:propstat>
            </d:response>
        </d:multistatus>"""
        mock_resp2.raise_for_status = Mock()

        mock_resp3 = Mock()
        mock_resp3.text = """<?xml version="1.0"?>
        <d:multistatus xmlns:d="DAV:" xmlns:cs="urn:ietf:params:xml:ns:caldav">
            <d:response>
                <d:href>/dav/user@example.com/Calendar/</d:href>
                <d:propstat>
                    <d:prop>
                        <d:displayname>My Calendar</d:displayname>
                        <d:resourcetype>
                            <cs:calendar/>
                        </d:resourcetype>
                    </d:prop>
                </d:propstat>
            </d:response>
        </d:multistatus>"""
        mock_resp3.raise_for_status = Mock()

        mock_request.side_effect = [mock_resp1, mock_resp2, mock_resp3]

        client = CalDAVClient(username="user@example.com", password="pass")
        calendars = client.discover_calendars("https://mail.example.com/dav")

        assert len(calendars) == 1
        assert calendars[0].name == "My Calendar"
        assert "Calendar" in calendars[0].href


class TestCalDAVConnector:
    """Test CalDAV connector"""

    def test_provider_name(self, caldav_integration):
        """Test provider name"""
        credentials = IntegrationCredential.query.filter_by(integration_id=caldav_integration.id).first()
        connector = CalDAVCalendarConnector(caldav_integration, credentials)
        assert connector.provider_name == "caldav_calendar"

    def test_get_basic_creds(self, caldav_integration):
        """Test getting basic credentials"""
        credentials = IntegrationCredential.query.filter_by(integration_id=caldav_integration.id).first()
        connector = CalDAVCalendarConnector(caldav_integration, credentials)
        username, password = connector._get_basic_creds()
        assert username == "user@example.com"
        assert password == "test_password"

    def test_get_basic_creds_missing(self, caldav_integration):
        """Test getting credentials when missing"""
        connector = CalDAVCalendarConnector(caldav_integration, None)
        with pytest.raises(ValueError, match="Missing CalDAV credentials"):
            connector._get_basic_creds()

    @patch("app.integrations.caldav_calendar.CalDAVClient")
    def test_test_connection(self, mock_client_class, caldav_integration):
        """Test connection testing"""
        mock_client = Mock()
        mock_client.discover_calendars.return_value = [
            CalDAVCalendar(href="https://mail.example.com/dav/Calendar/", name="My Calendar")
        ]
        mock_client.fetch_events.return_value = []
        mock_client_class.return_value = mock_client

        credentials = IntegrationCredential.query.filter_by(integration_id=caldav_integration.id).first()
        connector = CalDAVCalendarConnector(caldav_integration, credentials)
        result = connector.test_connection()

        assert result["success"] is True
        assert "Connected to CalDAV" in result["message"]
        assert len(result["calendars"]) == 1

    @patch("app.integrations.caldav_calendar.CalDAVClient")
    def test_sync_data_imports_events(self, mock_client_class, db_session, caldav_integration, test_project):
        """Test syncing imports calendar events as time entries"""
        # Mock calendar event
        now_utc = datetime.now(timezone.utc)
        event_data = {
            "uid": "test-event-123",
            "summary": "Meeting with Test Project",
            "description": "Important meeting",
            "start": now_utc - timedelta(hours=1),
            "end": now_utc,
            "href": "https://mail.example.com/dav/Calendar/test-event-123.ics",
        }

        mock_client = Mock()
        mock_client.fetch_events.return_value = [event_data]
        mock_client_class.return_value = mock_client

        credentials = IntegrationCredential.query.filter_by(integration_id=caldav_integration.id).first()
        connector = CalDAVCalendarConnector(caldav_integration, credentials)
        result = connector.sync_data()

        assert result["success"] is True
        assert result["imported"] == 1
        assert result["skipped"] == 0

        # Verify time entry was created
        time_entry = TimeEntry.query.filter_by(user_id=caldav_integration.user_id).first()
        assert time_entry is not None
        assert time_entry.project_id == test_project.id
        assert "Meeting with Test Project" in time_entry.notes

        # Verify external event link was created
        link = IntegrationExternalEventLink.query.filter_by(
            integration_id=caldav_integration.id, external_uid="test-event-123"
        ).first()
        assert link is not None
        assert link.time_entry_id == time_entry.id

    @patch("app.integrations.caldav_calendar.CalDAVClient")
    def test_sync_data_skips_duplicates(self, mock_client_class, db_session, caldav_integration, test_project):
        """Test sync skips already imported events"""
        # Create existing link
        time_entry = TimeEntry(
            user_id=caldav_integration.user_id,
            project_id=test_project.id,
            start_time=datetime.now(),
            end_time=datetime.now() + timedelta(hours=1),
            notes="Existing entry",
        )
        db_session.add(time_entry)
        db_session.flush()

        link = IntegrationExternalEventLink(
            integration_id=caldav_integration.id,
            time_entry_id=time_entry.id,
            external_uid="test-event-123",
        )
        db_session.add(link)
        db_session.commit()

        # Mock same event
        now_utc = datetime.now(timezone.utc)
        event_data = {
            "uid": "test-event-123",
            "summary": "Meeting",
            "description": "",
            "start": now_utc - timedelta(hours=1),
            "end": now_utc,
            "href": "https://mail.example.com/dav/Calendar/test-event-123.ics",
        }

        mock_client = Mock()
        mock_client.fetch_events.return_value = [event_data]
        mock_client_class.return_value = mock_client

        credentials = IntegrationCredential.query.filter_by(integration_id=caldav_integration.id).first()
        connector = CalDAVCalendarConnector(caldav_integration, credentials)
        result = connector.sync_data()

        assert result["success"] is True
        assert result["imported"] == 0
        assert result["skipped"] == 1

        # Verify no duplicate time entry
        entries = TimeEntry.query.filter_by(user_id=caldav_integration.user_id).all()
        assert len(entries) == 1


class TestCalDAVRoutes:
    """Test CalDAV routes"""

    def test_caldav_setup_get(self, authenticated_client, test_user, test_project):
        """Test CalDAV setup page loads"""
        response = authenticated_client.get(url_for("integrations.caldav_setup"))
        assert response.status_code == 200
        assert b"CalDAV Calendar Setup" in response.data

    def test_caldav_setup_post(self, authenticated_client, test_user, test_project):
        """Test CalDAV setup form submission"""
        response = authenticated_client.post(
            url_for("integrations.caldav_setup"),
            data={
                "server_url": "https://mail.example.com/dav",
                "username": "user@example.com",
                "password": "testpass",
                "calendar_url": "https://mail.example.com/dav/user@example.com/Calendar/",
                "calendar_name": "My Calendar",
                "default_project_id": str(test_project.id),
                "lookback_days": "90",
                "verify_ssl": "on",
            },
            follow_redirects=False,
        )

        # Should redirect to view integration
        assert response.status_code in (200, 302)

        # Verify integration was created
        integration = Integration.query.filter_by(provider="caldav_calendar", user_id=test_user.id).first()
        assert integration is not None
        assert integration.config["server_url"] == "https://mail.example.com/dav"
        assert integration.config["default_project_id"] == test_project.id

        # Verify credentials were saved
        credentials = IntegrationCredential.query.filter_by(integration_id=integration.id).first()
        assert credentials is not None
        assert credentials.access_token == "testpass"
        assert credentials.extra_data["username"] == "user@example.com"


class TestIntegrationExternalEventLink:
    """Test external event link model"""

    def test_link_creation(self, db_session, caldav_integration, test_project):
        """Test creating an external event link"""
        time_entry = TimeEntry(
            user_id=caldav_integration.user_id,
            project_id=test_project.id,
            start_time=datetime.now(),
            end_time=datetime.now() + timedelta(hours=1),
            notes="Test entry",
        )
        db_session.add(time_entry)
        db_session.flush()

        link = IntegrationExternalEventLink(
            integration_id=caldav_integration.id,
            time_entry_id=time_entry.id,
            external_uid="test-uid-123",
            external_href="https://example.com/event.ics",
        )
        db_session.add(link)
        db_session.commit()

        assert link.id is not None
        assert link.external_uid == "test-uid-123"
        assert link.integration_id == caldav_integration.id
        assert link.time_entry_id == time_entry.id

    def test_link_unique_constraint(self, db_session, caldav_integration, test_project):
        """Test unique constraint on integration_id + external_uid"""
        time_entry = TimeEntry(
            user_id=caldav_integration.user_id,
            project_id=test_project.id,
            start_time=datetime.now(),
            end_time=datetime.now() + timedelta(hours=1),
            notes="Test entry",
        )
        db_session.add(time_entry)
        db_session.flush()

        link1 = IntegrationExternalEventLink(
            integration_id=caldav_integration.id,
            time_entry_id=time_entry.id,
            external_uid="test-uid-123",
        )
        db_session.add(link1)
        db_session.commit()

        # Try to create duplicate
        link2 = IntegrationExternalEventLink(
            integration_id=caldav_integration.id,
            time_entry_id=time_entry.id,
            external_uid="test-uid-123",
        )
        db_session.add(link2)
        with pytest.raises(Exception):  # Should raise IntegrityError
            db_session.commit()

