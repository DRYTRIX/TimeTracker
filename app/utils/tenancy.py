"""
Tenancy helpers:
- Automatic tenant_id assignment on new objects (best-effort).
- Automatic tenant filtering for SELECTs using SQLAlchemy with_loader_criteria.

Goal: make multi-tenancy hard to bypass by accident.
"""

from __future__ import annotations

from typing import Iterable, Sequence, Type

from flask import has_request_context
from sqlalchemy import event
from sqlalchemy.orm import Session, with_loader_criteria


def _get_request_tenant_id() -> int | None:
    """Return current tenant id if in a request context, else None."""
    try:
        if not has_request_context():
            return None
        from flask import g

        tenant = getattr(g, "tenant", None)
        tenant_id = getattr(tenant, "id", None) if tenant is not None else None
        return int(tenant_id) if tenant_id is not None else None
    except Exception:
        return None


def register_tenancy_listeners(*, tenant_scoped_models: Sequence[Type]) -> None:
    """
    Register global SQLAlchemy session listeners.

    Args:
        tenant_scoped_models: ORM models that include a `tenant_id` column.
    """

    # Assign tenant_id on new objects (when not explicitly set)
    @event.listens_for(Session, "before_flush")
    def _set_tenant_id_before_flush(session: Session, flush_context, instances):
        tenant_id = _get_request_tenant_id()
        if not tenant_id:
            return

        try:
            for obj in list(session.new):
                # Only set tenant_id on models that are tenant-scoped and have the attribute.
                if obj.__class__ not in tenant_scoped_models:
                    continue
                if hasattr(obj, "tenant_id") and getattr(obj, "tenant_id", None) is None:
                    setattr(obj, "tenant_id", tenant_id)
        except Exception:
            # Best-effort; never block flush.
            pass

    # Filter SELECT queries by tenant_id automatically
    @event.listens_for(Session, "do_orm_execute")
    def _apply_tenant_filter(execute_state):
        if not execute_state.is_select:
            return

        tenant_id = _get_request_tenant_id()
        if not tenant_id:
            return

        stmt = execute_state.statement
        try:
            for model in tenant_scoped_models:
                stmt = stmt.options(
                    with_loader_criteria(
                        model,
                        lambda cls, tenant_id=tenant_id: cls.tenant_id == tenant_id,
                        include_aliases=True,
                    )
                )
            execute_state.statement = stmt
        except Exception:
            # Best-effort; never block query execution.
            pass

