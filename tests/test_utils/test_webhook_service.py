"""Tests for webhook service"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from app.models import Webhook, WebhookDelivery, User
from app.utils.webhook_service import WebhookService, WebhookDeliveryError
from app import db


@pytest.fixture
def test_user(db_session):
    """Create a test user"""
    user = User(username="testuser", role="admin")
    db_session.add(user)
    db_session.commit()
    return user


@pytest.fixture
def test_webhook(db_session, test_user):
    """Create a test webhook"""
    webhook = Webhook(
        name="Test Webhook",
        url="https://example.com/webhook",
        events=["project.created"],
        user_id=test_user.id,
        is_active=True,
    )
    webhook.set_secret()
    db_session.add(webhook)
    db_session.commit()
    return webhook


class TestWebhookService:
    """Test WebhookService"""

    @patch("app.utils.webhook_service.requests.post")
    def test_deliver_webhook_success(self, mock_post, db_session, test_webhook):
        """Test successful webhook delivery"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = "OK"
        mock_response.headers = {}
        mock_post.return_value = mock_response

        payload = {"event": "project.created", "data": {"id": 1}}

        delivery = WebhookService.deliver_webhook(webhook=test_webhook, event_type="project.created", payload=payload)

        assert delivery.status == "success"
        assert delivery.response_status_code == 200
        assert test_webhook.successful_deliveries == 1

    @patch("app.utils.webhook_service.requests.post")
    def test_deliver_webhook_http_error(self, mock_post, db_session, test_webhook):
        """Test webhook delivery with HTTP error"""
        mock_response = Mock()
        mock_response.status_code = 500
        mock_response.text = "Internal Server Error"
        mock_response.headers = {}
        mock_post.return_value = mock_response

        payload = {"event": "project.created"}

        delivery = WebhookService.deliver_webhook(webhook=test_webhook, event_type="project.created", payload=payload)

        assert delivery.status == "failed"
        assert delivery.response_status_code == 500
        assert test_webhook.failed_deliveries == 1

    @patch("app.utils.webhook_service.requests.post")
    def test_deliver_webhook_timeout(self, mock_post, db_session, test_webhook):
        """Test webhook delivery timeout"""
        import requests

        mock_post.side_effect = requests.exceptions.Timeout("Request timeout")

        payload = {"event": "project.created"}

        delivery = WebhookService.deliver_webhook(webhook=test_webhook, event_type="project.created", payload=payload)

        assert delivery.status == "failed"
        assert delivery.error_type == "timeout"
        assert test_webhook.failed_deliveries == 1

    def test_deliver_webhook_inactive(self, db_session, test_webhook):
        """Test delivering to inactive webhook"""
        test_webhook.is_active = False
        db_session.commit()

        payload = {"event": "project.created"}

        with pytest.raises(WebhookDeliveryError):
            WebhookService.deliver_webhook(webhook=test_webhook, event_type="project.created", payload=payload)

    def test_deliver_webhook_not_subscribed(self, db_session, test_webhook):
        """Test delivering event webhook doesn't subscribe to"""
        payload = {"event": "project.updated"}

        with pytest.raises(WebhookDeliveryError):
            WebhookService.deliver_webhook(webhook=test_webhook, event_type="project.updated", payload=payload)

    def test_get_available_events(self):
        """Test getting available events"""
        events = WebhookService.get_available_events()

        assert isinstance(events, list)
        assert len(events) > 0
        assert "project.created" in events
        assert "task.created" in events

    @patch("app.utils.webhook_service.requests.post")
    def test_retry_failed_deliveries(self, mock_post, db_session, test_webhook):
        """Test retrying failed deliveries"""
        from app.utils.timezone import now_in_app_timezone
        from datetime import timedelta

        # Create a failed delivery scheduled for retry
        delivery = WebhookDelivery(
            webhook_id=test_webhook.id,
            event_type="project.created",
            payload='{"test": "data"}',
            status="retrying",
            next_retry_at=now_in_app_timezone() - timedelta(minutes=1),
            retry_count=1,
        )
        db_session.add(delivery)
        db_session.commit()

        # Mock successful response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = "OK"
        mock_response.headers = {}
        mock_post.return_value = mock_response

        retried = WebhookService.retry_failed_deliveries(max_deliveries=10)

        assert retried == 1
        db_session.refresh(delivery)
        assert delivery.status == "success"
