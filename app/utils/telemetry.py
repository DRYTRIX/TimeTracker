"""
Telemetry utility wrappers.

Legacy helper names are preserved for compatibility and delegated to the
consent-aware telemetry service backed by Grafana OTLP.
"""

import hashlib
import json
import os
import platform
import time
from typing import Optional


def get_telemetry_fingerprint() -> str:
    """
    Generate an anonymized fingerprint for this installation.

    Returns a SHA-256 hash that:
    - Uniquely identifies this installation
    - Cannot be reversed to identify the server
    - Uses installation-specific salt (generated once, persisted)
    """
    try:
        # Import via re-export to allow tests to patch app.utils.telemetry.get_installation_config
        from app.utils.telemetry import get_installation_config  # type: ignore

        # Get installation-specific salt (generated once and stored)
        installation_config = get_installation_config()
        salt = installation_config.get_installation_salt()
    except Exception:
        # Fallback to environment variable if installation config fails
        salt = os.getenv("TELE_SALT", "8f4a7b2e9c1d6f3a5e8b4c7d2a9f6e3b1c8d5a7f2e9b4c6d3a8f5e1b7c4d9a2f")

    node = platform.node() or "unknown"
    fingerprint = hashlib.sha256((node + salt).encode()).hexdigest()
    return fingerprint


def is_telemetry_enabled() -> bool:
    """
    Check if telemetry is enabled.

    Checks both environment variable and user preference from installation config.
    User preference takes precedence over environment variable.
    """
    # Environment variable takes precedence for tests/CI and explicit overrides
    env_value = os.getenv("ENABLE_TELEMETRY")
    if env_value is not None:
        enabled = env_value.lower()
        return enabled in ("true", "1", "yes", "on")

    try:
        # Import here to avoid circular imports
        from app.utils.installation import get_installation_config

        # Get user preference from installation config
        installation_config = get_installation_config()
        if installation_config.is_setup_complete():
            return installation_config.get_telemetry_preference()
    except Exception:
        pass

    # Default disabled if not explicitly enabled
    return False


# Re-export helper for tests to patch
try:
    from app.utils.installation import get_installation_config  # type: ignore
except Exception:

    def get_installation_config():  # type: ignore
        raise RuntimeError("installation config unavailable")


def send_telemetry_ping(event_type: str = "install", extra_data: Optional[dict] = None) -> bool:
    """
    Send a telemetry ping via PostHog with person properties and groups.

    Args:
        event_type: Type of event ("install", "update", "health")
        extra_data: Optional additional data to send (must not contain PII)

    Returns:
        True if telemetry was sent successfully, False otherwise
    """
    # Check if telemetry is enabled
    if not is_telemetry_enabled():
        return False

    try:
        from app.config.analytics_defaults import get_analytics_config

        cfg = get_analytics_config()
        endpoint = cfg.get("otel_exporter_otlp_endpoint") or os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT", "")
        token = cfg.get("otel_exporter_otlp_token") or os.getenv("OTEL_EXPORTER_OTLP_TOKEN", "")
        if not endpoint or not token:
            return False
    except Exception:
        return False

    try:
        from app.telemetry.service import send_analytics_event

        send_analytics_event(
            user_id=get_telemetry_fingerprint(),
            event_name=f"telemetry.{event_type}",
            properties=extra_data or {},
        )
        return True
    except Exception:
        return False


def send_install_ping() -> bool:
    """
    Send an installation telemetry ping.

    This should be called once on first startup or when telemetry is first enabled.
    """
    return send_telemetry_ping(event_type="install")


def send_update_ping(old_version: str, new_version: str) -> bool:
    """
    Send an update telemetry ping.

    Args:
        old_version: Previous version
        new_version: New version
    """
    return send_telemetry_ping(event_type="update", extra_data={"old_version": old_version, "new_version": new_version})


def send_health_ping() -> bool:
    """
    Send a health check telemetry ping.

    This can be called periodically (e.g., once per day) to track active installations.
    """
    return send_telemetry_ping(event_type="health")


def should_send_telemetry(marker_file: str = "/data/telemetry_sent") -> bool:
    """
    Check if telemetry should be sent based on marker file.

    Args:
        marker_file: Path to the marker file

    Returns:
        True if telemetry should be sent (not sent before or file doesn't exist)
    """
    if not is_telemetry_enabled():
        return False

    return not os.path.exists(marker_file)


def mark_telemetry_sent(marker_file: str = "/data/telemetry_sent") -> None:
    """
    Create a marker file indicating telemetry has been sent.

    Args:
        marker_file: Path to the marker file
    """
    try:
        # Ensure directory exists
        marker_dir = os.path.dirname(marker_file)
        if marker_dir and not os.path.exists(marker_dir):
            os.makedirs(marker_dir, exist_ok=True)

        # Create marker file with metadata
        # Read version from setup.py via analytics config
        from app.config.analytics_defaults import get_analytics_config

        analytics_config = get_analytics_config()
        app_version = analytics_config.get("app_version")
        with open(marker_file, "w") as f:
            json.dump({"version": app_version, "fingerprint": get_telemetry_fingerprint(), "sent_at": time.time()}, f)
    except Exception:
        # Silently fail - marker file is not critical
        pass


def check_and_send_telemetry() -> bool:
    """
    Check if telemetry should be sent and send it if appropriate.

    This is a convenience function that:
    1. Checks if telemetry is enabled
    2. Checks if telemetry has been sent before
    3. Sends telemetry if appropriate
    4. Marks telemetry as sent

    Returns:
        True if telemetry was sent, False otherwise
    """
    if not is_telemetry_enabled():
        return False

    marker_file = os.getenv("TELEMETRY_MARKER_FILE", "/data/telemetry_sent")

    if should_send_telemetry(marker_file):
        success = send_install_ping()
        if success:
            mark_telemetry_sent(marker_file)
        return success

    return False
