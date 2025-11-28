"""
Schema/DTO layer for API serialization and validation.
Uses Marshmallow for consistent API responses and input validation.
"""

from .time_entry_schema import TimeEntrySchema, TimeEntryCreateSchema, TimeEntryUpdateSchema
from .project_schema import ProjectSchema, ProjectCreateSchema, ProjectUpdateSchema
from .invoice_schema import InvoiceSchema, InvoiceCreateSchema, InvoiceUpdateSchema
from .task_schema import TaskSchema, TaskCreateSchema, TaskUpdateSchema
from .expense_schema import ExpenseSchema, ExpenseCreateSchema, ExpenseUpdateSchema
from .client_schema import ClientSchema, ClientCreateSchema, ClientUpdateSchema
from .payment_schema import PaymentSchema, PaymentCreateSchema, PaymentUpdateSchema
from .comment_schema import CommentSchema, CommentCreateSchema, CommentUpdateSchema
from .user_schema import UserSchema, UserCreateSchema, UserUpdateSchema

__all__ = [
    "TimeEntrySchema",
    "TimeEntryCreateSchema",
    "TimeEntryUpdateSchema",
    "ProjectSchema",
    "ProjectCreateSchema",
    "ProjectUpdateSchema",
    "InvoiceSchema",
    "InvoiceCreateSchema",
    "InvoiceUpdateSchema",
    "TaskSchema",
    "TaskCreateSchema",
    "TaskUpdateSchema",
    "ExpenseSchema",
    "ExpenseCreateSchema",
    "ExpenseUpdateSchema",
    "ClientSchema",
    "ClientCreateSchema",
    "ClientUpdateSchema",
    "PaymentSchema",
    "PaymentCreateSchema",
    "PaymentUpdateSchema",
    "CommentSchema",
    "CommentCreateSchema",
    "CommentUpdateSchema",
    "UserSchema",
    "UserCreateSchema",
    "UserUpdateSchema",
]
