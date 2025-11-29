"""
Schemas for time entry serialization and validation.
"""

from marshmallow import Schema, fields, validate, validates, ValidationError
from datetime import datetime
from app.constants import TimeEntrySource


class TimeEntrySchema(Schema):
    """Schema for time entry serialization"""

    id = fields.Int(dump_only=True)
    user_id = fields.Int(required=True)
    project_id = fields.Int(allow_none=True)
    client_id = fields.Int(allow_none=True)
    task_id = fields.Int(allow_none=True)
    start_time = fields.DateTime(required=True)
    end_time = fields.DateTime(allow_none=True)
    duration_seconds = fields.Int(allow_none=True)
    notes = fields.Str(allow_none=True)
    tags = fields.Str(allow_none=True)
    source = fields.Str(validate=validate.OneOf([s.value for s in TimeEntrySource]))
    billable = fields.Bool(missing=True)
    created_at = fields.DateTime(dump_only=True)
    updated_at = fields.DateTime(dump_only=True)

    # Nested fields (when relations are loaded)
    project = fields.Nested("ProjectSchema", dump_only=True, allow_none=True)
    client = fields.Nested("ClientSchema", dump_only=True, allow_none=True)
    user = fields.Nested("UserSchema", dump_only=True, allow_none=True)
    task = fields.Nested("TaskSchema", dump_only=True, allow_none=True)


class TimeEntryCreateSchema(Schema):
    """Schema for creating a time entry"""

    project_id = fields.Int(allow_none=True)
    client_id = fields.Int(allow_none=True)
    task_id = fields.Int(allow_none=True)
    start_time = fields.DateTime(required=True)
    end_time = fields.DateTime(allow_none=True)
    notes = fields.Str(allow_none=True, validate=validate.Length(max=5000))
    tags = fields.Str(allow_none=True, validate=validate.Length(max=500))
    billable = fields.Bool(missing=True)

    @validates("end_time")
    def validate_end_time(self, value, **kwargs):
        """Validate that end_time is after start_time"""
        data = kwargs.get("data", {})
        start_time = data.get("start_time")
        if start_time and value and value <= start_time:
            raise ValidationError("end_time must be after start_time")

    @validates("project_id")
    def validate_project_or_client(self, value, **kwargs):
        """Validate that either project_id or client_id is provided"""
        data = kwargs.get("data", {})
        client_id = data.get("client_id")
        if not value and not client_id:
            raise ValidationError("Either project_id or client_id must be provided")

    @validates("client_id")
    def validate_client_or_project(self, value, **kwargs):
        """Validate that either project_id or client_id is provided"""
        data = kwargs.get("data", {})
        project_id = data.get("project_id")
        if not value and not project_id:
            raise ValidationError("Either project_id or client_id must be provided")

    @validates("task_id")
    def validate_task_with_project(self, value, **kwargs):
        """Validate that task_id is only provided when project_id is set"""
        data = kwargs.get("data", {})
        project_id = data.get("project_id")
        if value and not project_id:
            raise ValidationError("task_id can only be set when project_id is provided")


class TimeEntryUpdateSchema(Schema):
    """Schema for updating a time entry"""

    project_id = fields.Int(allow_none=True)
    client_id = fields.Int(allow_none=True)
    task_id = fields.Int(allow_none=True)
    start_time = fields.DateTime(allow_none=True)
    end_time = fields.DateTime(allow_none=True)
    notes = fields.Str(allow_none=True, validate=validate.Length(max=5000))
    tags = fields.Str(allow_none=True, validate=validate.Length(max=500))
    billable = fields.Bool(allow_none=True)


class TimerStartSchema(Schema):
    """Schema for starting a timer"""

    project_id = fields.Int(required=True)  # Timers are project-only for now
    task_id = fields.Int(allow_none=True)
    notes = fields.Str(allow_none=True, validate=validate.Length(max=5000))
    template_id = fields.Int(allow_none=True)


class TimerStopSchema(Schema):
    """Schema for stopping a timer"""

    entry_id = fields.Int(allow_none=True)  # Optional, will use active timer if not provided
