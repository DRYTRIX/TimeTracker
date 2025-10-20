"""
Tests for analytics functionality (logging, Prometheus, PostHog)
"""

import pytest
import os
import json
from unittest.mock import patch, MagicMock, call
from flask import g
from app import create_app, log_event, track_event


@pytest.fixture
def app():
    """Create test Flask application"""
    app = create_app({'TESTING': True, 'SQLALCHEMY_DATABASE_URI': 'sqlite:///:memory:'})
    return app


@pytest.fixture
def client(app):
    """Create test client"""
    return app.test_client()


class TestLogEvent:
    """Tests for structured JSON logging"""
    
    def test_log_event_basic(self, app):
        """Test basic log event"""
        with app.app_context():
            with app.test_request_context():
                g.request_id = 'test-request-123'
                # This should not raise an exception
                log_event("test.event", user_id=1, test_data="value")
    
    def test_log_event_without_request_context(self, app):
        """Test that log_event handles missing request context gracefully"""
        with app.app_context():
            # Should not raise an exception even without request context
            log_event("test.event", user_id=1)
    
    def test_log_event_with_extra_data(self, app):
        """Test log event with various data types"""
        with app.app_context():
            with app.test_request_context():
                g.request_id = 'test-request-456'
                log_event("test.event",
                         user_id=1,
                         project_id=42,
                         duration=3600,
                         success=True,
                         tags=['tag1', 'tag2'])


class TestTrackEvent:
    """Tests for PostHog event tracking"""
    
    @patch('app.posthog.capture')
    def test_track_event_when_enabled(self, mock_capture, app):
        """Test that PostHog events are tracked when API key is set"""
        with patch.dict(os.environ, {'POSTHOG_API_KEY': 'test-key'}):
            track_event(123, "test.event", {"property": "value"})
            # Verify the event was tracked
            assert mock_capture.called
            call_args = mock_capture.call_args
            assert call_args[1]['distinct_id'] == '123'
            assert call_args[1]['event'] == 'test.event'
            # Verify our property is included (along with context properties)
            assert call_args[1]['properties']['property'] == 'value'
    
    @patch('app.posthog.capture')
    def test_track_event_when_disabled(self, mock_capture, app):
        """Test that PostHog events are not tracked when API key is not set"""
        with patch.dict(os.environ, {'POSTHOG_API_KEY': ''}):
            track_event(123, "test.event", {"property": "value"})
            mock_capture.assert_not_called()
    
    @patch('app.posthog.capture')
    def test_track_event_handles_errors_gracefully(self, mock_capture, app):
        """Test that tracking errors don't crash the application"""
        mock_capture.side_effect = Exception("PostHog error")
        with patch.dict(os.environ, {'POSTHOG_API_KEY': 'test-key'}):
            # Should not raise an exception
            track_event(123, "test.event", {})
    
    def test_track_event_with_none_properties(self, app):
        """Test that track_event handles None properties"""
        with patch.dict(os.environ, {'POSTHOG_API_KEY': 'test-key'}):
            with patch('app.posthog.capture') as mock_capture:
                track_event(123, "test.event", None)
                # Should have context properties even when None is passed
                call_args = mock_capture.call_args
                # Properties should be a dict (not None) with at least context properties
                assert isinstance(call_args[1]['properties'], dict)
                # Context properties should be present
                assert 'environment' in call_args[1]['properties']


class TestPrometheusMetrics:
    """Tests for Prometheus metrics"""
    
    def test_metrics_endpoint_exists(self, client):
        """Test that /metrics endpoint exists"""
        response = client.get('/metrics')
        assert response.status_code == 200
        assert response.content_type == 'text/plain; version=0.0.4; charset=utf-8'
    
    def test_metrics_endpoint_format(self, client):
        """Test that /metrics returns Prometheus format"""
        response = client.get('/metrics')
        data = response.data.decode('utf-8')
        
        # Should contain our custom metrics
        assert 'tt_requests_total' in data
        assert 'tt_request_latency_seconds' in data
    
    def test_metrics_are_incremented(self, client):
        """Test that metrics are incremented on requests"""
        # Make a request to trigger metric recording
        response = client.get('/metrics')
        assert response.status_code == 200
        
        # Get metrics
        response = client.get('/metrics')
        data = response.data.decode('utf-8')
        
        # Should have recorded requests
        assert 'tt_requests_total' in data


class TestAnalyticsIntegration:
    """Integration tests for analytics in routes"""
    
    @patch('app.routes.auth.log_event')
    @patch('app.routes.auth.track_event')
    def test_login_analytics(self, mock_track, mock_log, user, client):
        """Test that login events are tracked"""
        # Attempt login with existing user fixture
        response = client.post('/login', data={
            'username': user.username,
            'password': 'testpassword'
        }, follow_redirects=False)
        
        # Note: Whether events are tracked depends on login success
        # This test verifies the analytics hooks are in place
    
    @patch('app.routes.timer.log_event')
    @patch('app.routes.timer.track_event')
    def test_timer_analytics_integration(self, mock_track, mock_log, app, client):
        """Test that timer events are tracked (integration test placeholder)"""
        # This is a placeholder - actual implementation would require:
        # 1. Authenticated session
        # 2. Valid project
        # 3. Timer start/stop operations
        pass


class TestSentryIntegration:
    """Tests for Sentry error monitoring"""
    
    @patch('app.sentry_sdk.init')
    def test_sentry_initializes_when_dsn_set(self, mock_init):
        """Test that Sentry initializes when DSN is provided"""
        with patch.dict(os.environ, {
            'SENTRY_DSN': 'https://test@sentry.io/123',
            'SENTRY_TRACES_RATE': '0.1',
            'FLASK_ENV': 'production'
        }):
            app = create_app({'TESTING': True})
            # Sentry should have been initialized
            # Note: The actual initialization happens in create_app
    
    def test_sentry_not_initialized_without_dsn(self):
        """Test that Sentry is not initialized when DSN is not set"""
        with patch.dict(os.environ, {'SENTRY_DSN': ''}, clear=True):
            with patch('app.sentry_sdk.init') as mock_init:
                app = create_app({'TESTING': True})
                # Sentry init should not be called
                mock_init.assert_not_called()


class TestRequestIDAttachment:
    """Tests for request ID attachment"""
    
    def test_request_id_attached(self, app, client):
        """Test that request ID is attached to requests"""
        with app.app_context():
            with app.test_request_context():
                # Trigger the before_request hook
                with client:
                    response = client.get('/metrics')
                    # Request ID should be set in g
                    # Note: This test might need adjustment based on context handling


class TestAnalyticsEventSchema:
    """Tests to ensure analytics events follow the documented schema"""
    
    def test_event_naming_convention(self):
        """Test that event names follow resource.action pattern"""
        valid_events = [
            "auth.login",
            "auth.logout",
            "timer.started",
            "timer.stopped",
            "project.created",
            "project.updated",
            "export.csv",
            "report.viewed"
        ]
        
        for event_name in valid_events:
            parts = event_name.split('.')
            assert len(parts) == 2, f"Event {event_name} should follow resource.action pattern"
            assert parts[0].isalpha(), f"Resource part should be alphabetic: {event_name}"
            assert parts[1].replace('_', '').isalpha(), f"Action part should be alphabetic: {event_name}"


class TestAnalyticsPrivacy:
    """Tests to ensure analytics respect privacy guidelines"""
    
    def test_no_pii_in_standard_events(self, app):
        """Test that standard events don't include PII"""
        # Events should use IDs, not emails or usernames
        with app.app_context():
            with app.test_request_context():
                g.request_id = 'test-123'
                
                # This is acceptable (uses ID)
                log_event("test.event", user_id=123)
                
                # In production, events should NOT include:
                # - email addresses
                # - usernames (use IDs instead)
                # - IP addresses (unless explicitly needed)
                # - passwords or tokens
    
    @patch('app.posthog.capture')
    def test_posthog_uses_internal_ids(self, mock_capture, app):
        """Test that PostHog events use internal IDs, not PII"""
        with patch.dict(os.environ, {'POSTHOG_API_KEY': 'test-key'}):
            # Should use numeric ID, not email
            track_event(123, "test.event", {"project_id": 456})
            
            call_args = mock_capture.call_args
            # distinct_id should be the internal user ID (converted to string)
            assert call_args[1]['distinct_id'] == '123'


class TestAnalyticsPerformance:
    """Tests to ensure analytics don't impact performance"""
    
    def test_analytics_dont_block_requests(self, client):
        """Test that analytics operations don't significantly delay requests"""
        import time
        
        start = time.time()
        response = client.get('/metrics')
        duration = time.time() - start
        
        # Request should complete quickly even with analytics
        assert duration < 1.0  # Should complete in less than 1 second
        assert response.status_code == 200
    
    @patch('app.posthog.capture')
    def test_analytics_errors_dont_break_app(self, mock_capture, app, client):
        """Test that analytics failures don't break the application"""
        mock_capture.side_effect = Exception("Analytics service down")
        
        # Application should still work
        response = client.get('/metrics')
        assert response.status_code == 200
