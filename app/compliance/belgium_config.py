"""
Belgium compliance configuration — modular overrides for Royal Decree updates.

When the final Royal Decree is published, update `ROYAL_DECREE_DEFAULTS` or set
`Settings.compliance_royal_decree_config` JSON without code changes where possible.
"""

from __future__ import annotations

from typing import Any, Dict

ROYAL_DECREE_DEFAULTS: Dict[str, Any] = {
    "version": "pending-2026",
    "effective_date": "2027-01-01",
    "notes": (
        "Placeholder until Belgian implementing legislation is published. "
        "Core requirements follow CJEU C-55/18 and Loredas (2024)."
    ),
    "export_columns_extra": [],
    "sector_overrides": {},
}


def merged_belgium_config(settings) -> Dict[str, Any]:
    """Merge built-in defaults with admin JSON overrides from settings."""
    merged = dict(ROYAL_DECREE_DEFAULTS)
    override = getattr(settings, "compliance_royal_decree_config", None) or {}
    if isinstance(override, dict):
        merged.update(override)
    return merged
