# All Tracked Events in TimeTracker

This document lists all events that are tracked via PostHog and logged via JSON logging when telemetry is enabled.

## Authentication Events

| Event Name | Description | Properties |
|-----------|-------------|-----------|
| `auth.login` | User successfully logs in | `user_id`, `username` |
| `auth.login_failed` | Login attempt fails | `reason`, `username` (if provided) |
| `auth.logout` | User logs out | `user_id` |

## Timer Events

| Event Name | Description | Properties |
|-----------|-------------|-----------|
| `timer.started` | Timer starts for a time entry | `user_id`, `entry_id`, `project_id`, `task_id` (optional) |
| `timer.stopped` | Timer stops for a time entry | `user_id`, `entry_id`, `duration_seconds` |

## Project Events

| Event Name | Description | Properties |
|-----------|-------------|-----------|
| `project.created` | New project is created | `user_id`, `project_id`, `client_id` (optional) |
| `project.updated` | Project details are updated | `user_id`, `project_id` |
| `project.archived` | Project is archived | `user_id`, `project_id` |
| `project.deleted` | Project is deleted | `user_id`, `project_id` |

## Task Events

| Event Name | Description | Properties |
|-----------|-------------|-----------|
| `task.created` | New task is created | `user_id`, `task_id`, `project_id`, `priority` |
| `task.updated` | Task details are updated | `user_id`, `task_id`, `project_id` |
| `task.status_changed` | Task status changes | `user_id`, `task_id`, `old_status`, `new_status` |
| `task.deleted` | Task is deleted | `user_id`, `task_id`, `project_id` |

## Client Events

| Event Name | Description | Properties |
|-----------|-------------|-----------|
| `client.created` | New client is created | `user_id`, `client_id` |
| `client.updated` | Client details are updated | `user_id`, `client_id` |
| `client.archived` | Client is archived | `user_id`, `client_id` |
| `client.deleted` | Client is deleted | `user_id`, `client_id` |

## Invoice Events

| Event Name | Description | Properties |
|-----------|-------------|-----------|
| `invoice.created` | New invoice is created | `user_id`, `invoice_id`, `project_id`, `total_amount` |
| `invoice.updated` | Invoice details are updated | `user_id`, `invoice_id`, `project_id` |
| `invoice.sent` | Invoice is sent to client | `user_id`, `invoice_id` |
| `invoice.paid` | Invoice is marked as paid | `user_id`, `invoice_id` |
| `invoice.deleted` | Invoice is deleted | `user_id`, `invoice_id` |

## Report Events

| Event Name | Description | Properties |
|-----------|-------------|-----------|
| `report.viewed` | User views a report | `user_id`, `report_type`, `date_range` |
| `export.csv` | User exports data to CSV | `user_id`, `export_type`, `row_count` |
| `export.pdf` | User exports data to PDF | `user_id`, `export_type` |

## Comment Events

| Event Name | Description | Properties |
|-----------|-------------|-----------|
| `comment.created` | New comment is created | `user_id`, `comment_id`, `target_type` (project/task) |
| `comment.updated` | Comment is edited | `user_id`, `comment_id` |
| `comment.deleted` | Comment is deleted | `user_id`, `comment_id` |

## Admin Events

| Event Name | Description | Properties |
|-----------|-------------|-----------|
| `admin.user_created` | Admin creates a new user | `user_id`, `new_user_id` |
| `admin.user_updated` | Admin updates user details | `user_id`, `target_user_id` |
| `admin.user_deleted` | Admin deletes a user | `user_id`, `deleted_user_id` |
| `admin.settings_updated` | Admin updates system settings | `user_id` |
| `admin.telemetry_dashboard_viewed` | Admin views telemetry dashboard | `user_id` |
| `admin.telemetry_toggled` | Admin toggles telemetry on/off | `user_id`, `enabled` |

## Setup Events

| Event Name | Description | Properties |
|-----------|-------------|-----------|
| `setup.completed` | Initial setup is completed | `telemetry_enabled` |

## Privacy Note

All events listed above are tracked only when:
1. Telemetry is explicitly enabled by the user during setup or in admin settings
2. PostHog API key is configured

**No personally identifiable information (PII) is ever collected:**
- ❌ No email addresses, usernames, or real names
- ❌ No project names, descriptions, or client data
- ❌ No time entry notes or descriptions
- ❌ No IP addresses or server information
- ✅ Only internal numeric IDs and event types

For more information, see [Privacy Policy](./privacy.md) and [Analytics Documentation](./analytics.md).

