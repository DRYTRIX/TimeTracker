"""
Tests for refactored calendar and template API routes with eager loading.
"""

import pytest
from datetime import datetime, timedelta
from app.models import CalendarEvent, TimeEntryTemplate, ApiToken


class TestAPICalendarTemplatesRefactored:
    """Tests for calendar and template API routes"""

    @pytest.fixture
    def api_token(self, app, user):
        """Create an API token for testing"""
        token, plain_token = ApiToken.create_token(
            user_id=user.id,
            name="Test API Token",
            scopes="read:calendar,write:calendar,read:time_entries,write:time_entries"
        )
        from app import db
        db.session.add(token)
        db.session.commit()
        return token, plain_token

    @pytest.fixture
    def client_with_token(self, app, api_token):
        """Create a test client with API token"""
        token, plain_token = api_token
        test_client = app.test_client()
        test_client.environ_base['HTTP_AUTHORIZATION'] = f'Bearer {plain_token}'
        return test_client

    def test_list_calendar_events_uses_eager_loading(self, app, client_with_token, user):
        """Test that list_calendar_events uses eager loading"""
        # Create a test event
        from app import db
        event = CalendarEvent(
            user_id=user.id,
            title="Test Event",
            start_time=datetime.utcnow(),
            end_time=datetime.utcnow() + timedelta(hours=1)
        )
        db.session.add(event)
        db.session.commit()
        
        response = client_with_token.get("/api/v1/calendar/events")
        
        assert response.status_code == 200
        data = response.get_json()
        assert "events" in data

    def test_get_calendar_event_uses_eager_loading(self, app, client_with_token, user):
        """Test that get_calendar_event uses eager loading"""
        from app import db
        event = CalendarEvent(
            user_id=user.id,
            title="Test Event",
            start_time=datetime.utcnow(),
            end_time=datetime.utcnow() + timedelta(hours=1)
        )
        db.session.add(event)
        db.session.commit()
        
        response = client_with_token.get(f"/api/v1/calendar/events/{event.id}")
        
        assert response.status_code == 200
        data = response.get_json()
        assert "event" in data
        assert data["event"]["title"] == "Test Event"

    def test_list_time_entry_templates_uses_eager_loading(self, app, client_with_token, user):
        """Test that list_time_entry_templates uses eager loading"""
        response = client_with_token.get("/api/v1/time-entry-templates")
        
        assert response.status_code == 200
        data = response.get_json()
        assert "templates" in data
        assert "pagination" in data

    def test_get_time_entry_template_uses_eager_loading(self, app, client_with_token, user):
        """Test that get_time_entry_template uses eager loading"""
        from app import db
        template = TimeEntryTemplate(
            user_id=user.id,
            name="Test Template",
            default_notes="Test notes"
        )
        db.session.add(template)
        db.session.commit()
        
        response = client_with_token.get(f"/api/v1/time-entry-templates/{template.id}")
        
        assert response.status_code == 200
        data = response.get_json()
        assert "template" in data
        assert data["template"]["name"] == "Test Template"

