"""
Schemas for payment serialization and validation.
"""

from marshmallow import Schema, fields, validate
from decimal import Decimal
from datetime import date


class PaymentSchema(Schema):
    """Schema for payment serialization"""

    id = fields.Int(dump_only=True)
    invoice_id = fields.Int(required=True)
    amount = fields.Decimal(required=True, places=2)
    currency = fields.Str(allow_none=True, validate=validate.Length(equal=3))
    payment_date = fields.Date(required=True)
    method = fields.Str(allow_none=True)
    reference = fields.Str(allow_none=True, validate=validate.Length(max=100))
    notes = fields.Str(allow_none=True)
    status = fields.Str(validate=validate.OneOf(["completed", "pending", "failed", "refunded"]))
    received_by = fields.Int(allow_none=True)
    gateway_transaction_id = fields.Str(allow_none=True)
    gateway_fee = fields.Decimal(allow_none=True, places=2)
    net_amount = fields.Decimal(allow_none=True, places=2)
    created_at = fields.DateTime(dump_only=True)
    updated_at = fields.DateTime(dump_only=True)

    # Nested fields
    invoice = fields.Nested("InvoiceSchema", dump_only=True, allow_none=True)
    receiver = fields.Nested("UserSchema", dump_only=True, allow_none=True)


class PaymentCreateSchema(Schema):
    """Schema for creating a payment"""

    invoice_id = fields.Int(required=True)
    amount = fields.Decimal(required=True, places=2, validate=validate.Range(min=Decimal("0.01")))
    currency = fields.Str(allow_none=True, validate=validate.Length(equal=3))
    payment_date = fields.Date(required=True)
    method = fields.Str(allow_none=True)
    reference = fields.Str(allow_none=True, validate=validate.Length(max=100))
    notes = fields.Str(allow_none=True)
    status = fields.Str(missing="completed", validate=validate.OneOf(["completed", "pending", "failed", "refunded"]))
    gateway_transaction_id = fields.Str(allow_none=True)
    gateway_fee = fields.Decimal(allow_none=True, places=2, validate=validate.Range(min=Decimal("0")))


class PaymentUpdateSchema(Schema):
    """Schema for updating a payment"""

    amount = fields.Decimal(allow_none=True, places=2, validate=validate.Range(min=Decimal("0.01")))
    currency = fields.Str(allow_none=True, validate=validate.Length(equal=3))
    payment_date = fields.Date(allow_none=True)
    method = fields.Str(allow_none=True)
    reference = fields.Str(allow_none=True, validate=validate.Length(max=100))
    notes = fields.Str(allow_none=True)
    status = fields.Str(allow_none=True, validate=validate.OneOf(["completed", "pending", "failed", "refunded"]))
    gateway_transaction_id = fields.Str(allow_none=True)
    gateway_fee = fields.Decimal(allow_none=True, places=2, validate=validate.Range(min=Decimal("0")))
