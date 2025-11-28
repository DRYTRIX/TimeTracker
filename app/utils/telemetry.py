"""
Telemetry utilities for anonymous usage tracking

This module provides opt-in telemetry functionality that sends anonymized
installation information via PostHog. All telemetry is:
- Opt-in (disabled by default)
- Anonymous (no PII)
- Transparent (see docs/privacy.md)
"""

import hashlib
import platform
import os
import json
import time
from typing import Optional
import posthog


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


def _ensure_posthog_initialized() -> bool:
    """
    Ensure PostHog is initialized with API key and host.

    Returns:
        True if PostHog is ready to use, False otherwise
    """
    posthog_api_key = os.getenv("POSTHOG_API_KEY", "")
    if not posthog_api_key:
        return False

    try:
        # Initialize PostHog if not already done
        if not hasattr(posthog, "project_api_key") or not posthog.project_api_key:
            posthog.project_api_key = posthog_api_key
            posthog.host = os.getenv("POSTHOG_HOST", "https://app.posthog.com")
        return True
    except Exception:
        return False


def _get_installation_properties() -> dict:
    """
    Get installation properties for PostHog person/group properties.

    Returns:
        Dictionary of installation characteristics (no PII)
    """
    import sys

    # Get app version from analytics config (which reads from setup.py)
    from app.config.analytics_defaults import get_analytics_config

    analytics_config = get_analytics_config()
    app_version = analytics_config.get("app_version")
    flask_env = os.getenv("FLASK_ENV", "production")

    properties = {
        # Version info
        "app_version": app_version,
        "python_version": platform.python_version(),
        "python_major_version": f"{sys.version_info.major}.{sys.version_info.minor}",
        # Platform info
        "platform": platform.system(),
        "platform_release": platform.release(),
        "platform_version": platform.version(),
        "machine": platform.machine(),
        # Environment
        "environment": flask_env,
        "timezone": os.getenv("TZ", "Unknown"),
        # Deployment info
        "deployment_method": "docker" if os.path.exists("/.dockerenv") else "native",
        "auth_method": os.getenv("AUTH_METHOD", "local"),
    }

    return properties


def _identify_installation(fingerprint: str) -> None:
    """
    Identify the installation in PostHog with person properties.

    This sets/updates properties on the installation fingerprint for better
    segmentation and cohort analysis in PostHog.

    Args:
        fingerprint: The installation fingerprint (distinct_id)
    """
    try:
        properties = _get_installation_properties()

        # Use $set_once for properties that shouldn't change (first install data)
        set_once_properties = {
            "first_seen_platform": properties["platform"],
            "first_seen_python_version": properties["python_version"],
            "first_seen_version": properties["app_version"],
        }

        # Regular $set properties that can update
        set_properties = {
            "current_version": properties["app_version"],
            "current_platform": properties["platform"],
            "current_python_version": properties["python_version"],
            "environment": properties["environment"],
            "deployment_method": properties["deployment_method"],
            "auth_method": properties["auth_method"],
            "timezone": properties["timezone"],
            "last_seen": time.strftime("%Y-%m-%d %H:%M:%S"),
        }

        # Identify the installation
        posthog.identify(distinct_id=fingerprint, properties={"$set": set_properties, "$set_once": set_once_properties})
    except Exception:
        # Don't let identification errors break telemetry
        pass


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

    # Ensure PostHog is initialized and ready
    if not _ensure_posthog_initialized():
        return False

    # Get fingerprint for distinct_id
    fingerprint = get_telemetry_fingerprint()

    # Identify the installation with person properties (for better segmentation)
    _identify_installation(fingerprint)

    # Get installation properties
    install_props = _get_installation_properties()

    # Build event properties
    properties = {
        "app_version": install_props["app_version"],
        "platform": install_props["platform"],
        "python_version": install_props["python_version"],
        "environment": install_props["environment"],
        "deployment_method": install_props["deployment_method"],
    }

    # Add extra data if provided
    if extra_data:
        properties.update(extra_data)

    # Send telemetry via PostHog
    try:
        posthog.capture(
            distinct_id=fingerprint,
            event=f"telemetry.{event_type}",
            properties=properties,
            groups={
                "version": install_props["app_version"],
                "platform": install_props["platform"],
            },
        )

        # Also update group properties for cohort analysis
        _update_group_properties(install_props)

        return True
    except Exception:
        # Silently fail - telemetry should never break the application
        return False


def _update_group_properties(install_props: dict) -> None:
    """
    Update PostHog group properties for version and platform cohorts.

    This enables analysis like "all installations on version X" or
    "all Linux installations".

    Args:
        install_props: Installation properties dictionary
    """
    try:
        # Group by version
        posthog.group_identify(
            group_type="version",
            group_key=install_props["app_version"],
            properties={
                "version_number": install_props["app_version"],
                "python_versions": [install_props["python_version"]],  # Will aggregate
            },
        )

        # Group by platform
        posthog.group_identify(
            group_type="platform",
            group_key=install_props["platform"],
            properties={
                "platform_name": install_props["platform"],
                "platform_release": install_props.get("platform_release", "Unknown"),
            },
        )
    except Exception:
        # Don't let group errors break telemetry
        pass


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


def should_send_telemetry(marker_file: str = "data/telemetry_sent") -> bool:
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


def mark_telemetry_sent(marker_file: str = "data/telemetry_sent") -> None:
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

    marker_file = os.getenv("TELEMETRY_MARKER_FILE", "data/telemetry_sent")

    if should_send_telemetry(marker_file):
        success = send_install_ping()
        if success:
            mark_telemetry_sent(marker_file)
        return success

    return False
