"""Helpers for storing external accounting system IDs on invoices/expenses."""

from typing import Any, Dict, Optional


def _ensure_dict(obj) -> Dict[str, Any]:
    if obj is None:
        return {}
    if isinstance(obj, dict):
        return dict(obj)
    return {}


def get_integration_ref(record, provider: str, key: str) -> Optional[str]:
    """Return a stored external ID for provider (e.g. quickbooks, xero)."""
    meta = _ensure_dict(getattr(record, "integration_metadata", None))
    provider_data = _ensure_dict(meta.get(provider))
    value = provider_data.get(key)
    return str(value) if value is not None else None


def set_integration_ref(record, provider: str, key: str, value: str) -> None:
    """Persist an external ID under integration_metadata[provider][key]."""
    meta = _ensure_dict(getattr(record, "integration_metadata", None))
    provider_data = _ensure_dict(meta.get(provider))
    provider_data[key] = value
    meta[provider] = provider_data
    record.integration_metadata = meta


def has_integration_ref(record, provider: str, key: str) -> bool:
    return bool(get_integration_ref(record, provider, key))
