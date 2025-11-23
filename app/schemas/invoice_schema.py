"""
Schemas for invoice serialization and validation.
"""

from marshmallow import Schema, fields, validate
from datetime import date
from app.constants import InvoiceStatus, PaymentStatus


class InvoiceItemSchema(Schema):
    """Schema for invoice item serialization"""
    id = fields.Int(dump_only=True)
    invoice_id = fields.Int(dump_only=True)
    description = fields.Str(required=True)
    quantity = fields.Decimal(required=True, places=2)
    unit_price = fields.Decimal(required=True, places=2)
    amount = fields.Decimal(required=True, places=2)


class InvoiceSchema(Schema):
    """Schema for invoice serialization"""
    id = fields.Int(dump_only=True)
    invoice_number = fields.Str(required=True)
    project_id = fields.Int(required=True)
    client_id = fields.Int(required=True)
    client_name = fields.Str(required=True)
    client_email = fields.Str(allow_none=True)
    client_address = fields.Str(allow_none=True)
    quote_id = fields.Int(allow_none=True)
    issue_date = fields.Date(required=True)
    due_date = fields.Date(required=True)
    status = fields.Str(validate=validate.OneOf([s.value for s in InvoiceStatus]))
    subtotal = fields.Decimal(required=True, places=2)
    tax_rate = fields.Decimal(required=True, places=2)
    tax_amount = fields.Decimal(required=True, places=2)
    total_amount = fields.Decimal(required=True, places=2)
    currency_code = fields.Str(required=True, validate=validate.Length(equal=3))
    notes = fields.Str(allow_none=True)
    terms = fields.Str(allow_none=True)
    payment_date = fields.Date(allow_none=True)
    payment_method = fields.Str(allow_none=True)
    payment_reference = fields.Str(allow_none=True)
    payment_status = fields.Str(validate=validate.OneOf([s.value for s in PaymentStatus]))
    amount_paid = fields.Decimal(allow_none=True, places=2)
    created_by = fields.Int(required=True)
    created_at = fields.DateTime(dump_only=True)
    updated_at = fields.DateTime(dump_only=True)
    
    # Nested fields
    project = fields.Nested('ProjectSchema', dump_only=True, allow_none=True)
    items = fields.Nested(InvoiceItemSchema, many=True, dump_only=True, allow_none=True)


class InvoiceCreateSchema(Schema):
    """Schema for creating an invoice"""
    project_id = fields.Int(required=True)
    issue_date = fields.Date(allow_none=True)
    due_date = fields.Date(allow_none=True)
    time_entry_ids = fields.List(fields.Int(), allow_none=True)
    include_expenses = fields.Bool(missing=False)
    notes = fields.Str(allow_none=True)
    terms = fields.Str(allow_none=True)


class InvoiceUpdateSchema(Schema):
    """Schema for updating an invoice"""
    issue_date = fields.Date(allow_none=True)
    due_date = fields.Date(allow_none=True)
    status = fields.Str(allow_none=True, validate=validate.OneOf([s.value for s in InvoiceStatus]))
    notes = fields.Str(allow_none=True)
    terms = fields.Str(allow_none=True)

