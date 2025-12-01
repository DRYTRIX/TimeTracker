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


def receive_after_flush(session, flush_context):
    """Track changes after flush but before commit"""
    try:
        # Check if audit_logs table exists before trying to log
        # Force check every 100 calls to allow for table creation after migration
        if not hasattr(receive_after_flush, "_call_count"):
            receive_after_flush._call_count = 0
        receive_after_flush._call_count += 1

        # Force check every 100 calls or if cache is None
        force_check = receive_after_flush._call_count % 100 == 0
        table_exists = check_audit_table_exists(force_check=force_check)
        if not table_exists:
            # Log at info level (not debug) so it's visible if table doesn't exist
            if receive_after_flush._call_count == 1 or force_check:
                logger.warning("audit_logs table does not exist - audit logging disabled. Run migration: flask db upgrade")
            return
        
        # Log that the event listener is being triggered (only first few times for debugging)
        if receive_after_flush._call_count <= 3:
            logger.debug(f"Audit logging event listener triggered (call #{receive_after_flush._call_count})")

        user_id = get_current_user_id()
        ip_address, user_agent, request_path = get_request_info()

        # Track inserts (creates)
        for instance in session.new:
            if should_track_model(instance):
                entity_type = get_entity_type(instance)
                entity_id = instance.id if hasattr(instance, "id") else None
                entity_name = get_entity_name(instance)

                # Log creation
                AuditLog = get_audit_log_model()
                AuditLog.log_change(
                    user_id=user_id,
                    action="created",
                    entity_type=entity_type,
                    entity_id=entity_id,
                    entity_name=entity_name,
                    change_description=f"Created {entity_type.lower()} '{entity_name}'",
                    ip_address=ip_address,
                    user_agent=user_agent,
                    request_path=request_path,
                )

        # Track updates
        for instance in session.dirty:
            if should_track_model(instance):
                entity_type = get_entity_type(instance)
                entity_id = instance.id if hasattr(instance, "id") else None
                entity_name = get_entity_name(instance)

                # Get the instance state using SQLAlchemy inspect
                try:
                    instance_state = inspect(instance)

                    # Track individual field changes
                    changed_fields = []
                    for attr_name in instance_state.mapper.column_attrs.keys():
                        if should_track_field(attr_name):
                            # Get history for this attribute
                            history = instance_state.get_history(attr_name, True)
                            if history.has_changes():
                                old_value = history.deleted[0] if history.deleted else None
                                new_value = history.added[0] if history.added else None

                                if old_value != new_value:
                                    changed_fields.append({"field": attr_name, "old": old_value, "new": new_value})

                    # Log each field change separately for detailed audit trail
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
                                ip_address=ip_address,
                                user_agent=user_agent,
                                request_path=request_path,
                            )
                    else:
                        # Fallback: log update without field details if history is not available
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
                except Exception as e:
                    # Fallback: log update without field details if inspection fails
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

                # Log deletion
                try:
                    AuditLog = get_audit_log_model()
                    AuditLog.log_change(
                        user_id=user_id,
                        action="deleted",
                        entity_type=entity_type,
                        entity_id=entity_id,
                        entity_name=entity_name,
                        change_description=f"Deleted {entity_type.lower()} '{entity_name}'",
                        ip_address=ip_address,
                        user_agent=user_agent,
                        request_path=request_path,
                    )
                    logger.debug(f"Audit log: Deleted {entity_type}#{entity_id} by user#{user_id}")
                except Exception as log_error:
                    # Log the error but don't break the main flow
                    logger.error(f"Failed to log audit entry for deletion of {entity_type}#{entity_id}: {log_error}", exc_info=True)

    except Exception as e:
        # Don't let audit logging break the main flow
        logger.error(f"Error in audit logging: {e}", exc_info=True)


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
