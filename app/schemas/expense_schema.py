"""
Schemas for expense serialization and validation.
"""

from marshmallow import Schema, fields, validate
from decimal import Decimal


class ExpenseSchema(Schema):
    """Schema for expense serialization"""
    id = fields.Int(dump_only=True)
    project_id = fields.Int(required=True)
    amount = fields.Decimal(required=True, places=2)
    description = fields.Str(required=True, validate=validate.Length(max=500))
    date = fields.Date(required=True)
    category_id = fields.Int(allow_none=True)
    billable = fields.Bool(missing=False)
    receipt_path = fields.Str(allow_none=True)
    created_by = fields.Int(required=True)
    created_at = fields.DateTime(dump_only=True)
    updated_at = fields.DateTime(dump_only=True)
    
    # Nested fields
    project = fields.Nested('ProjectSchema', dump_only=True, allow_none=True)
    category = fields.Nested('ExpenseCategorySchema', dump_only=True, allow_none=True)


class ExpenseCreateSchema(Schema):
    """Schema for creating an expense"""
    project_id = fields.Int(required=True)
    amount = fields.Decimal(required=True, places=2, validate=validate.Range(min=Decimal('0.01')))
    description = fields.Str(required=True, validate=validate.Length(min=1, max=500))
    date = fields.Date(required=True)
    category_id = fields.Int(allow_none=True)
    billable = fields.Bool(missing=False)
    receipt_path = fields.Str(allow_none=True)


class ExpenseUpdateSchema(Schema):
    """Schema for updating an expense"""
    project_id = fields.Int(allow_none=True)
    amount = fields.Decimal(allow_none=True, places=2, validate=validate.Range(min=Decimal('0.01')))
    description = fields.Str(allow_none=True, validate=validate.Length(max=500))
    date = fields.Date(allow_none=True)
    category_id = fields.Int(allow_none=True)
    billable = fields.Bool(allow_none=True)
    receipt_path = fields.Str(allow_none=True)

