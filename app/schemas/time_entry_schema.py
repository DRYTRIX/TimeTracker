"""
Schemas for time entry serialization and validation.
"""

from datetime import datetime

from marshmallow import Schema, ValidationError, fields, validate, validates_schema

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
    break_seconds = fields.Int(allow_none=True)
    notes = fields.Str(allow_none=True)
    tags = fields.Str(allow_none=True)
    source = fields.Str(validate=validate.OneOf([s.value for s in TimeEntrySource]))
    billable = fields.Bool(load_default=True)
    paid = fields.Bool(load_default=False)
    invoice_number = fields.Str(allow_none=True, validate=validate.Length(max=100))
    custom_fields = fields.Dict(keys=fields.Str(), values=fields.Raw(), allow_none=True)
    created_at = fields.DateTime(dump_only=True)
    updated_at = fields.DateTime(dump_only=True)

    # Nested fields (when relations are loaded)
    project = fields.Nested("ProjectSchema", dump_only=True, allow_none=True)
    client = fields.Nested("ClientSchema", dump_only=True, allow_none=True)
    user = fields.Nested("UserSchema", dump_only=True, allow_none=True)
    task = fields.Nested("TaskSchema", dump_only=True, allow_none=True)


class TimeEntryCreateSchema(Schema):
    """Schema for creating a time entry"""

    user_id = fields.Int(allow_none=True)  # Admin-only: create on behalf of another user
    project_id = fields.Int(allow_none=True)
    client_id = fields.Int(allow_none=True)
    task_id = fields.Int(allow_none=True)
    start_time = fields.DateTime(required=True)
    end_time = fields.DateTime(allow_none=True)
    break_seconds = fields.Int(allow_none=True)
    notes = fields.Str(allow_none=True, validate=validate.Length(max=5000))
    tags = fields.Str(allow_none=True, validate=validate.Length(max=500))
    billable = fields.Bool(load_default=True)
    paid = fields.Bool(load_default=False)
    invoice_number = fields.Str(allow_none=True, validate=validate.Length(max=100))
    custom_fields = fields.Dict(keys=fields.Str(), values=fields.Raw(), allow_none=True)

    @validates_schema
    def validate_relations_and_times(self, data, **kwargs):
        """Cross-field rules: project or client, task only with project, end after start.

        Schema-level on purpose (same as TimerStartSchema): field-level @validates hooks only get
        data_key in marshmallow 4, never the other fields, so these rules cannot live there.
        """
        project_id = data.get("project_id")
        client_id = data.get("client_id")
        errors = {}
        if not project_id and not client_id:
            errors["project_id"] = ["Either project_id or client_id must be provided"]
        if data.get("task_id") and not project_id:
            errors["task_id"] = ["task_id can only be set when project_id is provided"]
        start_time = data.get("start_time")
        end_time = data.get("end_time")
        same_kind = start_time and end_time and (start_time.tzinfo is None) == (end_time.tzinfo is None)
        if same_kind and end_time <= start_time:
            errors["end_time"] = ["end_time must be after start_time"]
        if errors:
            raise ValidationError(errors)


class TimeEntryUpdateSchema(Schema):
    """Schema for updating a time entry"""

    if_updated_at = fields.DateTime(
        allow_none=True,
        metadata={"description": "Last known updated_at for optimistic locking (ISO 8601)."},
    )
    project_id = fields.Int(allow_none=True)
    client_id = fields.Int(allow_none=True)
    task_id = fields.Int(allow_none=True)
    start_time = fields.DateTime(allow_none=True)
    end_time = fields.DateTime(allow_none=True)
    break_seconds = fields.Int(allow_none=True)
    notes = fields.Str(allow_none=True, validate=validate.Length(max=5000))
    tags = fields.Str(allow_none=True, validate=validate.Length(max=500))
    billable = fields.Bool(allow_none=True)
    paid = fields.Bool(allow_none=True)
    invoice_number = fields.Str(allow_none=True, validate=validate.Length(max=100))
    custom_fields = fields.Dict(keys=fields.Str(), values=fields.Raw(), allow_none=True)


class TimerStartSchema(Schema):
    """Schema for starting a timer (project or client; at least one required)."""

    project_id = fields.Int(allow_none=True)
    client_id = fields.Int(allow_none=True)
    task_id = fields.Int(allow_none=True)
    notes = fields.Str(allow_none=True, validate=validate.Length(max=5000))
    template_id = fields.Int(allow_none=True)

    @validates_schema
    def validate_project_or_client(self, data, **kwargs):
        if not data.get("project_id") and not data.get("client_id"):
            raise ValidationError("Either project_id or client_id must be provided")
        if data.get("task_id") and not data.get("project_id"):
            raise ValidationError({"task_id": ["task_id can only be set when project_id is provided"]})


class TimerStopSchema(Schema):
    """Schema for stopping a timer"""

    entry_id = fields.Int(allow_none=True)  # Optional, will use active timer if not provided
