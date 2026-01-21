"""
Tests for ActivityWatch integration.
"""

from datetime import datetime, timezone
from unittest.mock import Mock, patch

import pytest

from app import db
from app.integrations.activitywatch import ActivityWatchConnector
from app.models import Integration, IntegrationExternalEventLink, Project, TimeEntry, User


@pytest.fixture
def test_user(db_session):
    """Create a test user."""
    user = User(username="awuser", email="aw@example.com", role="admin")
    user.set_password("testpass")
    db_session.add(user)
    db_session.commit()
    return user


@pytest.fixture
def test_project(db_session, test_user):
    """Create a test project."""
    from app.models import Client

    client = Client(name="AW Client", email="awclient@example.com")
    db_session.add(client)
    db_session.commit()

    project = Project(name="AW Project", client_id=client.id, status="active")
    db_session.add(project)
    db_session.commit()
    return project


@pytest.fixture
def activitywatch_integration(db_session, test_user, test_project):
    """Create an ActivityWatch integration (no credentials)."""
    integration = Integration(
        name="ActivityWatch",
        provider="activitywatch",
        user_id=test_user.id,
        is_global=False,
        is_active=True,
        config={
            "server_url": "http://localhost:5600",
            "default_project_id": test_project.id,
            "lookback_days": 7,
        },
    )
    db_session.add(integration)
    db_session.commit()
    return integration


class TestActivityWatchConnector:
    """Test ActivityWatch connector."""

    def test_provider_name(self, activitywatch_integration):
        """Test provider name."""
        connector = ActivityWatchConnector(activitywatch_integration, None)
        assert connector.provider_name == "activitywatch"

    @patch("app.integrations.activitywatch.requests.get")
    def test_test_connection_success(self, mock_get, activitywatch_integration):
        """Test connection when aw-server returns buckets."""
        mock_resp = Mock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {}
        mock_resp.raise_for_status = Mock()
        mock_get.return_value = mock_resp

        connector = ActivityWatchConnector(activitywatch_integration, None)
        result = connector.test_connection()

        assert result["success"] is True
        assert "Connected to ActivityWatch" in result["message"]
        mock_get.assert_called_once()
        call_args = mock_get.call_args
        assert "buckets" in call_args[0][0]

    @patch("app.integrations.activitywatch.requests.get")
    def test_test_connection_failure(self, mock_get, activitywatch_integration):
        """Test connection when aw-server is unreachable."""
        mock_get.side_effect = Exception("Connection refused")

        connector = ActivityWatchConnector(activitywatch_integration, None)
        result = connector.test_connection()

        assert result["success"] is False
        assert "message" in result

    @patch("app.integrations.activitywatch.requests.get")
    def test_sync_data_imports_events(self, mock_get, db_session, activitywatch_integration, test_project):
        """Test sync imports ActivityWatch events as time entries."""
        # buckets: dict format
        mock_get.side_effect = [
            Mock(status_code=200, raise_for_status=Mock(), json=Mock(return_value={
                "aw-watcher-window_testhost": {"id": "aw-watcher-window_testhost", "type": "currentwindow"},
            })),
            Mock(status_code=200, raise_for_status=Mock(), json=Mock(return_value=[
                {
                    "timestamp": "2024-01-15T10:00:00.000000Z",
                    "duration": 300.0,
                    "data": {"app": "Chrome", "title": "Inbox"},
                },
            ])),
        ]

        connector = ActivityWatchConnector(activitywatch_integration, None)
        result = connector.sync_data()

        assert result["success"] is True
        assert result["imported"] == 1
        assert result["skipped"] >= 0

        entry = TimeEntry.query.filter_by(user_id=activitywatch_integration.user_id, source="auto").first()
        assert entry is not None
        assert entry.project_id == test_project.id
        assert "Chrome" in (entry.notes or "")
        assert "Inbox" in (entry.notes or "")

        link = IntegrationExternalEventLink.query.filter_by(integration_id=activitywatch_integration.id).first()
        assert link is not None
        assert link.time_entry_id == entry.id
        assert "aw-watcher-window_testhost" in link.external_uid

    @patch("app.integrations.activitywatch.requests.get")
    def test_sync_data_skips_duplicates(self, mock_get, db_session, activitywatch_integration, test_project):
        """Test sync skips already imported events (idempotency)."""
        ts_raw = "2024-01-15T10:00:00.000000Z"
        ev = {
            "timestamp": ts_raw,
            "duration": 300.0,
            "data": {"app": "Chrome", "title": "Inbox"},
        }
        # Build external_uid the same way the connector does (uses ts after Z->+00:00)
        import hashlib
        ts_uid = "2024-01-15T10:00:00.000000+00:00"
        data_str = "Chrome" + "|" + "Inbox" + ""
        h = hashlib.md5(data_str.encode("utf-8")).hexdigest()[:16]
        external_uid = f"aw-watcher-window_testhost|{ts_uid}|300|{h}"[:255]

        # Pre-create link to simulate already imported
        entry = TimeEntry(
            user_id=activitywatch_integration.user_id,
            project_id=test_project.id,
            start_time=datetime(2024, 1, 15, 10, 0, 0),
            end_time=datetime(2024, 1, 15, 10, 5, 0),
            duration_seconds=300,
            notes="ActivityWatch: Chrome - Inbox",
            source="auto",
        )
        db_session.add(entry)
        db_session.flush()
        link = IntegrationExternalEventLink(
            integration_id=activitywatch_integration.id,
            time_entry_id=entry.id,
            external_uid=external_uid,
        )
        db_session.add(link)
        db_session.commit()

        mock_get.side_effect = [
            Mock(status_code=200, raise_for_status=Mock(), json=Mock(return_value={
                "aw-watcher-window_testhost": {"id": "aw-watcher-window_testhost"},
            })),
            Mock(status_code=200, raise_for_status=Mock(), json=Mock(return_value=[ev])),
        ]

        connector = ActivityWatchConnector(activitywatch_integration, None)
        result = connector.sync_data()

        assert result["success"] is True
        assert result["imported"] == 0
        assert result["skipped"] == 1

        entries = TimeEntry.query.filter_by(user_id=activitywatch_integration.user_id, source="auto").all()
        assert len(entries) == 1
        links = IntegrationExternalEventLink.query.filter_by(integration_id=activitywatch_integration.id).all()
        assert len(links) == 1

    def test_get_config_schema(self, activitywatch_integration):
        """Test config schema has required fields."""
        connector = ActivityWatchConnector(activitywatch_integration, None)
        schema = connector.get_config_schema()
        assert "server_url" in schema["required"]
        names = [f["name"] for f in schema["fields"]]
        assert "server_url" in names
        assert "default_project_id" in names
        assert "lookback_days" in names
        assert schema["sync_settings"]["sync_direction"] == "provider_to_timetracker"
