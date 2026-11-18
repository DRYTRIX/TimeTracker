"""Non-translated support/checkout configuration (URLs, numeric defaults)."""

from __future__ import annotations

import os
from typing import Any, Dict, Optional
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit


def get_support_portal_base(config: Dict[str, Any] | Any) -> str:
    """Marketing site base; defaults to drytrix TimeTracker domain."""
    if hasattr(config, "get"):
        raw = (config.get("SUPPORT_PORTAL_BASE") or "").strip()
    else:
        raw = ""
    if not raw:
        raw = os.getenv("SUPPORT_PORTAL_BASE", "https://timetracker.drytrix.com").strip()
    return raw.rstrip("/")


def append_query_params(url: str, params: Dict[str, str]) -> str:
    """Merge query params into *url* (existing keys are overwritten). Empty values skipped."""
    if not url or not params:
        return url
    parts = urlsplit(url)
    query = dict(parse_qsl(parts.query, keep_blank_values=True))
    for key, value in params.items():
        if value is None:
            continue
        text = str(value).strip()
        if text:
            query[key] = text
    return urlunsplit((parts.scheme, parts.netloc, parts.path, urlencode(query), parts.fragment))


def build_support_purchase_url(config: Dict[str, Any] | Any, system_id: Optional[str] = None) -> str:
    """Return the Supporter key checkout URL, optionally prefilling system_id."""
    if hasattr(config, "get"):
        purchase = (config.get("SUPPORT_PURCHASE_URL") or "").strip()
    else:
        purchase = ""
    if not purchase:
        purchase = os.getenv("SUPPORT_PURCHASE_URL", "https://timetracker.drytrix.com/support").strip()
    return append_query_params(purchase, {"system_id": (system_id or "").strip()})


_DEFAULT_BMC = "https://buymeacoffee.com/DryTrix"
_DEFAULT_TIP_URLS = {
    "eur5": f"{_DEFAULT_BMC}?utm_source=timetracker&utm_medium=support_modal&utm_campaign=tip_eur5",
    "eur10": f"{_DEFAULT_BMC}?utm_source=timetracker&utm_medium=support_modal&utm_campaign=tip_eur10",
    "eur25": f"{_DEFAULT_BMC}?utm_source=timetracker&utm_medium=support_modal&utm_campaign=tip_eur25",
}


def build_support_checkout_urls(config: Dict[str, Any] | Any, system_id: Optional[str] = None) -> Dict[str, str]:
    """
    Per-tier outbound URLs.

    Tip tiers (eur5/10/25) default to Buy Me a Coffee — never to the license checkout page.
    The license/key URL includes system_id when provided so the marketing site can autofill.
    """
    if hasattr(config, "get"):
        purchase = (config.get("SUPPORT_PURCHASE_URL") or "").strip()
    else:
        purchase = ""
    if not purchase:
        purchase = os.getenv("SUPPORT_PURCHASE_URL", "https://timetracker.drytrix.com/support").strip()

    def _tip(env_name: str, fallback: str) -> str:
        v = os.getenv(env_name, "").strip()
        return v or fallback

    license_url = append_query_params(purchase, {"system_id": (system_id or "").strip()})

    return {
        "eur5": _tip("SUPPORT_DONATE_EUR5_URL", _DEFAULT_TIP_URLS["eur5"]),
        "eur10": _tip("SUPPORT_DONATE_EUR10_URL", _DEFAULT_TIP_URLS["eur10"]),
        "eur25": _tip("SUPPORT_DONATE_EUR25_URL", _DEFAULT_TIP_URLS["eur25"]),
        "bmc": f"{_DEFAULT_BMC}?utm_source=timetracker&utm_medium=support_modal&utm_campaign=support",
        "license": license_url,
    }


def get_long_session_minutes() -> int:
    try:
        return max(30, int(os.getenv("SUPPORT_LONG_SESSION_MINUTES", "120")))
    except ValueError:
        return 120


def get_social_proof_text(config: Dict[str, Any] | Any) -> str:
    if hasattr(config, "get"):
        t = (config.get("SUPPORT_SOCIAL_PROOF_TEXT") or "").strip()
    else:
        t = ""
    if not t:
        t = os.getenv("SUPPORT_SOCIAL_PROOF_TEXT", "").strip()
    return t
