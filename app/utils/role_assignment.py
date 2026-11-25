"""Helpers that cap which roles a caller may grant to other users."""

from __future__ import annotations

from typing import Optional, Tuple

# Roles that imply full administrative control. Only super_admins may grant these.
_ADMIN_TIER_ROLES = frozenset({"admin", "super_admin"})


def user_can_assign_role(actor, role_name: Optional[str]) -> Tuple[bool, str]:
    """Return (allowed, error_message) for assigning ``role_name`` to another user.

    Only ``super_admin`` may grant ``admin`` or ``super_admin``. Empty names rejected.
    """
    name = (role_name or "").strip()
    if not name:
        return False, "A role is required"

    if name in _ADMIN_TIER_ROLES and not bool(getattr(actor, "is_super_admin", False)):
        return False, f"Only Super Admins can assign the {name} role"

    return True, ""


def user_can_reset_password_for(actor, target) -> Tuple[bool, str]:
    """Block privilege escalation via password reset of higher-privilege accounts."""
    if not target:
        return False, "User not found"

    if bool(getattr(target, "is_super_admin", False)) and not bool(getattr(actor, "is_super_admin", False)):
        return False, "Only Super Admins can reset a Super Admin password"

    # Managers (edit_users without is_admin) must not reset admin passwords
    if bool(getattr(target, "is_admin", False)) and not bool(getattr(actor, "is_admin", False)):
        return False, "Only admins can reset an admin password"

    return True, ""


def filter_assignable_roles(actor, roles):
    """Filter a Role query/list to those the actor may assign."""
    if bool(getattr(actor, "is_super_admin", False)):
        return list(roles)
    return [r for r in roles if getattr(r, "name", None) not in _ADMIN_TIER_ROLES]
