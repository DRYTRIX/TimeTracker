"""
Schema/DTO layer for API serialization and validation.
Uses Marshmallow for consistent API responses and input validation.
"""

from .client_schema import ClientCreateSchema, ClientSchema, ClientUpdateSchema
from .comment_schema import CommentCreateSchema, CommentSchema, CommentUpdateSchema
from .expense_schema import ExpenseCreateSchema, ExpenseSchema, ExpenseUpdateSchema
from .invoice_schema import InvoiceCreateSchema, InvoiceSchema, InvoiceUpdateSchema
from .payment_schema import PaymentCreateSchema, PaymentSchema, PaymentUpdateSchema
from .project_schema import ProjectCreateSchema, ProjectSchema, ProjectUpdateSchema
from .task_schema import TaskCreateSchema, TaskSchema, TaskUpdateSchema
from .time_entry_schema import TimeEntryCreateSchema, TimeEntrySchema, TimeEntryUpdateSchema
from .user_schema import UserCreateSchema, UserSchema, UserUpdateSchema

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
