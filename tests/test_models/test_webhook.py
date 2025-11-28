"""Tests for Webhook models"""

import pytest
from datetime import datetime, timedelta
from app import db
from app.models import Webhook, WebhookDelivery, User
from app.utils.timezone import now_in_app_timezone


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
        events=["project.created", "task.created"],
        user_id=test_user.id,
        is_active=True,
    )
    webhook.set_secret()
    db_session.add(webhook)
    db_session.commit()
    return webhook


class TestWebhook:
    """Test Webhook model"""

    def test_create_webhook(self, db_session, test_user):
        """Test creating a webhook"""
        webhook = Webhook(
            name="My Webhook", url="https://example.com/webhook", events=["project.created"], user_id=test_user.id
        )
        webhook.set_secret()

        db_session.add(webhook)
        db_session.commit()

        assert webhook.id is not None
        assert webhook.name == "My Webhook"
        assert webhook.url == "https://example.com/webhook"
        assert webhook.secret is not None
        assert len(webhook.secret) > 0

    def test_webhook_subscribes_to(self, test_webhook):
        """Test webhook event subscription"""
        assert test_webhook.subscribes_to("project.created") is True
        assert test_webhook.subscribes_to("task.created") is True
        assert test_webhook.subscribes_to("project.updated") is False

    def test_webhook_wildcard_subscription(self, db_session, test_user):
        """Test wildcard subscription"""
        webhook = Webhook(name="All Events", url="https://example.com/webhook", events=["*"], user_id=test_user.id)
        db_session.add(webhook)
        db_session.commit()

        assert webhook.subscribes_to("project.created") is True
        assert webhook.subscribes_to("any.event") is True

    def test_webhook_signature_generation(self, test_webhook):
        """Test signature generation"""
        payload = '{"test": "data"}'
        signature = test_webhook.generate_signature(payload)

        assert signature is not None
        assert signature.startswith("sha256=")
        assert len(signature) > 10

    def test_webhook_signature_verification(self, test_webhook):
        """Test signature verification"""
        payload = '{"test": "data"}'
        signature = test_webhook.generate_signature(payload)

        assert test_webhook.verify_signature(payload, signature) is True
        assert test_webhook.verify_signature(payload, "invalid") is False

    def test_webhook_to_dict(self, test_webhook):
        """Test webhook serialization"""
        data = test_webhook.to_dict()

        assert "id" in data
        assert "name" in data
        assert "url" in data
        assert "events" in data
        assert "is_active" in data
        assert "secret" not in data  # Secret not included by default

    def test_webhook_to_dict_with_secret(self, test_webhook):
        """Test webhook serialization with secret"""
        data = test_webhook.to_dict(include_secret=True)

        assert "secret" in data
        assert data["secret"] == test_webhook.secret


class TestWebhookDelivery:
    """Test WebhookDelivery model"""

    def test_create_delivery(self, db_session, test_webhook):
        """Test creating a delivery record"""
        delivery = WebhookDelivery(
            webhook_id=test_webhook.id, event_type="project.created", payload='{"test": "data"}', status="pending"
        )

        db_session.add(delivery)
        db_session.commit()

        assert delivery.id is not None
        assert delivery.webhook_id == test_webhook.id
        assert delivery.status == "pending"

    def test_delivery_mark_success(self, db_session, test_webhook):
        """Test marking delivery as successful"""
        delivery = WebhookDelivery(
            webhook_id=test_webhook.id, event_type="project.created", payload='{"test": "data"}', status="pending"
        )
        db_session.add(delivery)
        db_session.commit()

        delivery.mark_success(status_code=200, response_body="OK", duration_ms=100)
        db_session.commit()

        assert delivery.status == "success"
        assert delivery.response_status_code == 200
        assert delivery.completed_at is not None
        assert test_webhook.successful_deliveries == 1

    def test_delivery_mark_failed(self, db_session, test_webhook):
        """Test marking delivery as failed"""
        delivery = WebhookDelivery(
            webhook_id=test_webhook.id, event_type="project.created", payload='{"test": "data"}', status="pending"
        )
        db_session.add(delivery)
        db_session.commit()

        delivery.mark_failed(error_message="Connection timeout", error_type="timeout", duration_ms=30000)
        db_session.commit()

        assert delivery.status == "failed"
        assert delivery.error_message == "Connection timeout"
        assert test_webhook.failed_deliveries == 1

    def test_delivery_mark_retrying(self, db_session, test_webhook):
        """Test marking delivery for retry"""
        delivery = WebhookDelivery(
            webhook_id=test_webhook.id, event_type="project.created", payload='{"test": "data"}', status="pending"
        )
        db_session.add(delivery)
        db_session.commit()

        next_retry = now_in_app_timezone() + timedelta(minutes=5)
        delivery.mark_retrying(next_retry)
        db_session.commit()

        assert delivery.status == "retrying"
        assert delivery.retry_count == 1
        assert delivery.next_retry_at == next_retry

    def test_delivery_hash_payload(self):
        """Test payload hashing"""
        payload = '{"test": "data"}'
        hash1 = WebhookDelivery.hash_payload(payload)
        hash2 = WebhookDelivery.hash_payload(payload)

        assert hash1 == hash2
        assert len(hash1) == 64  # SHA256 hex length

    def test_delivery_to_dict(self, db_session, test_webhook):
        """Test delivery serialization"""
        delivery = WebhookDelivery(
            webhook_id=test_webhook.id, event_type="project.created", payload='{"test": "data"}', status="success"
        )
        db_session.add(delivery)
        db_session.commit()

        data = delivery.to_dict()

        assert "id" in data
        assert "webhook_id" in data
        assert "event_type" in data
        assert "status" in data
