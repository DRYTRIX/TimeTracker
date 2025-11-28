"""
Schemas for comment serialization and validation.
"""

from marshmallow import Schema, fields, validate


class CommentSchema(Schema):
    """Schema for comment serialization"""

    id = fields.Int(dump_only=True)
    content = fields.Str(required=True, validate=validate.Length(min=1, max=5000))
    project_id = fields.Int(allow_none=True)
    task_id = fields.Int(allow_none=True)
    quote_id = fields.Int(allow_none=True)
    user_id = fields.Int(required=True)
    is_internal = fields.Bool(missing=True)
    parent_id = fields.Int(allow_none=True)
    created_at = fields.DateTime(dump_only=True)
    updated_at = fields.DateTime(dump_only=True)

    # Nested fields
    author = fields.Nested("UserSchema", dump_only=True, allow_none=True)
    project = fields.Nested("ProjectSchema", dump_only=True, allow_none=True)
    task = fields.Nested("TaskSchema", dump_only=True, allow_none=True)
    replies = fields.Nested("CommentSchema", many=True, dump_only=True, allow_none=True)


class CommentCreateSchema(Schema):
    """Schema for creating a comment"""

    content = fields.Str(required=True, validate=validate.Length(min=1, max=5000))
    project_id = fields.Int(allow_none=True)
    task_id = fields.Int(allow_none=True)
    quote_id = fields.Int(allow_none=True)
    parent_id = fields.Int(allow_none=True)
    is_internal = fields.Bool(missing=True)


class CommentUpdateSchema(Schema):
    """Schema for updating a comment"""

    content = fields.Str(allow_none=True, validate=validate.Length(min=1, max=5000))
    is_internal = fields.Bool(allow_none=True)
