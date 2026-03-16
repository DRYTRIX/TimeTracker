"""
Tests for Jira integration: webhook handling and issue-specific sync.
"""

import hashlib
import hmac
import json
from unittest.mock import Mock, patch

import pytest

pytestmark = [pytest.mark.integration]

from app.integrations.jira import JiraConnector, JIRA_ISSUE_KEY_PATTERN
from app.models import Integration, User


@pytest.fixture
def test_user(db_session):
    """Create a test user."""
    user = User(username="jirauser", email="jira@example.com", role="admin")
    user.set_password("testpass")
    db_session.add(user)
    db_session.commit()
    return user


@pytest.fixture
def jira_integration(db_session, test_user):
    """Jira integration with auto_sync enabled for webhook tests."""
    integration = Integration(
        name="Jira",
        provider="jira",
        user_id=test_user.id,
        is_global=False,
        is_active=True,
        config={
            "jira_url": "https://example.atlassian.net",
            "auto_sync": True,
        },
    )
    db_session.add(integration)
    db_session.commit()
    return integration


@pytest.fixture
def jira_integration_no_auto_sync(db_session, test_user):
    """Jira integration with auto_sync disabled."""
    integration = Integration(
        name="Jira",
        provider="jira",
        user_id=test_user.id,
        is_global=False,
        is_active=True,
        config={
            "jira_url": "https://example.atlassian.net",
            "auto_sync": False,
        },
    )
    db_session.add(integration)
    db_session.commit()
    return integration


@pytest.fixture
def jira_integration_with_webhook_secret(db_session, test_user):
    """Jira integration with webhook_secret set (signature verification enabled)."""
    integration = Integration(
        name="Jira",
        provider="jira",
        user_id=test_user.id,
        is_global=False,
        is_active=True,
        config={
            "jira_url": "https://example.atlassian.net",
            "auto_sync": True,
            "webhook_secret": "test-webhook-secret",
        },
    )
    db_session.add(integration)
    db_session.commit()
    return integration


def _jira_webhook_signature(secret: str, body: bytes) -> str:
    """Compute HMAC-SHA256 signature for Jira webhook body (sha256=hex format)."""
    digest = hmac.new(secret.encode("utf-8"), body, hashlib.sha256).hexdigest()
    return f"sha256={digest}"


class TestJiraIssueKeyPattern:
    """Test issue key validation."""

    def test_valid_keys(self):
        assert JIRA_ISSUE_KEY_PATTERN.match("PROJ-1")
        assert JIRA_ISSUE_KEY_PATTERN.match("PROJ-123")
        assert JIRA_ISSUE_KEY_PATTERN.match("MYPROJECT-42")
        assert JIRA_ISSUE_KEY_PATTERN.match("ABC_12-999")

    def test_invalid_keys(self):
        assert not JIRA_ISSUE_KEY_PATTERN.match("")
        assert not JIRA_ISSUE_KEY_PATTERN.match("PROJ")
        assert not JIRA_ISSUE_KEY_PATTERN.match("PROJ-")
        assert not JIRA_ISSUE_KEY_PATTERN.match("-1")
        assert not JIRA_ISSUE_KEY_PATTERN.match("PROJ-1a")


class TestJiraHandleWebhook:
    """Test webhook handling and sync triggering."""

    def test_handle_webhook_valid_issue_updated_triggers_sync(
        self, jira_integration
    ):
        """Valid issue_updated webhook with auto_sync triggers sync_issue."""
        connector = JiraConnector(jira_integration, None)
        payload = {
            "webhookEvent": "jira:issue_updated",
            "issue": {"key": "PROJ-1", "id": "10001"},
        }
        headers = {}

        with patch.object(connector, "sync_issue", return_value={"success": True, "synced_items": 1}) as mock_sync:
            result = connector.handle_webhook(payload, headers)

        assert result["success"] is True
        assert result.get("issue_key") == "PROJ-1"
        assert result.get("event_type") == "jira:issue_updated"
        mock_sync.assert_called_once_with("PROJ-1")

    def test_handle_webhook_valid_issue_created_triggers_sync(
        self, jira_integration
    ):
        """Valid issue_created webhook with auto_sync triggers sync_issue."""
        connector = JiraConnector(jira_integration, None)
        payload = {
            "webhookEvent": "jira:issue_created",
            "issue": {"key": "DEMO-42"},
        }
        with patch.object(connector, "sync_issue", return_value={"success": True, "synced_items": 1}) as mock_sync:
            result = connector.handle_webhook(payload, {})

        assert result["success"] is True
        mock_sync.assert_called_once_with("DEMO-42")

    def test_handle_webhook_malformed_payload_not_dict(self, jira_integration):
        """Non-dict payload returns safe error, no sync."""
        connector = JiraConnector(jira_integration, None)
        with patch.object(connector, "sync_issue") as mock_sync:
            result = connector.handle_webhook("not a dict", {})

        assert result["success"] is False
        assert "Invalid webhook payload" in result["message"]
        mock_sync.assert_not_called()

    def test_handle_webhook_malformed_payload_issue_not_dict(
        self, jira_integration
    ):
        """Payload with issue not a dict returns safe error."""
        connector = JiraConnector(jira_integration, None)
        payload = {"webhookEvent": "jira:issue_updated", "issue": "string"}
        with patch.object(connector, "sync_issue") as mock_sync:
            result = connector.handle_webhook(payload, {})

        assert result["success"] is False
        assert "issue" in result["message"].lower()
        mock_sync.assert_not_called()

    def test_handle_webhook_malformed_payload_missing_issue_key(
        self, jira_integration
    ):
        """Payload with missing or empty issue key returns error."""
        connector = JiraConnector(jira_integration, None)
        with patch.object(connector, "sync_issue") as mock_sync:
            result1 = connector.handle_webhook(
                {"webhookEvent": "jira:issue_updated", "issue": {}}, {}
            )
            result2 = connector.handle_webhook(
                {
                    "webhookEvent": "jira:issue_updated",
                    "issue": {"key": ""},
                },
                {},
            )

        assert result1["success"] is False
        assert result2["success"] is False
        mock_sync.assert_not_called()

    def test_handle_webhook_malformed_payload_invalid_key_format(
        self, jira_integration
    ):
        """Payload with invalid issue key format returns error."""
        connector = JiraConnector(jira_integration, None)
        payload = {
            "webhookEvent": "jira:issue_updated",
            "issue": {"key": "INVALID"},
        }
        with patch.object(connector, "sync_issue") as mock_sync:
            result = connector.handle_webhook(payload, {})

        assert result["success"] is False
        assert "format" in result["message"].lower() or "Invalid" in result["message"]
        mock_sync.assert_not_called()

    def test_handle_webhook_unsupported_event_type(self, jira_integration):
        """Unsupported event type returns success ack, no sync."""
        connector = JiraConnector(jira_integration, None)
        payload = {
            "webhookEvent": "comment_created",
            "issue": {"key": "PROJ-1"},
        }
        with patch.object(connector, "sync_issue") as mock_sync:
            result = connector.handle_webhook(payload, {})

        assert result["success"] is True
        assert "ignored" in result["message"].lower()
        mock_sync.assert_not_called()

    def test_handle_webhook_sync_failure(self, jira_integration):
        """When sync_issue fails, handle_webhook returns failure."""
        connector = JiraConnector(jira_integration, None)
        payload = {
            "webhookEvent": "jira:issue_updated",
            "issue": {"key": "PROJ-1"},
        }
        with patch.object(
            connector,
            "sync_issue",
            return_value={"success": False, "message": "Issue not found"},
        ):
            result = connector.handle_webhook(payload, {})

        assert result["success"] is False
        assert result.get("issue_key") == "PROJ-1"
        assert "not found" in result["message"].lower() or "Issue" in result["message"]

    def test_handle_webhook_auto_sync_disabled_ack_only(
        self, jira_integration_no_auto_sync
    ):
        """When auto_sync is disabled, webhook is acknowledged but sync_issue not called."""
        connector = JiraConnector(jira_integration_no_auto_sync, None)
        payload = {
            "webhookEvent": "jira:issue_updated",
            "issue": {"key": "PROJ-1"},
        }
        with patch.object(connector, "sync_issue") as mock_sync:
            result = connector.handle_webhook(payload, {})

        assert result["success"] is True
        assert "received" in result["message"].lower() or "Webhook" in result["message"]
        mock_sync.assert_not_called()

    def test_handle_webhook_duplicate_idempotent(self, jira_integration):
        """Processing same payload twice is idempotent (both succeed)."""
        connector = JiraConnector(jira_integration, None)
        payload = {
            "webhookEvent": "jira:issue_updated",
            "issue": {"key": "PROJ-1"},
        }
        with patch.object(connector, "sync_issue", return_value={"success": True, "synced_items": 1}) as mock_sync:
            r1 = connector.handle_webhook(payload, {})
            r2 = connector.handle_webhook(payload, {})

        assert r1["success"] is True
        assert r2["success"] is True
        assert mock_sync.call_count == 2
        mock_sync.assert_any_call("PROJ-1")


class TestJiraWebhookVerification:
    """Test Jira webhook signature verification when webhook_secret is configured."""

    def test_handle_webhook_with_secret_and_valid_signature_accepted(
        self, jira_integration_with_webhook_secret
    ):
        """When webhook_secret is set and signature is valid, webhook is accepted."""
        connector = JiraConnector(jira_integration_with_webhook_secret, None)
        payload = {
            "webhookEvent": "jira:issue_updated",
            "issue": {"key": "PROJ-1", "id": "10001"},
        }
        raw_body = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
        sig = _jira_webhook_signature("test-webhook-secret", raw_body)
        headers = {"X-Hub-Signature-256": sig}

        with patch.object(connector, "sync_issue", return_value={"success": True, "synced_items": 1}) as mock_sync:
            result = connector.handle_webhook(payload, headers, raw_body=raw_body)

        assert result["success"] is True
        assert result.get("issue_key") == "PROJ-1"
        mock_sync.assert_called_once_with("PROJ-1")

    def test_handle_webhook_with_secret_and_missing_signature_rejected(
        self, jira_integration_with_webhook_secret
    ):
        """When webhook_secret is set but no signature provided, webhook is rejected."""
        connector = JiraConnector(jira_integration_with_webhook_secret, None)
        payload = {
            "webhookEvent": "jira:issue_updated",
            "issue": {"key": "PROJ-1"},
        }
        with patch.object(connector, "sync_issue") as mock_sync:
            result = connector.handle_webhook(payload, {}, raw_body=b"{}")

        assert result["success"] is False
        assert "signature" in result["message"].lower()
        mock_sync.assert_not_called()

    def test_handle_webhook_with_secret_and_wrong_signature_rejected(
        self, jira_integration_with_webhook_secret
    ):
        """When webhook_secret is set but signature is invalid, webhook is rejected."""
        connector = JiraConnector(jira_integration_with_webhook_secret, None)
        payload = {
            "webhookEvent": "jira:issue_updated",
            "issue": {"key": "PROJ-1"},
        }
        headers = {"X-Hub-Signature-256": "sha256=invalidwrongsignature"}
        with patch.object(connector, "sync_issue") as mock_sync:
            result = connector.handle_webhook(
                payload, headers, raw_body=json.dumps(payload).encode("utf-8")
            )

        assert result["success"] is False
        assert "verification" in result["message"].lower() or "signature" in result["message"].lower()
        mock_sync.assert_not_called()

    def test_handle_webhook_without_secret_no_verification(self, jira_integration):
        """When webhook_secret is not set, webhooks are accepted without signature (backward compat)."""
        connector = JiraConnector(jira_integration, None)
        payload = {
            "webhookEvent": "jira:issue_updated",
            "issue": {"key": "PROJ-1"},
        }
        with patch.object(connector, "sync_issue", return_value={"success": True, "synced_items": 1}) as mock_sync:
            result = connector.handle_webhook(payload, {})

        assert result["success"] is True
        mock_sync.assert_called_once_with("PROJ-1")


class TestJiraSyncIssue:
    """Test sync_issue method."""

    def test_sync_issue_success(self, jira_integration):
        """sync_issue with valid key and mocked GET returns success."""
        connector = JiraConnector(jira_integration, None)
        issue_body = {
            "key": "PROJ-1",
            "id": "10001",
            "fields": {
                "summary": "Test issue",
                "description": None,
                "status": {"name": "In Progress"},
                "project": {"key": "PROJ"},
            },
        }

        with patch.object(connector, "get_access_token", return_value="mock-token"):
            with patch("app.integrations.jira.requests.get") as mock_get:
                mock_get.return_value = Mock(status_code=200, json=Mock(return_value=issue_body))
                with patch.object(connector, "_upsert_task_from_issue", return_value=1) as mock_upsert:
                    result = connector.sync_issue("PROJ-1")

        assert result["success"] is True
        assert result.get("synced_items") == 1
        assert result.get("issue_key") == "PROJ-1"
        mock_get.assert_called_once()
        mock_upsert.assert_called_once()
        call_issue = mock_upsert.call_args[0][0]
        assert call_issue["key"] == "PROJ-1"

    def test_sync_issue_not_found(self, jira_integration):
        """sync_issue when Jira returns 404 returns failure."""
        connector = JiraConnector(jira_integration, None)
        with patch.object(connector, "get_access_token", return_value="mock-token"):
            with patch("app.integrations.jira.requests.get") as mock_get:
                mock_get.return_value = Mock(status_code=404, text="Not found")
                result = connector.sync_issue("PROJ-999")

        assert result["success"] is False
        assert "not found" in result["message"].lower()
        assert result.get("issue_key") == "PROJ-999"

    def test_sync_issue_invalid_key_empty(self, jira_integration):
        """sync_issue with empty key returns failure without calling API."""
        connector = JiraConnector(jira_integration, None)
        with patch("app.integrations.jira.requests.get") as mock_get:
            result = connector.sync_issue("")

        assert result["success"] is False
        mock_get.assert_not_called()

    def test_sync_issue_invalid_key_format(self, jira_integration):
        """sync_issue with invalid key format returns failure without calling API."""
        connector = JiraConnector(jira_integration, None)
        with patch("app.integrations.jira.requests.get") as mock_get:
            result = connector.sync_issue("INVALIDKEY")

        assert result["success"] is False
        assert "format" in result["message"].lower() or "Invalid" in result["message"]
        mock_get.assert_not_called()

    def test_sync_issue_no_token(self, jira_integration):
        """sync_issue when get_access_token returns None returns failure."""
        connector = JiraConnector(jira_integration, None)
        with patch.object(connector, "get_access_token", return_value=None):
            with patch("app.integrations.jira.requests.get") as mock_get:
                result = connector.sync_issue("PROJ-1")

        assert result["success"] is False
        assert "access token" in result["message"].lower()
        mock_get.assert_not_called()


class TestJiraWebhookRoute:
    """HTTP-level tests for POST /integrations/<provider>/webhook."""

    def test_post_webhook_unknown_provider_returns_404(self, app, client):
        """POST to webhook with unknown provider returns 404."""
        response = client.post(
            "/integrations/unknownprovider/webhook",
            data="{}",
            headers={"Content-Type": "application/json"},
        )
        assert response.status_code == 404
        data = response.get_json()
        assert data is not None and "error" in data

    def test_post_jira_webhook_malformed_body_returns_500(
        self, app, client, jira_integration
    ):
        """POST to jira webhook with malformed or empty body returns 500 when no integration succeeds."""
        response = client.post(
            "/integrations/jira/webhook",
            data="not valid json",
            headers={"Content-Type": "application/json"},
        )
        # get_json(silent=True) returns None -> payload = {}; handle_webhook fails -> 500
        assert response.status_code in (400, 500)
        if response.status_code == 500:
            data = response.get_json()
            assert data is not None
            assert "results" in data or "success" in data

    def test_post_jira_webhook_valid_payload_returns_200(
        self, app, client, jira_integration
    ):
        """POST to jira webhook with valid payload returns 200 when connector handles it."""
        with patch(
            "app.integrations.jira.JiraConnector.handle_webhook",
            return_value={"success": True, "message": "Webhook processed"},
        ):
            response = client.post(
                "/integrations/jira/webhook",
                json={
                    "webhookEvent": "jira:issue_updated",
                    "issue": {"key": "PROJ-1", "id": "10001"},
                },
                headers={"Content-Type": "application/json"},
            )
        assert response.status_code == 200
        data = response.get_json()
        assert data is not None
        assert data.get("success") is True
        assert "results" in data
