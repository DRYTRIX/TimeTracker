"""
Privacy-aware telemetry: base (always-on, minimal) and detailed analytics (opt-in only).

- base_telemetry.*: install footprint, version, platform, heartbeat; no PII.
- analytics.* / product events: only when user has opted in; feature usage, screens, errors.
"""

from app.telemetry.service import (
    is_detailed_analytics_enabled,
    send_analytics_event,
    send_base_first_seen,
    send_base_heartbeat,
    send_base_telemetry,
)

__all__ = [
    "is_detailed_analytics_enabled",
    "send_analytics_event",
    "send_base_first_seen",
    "send_base_heartbeat",
    "send_base_telemetry",
]
