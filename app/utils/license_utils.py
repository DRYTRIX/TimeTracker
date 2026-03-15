"""
Optional support/license visibility helpers.

Instance-level "license activated" state is represented by Settings.donate_ui_hidden
(set when a user verifies the donate-hide / license key). This is non-blocking
monetization awareness only—no paywall or feature gating.
"""


def is_license_activated(settings) -> bool:
    """Return True if this instance has an active license (donate/support UI hidden)."""
    return bool(getattr(settings, "donate_ui_hidden", False))
