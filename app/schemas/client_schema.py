"""
Schemas for client serialization and validation.
"""

from marshmallow import Schema, fields, validate
from decimal import Decimal


class ClientSchema(Schema):
    """Schema for client serialization"""
    id = fields.Int(dump_only=True)
    name = fields.Str(required=True, validate=validate.Length(max=200))
    email = fields.Email(allow_none=True)
    company = fields.Str(allow_none=True, validate=validate.Length(max=200))
    phone = fields.Str(allow_none=True, validate=validate.Length(max=50))
    address = fields.Str(allow_none=True)
    default_hourly_rate = fields.Decimal(allow_none=True, places=2)
    status = fields.Str(validate=validate.OneOf(['active', 'inactive', 'archived']))
    created_at = fields.DateTime(dump_only=True)
    updated_at = fields.DateTime(dump_only=True)
    
    # Nested fields
    projects = fields.Nested('ProjectSchema', many=True, dump_only=True, allow_none=True)


class ClientCreateSchema(Schema):
    """Schema for creating a client"""
    name = fields.Str(required=True, validate=validate.Length(min=1, max=200))
    email = fields.Email(allow_none=True)
    company = fields.Str(allow_none=True, validate=validate.Length(max=200))
    phone = fields.Str(allow_none=True, validate=validate.Length(max=50))
    address = fields.Str(allow_none=True)
    default_hourly_rate = fields.Decimal(allow_none=True, places=2, validate=validate.Range(min=Decimal('0')))


class ClientUpdateSchema(Schema):
    """Schema for updating a client"""
    name = fields.Str(allow_none=True, validate=validate.Length(min=1, max=200))
    email = fields.Email(allow_none=True)
    company = fields.Str(allow_none=True, validate=validate.Length(max=200))
    phone = fields.Str(allow_none=True, validate=validate.Length(max=50))
    address = fields.Str(allow_none=True)
    default_hourly_rate = fields.Decimal(allow_none=True, places=2, validate=validate.Range(min=Decimal('0')))
    status = fields.Str(allow_none=True, validate=validate.OneOf(['active', 'inactive', 'archived']))

