"""
Schemas for task serialization and validation.
"""

from marshmallow import Schema, fields, validate
from app.constants import TaskStatus


class TaskSchema(Schema):
    """Schema for task serialization"""
    id = fields.Int(dump_only=True)
    name = fields.Str(required=True, validate=validate.Length(max=200))
    description = fields.Str(allow_none=True)
    project_id = fields.Int(required=True)
    assignee_id = fields.Int(allow_none=True)
    status = fields.Str(validate=validate.OneOf([s.value for s in TaskStatus]))
    priority = fields.Str(validate=validate.OneOf(['low', 'medium', 'high', 'urgent']))
    due_date = fields.Date(allow_none=True)
    created_by = fields.Int(required=True)
    created_at = fields.DateTime(dump_only=True)
    updated_at = fields.DateTime(dump_only=True)
    
    # Nested fields
    project = fields.Nested('ProjectSchema', dump_only=True, allow_none=True)
    assignee = fields.Nested('UserSchema', dump_only=True, allow_none=True)


class TaskCreateSchema(Schema):
    """Schema for creating a task"""
    name = fields.Str(required=True, validate=validate.Length(min=1, max=200))
    description = fields.Str(allow_none=True)
    project_id = fields.Int(required=True)
    assignee_id = fields.Int(allow_none=True)
    priority = fields.Str(missing='medium', validate=validate.OneOf(['low', 'medium', 'high', 'urgent']))
    due_date = fields.Date(allow_none=True)


class TaskUpdateSchema(Schema):
    """Schema for updating a task"""
    name = fields.Str(allow_none=True, validate=validate.Length(min=1, max=200))
    description = fields.Str(allow_none=True)
    assignee_id = fields.Int(allow_none=True)
    status = fields.Str(allow_none=True, validate=validate.OneOf([s.value for s in TaskStatus]))
    priority = fields.Str(allow_none=True, validate=validate.OneOf(['low', 'medium', 'high', 'urgent']))
    due_date = fields.Date(allow_none=True)

