"""Contract tests for Slack connector (no live Slack API)."""

from unittest.mock import Mock, patch

import pytest

pytestmark = [pytest.mark.integration]

from app.integrations.slack_connector import SlackConnector
from app.models import Integration, User


@pytest.fixture
def slack_user(db_session):
    user = User(username="slackuser", email="slack@example.com", role="admin")
    user.set_password("testpass")
    db_session.add(user)
    db_session.commit()
    return user


@pytest.fixture
def slack_integration(db_session, slack_user):
    integration = Integration(
        name="Slack",
        provider="slack_connector",
        user_id=slack_user.id,
        is_global=False,
        is_active=True,
        config={
            "bot_token": "xoxb-test-token",
            "channel_id": "C123",
            "notify_on_start": True,
            "notify_on_stop": True,
        },
    )
    db_session.add(integration)
    db_session.commit()
    return integration


class TestSlackConnector:
    def test_provider_name(self, slack_integration):
        connector = SlackConnector(slack_integration, None)
        assert connector.provider_name == "slack_connector"

    def test_test_connection_not_configured(self, db_session, slack_user):
        integration = Integration(
            name="Slack empty",
            provider="slack_connector",
            user_id=slack_user.id,
            is_active=True,
            config={},
        )
        db_session.add(integration)
        db_session.commit()
        connector = SlackConnector(integration, None)
        result = connector.test_connection()
        assert result["success"] is False

    @patch("app.integrations.slack_connector.requests.post")
    def test_test_connection_success(self, mock_post, slack_integration):
        mock_resp = Mock()
        mock_resp.json.return_value = {"ok": True, "user": "bot"}
        mock_post.return_value = mock_resp

        connector = SlackConnector(slack_integration, None)
        # Ensure connector sees a usable token path even if encryption wraps values.
        with patch.object(connector, "_bot_token", return_value="xoxb-test"):
            with patch.object(connector, "_is_ready", return_value=True):
                result = connector.test_connection()
        assert result["success"] is True
        assert "Connected" in result["message"]

    def test_oauth_methods_not_supported(self, slack_integration):
        connector = SlackConnector(slack_integration, None)
        with pytest.raises(NotImplementedError):
            connector.get_authorization_url("https://example.com/cb")
        with pytest.raises(NotImplementedError):
            connector.exchange_code_for_tokens("code", "https://example.com/cb")
