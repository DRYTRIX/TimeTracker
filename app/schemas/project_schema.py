"""
Schemas for project serialization and validation.
"""

from marshmallow import Schema, fields, validate
from decimal import Decimal
from app.constants import ProjectStatus


class ProjectSchema(Schema):
    """Schema for project serialization"""

    id = fields.Int(dump_only=True)
    name = fields.Str(required=True, validate=validate.Length(max=200))
    client_id = fields.Int(required=True)
    quote_id = fields.Int(allow_none=True)
    description = fields.Str(allow_none=True)
    billable = fields.Bool(missing=True)
    hourly_rate = fields.Decimal(allow_none=True, places=2)
    billing_ref = fields.Str(allow_none=True, validate=validate.Length(max=100))
    code = fields.Str(allow_none=True, validate=validate.Length(max=20))
    status = fields.Str(validate=validate.OneOf([s.value for s in ProjectStatus]))
    estimated_hours = fields.Float(allow_none=True)
    budget_amount = fields.Decimal(allow_none=True, places=2)
    budget_threshold_percent = fields.Int(missing=80)
    created_at = fields.DateTime(dump_only=True)
    updated_at = fields.DateTime(dump_only=True)
    archived_at = fields.DateTime(dump_only=True, allow_none=True)
    archived_by = fields.Int(dump_only=True, allow_none=True)
    archived_reason = fields.Str(dump_only=True, allow_none=True)

    # Nested fields
    client = fields.Nested("ClientSchema", dump_only=True, allow_none=True)
    time_entries = fields.Nested("TimeEntrySchema", many=True, dump_only=True, allow_none=True)


class ProjectCreateSchema(Schema):
    """Schema for creating a project"""

    name = fields.Str(required=True, validate=validate.Length(min=1, max=200))
    client_id = fields.Int(required=True)
    description = fields.Str(allow_none=True)
    billable = fields.Bool(missing=True)
    hourly_rate = fields.Decimal(allow_none=True, places=2)
    billing_ref = fields.Str(allow_none=True, validate=validate.Length(max=100))
    code = fields.Str(allow_none=True, validate=validate.Length(max=20))
    estimated_hours = fields.Float(allow_none=True)
    budget_amount = fields.Decimal(allow_none=True, places=2)
    budget_threshold_percent = fields.Int(missing=80, validate=validate.Range(min=0, max=100))


class ProjectUpdateSchema(Schema):
    """Schema for updating a project"""

    name = fields.Str(allow_none=True, validate=validate.Length(min=1, max=200))
    client_id = fields.Int(allow_none=True)
    description = fields.Str(allow_none=True)
    billable = fields.Bool(allow_none=True)
    hourly_rate = fields.Decimal(allow_none=True, places=2)
    billing_ref = fields.Str(allow_none=True, validate=validate.Length(max=100))
    code = fields.Str(allow_none=True, validate=validate.Length(max=20))
    status = fields.Str(allow_none=True, validate=validate.OneOf([s.value for s in ProjectStatus]))
    estimated_hours = fields.Float(allow_none=True)
    budget_amount = fields.Decimal(allow_none=True, places=2)
    budget_threshold_percent = fields.Int(allow_none=True, validate=validate.Range(min=0, max=100))
