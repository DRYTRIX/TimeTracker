"""SaaS limits (seats/users) helpers."""

from __future__ import annotations

from flask import current_app

from app import db
from app.models import TenantBilling, TenantMember


def get_effective_seat_limit(tenant_id: int) -> int:
    """
    Return the maximum allowed users (seats) for a tenant.

    Defaults:
    - If no billing row exists, default to 1 seat (basic).
    - Basic always returns 1.
    - Team is clamped to max 5.
    - Pro has no max, but we treat seat_quantity as the purchased seat count (>=1).
    """
    billing = TenantBilling.query.filter_by(tenant_id=tenant_id).first()
    if not billing:
        return 1
    tier = (billing.tier or "basic").strip().lower()
    if tier == "basic":
        return 1
    seats = int(billing.seat_quantity or 1)
    seats = max(1, seats)
    if tier == "team":
        return min(5, seats)
    return seats


def can_add_member(tenant_id: int) -> bool:
    limit = get_effective_seat_limit(tenant_id)
    current_count = TenantMember.query.filter_by(tenant_id=tenant_id).count()
    return current_count < limit

