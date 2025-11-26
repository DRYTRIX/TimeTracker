"""
Schemas for user serialization and validation.
"""

from marshmallow import Schema, fields, validate
from app.constants import UserRole


class UserSchema(Schema):
    """Schema for user serialization"""
    id = fields.Int(dump_only=True)
    username = fields.Str(required=True, validate=validate.Length(max=100))
    email = fields.Email(allow_none=True)
    full_name = fields.Str(allow_none=True, validate=validate.Length(max=200))
    role = fields.Str(validate=validate.OneOf([r.value for r in UserRole]))
    is_active = fields.Bool(missing=True)
    preferred_language = fields.Str(allow_none=True)
    created_at = fields.DateTime(dump_only=True)
    updated_at = fields.DateTime(dump_only=True)
    
    # Nested fields (when relations are loaded)
    favorite_projects = fields.Nested('ProjectSchema', many=True, dump_only=True, allow_none=True)


class UserCreateSchema(Schema):
    """Schema for creating a user"""
    username = fields.Str(required=True, validate=validate.Length(min=1, max=100))
    email = fields.Email(allow_none=True)
    full_name = fields.Str(allow_none=True, validate=validate.Length(max=200))
    role = fields.Str(missing=UserRole.USER.value, validate=validate.OneOf([r.value for r in UserRole]))
    is_active = fields.Bool(missing=True)
    preferred_language = fields.Str(allow_none=True)


class UserUpdateSchema(Schema):
    """Schema for updating a user"""
    username = fields.Str(allow_none=True, validate=validate.Length(min=1, max=100))
    email = fields.Email(allow_none=True)
    full_name = fields.Str(allow_none=True, validate=validate.Length(max=200))
    role = fields.Str(allow_none=True, validate=validate.OneOf([r.value for r in UserRole]))
    is_active = fields.Bool(allow_none=True)
    preferred_language = fields.Str(allow_none=True)

