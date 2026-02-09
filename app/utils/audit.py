"""
Audit logging utility for tracking changes to models using SQLAlchemy events.

This module provides automatic audit trail tracking for model changes.
It uses SQLAlchemy event listeners to capture create, update, and delete operations.
"""

from sqlalchemy import event
from sqlalchemy.orm import Session
from sqlalchemy.inspection import inspect
from sqlalchemy import inspect as sqlalchemy_inspect
from flask import request, has_request_context
from flask_login import current_user
from app import db
import logging

logger = logging.getLogger(__name__)


# Lazy import to avoid circular dependencies
def get_audit_log_model():
    """Get AuditLog model with lazy import"""
    from app.models.audit_log import AuditLog

    return AuditLog


# Cache to track if audit_logs table exists
_audit_table_exists = None

# Models that should be tracked for audit logging
TRACKED_MODELS = [
    "Project",
    "Task",
    "TimeEntry",
    "Invoice",
    "InvoiceItem",
    "Client",
    "Deal",
    "User",
    "Expense",
    "Payment",
    "Settings",
    "Comment",
    "ProjectCost",
    "KanbanColumn",
    "TimeEntryTemplate",
    "ClientNote",
    "WeeklyTimeGoal",
    "CalendarEvent",
    "BudgetAlert",
    "ExtraGood",
    "Mileage",
    "PerDiem",
    "RateOverride",
    "SavedFilter",
    "InvoiceTemplate",
    "InvoicePDFTemplate",
    "ClientPrepaidConsumption",
]

# Fields to exclude from audit logging (internal/system fields)
EXCLUDED_FIELDS = {
    "id",
    "created_at",
    "updated_at",
    "password_hash",  # Never log passwords
    "password",  # Never log passwords
}


def get_current_user_id():
    """Get the current user ID, handling cases where user might not be authenticated"""
    try:
        if has_request_context() and current_user.is_authenticated:
            return current_user.id
    except Exception:
        pass
    return None


def get_request_info():
    """Get request information for audit logging"""
    if not has_request_context():
        return None, None, None

    ip_address = request.remote_addr
    user_agent = request.headers.get("User-Agent")
    request_path = request.path

    return ip_address, user_agent, request_path


def get_entity_name(instance):
    """Get a human-readable name for an entity instance"""
    # Try common name fields
    for field in ["name", "title", "username", "email", "invoice_number"]:
        if hasattr(instance, field):
            value = getattr(instance, field)
            if value:
                return str(value)

    # Fallback to string representation
    return str(instance)


def get_entity_type(instance):
    """Get the entity type name from an instance"""
    return instance.__class__.__name__


def should_track_model(instance):
    """Check if a model instance should be tracked"""
    return get_entity_type(instance) in TRACKED_MODELS


def should_track_field(field_name):
    """Check if a field should be tracked"""
    return field_name not in EXCLUDED_FIELDS


def serialize_value(value):
    """Serialize a value for storage in audit log"""
    if value is None:
        return None

    # Handle datetime objects
    from datetime import datetime

    if isinstance(value, datetime):
        return value.isoformat()

    # Handle Decimal
    from decimal import Decimal

    if isinstance(value, Decimal):
        return str(value)

    # Handle boolean
    if isinstance(value, bool):
        return value

    # Handle lists and dicts
    if isinstance(value, (list, dict)):
        import json

        try:
            return json.dumps(value)
        except (TypeError, ValueError):
            return str(value)

    # For everything else, convert to string
    return str(value)


def capture_timeentry_metadata(entry):
    """Capture TimeEntry metadata for audit logging
    
    Args:
        entry: TimeEntry instance
        
    Returns:
        dict with client_id, project_id, created_at, and related entity names
    """
    metadata = {
        "client_id": entry.client_id,
        "client_name": entry.client.name if entry.client else None,
        "project_id": entry.project_id,
        "project_name": entry.project.name if entry.project else None,
        "task_id": entry.task_id,
        "task_name": entry.task.name if entry.task else None,
        "created_at": entry.created_at.isoformat() if hasattr(entry, "created_at") and entry.created_at else None,
        "user_id": entry.user_id,
        "user_name": entry.user.username if entry.user else None,
    }
    return metadata


def capture_timeentry_state(entry):
    """Capture full TimeEntry state for audit logging
    
    Args:
        entry: TimeEntry instance
        
    Returns:
        dict with all TimeEntry fields and related entity information
    """
    state = {
        "id": entry.id if hasattr(entry, "id") else None,
        "user_id": entry.user_id,
        "project_id": entry.project_id,
        "client_id": entry.client_id,
        "task_id": entry.task_id,
        "start_time": entry.start_time.isoformat() if entry.start_time else None,
        "end_time": entry.end_time.isoformat() if entry.end_time else None,
        "duration_seconds": entry.duration_seconds,
        "notes": entry.notes,
        "tags": entry.tags,
        "source": entry.source,
        "billable": entry.billable,
        "paid": entry.paid,
        "invoice_number": entry.invoice_number,
        "created_at": entry.created_at.isoformat() if hasattr(entry, "created_at") and entry.created_at else None,
        "updated_at": entry.updated_at.isoformat() if hasattr(entry, "updated_at") and entry.updated_at else None,
        # Related entity names for context
        "project_name": entry.project.name if entry.project else None,
        "client_name": entry.client.name if entry.client else None,
        "task_name": entry.task.name if entry.task else None,
        "user_name": entry.user.username if entry.user else None,
    }
    return state


# Call count for table-exists check (force recheck every 100) and warning/debug logs
_audit_call_count = 0


def receive_before_flush(session, flush_context, instances=None):
    """Track updates and deletes before flush; stash new objects for receive_after_flush.

    At before_flush, session.dirty, session.deleted, and attribute history are still
    valid. session.new is present but new objects do not have ids yet, so we stash
    them in session.info to be logged in after_flush when ids are available.

    Note: SQLAlchemy's before_flush passes (session, flush_context, instances);
    we use session.new/dirty/deleted directly, so instances is not used.
    """
    global _audit_call_count
    try:
        if flush_context and getattr(flush_context, "nested", False):
            return

        _audit_call_count += 1
        force_check = _audit_call_count % 100 == 0
        table_exists = check_audit_table_exists(force_check=force_check)
        if not table_exists:
            if _audit_call_count == 1 or force_check:
                logger.warning("audit_logs table does not exist - audit logging disabled. Run migration: flask db upgrade")
            return

        user_id = get_current_user_id()
        ip_address, user_agent, request_path = get_request_info()

        # Track updates (dirty) - attribute history is still valid in before_flush
        for instance in session.dirty:
            if should_track_model(instance):
                entity_type = get_entity_type(instance)
                entity_id = instance.id if hasattr(instance, "id") else None
                entity_name = get_entity_name(instance)

                try:
                    # For TimeEntry, capture full old state before changes
                    full_old_state = None
                    entity_metadata = None
                    if entity_type == "TimeEntry":
                        try:
                            full_old_state = capture_timeentry_state(instance)
                            entity_metadata = capture_timeentry_metadata(instance)
                        except Exception as e:
                            logger.warning(f"Could not capture TimeEntry state for {entity_id}: {e}")

                    instance_state = inspect(instance)
                    changed_fields = []
                    for attr_name in instance_state.mapper.column_attrs.keys():
                        if should_track_field(attr_name):
                            history = instance_state.get_history(attr_name, True)
                            if history.has_changes():
                                old_value = history.deleted[0] if history.deleted else None
                                new_value = history.added[0] if history.added else None
                                if old_value != new_value:
                                    changed_fields.append({"field": attr_name, "old": old_value, "new": new_value})

                    AuditLog = get_audit_log_model()
                    if changed_fields:
                        for change in changed_fields:
                            AuditLog.log_change(
                                user_id=user_id,
                                action="updated",
                                entity_type=entity_type,
                                entity_id=entity_id,
                                field_name=change["field"],
                                old_value=serialize_value(change["old"]),
                                new_value=serialize_value(change["new"]),
                                entity_name=entity_name,
                                change_description=f"Updated {entity_type.lower()} '{entity_name}': {change['field']}",
                                entity_metadata=entity_metadata,
                                full_old_state=full_old_state,
                                ip_address=ip_address,
                                user_agent=user_agent,
                                request_path=request_path,
                            )
                    else:
                        AuditLog.log_change(
                            user_id=user_id,
                            action="updated",
                            entity_type=entity_type,
                            entity_id=entity_id,
                            entity_name=entity_name,
                            change_description=f"Updated {entity_type.lower()} '{entity_name}'",
                            entity_metadata=entity_metadata,
                            full_old_state=full_old_state,
                            ip_address=ip_address,
                            user_agent=user_agent,
                            request_path=request_path,
                        )
                except Exception as e:
                    logger.warning(f"Could not inspect changes for {entity_type}#{entity_id}: {e}")
                    AuditLog = get_audit_log_model()
                    AuditLog.log_change(
                        user_id=user_id,
                        action="updated",
                        entity_type=entity_type,
                        entity_id=entity_id,
                        entity_name=entity_name,
                        change_description=f"Updated {entity_type.lower()} '{entity_name}'",
                        ip_address=ip_address,
                        user_agent=user_agent,
                        request_path=request_path,
                    )

        # Track deletes
        for instance in session.deleted:
            if should_track_model(instance):
                entity_type = get_entity_type(instance)
                entity_id = instance.id if hasattr(instance, "id") else None
                entity_name = get_entity_name(instance)
                try:
                    # For TimeEntry, capture full state and metadata before deletion
                    full_old_state = None
                    entity_metadata = None
                    if entity_type == "TimeEntry":
                        try:
                            full_old_state = capture_timeentry_state(instance)
                            entity_metadata = capture_timeentry_metadata(instance)
                        except Exception as e:
                            logger.warning(f"Could not capture TimeEntry state for deletion of {entity_id}: {e}")
                    
                    AuditLog = get_audit_log_model()
                    AuditLog.log_change(
                        user_id=user_id,
                        action="deleted",
                        entity_type=entity_type,
                        entity_id=entity_id,
                        entity_name=entity_name,
                        change_description=f"Deleted {entity_type.lower()} '{entity_name}'",
                        entity_metadata=entity_metadata,
                        full_old_state=full_old_state,
                        ip_address=ip_address,
                        user_agent=user_agent,
                        request_path=request_path,
                    )
                except Exception as log_error:
                    logger.error(f"Failed to log audit entry for deletion of {entity_type}#{entity_id}: {log_error}", exc_info=True)

        # Stash new (creates) for after_flush when instance.id is available
        info = getattr(session, "info", None)
        if info is not None:
            info["_audit_pending_creates"] = [o for o in session.new if should_track_model(o)]

    except Exception as e:
        logger.error(f"Error in audit logging (before_flush): {e}", exc_info=True)


def receive_after_flush(session, flush_context):
    """Log creates from stashed new objects (now with ids) and flush audit rows."""
    try:
        if flush_context and getattr(flush_context, "nested", False):
            return

        table_exists = check_audit_table_exists(force_check=False)
        if not table_exists:
            return

        user_id = get_current_user_id()
        ip_address, user_agent, request_path = get_request_info()

        info = getattr(session, "info", None)
        pending = info.pop("_audit_pending_creates", []) if info is not None else []

        for instance in pending:
            entity_type = get_entity_type(instance)
            entity_id = getattr(instance, "id", None)
            if entity_id is None:
                continue
            entity_name = get_entity_name(instance)
            
            # For TimeEntry, capture full state and metadata
            full_new_state = None
            entity_metadata = None
            if entity_type == "TimeEntry":
                try:
                    full_new_state = capture_timeentry_state(instance)
                    entity_metadata = capture_timeentry_metadata(instance)
                except Exception as e:
                    logger.warning(f"Could not capture TimeEntry state for creation of {entity_id}: {e}")
            
            AuditLog = get_audit_log_model()
            AuditLog.log_change(
                user_id=user_id,
                action="created",
                entity_type=entity_type,
                entity_id=entity_id,
                entity_name=entity_name,
                change_description=f"Created {entity_type.lower()} '{entity_name}'",
                entity_metadata=entity_metadata,
                full_new_state=full_new_state,
                ip_address=ip_address,
                user_agent=user_agent,
                request_path=request_path,
            )

    except Exception as e:
        logger.error(f"Error in audit logging (after_flush): {e}", exc_info=True)


def check_audit_table_exists(force_check=False):
    """Check if the audit_logs table exists

    Args:
        force_check: If True, force a fresh check even if cached
    """
    global _audit_table_exists

    # Return cached value if available and not forcing a check
    if not force_check and _audit_table_exists is not None:
        return _audit_table_exists

    try:
        # Try to check if the table exists
        inspector = sqlalchemy_inspect(db.engine)
        tables = inspector.get_table_names()
        exists = "audit_logs" in tables
        _audit_table_exists = exists

        if not exists:
            logger.debug("audit_logs table does not exist - audit logging disabled")
        else:
            logger.debug("audit_logs table exists - audit logging enabled")

        return exists
    except Exception as e:
        # If we can't check, log it and assume it doesn't exist to be safe
        logger.debug(f"Could not check if audit_logs table exists: {e}")
        # Don't cache the error - allow retry on next call
        if force_check:
            _audit_table_exists = False
        return False


def reset_audit_table_cache():
    """Reset the audit table existence cache - useful after migrations"""
    global _audit_table_exists
    _audit_table_exists = None


def track_model_changes(model_class):
    """Decorator/function to enable audit tracking for a model class"""
    # The event listener above handles all models, but this can be used
    # to explicitly register a model if needed
    if model_class.__name__ not in TRACKED_MODELS:
        TRACKED_MODELS.append(model_class.__name__)
    return model_class
