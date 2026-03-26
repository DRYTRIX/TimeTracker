"""
Consent-aware telemetry service backed by Grafana Cloud OTLP.

- Base telemetry is always-on and anonymous per installation.
- Detailed analytics is sent only when the user opted in.
"""

import json
import logging
import os
import platform
import base64
import time
from datetime import datetime, timezone
from typing import Any, Dict, Optional
from urllib import request
from urllib.parse import urlparse

logger = logging.getLogger(__name__)

BASE_SCHEMA_KEYS = frozenset(
    {
        "install_id",
        "telemetry_fingerprint",
        "app_version",
        "platform",
        "os_version",
        "architecture",
        "locale",
        "timezone",
        "first_seen_at",
        "last_seen_at",
        "heartbeat_at",
        "release_channel",
        "deployment_type",
    }
)


def is_detailed_analytics_enabled() -> bool:
    from app.utils.telemetry import is_telemetry_enabled

    return is_telemetry_enabled()


def _build_base_telemetry_payload(event_kind: str) -> Dict[str, Any]:
    from app.config.analytics_defaults import get_analytics_config
    from app.utils.installation import get_installation_config
    from app.utils.telemetry import get_telemetry_fingerprint

    config = get_analytics_config()
    inst = get_installation_config()
    now = datetime.now(timezone.utc).isoformat()

    first_seen = inst.get_base_first_seen_sent_at() or now
    payload = {
        "install_id": inst.get_install_id(),
        "telemetry_fingerprint": get_telemetry_fingerprint(),
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


def _otlp_enabled() -> bool:
    from app.config.analytics_defaults import get_analytics_config

    config = get_analytics_config()
    endpoint = (
        config.get("otel_exporter_otlp_endpoint")
        or os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT", "")
    )
    token = config.get("otel_exporter_otlp_token") or os.getenv("OTEL_EXPORTER_OTLP_TOKEN", "")
    return bool(endpoint and token)


def _build_otlp_auth_header(token: str) -> str:
    """
    Build OTLP Authorization header from a single token input.
    Accepted token formats:
    - "Basic <base64>"
    - "<instance_id>:<token>"  -> converted to Basic
    - "<base64blob>"           -> treated as Basic payload
    """
    value = (token or "").strip()
    if value.lower().startswith("basic "):
        return value
    if ":" in value:
        encoded = base64.b64encode(value.encode("utf-8")).decode("ascii")
        return f"Basic {encoded}"
    return f"Basic {value}"


def _telemetry_debug_logging_enabled() -> bool:
    return (os.getenv("OTEL_DEBUG_LOGGING", "false") or "").strip().lower() in {"1", "true", "yes", "on"}


def _remove_pii(properties: Dict[str, Any]) -> Dict[str, Any]:
    pii_keys = {"email", "username", "ip", "ip_address", "full_name", "name", "password", "token"}
    return {k: v for k, v in properties.items() if k.lower() not in pii_keys}


def _to_otlp_any_value(value: Any) -> Dict[str, Any]:
    if isinstance(value, bool):
        return {"boolValue": value}
    if isinstance(value, int):
        return {"intValue": str(value)}
    if isinstance(value, float):
        return {"doubleValue": value}
    return {"stringValue": str(value)}


def _build_otlp_logs_payload(
    event_name: str,
    identity: str,
    detailed: bool,
    safe_props: Dict[str, Any],
    service_version: str,
) -> Dict[str, Any]:
    now_nanos = str(int(time.time() * 1_000_000_000))
    resource_attributes = [
        {"key": "service.name", "value": {"stringValue": "timetracker"}},
        {"key": "service.version", "value": {"stringValue": str(service_version or "unknown")}},
        {"key": "deployment.environment", "value": {"stringValue": os.getenv("FLASK_ENV", "production")}},
    ]
    record_attributes = [
        {"key": "event_name", "value": {"stringValue": event_name}},
        {"key": "identity", "value": {"stringValue": str(identity)}},
        {"key": "detailed", "value": {"boolValue": bool(detailed)}},
    ]
    for key, value in safe_props.items():
        record_attributes.append({"key": str(key), "value": _to_otlp_any_value(value)})

    return {
        "resourceLogs": [
            {
                "resource": {"attributes": resource_attributes},
                "scopeLogs": [
                    {
                        "scope": {"name": "timetracker.telemetry"},
                        "logRecords": [
                            {
                                "timeUnixNano": now_nanos,
                                "severityText": "INFO",
                                "body": {"stringValue": event_name},
                                "attributes": record_attributes,
                            }
                        ],
                    }
                ],
            }
        ]
    }


def _send_otlp_event(event_name: str, identity: str, properties: Dict[str, Any], detailed: bool) -> bool:
    from app.config.analytics_defaults import get_analytics_config

    config = get_analytics_config()
    endpoint = config.get("otel_exporter_otlp_endpoint") or os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT", "")
    token = config.get("otel_exporter_otlp_token") or os.getenv("OTEL_EXPORTER_OTLP_TOKEN", "")

    if not endpoint or not token:
        if _telemetry_debug_logging_enabled():
            logger.info(
                "telemetry.skip event=%s reason=missing_otlp_config endpoint_set=%s token_set=%s",
                event_name,
                bool(endpoint),
                bool(token),
            )
        return False

    # Support OTEL-style base endpoint by auto-targeting logs path.
    endpoint = endpoint.rstrip("/")
    if endpoint.endswith("/otlp"):
        endpoint = f"{endpoint}/v1/logs"
    elif not endpoint.endswith("/v1/logs"):
        endpoint = f"{endpoint}/v1/logs"

    safe_props = _remove_pii(properties) if detailed else properties
    payload = _build_otlp_logs_payload(
        event_name=event_name,
        identity=str(identity),
        detailed=detailed,
        safe_props=safe_props,
        service_version=str(config.get("app_version", "unknown")),
    )
    body = json.dumps(payload).encode("utf-8")
    auth_header = _build_otlp_auth_header(token)
    headers = {
        "Content-Type": "application/json",
        "Authorization": auth_header,
    }
    if _telemetry_debug_logging_enabled():
        parsed = urlparse(endpoint)
        auth_mode = "basic_from_colon" if ":" in token and not token.lower().startswith("basic ") else "basic_direct"
        logger.info(
            "telemetry.send event=%s detailed=%s endpoint=%s://%s%s auth_mode=%s identity_len=%s props_count=%s",
            event_name,
            detailed,
            parsed.scheme or "https",
            parsed.netloc,
            parsed.path,
            auth_mode,
            len(str(identity)),
            len(safe_props),
        )

    req = request.Request(
        endpoint,
        data=body,
        method="POST",
        headers=headers,
    )
    try:
        with request.urlopen(req, timeout=5) as response:
            if _telemetry_debug_logging_enabled():
                logger.info("telemetry.ok event=%s status=%s", event_name, getattr(response, "status", "unknown"))
            return True
    except Exception as exc:
        logger.warning("telemetry.fail event=%s error=%s", event_name, exc)
        return False


def send_base_telemetry(payload: Dict[str, Any]) -> bool:
    install_id = payload.get("install_id")
    if not install_id:
        return False
    event_name = payload.get("_event", "base_telemetry.heartbeat")
    props = {k: v for k, v in payload.items() if k != "_event"}
    return _send_otlp_event(event_name=event_name, identity=str(install_id), properties=props, detailed=False)


def send_base_first_seen() -> bool:
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
    payload = _build_base_telemetry_payload("heartbeat")
    payload["_event"] = "base_telemetry.heartbeat"
    return send_base_telemetry(payload)


def identify_user(user_id: Any, properties: Optional[Dict[str, Any]] = None) -> None:
    if not is_detailed_analytics_enabled():
        return
    _send_otlp_event("analytics.identify", str(user_id), properties or {}, detailed=True)


def send_analytics_event(user_id: Any, event_name: str, properties: Optional[Dict[str, Any]] = None) -> None:
    if not is_detailed_analytics_enabled():
        return
    from app.config.analytics_defaults import get_analytics_config
    from app.utils.installation import get_installation_config
    from app.utils.telemetry import get_telemetry_fingerprint

    config = get_analytics_config()
    enhanced = dict(properties or {})
    enhanced["install_id"] = get_installation_config().get_install_id()
    enhanced["telemetry_fingerprint"] = get_telemetry_fingerprint()
    enhanced["environment"] = os.getenv("FLASK_ENV", "production")
    enhanced["app_version"] = config.get("app_version")
    enhanced["deployment_method"] = "docker" if os.path.exists("/.dockerenv") else "native"

    try:
        from flask import request as flask_request

        if flask_request:
            enhanced["current_url"] = flask_request.url
            enhanced["host"] = flask_request.host
            enhanced["pathname"] = flask_request.path
            enhanced["browser"] = getattr(flask_request.user_agent, "browser", None)
            enhanced["device_type"] = (
                "mobile" if getattr(flask_request.user_agent, "platform", None) in ["android", "iphone"] else "desktop"
            )
            enhanced["os"] = getattr(flask_request.user_agent, "platform", None)
    except Exception:
        pass

    _send_otlp_event(event_name=event_name, identity=str(user_id), properties=enhanced, detailed=True)
