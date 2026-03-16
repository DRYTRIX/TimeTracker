"""
Consent-aware telemetry service.

- Base telemetry: always-on, minimal schema (install footprint, heartbeat).
  Event names: base_telemetry.first_seen, base_telemetry.heartbeat.
- Detailed analytics: only when user has opted in; product events (analytics.* or existing names).
"""

import os
import platform
from datetime import datetime, timezone
from typing import Any, Dict, Optional

# Lazy imports to avoid circular deps and to keep posthog optional at import time

# Base telemetry schema keys (no PII). Country omitted unless added server-side later.
BASE_SCHEMA_KEYS = frozenset({
    "install_id", "app_version", "platform", "os_version", "architecture",
    "locale", "timezone", "first_seen_at", "last_seen_at", "heartbeat_at",
    "release_channel", "deployment_type",
})


def is_detailed_analytics_enabled() -> bool:
    """True if the user has opted in to detailed analytics (feature usage, screens, etc.)."""
    from app.utils.telemetry import is_telemetry_enabled

    return is_telemetry_enabled()


def _build_base_telemetry_payload(
    event_kind: str,
) -> Dict[str, Any]:
    """Build minimal base telemetry payload. No PII."""
    from app.config.analytics_defaults import get_analytics_config
    from app.utils.installation import get_installation_config

    config = get_analytics_config()
    inst = get_installation_config()
    now = datetime.now(timezone.utc).isoformat()

    first_seen = inst.get_base_first_seen_sent_at() or now
    payload = {
        "install_id": inst.get_install_id(),
        "app_version": config.get("app_version", "unknown"),
        "platform": platform.system(),
        "os_version": platform.release(),
        "architecture": platform.machine(),
        "locale": (os.getenv("LANG") or os.getenv("LC_ALL") or "unknown")[:5] or "unknown",
        "timezone": os.getenv("TZ", "UTC"),
        "first_seen_at": first_seen,
        "last_seen_at": now,
        "heartbeat_at": now,
        "release_channel": os.getenv("RELEASE_CHANNEL", "default"),
        "deployment_type": "docker" if os.path.exists("/.dockerenv") else "native",
    }
    if event_kind == "first_seen":
        payload["first_seen_at"] = now
    return payload


def send_base_telemetry(payload: Dict[str, Any]) -> bool:
    """
    Send base telemetry (always-on, minimal). Schema: install_id, app_version,
    platform, os_version, architecture, locale, timezone, first_seen_at, last_seen_at,
    heartbeat_at, release_channel, deployment_type.
    Sends to PostHog as base_telemetry.first_seen or base_telemetry.heartbeat when payload
    includes event_kind or uses distinct event names. Returns True if sent.
    """
    try:
        import posthog
        from app.config.analytics_defaults import get_analytics_config

        config = get_analytics_config()
        posthog_api_key = config.get("posthog_api_key") or os.getenv("POSTHOG_API_KEY", "")
        if not posthog_api_key:
            return False

        if not getattr(posthog, "project_api_key", None) or not posthog.project_api_key:
            posthog.project_api_key = posthog_api_key
            posthog.host = config.get("posthog_host", os.getenv("POSTHOG_HOST", "https://app.posthog.com"))

        install_id = payload.get("install_id")
        if not install_id:
            return False

        event_name = payload.get("_event", "base_telemetry.heartbeat")
        props = {k: v for k, v in payload.items() if k != "_event"}
        posthog.capture(distinct_id=install_id, event=event_name, properties=props)
        return True
    except Exception:
        return False


def send_base_first_seen() -> bool:
    """Send base_telemetry.first_seen once per install. Idempotent."""
    from app.utils.installation import get_installation_config

    inst = get_installation_config()
    if inst.get_base_first_seen_sent_at():
        return False
    payload = _build_base_telemetry_payload("first_seen")
    payload["_event"] = "base_telemetry.first_seen"
    payload["first_seen_at"] = datetime.now(timezone.utc).isoformat()
    if send_base_telemetry(payload):
        inst.set_base_first_seen_sent_at(payload["first_seen_at"])
        return True
    return False


def send_base_heartbeat() -> bool:
    """Send base_telemetry.heartbeat (e.g. daily). Updates last_seen_at."""
    payload = _build_base_telemetry_payload("heartbeat")
    payload["_event"] = "base_telemetry.heartbeat"
    return send_base_telemetry(payload)


def identify_user(user_id: Any, properties: Optional[Dict[str, Any]] = None) -> None:
    """Identify user in analytics backend. Only when opted in and PostHog configured."""
    if not is_detailed_analytics_enabled():
        return
    try:
        import posthog
        from app.config.analytics_defaults import get_analytics_config

        config = get_analytics_config()
        posthog_api_key = config.get("posthog_api_key") or os.getenv("POSTHOG_API_KEY", "")
        if not posthog_api_key:
            return
        if not getattr(posthog, "project_api_key", None) or not posthog.project_api_key:
            posthog.project_api_key = posthog_api_key
            posthog.host = config.get("posthog_host", os.getenv("POSTHOG_HOST", "https://app.posthog.com"))
        posthog.identify(distinct_id=str(user_id), properties=properties or {})
    except Exception:
        pass


def send_analytics_event(
    user_id: Any,
    event_name: str,
    properties: Optional[Dict[str, Any]] = None,
) -> None:
    """
    Send a product analytics event. Only sent when detailed analytics is opted in
    and PostHog is configured. Adds install_id and context.
    """
    if not is_detailed_analytics_enabled():
        return
    try:
        import posthog
        from app.config.analytics_defaults import get_analytics_config
        from app.utils.installation import get_installation_config

        config = get_analytics_config()
        posthog_api_key = config.get("posthog_api_key") or os.getenv("POSTHOG_API_KEY", "")
        if not posthog_api_key:
            return

        if not getattr(posthog, "project_api_key", None) or not posthog.project_api_key:
            posthog.project_api_key = posthog_api_key
            posthog.host = config.get("posthog_host", os.getenv("POSTHOG_HOST", "https://app.posthog.com"))

        enhanced = dict(properties or {})
        enhanced["install_id"] = get_installation_config().get_install_id()
        enhanced["environment"] = os.getenv("FLASK_ENV", "production")
        enhanced["app_version"] = config.get("app_version")
        enhanced["deployment_method"] = "docker" if os.path.exists("/.dockerenv") else "native"

        try:
            from flask import request

            if request:
                enhanced["$current_url"] = request.url
                enhanced["$host"] = request.host
                enhanced["$pathname"] = request.path
                enhanced["$browser"] = getattr(request.user_agent, "browser", None)
                enhanced["$device_type"] = (
                    "mobile"
                    if getattr(request.user_agent, "platform", None) in ["android", "iphone"]
                    else "desktop"
                )
                enhanced["$os"] = getattr(request.user_agent, "platform", None)
        except Exception:
            pass

        posthog.capture(distinct_id=str(user_id), event=event_name, properties=enhanced)
    except Exception:
        pass


def send_base_telemetry(payload: Dict[str, Any]) -> bool:
    """
    Send base telemetry (always-on, minimal). Schema: install_id, app_version,
    platform, os_version, architecture, locale, timezone, first_seen_at, last_seen_at,
    heartbeat_at, release_channel, deployment_type; country server-derived if possible.
    Implemented in Phase 2; for now no-op if no sink configured.
    """
    # Phase 2 will implement the sink (PostHog base event or custom endpoint)
    return False
