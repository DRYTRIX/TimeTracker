"""
Application-wide constants and enums.
This module centralizes magic strings and numbers used throughout the application.
"""

from enum import Enum


class TimeEntryStatus(Enum):
    """Status of a time entry"""

    RUNNING = "running"
    PAUSED = "paused"
    STOPPED = "stopped"
    COMPLETED = "completed"


class TimeEntrySource(Enum):
    """Source of a time entry"""

    MANUAL = "manual"
    AUTO = "auto"
    API = "api"
    TEMPLATE = "template"
    BULK = "bulk"


class ProjectStatus(Enum):
    """Project status values"""

    ACTIVE = "active"
    INACTIVE = "inactive"
    ARCHIVED = "archived"


class InvoiceStatus(Enum):
    """Invoice status values"""

    DRAFT = "draft"
    SENT = "sent"
    PAID = "paid"
    OVERDUE = "overdue"
    CANCELLED = "cancelled"
    PARTIALLY_PAID = "partially_paid"
    FULLY_PAID = "fully_paid"
    OVERPAID = "overpaid"


class PaymentStatus(Enum):
    """Payment status values"""

    UNPAID = "unpaid"
    PARTIALLY_PAID = "partially_paid"
    FULLY_PAID = "fully_paid"
    OVERPAID = "overpaid"


class TaskStatus(Enum):
    """Task status values"""

    TODO = "todo"
    IN_PROGRESS = "in_progress"
    REVIEW = "review"
    DONE = "done"
    CANCELLED = "cancelled"


class UserRole(Enum):
    """User role values"""

    ADMIN = "admin"
    MANAGER = "manager"
    USER = "user"
    VIEWER = "viewer"


class BillableStatus(Enum):
    """Billable status"""

    BILLABLE = True
    NON_BILLABLE = False


# Pagination defaults
DEFAULT_PAGE_SIZE = 50
DEFAULT_PROJECTS_PER_PAGE = 20
MAX_PAGE_SIZE = 500

# Time rounding options (in minutes)
ROUNDING_OPTIONS = [1, 5, 15, 30, 60]

# Default timeouts (in minutes)
DEFAULT_IDLE_TIMEOUT = 30
MIN_IDLE_TIMEOUT = 1
MAX_IDLE_TIMEOUT = 480  # 8 hours

# File upload limits
MAX_FILE_SIZE = 16 * 1024 * 1024  # 16MB
ALLOWED_IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".gif", ".webp"}
ALLOWED_DOCUMENT_EXTENSIONS = {".pdf", ".doc", ".docx", ".xls", ".xlsx", ".txt"}

# Session and cookie defaults
DEFAULT_SESSION_LIFETIME = 86400  # 24 hours in seconds
DEFAULT_REMEMBER_COOKIE_DAYS = 365

# API rate limiting defaults
DEFAULT_RATE_LIMIT = "200 per day;50 per hour"
STRICT_RATE_LIMIT = "100 per day;20 per hour"

# Currency codes (ISO 4217)
SUPPORTED_CURRENCIES = [
    "USD",
    "EUR",
    "GBP",
    "JPY",
    "AUD",
    "CAD",
    "CHF",
    "CNY",
    "SEK",
    "NOK",
    "DKK",
    "PLN",
    "BRL",
    "INR",
    "ZAR",
    "MXN",
]

# Date/time formats
DATE_FORMAT = "%Y-%m-%d"
TIME_FORMAT = "%H:%M"
DATETIME_FORMAT = "%Y-%m-%d %H:%M:%S"
ISO_DATETIME_FORMAT = "%Y-%m-%dT%H:%M:%S"


# Audit log action types
class AuditAction(Enum):
    """Audit log action types"""

    CREATE = "create"
    UPDATE = "update"
    DELETE = "delete"
    VIEW = "view"
    LOGIN = "login"
    LOGOUT = "logout"
    EXPORT = "export"
    IMPORT = "import"
    APPROVE = "approve"
    REJECT = "reject"


# Webhook event types
class WebhookEvent(Enum):
    """Webhook event types"""

    TIME_ENTRY_CREATED = "time_entry.created"
    TIME_ENTRY_UPDATED = "time_entry.updated"
    TIME_ENTRY_DELETED = "time_entry.deleted"
    PROJECT_CREATED = "project.created"
    PROJECT_UPDATED = "project.updated"
    PROJECT_DELETED = "project.deleted"
    INVOICE_CREATED = "invoice.created"
    INVOICE_SENT = "invoice.sent"
    INVOICE_PAID = "invoice.paid"
    TASK_CREATED = "task.created"
    TASK_UPDATED = "task.updated"
    TASK_DELETED = "task.deleted"
    PROJECT_TEMPLATE_CREATED = "project_template.created"
    PROJECT_TEMPLATE_UPDATED = "project_template.updated"
    PROJECT_TEMPLATE_DELETED = "project_template.deleted"
    INVOICE_APPROVAL_REQUESTED = "invoice.approval_requested"
    INVOICE_APPROVED = "invoice.approved"
    INVOICE_REJECTED = "invoice.rejected"
    PAYMENT_PROCESSED = "payment.processed"
    PAYMENT_FAILED = "payment.failed"
    CALENDAR_SYNCED = "calendar.synced"
    INTEGRATION_CREATED = "integration.created"
    INTEGRATION_UPDATED = "integration.updated"
    INTEGRATION_DELETED = "integration.deleted"
    INTEGRATION_SYNCED = "integration.synced"
    INTEGRATION_ERROR = "integration.error"


# Notification types
class NotificationType(Enum):
    """Notification types"""

    INFO = "info"
    SUCCESS = "success"
    WARNING = "warning"
    ERROR = "error"


# Cache keys (for future Redis implementation)
class CacheKey:
    """Cache key prefixes"""

    USER = "user:"
    PROJECT = "project:"
    TIME_ENTRY = "time_entry:"
    INVOICE = "invoice:"
    CLIENT = "client:"
    DASHBOARD = "dashboard:"
    REPORT = "report:"
