"""
Tests for consent-aware analytics and base telemetry.
"""

import os
from unittest.mock import patch, MagicMock

import pytest


class TestConsentGate:
    """Product analytics only sent when opt-in is enabled."""

    @patch("app.telemetry.service._send_otlp_event")
    def test_send_analytics_event_no_capture_when_opt_out(self, mock_send):
        """When detailed analytics is disabled, send_analytics_event must not call OTLP sender."""
        from app.telemetry.service import send_analytics_event

        with patch("app.telemetry.service.is_detailed_analytics_enabled", return_value=False):
            send_analytics_event(1, "test.event", {"k": "v"})
        mock_send.assert_not_called()

    @patch("app.telemetry.service._send_otlp_event")
    def test_send_analytics_event_capture_when_opt_in(self, mock_send):
        """When detailed analytics is enabled and OTLP configured, sender is called."""
        from app.telemetry.service import send_analytics_event

        with patch("app.telemetry.service.is_detailed_analytics_enabled", return_value=True):
            with patch("app.config.analytics_defaults.get_analytics_config") as mock_config:
                mock_config.return_value = {
                    "otel_exporter_otlp_endpoint": "https://otlp.example.com",
                    "otel_exporter_otlp_token": "test-token",
                    "app_version": "1.0.0",
                }
                with patch("app.utils.installation.get_installation_config") as mock_inst:
                    mock_inst.return_value.get_install_id.return_value = "install-uuid-123"
                    with patch("app.utils.telemetry.get_telemetry_fingerprint", return_value="fp-abc-123"):
                        send_analytics_event(1, "test.event", {"k": "v"})
        mock_send.assert_called_once()
        call_kw = mock_send.call_args[1]
        assert call_kw["identity"] == "1"
        assert call_kw["event_name"] == "test.event"
        assert call_kw["properties"].get("install_id") == "install-uuid-123"
        assert call_kw["properties"].get("telemetry_fingerprint") == "fp-abc-123"


class TestBaseTelemetry:
    """Base telemetry (first_seen, heartbeat) and schema."""

    def test_send_base_first_seen_idempotent(self):
        """send_base_first_seen sends once; second call is no-op and does not send again."""
        from app.telemetry.service import send_base_first_seen, send_base_telemetry

        mock_inst = MagicMock()
        mock_inst.get_base_first_seen_sent_at.side_effect = [None, None, "2025-01-01T00:00:00Z"]
        mock_inst.get_install_id.return_value = "uuid-base"
        mock_inst._config = {}

        with patch("app.utils.installation.get_installation_config", return_value=mock_inst):
            with patch("app.telemetry.service.send_base_telemetry") as mock_send:
                with patch("app.utils.telemetry.get_telemetry_fingerprint", return_value="fp-abc-123"):
                    mock_send.return_value = True
                    r1 = send_base_first_seen()
                    r2 = send_base_first_seen()
        assert mock_send.call_count == 1, "first_seen should be sent only once"
        assert r1 is True
        assert r2 is False
        call_payload = mock_send.call_args[0][0]
        assert call_payload.get("_event") == "base_telemetry.first_seen"
        assert call_payload.get("install_id") == "uuid-base"
        mock_inst.set_base_first_seen_sent_at.assert_called_once()

    def test_send_base_heartbeat_calls_telemetry_with_schema(self):
        """send_base_heartbeat builds payload and calls send_base_telemetry with schema fields."""
        from app.telemetry.service import send_base_heartbeat, send_base_telemetry

        payload = {
            "install_id": "uuid-hb",
            "app_version": "2.0.0",
            "platform": "Linux",
            "os_version": "5.0",
            "architecture": "x86_64",
            "locale": "en_US",
            "timezone": "UTC",
            "first_seen_at": "2025-01-01T00:00:00Z",
            "last_seen_at": "2025-01-02T00:00:00Z",
            "heartbeat_at": "2025-01-02T00:00:00Z",
            "release_channel": "default",
            "deployment_type": "docker",
            "_event": "base_telemetry.heartbeat",
        }
        with patch("app.telemetry.service._build_base_telemetry_payload", return_value=payload.copy()):
            with patch("app.telemetry.service.send_base_telemetry") as mock_send:
                mock_send.return_value = True
                result = send_base_heartbeat()
        assert result is True
        mock_send.assert_called_once()
        call_payload = mock_send.call_args[0][0]
        assert call_payload["_event"] == "base_telemetry.heartbeat"
        assert call_payload["install_id"] == "uuid-hb"
        assert "app_version" in call_payload
        assert "platform" in call_payload

    def test_base_payload_includes_telemetry_fingerprint(self):
        """Base telemetry payload includes both install_id and telemetry fingerprint."""
        from app.telemetry.service import _build_base_telemetry_payload

        mock_inst = MagicMock()
        mock_inst.get_base_first_seen_sent_at.return_value = None
        mock_inst.get_install_id.return_value = "install-uuid-123"

        with patch("app.utils.installation.get_installation_config", return_value=mock_inst):
            with patch("app.config.analytics_defaults.get_analytics_config", return_value={"app_version": "1.0.0"}):
                with patch("app.utils.telemetry.get_telemetry_fingerprint", return_value="fp-abc-123"):
                    payload = _build_base_telemetry_payload("heartbeat")

        assert payload["install_id"] == "install-uuid-123"
        assert payload["telemetry_fingerprint"] == "fp-abc-123"


class TestInstallIdInPayloads:
    """install_id is stable and present where required."""

    def test_install_id_stable_across_calls(self, tmp_path, monkeypatch):
        """get_install_id returns the same value across calls."""
        monkeypatch.setenv("INSTALLATION_CONFIG_DIR", str(tmp_path))
        from app.utils.installation import get_installation_config

        config = get_installation_config()
        id1 = config.get_install_id()
        id2 = config.get_install_id()
        assert id1 == id2
        assert len(id1) == 36
