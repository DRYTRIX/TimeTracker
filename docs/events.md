# Event Schema

This document lists all analytics events tracked by TimeTracker, including their properties and when they are triggered.

## Event Naming Convention

Events follow the pattern `resource.action`:
- `resource`: The entity being acted upon (project, timer, task, etc.)
- `action`: The action being performed (created, started, updated, etc.)

## Authentication Events

### `auth.login`
User successfully logs in

**Properties:**
- `user_id` (string): User ID
- `auth_method` (string): Authentication method used ("local" or "oidc")
- `timestamp` (datetime): When the login occurred

**Triggered:** On successful login via local or OIDC authentication

### `auth.logout`
User logs out

**Properties:**
- `user_id` (string): User ID
- `timestamp` (datetime): When the logout occurred

**Triggered:** When user explicitly logs out

### `auth.login_failed`
Failed login attempt

**Properties:**
- `username` (string): Attempted username
- `auth_method` (string): Authentication method attempted
- `reason` (string): Failure reason
- `timestamp` (datetime): When the attempt occurred

**Triggered:** On failed login attempt

## Project Events

### `project.created`
New project is created

**Properties:**
- `user_id` (string): User who created the project
- `project_id` (string): Created project ID
- `project_name` (string): Project name
- `has_client` (boolean): Whether project is associated with a client
- `timestamp` (datetime): Creation timestamp

**Triggered:** When a new project is created via the projects interface

### `project.updated`
Project is updated

**Properties:**
- `user_id` (string): User who updated the project
- `project_id` (string): Updated project ID
- `fields_changed` (array): List of field names that changed
- `timestamp` (datetime): Update timestamp

**Triggered:** When project details are modified

### `project.deleted`
Project is deleted

**Properties:**
- `user_id` (string): User who deleted the project
- `project_id` (string): Deleted project ID
- `had_time_entries` (boolean): Whether project had time entries
- `timestamp` (datetime): Deletion timestamp

**Triggered:** When a project is deleted

### `project.archived`
Project is archived

**Properties:**
- `user_id` (string): User who archived the project
- `project_id` (string): Archived project ID
- `timestamp` (datetime): Archive timestamp

**Triggered:** When a project is archived

## Timer Events

### `timer.started`
Time tracking timer is started

**Properties:**
- `user_id` (string): User who started the timer
- `project_id` (string): Project being tracked
- `task_id` (string|null): Associated task ID (if any)
- `description` (string): Timer description
- `timestamp` (datetime): Start timestamp

**Triggered:** When user starts a new timer

### `timer.stopped`
Time tracking timer is stopped

**Properties:**
- `user_id` (string): User who stopped the timer
- `time_entry_id` (string): Created time entry ID
- `project_id` (string): Project tracked
- `task_id` (string|null): Associated task ID (if any)
- `duration_seconds` (number): Duration in seconds
- `timestamp` (datetime): Stop timestamp

**Triggered:** When user stops an active timer

### `timer.idle_detected`
Timer is automatically stopped due to idle detection

**Properties:**
- `user_id` (string): User whose timer was stopped
- `time_entry_id` (string): Created time entry ID
- `idle_minutes` (number): Minutes of idle time detected
- `duration_seconds` (number): Total duration
- `timestamp` (datetime): Detection timestamp

**Triggered:** When idle timeout expires and timer is auto-stopped

## Task Events

### `task.created`
New task is created

**Properties:**
- `user_id` (string): User who created the task
- `task_id` (string): Created task ID
- `project_id` (string): Associated project ID
- `priority` (string): Task priority
- `has_due_date` (boolean): Whether task has a due date
- `timestamp` (datetime): Creation timestamp

**Triggered:** When a new task is created

### `task.updated`
Task is updated

**Properties:**
- `user_id` (string): User who updated the task
- `task_id` (string): Updated task ID
- `status_changed` (boolean): Whether status changed
- `assignee_changed` (boolean): Whether assignee changed
- `timestamp` (datetime): Update timestamp

**Triggered:** When task details are modified

### `task.status_changed`
Task status is changed (e.g., todo → in_progress → done)

**Properties:**
- `user_id` (string): User who changed the status
- `task_id` (string): Task ID
- `old_status` (string): Previous status
- `new_status` (string): New status
- `timestamp` (datetime): Change timestamp

**Triggered:** When task is moved between statuses/columns

## Report Events

### `report.generated`
Report is generated

**Properties:**
- `user_id` (string): User who generated the report
- `report_type` (string): Type of report ("summary", "detailed", "project")
- `date_range_days` (number): Number of days in report
- `format` (string): Export format ("html", "pdf", "csv")
- `num_entries` (number): Number of time entries in report
- `timestamp` (datetime): Generation timestamp

**Triggered:** When user generates any report

### `export.csv`
Data is exported to CSV

**Properties:**
- `user_id` (string): User who performed export
- `export_type` (string): Type of export ("time_entries", "projects", "tasks")
- `num_rows` (number): Number of rows exported
- `timestamp` (datetime): Export timestamp

**Triggered:** When user exports data to CSV format

### `export.pdf`
Report is exported to PDF

**Properties:**
- `user_id` (string): User who performed export
- `report_type` (string): Type of report
- `num_pages` (number): Number of pages in PDF
- `timestamp` (datetime): Export timestamp

**Triggered:** When user exports a report to PDF

## Invoice Events

### `invoice.created`
Invoice is created

**Properties:**
- `user_id` (string): User who created the invoice
- `invoice_id` (string): Created invoice ID
- `client_id` (string): Associated client ID
- `total_amount` (number): Invoice total
- `num_line_items` (number): Number of line items
- `timestamp` (datetime): Creation timestamp

**Triggered:** When a new invoice is created

### `invoice.sent`
Invoice is marked as sent

**Properties:**
- `user_id` (string): User who marked invoice as sent
- `invoice_id` (string): Invoice ID
- `timestamp` (datetime): Send timestamp

**Triggered:** When invoice status is changed to "sent"

### `invoice.paid`
Invoice is marked as paid

**Properties:**
- `user_id` (string): User who marked invoice as paid
- `invoice_id` (string): Invoice ID
- `amount` (number): Payment amount
- `timestamp` (datetime): Payment timestamp

**Triggered:** When invoice status is changed to "paid"

## Client Events

### `client.created`
New client is created

**Properties:**
- `user_id` (string): User who created the client
- `client_id` (string): Created client ID
- `has_billing_info` (boolean): Whether billing info was provided
- `timestamp` (datetime): Creation timestamp

**Triggered:** When a new client is created

### `client.updated`
Client information is updated

**Properties:**
- `user_id` (string): User who updated the client
- `client_id` (string): Updated client ID
- `timestamp` (datetime): Update timestamp

**Triggered:** When client details are modified

## Admin Events

### `admin.user_created`
Admin creates a new user

**Properties:**
- `admin_user_id` (string): Admin who created the user
- `new_user_id` (string): Created user ID
- `role` (string): Assigned role
- `timestamp` (datetime): Creation timestamp

**Triggered:** When admin creates a new user

### `admin.user_role_changed`
User role is changed by admin

**Properties:**
- `admin_user_id` (string): Admin who changed the role
- `user_id` (string): Affected user ID
- `old_role` (string): Previous role
- `new_role` (string): New role
- `timestamp` (datetime): Change timestamp

**Triggered:** When admin changes a user's role

### `admin.settings_updated`
Application settings are updated

**Properties:**
- `admin_user_id` (string): Admin who updated settings
- `settings_changed` (array): List of setting keys changed
- `timestamp` (datetime): Update timestamp

**Triggered:** When admin modifies application settings

## System Events

### `system.backup_created`
System backup is created

**Properties:**
- `backup_type` (string): Type of backup ("manual", "scheduled")
- `size_bytes` (number): Backup file size
- `timestamp` (datetime): Backup timestamp

**Triggered:** When automated or manual backup is performed

### `system.error`
System error occurred

**Properties:**
- `error_type` (string): Error type/class
- `endpoint` (string): Endpoint where error occurred
- `user_id` (string|null): User ID if authenticated
- `error_message` (string): Error message
- `timestamp` (datetime): Error timestamp

**Triggered:** When an unhandled error occurs (also sent to Sentry)

## Usage Guidelines

### Adding New Events

When adding new events:

1. Follow the `resource.action` naming convention
2. Document all properties with types
3. Include a clear description of when the event is triggered
4. Update this document before implementing the event
5. Ensure no PII (personally identifiable information) is included unless necessary

### Event Properties

**Required properties (automatically added):**
- `timestamp`: When the event occurred
- `request_id`: Request ID for tracing

**Common optional properties:**
- `user_id`: Acting user (when authenticated)
- `duration_seconds`: For timed operations
- `success`: Boolean for operation outcomes

### Privacy Considerations

**Do NOT include:**
- Passwords or authentication tokens
- Email addresses (unless explicitly required)
- IP addresses
- Personal notes or descriptions (unless aggregated)

**OK to include:**
- User IDs (internal references)
- Counts and aggregates
- Feature usage flags
- Technical metadata

## Event Lifecycle

1. **Definition**: Event is defined in this document
2. **Implementation**: Code is instrumented with `log_event()` or `track_event()`
3. **Testing**: Event is verified in development/staging
4. **Monitoring**: Event appears in PostHog, logs, and dashboards
5. **Review**: Periodic review of event usefulness
6. **Deprecation**: Unused events are removed and documented

## Changelog

Maintain a changelog of event schema changes:

### 2025-10-20
- Initial event schema documentation
- Defined core events for authentication, projects, timers, tasks, reports, invoices, clients, and admin operations

---

**Document Owner**: Product & Engineering Team  
**Last Updated**: 2025-10-20  
**Review Cycle**: Quarterly

