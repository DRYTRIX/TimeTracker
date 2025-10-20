"""
Tests for telemetry functionality
"""

import pytest
import os
import json
import tempfile
from unittest.mock import patch, MagicMock
from app.utils.telemetry import (
    get_telemetry_fingerprint,
    is_telemetry_enabled,
    send_telemetry_ping,
    send_install_ping,
    send_update_ping,
    send_health_ping,
    should_send_telemetry,
    mark_telemetry_sent,
    check_and_send_telemetry
)


class TestTelemetryFingerprint:
    """Tests for telemetry fingerprint generation"""
    
    def test_fingerprint_is_consistent(self):
        """Test that fingerprint is consistent for same inputs"""
        with patch.dict(os.environ, {'TELE_SALT': 'test-salt'}):
            fp1 = get_telemetry_fingerprint()
            fp2 = get_telemetry_fingerprint()
            assert fp1 == fp2
    
    def test_fingerprint_changes_with_salt(self):
        """Test that fingerprint changes when salt changes"""
        with patch.dict(os.environ, {'TELE_SALT': 'salt1'}):
            fp1 = get_telemetry_fingerprint()
        
        with patch.dict(os.environ, {'TELE_SALT': 'salt2'}):
            fp2 = get_telemetry_fingerprint()
        
        assert fp1 != fp2
    
    def test_fingerprint_is_sha256_hash(self):
        """Test that fingerprint is a valid SHA-256 hash"""
        fp = get_telemetry_fingerprint()
        assert len(fp) == 64  # SHA-256 produces 64 hex characters
        assert all(c in '0123456789abcdef' for c in fp)


class TestTelemetryEnabled:
    """Tests for telemetry enabled check"""
    
    @pytest.mark.parametrize('value,expected', [
        ('true', True),
        ('True', True),
        ('TRUE', True),
        ('1', True),
        ('yes', True),
        ('on', True),
        ('false', False),
        ('False', False),
        ('0', False),
        ('no', False),
        ('', False),
        ('random', False),
    ])
    def test_telemetry_enabled_values(self, value, expected):
        """Test various values for ENABLE_TELEMETRY"""
        with patch.dict(os.environ, {'ENABLE_TELEMETRY': value}):
            assert is_telemetry_enabled() == expected
    
    def test_telemetry_disabled_by_default(self):
        """Test that telemetry is disabled by default"""
        with patch.dict(os.environ, {}, clear=True):
            assert is_telemetry_enabled() is False


class TestSendTelemetryPing:
    """Tests for sending telemetry pings"""
    
    @patch('app.utils.telemetry.posthog.capture')
    def test_send_ping_when_enabled(self, mock_capture):
        """Test sending telemetry ping when enabled"""
        with patch.dict(os.environ, {
            'ENABLE_TELEMETRY': 'true',
            'POSTHOG_API_KEY': 'test-api-key',
            'APP_VERSION': '1.0.0',
            'TELE_SALT': 'test-salt'
        }):
            result = send_telemetry_ping('install')
            assert result is True
            assert mock_capture.called
            
            # Verify the call
            call_args = mock_capture.call_args
            assert call_args[1]['event'] == 'telemetry.install'
            assert 'distinct_id' in call_args[1]
            assert 'properties' in call_args[1]
    
    @patch('app.utils.telemetry.posthog.capture')
    def test_no_ping_when_disabled(self, mock_capture):
        """Test that no ping is sent when telemetry is disabled"""
        with patch.dict(os.environ, {'ENABLE_TELEMETRY': 'false'}):
            result = send_telemetry_ping('install')
            assert result is False
            assert not mock_capture.called
    
    @patch('app.utils.telemetry.posthog.capture')
    def test_no_ping_when_no_api_key(self, mock_capture):
        """Test that no ping is sent when POSTHOG_API_KEY is not set"""
        with patch.dict(os.environ, {'ENABLE_TELEMETRY': 'true', 'POSTHOG_API_KEY': ''}):
            result = send_telemetry_ping('install')
            assert result is False
            assert not mock_capture.called
    
    @patch('app.utils.telemetry.posthog.capture')
    def test_ping_includes_required_fields(self, mock_capture):
        """Test that telemetry ping includes required fields"""
        with patch.dict(os.environ, {
            'ENABLE_TELEMETRY': 'true',
            'POSTHOG_API_KEY': 'test-api-key',
            'APP_VERSION': '1.0.0',
            'TELE_SALT': 'test-salt'
        }):
            send_telemetry_ping('install', extra_data={'test': 'value'})
            
            # Get the call arguments
            call_args = mock_capture.call_args
            event = call_args[1]['event']
            properties = call_args[1]['properties']
            
            assert event == 'telemetry.install'
            assert 'app_version' in properties
            assert 'platform' in properties
            assert 'python_version' in properties
            assert 'environment' in properties
            assert 'deployment_method' in properties
            assert properties['test'] == 'value'
    
    @patch('app.utils.telemetry.posthog.capture')
    def test_ping_handles_network_errors_gracefully(self, mock_capture):
        """Test that network errors don't crash the application"""
        mock_capture.side_effect = Exception("Network error")
        
        with patch.dict(os.environ, {
            'ENABLE_TELEMETRY': 'true',
            'POSTHOG_API_KEY': 'test-api-key'
        }):
            result = send_telemetry_ping('install')
            assert result is False


class TestTelemetryEventTypes:
    """Tests for different telemetry event types"""
    
    @patch('app.utils.telemetry.send_telemetry_ping')
    def test_send_install_ping(self, mock_send):
        """Test sending install ping"""
        send_install_ping()
        mock_send.assert_called_once_with(event_type='install')
    
    @patch('app.utils.telemetry.send_telemetry_ping')
    def test_send_update_ping(self, mock_send):
        """Test sending update ping"""
        send_update_ping('1.0.0', '1.1.0')
        mock_send.assert_called_once()
        call_args = mock_send.call_args
        assert call_args[1]['event_type'] == 'update'
        assert call_args[1]['extra_data']['old_version'] == '1.0.0'
        assert call_args[1]['extra_data']['new_version'] == '1.1.0'
    
    @patch('app.utils.telemetry.send_telemetry_ping')
    def test_send_health_ping(self, mock_send):
        """Test sending health ping"""
        send_health_ping()
        mock_send.assert_called_once_with(event_type='health')


class TestTelemetryMarker:
    """Tests for telemetry marker file functionality"""
    
    def test_should_send_when_no_marker(self):
        """Test that telemetry should be sent when marker doesn't exist"""
        with tempfile.NamedTemporaryFile(delete=True) as tmp:
            marker_path = tmp.name + '_nonexistent'
            with patch.dict(os.environ, {'ENABLE_TELEMETRY': 'true'}):
                assert should_send_telemetry(marker_path) is True
    
    def test_should_not_send_when_marker_exists(self):
        """Test that telemetry shouldn't be sent when marker exists"""
        with tempfile.NamedTemporaryFile(delete=False) as tmp:
            marker_path = tmp.name
            try:
                with patch.dict(os.environ, {'ENABLE_TELEMETRY': 'true'}):
                    assert should_send_telemetry(marker_path) is False
            finally:
                os.unlink(marker_path)
    
    def test_mark_telemetry_sent_creates_file(self):
        """Test that marking telemetry as sent creates marker file"""
        with tempfile.TemporaryDirectory() as tmpdir:
            marker_path = os.path.join(tmpdir, 'test_marker')
            with patch.dict(os.environ, {'APP_VERSION': '1.0.0'}):
                mark_telemetry_sent(marker_path)
                assert os.path.exists(marker_path)
                
                # Verify file contents
                with open(marker_path, 'r') as f:
                    data = json.load(f)
                    assert 'version' in data
                    assert 'fingerprint' in data


class TestCheckAndSendTelemetry:
    """Tests for the convenience function"""
    
    @patch('app.utils.telemetry.send_install_ping')
    @patch('app.utils.telemetry.mark_telemetry_sent')
    def test_check_and_send_when_appropriate(self, mock_mark, mock_send):
        """Test that telemetry is sent and marked when appropriate"""
        mock_send.return_value = True
        
        with tempfile.TemporaryDirectory() as tmpdir:
            marker_path = os.path.join(tmpdir, 'telemetry_sent')
            with patch.dict(os.environ, {
                'ENABLE_TELEMETRY': 'true',
                'TELEMETRY_MARKER_FILE': marker_path
            }):
                result = check_and_send_telemetry()
                assert result is True
                mock_send.assert_called_once()
                mock_mark.assert_called_once()
    
    @patch('app.utils.telemetry.send_install_ping')
    def test_no_send_when_disabled(self, mock_send):
        """Test that telemetry is not sent when disabled"""
        with patch.dict(os.environ, {'ENABLE_TELEMETRY': 'false'}):
            result = check_and_send_telemetry()
            assert result is False
            assert not mock_send.called
    
    @patch('app.utils.telemetry.send_install_ping')
    def test_no_send_when_already_sent(self, mock_send):
        """Test that telemetry is not sent when already marked as sent"""
        with tempfile.NamedTemporaryFile(delete=False) as tmp:
            marker_path = tmp.name
            try:
                with patch.dict(os.environ, {
                    'ENABLE_TELEMETRY': 'true',
                    'TELEMETRY_MARKER_FILE': marker_path
                }):
                    result = check_and_send_telemetry()
                    assert result is False
                    assert not mock_send.called
            finally:
                os.unlink(marker_path)

