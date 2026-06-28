# Client Portal Feature

## Overview

The Client Portal provides a simplified interface for client users to view their projects, invoices, and time entries, and to perform selected client-facing actions (approvals, comments, issue reporting, quote responses, and online payments). This feature allows you to grant clients access to their own data without exposing internal system functionality or other clients' information.

**Related:** For internal users (e.g. subcontractors) who should see only certain clients and projects in the **main app**, use the **Subcontractor** role and assigned clients instead. See [SUBCONTRACTOR_ROLE.md](SUBCONTRACTOR_ROLE.md).

## Features

- **Dashboard**: Overview of projects, invoices, and time entries (customizable widgets)
- **Projects View**: List of all active projects with statistics and links to time entries and comments
- **Invoices View**: List of invoices with filtering options (all, paid, unpaid, overdue)
- **Invoice Details**: Detailed view of individual invoices; online payment when configured
- **Time Entries**: View time entries for projects with filtering capabilities
- **Approvals**: Review and approve/reject time entry approval requests
- **Quotes**: View quotes and accept or reject them
- **Issues**: Report and track issues (when enabled per client)
- **Notifications**: In-app notification center with mark-as-read actions
- **Documents**: Download client and project attachments shared with the portal
- **Reports**: Project and invoice summaries with date-range selection and CSV export
- **Activity Feed**: Client-visible project activity and comments

## Enabling Client Portal Access

There are **two ways** to grant client portal access. Choose based on who needs access:

### External clients (recommended)

For customers who should **only** view their invoices, projects, and time entries (no main app):

1. Navigate to **Clients** → edit the client record
2. Enable **Client Portal** and set a **portal username** (and password, or send the password-setup email)
3. Optionally enable **Issue reporting** for the client portal
4. Share the login URL: **`/client-portal/login`**

This uses dedicated portal credentials on the `clients` table (`portal_username`, `portal_password_hash`). The client never needs a user account under Admin → Users.

### Internal users with portal access

For staff who use the main app **and** need to view a client's portal data:

1. Navigate to **Admin** → **Users**
2. Click **Edit** on the user
3. In **Client Portal Access**, check **Enable Client Portal** and select the client
4. Optionally check **Portal only (no main app access)** to restrict the user to `/client-portal` only (they will be redirected away from the main UI after login)
5. Click **Save**

The user can access the portal at `/client-portal` after signing in (at `/login` unless portal-only is enabled).

### Login URLs

| Account type | Login URL |
|--------------|-----------|
| Client-record portal (external) | `/client-portal/login` |
| User with portal access (internal) | `/login` (main app) or `/client-portal` if already signed in |

### User Requirements (user-based portal)

For a user to access the client portal:
- `client_portal_enabled` must be `True`
- `client_id` must be set to a valid client ID
- The user must be active (`is_active = True`)
- The assigned client must be active (`status = 'active'`)

## Access Control

- Client portal users can only see data for their assigned client
- They cannot access:
  - Other clients' data
  - Internal admin functions
  - User management
  - System settings
- All portal routes require authentication and portal access verification
- Native client login clears any stale main-app session keys to avoid preference/session conflicts

## Portal Routes

### Authentication
- **Login**: `/client-portal/login` (native client credentials)
- **Logout**: `/client-portal/logout`
- **Set password**: `/client-portal/set-password?token=...` (password setup email link)

### Dashboard
- **URL**: `/client-portal` or `/client-portal/dashboard`
- **Description**: Overview page showing statistics and recent activity. Clients can **customize the dashboard**: choose which widgets to show (stats, pending actions, projects, recent invoices, recent time entries) and their order. Preferences are stored per client (or per user when logged in as a portal user). Use the "Customize dashboard" button to change layout.
- **Preferences API**: `GET /client-portal/dashboard/preferences` returns current widget layout; `POST /client-portal/dashboard/preferences` with body `{ "widget_ids": [...], "widget_order": [...] }` saves the layout.

### Projects
- **URL**: `/client-portal/projects`
- **Description**: List of all active projects for the client, with links to time entries and project comments

### Project Comments
- **URL**: `/client-portal/projects/<project_id>/comments`
- **Description**: View and post client-visible comments on a project

### Invoices
- **URL**: `/client-portal/invoices`
- **Query Parameters**:
  - `status`: Filter by status (`all`, `paid`, `unpaid`, `overdue`)
- **Description**: List of invoices with filtering options

### Invoice Detail
- **URL**: `/client-portal/invoices/<invoice_id>`
- **Description**: Detailed view of a specific invoice

### Payments
- **Checkout**: `/client-portal/invoices/<invoice_id>/checkout`
- **Success return**: `/client-portal/payment/success?invoice_id=<id>`
- **Description**: Start online checkout when a payment gateway is configured; success is confirmed from gateway capture (PayPal) or invoice payment status after return

### Quotes
- **URL**: `/client-portal/quotes`
- **Detail**: `/client-portal/quotes/<quote_id>`
- **Accept/Reject**: `POST /client-portal/quotes/<quote_id>/accept` and `/reject`

### Time Entries
- **URL**: `/client-portal/time-entries`
- **Query Parameters**:
  - `project_id`: Filter by project
  - `date_from`: Filter entries from this date (YYYY-MM-DD)
  - `date_to`: Filter entries to this date (YYYY-MM-DD)
- **Description**: List of time entries with filtering capabilities

### Approvals
- **URL**: `/client-portal/approvals`
- **Detail**: `/client-portal/approvals/<approval_id>`
- **Actions**: `POST .../approve`, `POST .../reject`
- **Description**: Pending and historical time entry approvals for the client

### Issues
- **URL**: `/client-portal/issues`
- **New**: `/client-portal/issues/new`
- **Detail**: `/client-portal/issues/<issue_id>`
- **Description**: Issue reporting when `portal_issues_enabled` is true for the client (available to both native and user-based portal auth)

### Notifications
- **URL**: `/client-portal/notifications`
- **Mark read**: `POST /client-portal/notifications/<id>/read`
- **Mark all read**: `POST /client-portal/notifications/mark-all-read`

### Documents
- **URL**: `/client-portal/documents`
- **Download**: `/client-portal/documents/<attachment_id>/download?type=client|project`
- **Description**: Client and project attachments visible to the client; `type` disambiguates client vs project attachment IDs

### Reports
- **URL**: `/client-portal/reports`
- **Query Parameters**:
  - `days`: Date range in days (1–365, default 30)
  - `format=csv`: CSV export download
- **Description**: Client reports: project progress, invoice/payment summary, task/status summary, time by date, and recent time entries. All data is scoped to the authenticated client.

### Activity Feed
- **URL**: `/client-portal/activity`
- **Description**: Unified feed of client-visible events: project and time-entry activities for the client's projects, and non-internal comments. Internal-only comments are excluded.

### Real-time updates
- The client portal uses **Flask-SocketIO** for real-time notifications. When a client has the portal open, they join a room `client_portal_{client_id}` after connecting. The server emits:
  - **client_notification**: when a new in-app notification is created (e.g. new invoice, quote, approval request). The client can show a toast.
  - **client_approval_update**: when a time entry approval is requested or when an approval is approved/rejected. The client can show a toast.
- **Auth**: Only connections with a valid client portal session (either `client_portal_id` or `_user_id` with portal access) can join their client room. No cross-client access.
- **Fallback**: If WebSockets are unavailable, the portal works without real-time updates; notification and approval counts still update on the next page load.

## Database Schema

### User Model Changes

Fields on the `users` table:

```sql
client_portal_enabled BOOLEAN NOT NULL DEFAULT 0
client_id INTEGER REFERENCES clients(id) ON DELETE SET NULL
portal_only BOOLEAN NOT NULL DEFAULT 0
```

### Client Portal Credentials (native login)

On the `clients` table:

```sql
portal_enabled BOOLEAN
portal_username VARCHAR
portal_password_hash VARCHAR
portal_issues_enabled BOOLEAN
```

### Migrations

Relevant migrations (run `alembic upgrade head`):

| Migration | Purpose |
|-----------|---------|
| `047_add_client_portal_fields.py` | User portal fields (`client_portal_enabled`, `client_id`) |
| `048_add_client_portal_credentials.py` | Native client portal credentials |
| `072_add_client_portal_customization_and_team_chat.py` | `client_portal_customizations` admin table |
| `096_add_missing_portal_issues_enabled.py` | `portal_issues_enabled` on clients |
| `140_add_client_portal_dashboard_preferences.py` | Dashboard widget preferences |
| `163_deleted_usernames_and_portal_only.py` | `portal_only` on users, deleted username blocklist |

## User Model Methods

### `is_client_portal_user` (property)

Returns `True` if the user has client portal access enabled and a client assigned.

```python
if user.is_client_portal_user:
    # User has portal access
```

### `get_client_portal_data()`

Returns a dictionary containing all portal data for the user's assigned client:

```python
data = user.get_client_portal_data()
# Returns:
# {
#     'client': Client object,
#     'projects': [list of active projects],
#     'invoices': [list of invoices],
#     'time_entries': [list of time entries]
# }
```

Returns `None` if portal access is not enabled or no client is assigned.

## Admin Interface

### User List

The user list now displays a "Portal" badge for users with client portal access enabled, showing which client they're assigned to.

### User Edit Form

The user edit form includes a new **Client Portal Access** section with:
- Checkbox to enable/disable portal access
- Dropdown to select the assigned client
- **Portal only** checkbox to block main app access (redirects to `/client-portal` after login)
- Validation to ensure a client is selected when enabling portal access
- Guidance to use **Clients → Edit → Portal** for external clients

## Security Considerations

1. **Access Control**: All portal routes verify authentication via either:
   - Native client session (`client_portal_id`) with `has_portal_access`, or
   - User session (`_user_id`) with `client_portal_enabled`, valid `client_id`, active user, and active client

2. **Data Isolation**: Portal users can only see:
   - Projects belonging to their assigned client
   - Invoices for their assigned client
   - Time entries for projects belonging to their assigned client

3. **Write Actions**: The portal supports client-facing write actions (comments, approvals, issues, quote responses, payments, dashboard preferences) scoped to the authenticated client.

4. **Invoice Access**: Users can only view invoices that belong to their assigned client

5. **Document Downloads**: Attachment downloads require an explicit `type=client|project` query parameter to avoid ID collisions between attachment tables

## Testing

Comprehensive tests are available in `tests/test_client_portal.py`:

- Model tests for user portal properties
- Route tests for access control
- Admin interface tests for enabling/disabling portal access
- Native login, notification redirects, issues access, attachment type checks, inactive client blocking
- Smoke tests for basic functionality

Run tests with:

```bash
pytest tests/test_client_portal.py -v
```

## Troubleshooting

### User Cannot Access Portal

1. Verify `client_portal_enabled` is `True` in the database
2. Verify `client_id` is set to a valid client ID
3. Verify the user is active (`is_active = True`)
4. Check that the client exists and is active (`status = 'active'`)

### Portal Shows No Data

1. Verify the client has active projects
2. Check that invoices exist for the client
3. Verify time entries exist for the client's projects

### Admin Cannot Enable Portal

1. Ensure a client is selected when enabling portal access
2. Verify the client exists and is active
3. Check for database errors in server logs

## Database Schema (additional)

### Client Portal Dashboard Preferences

Table `client_portal_dashboard_preferences` stores per-client (and optionally per-user) widget layout:

- `client_id`, `user_id` (nullable; null = client login)
- `widget_ids` (JSON array of widget keys)
- `widget_order` (JSON array for display order)

Migration: `140_add_client_portal_dashboard_preferences.py`.

## Future Enhancements

Potential future improvements:
- Per-contact preferences when contact-based login is added
- Report export (PDF)
- Activity feed: quote/invoice events; optional `visible_to_client` on Activity
- Real-time activity feed live updates
- New widget types (e.g. upcoming deadlines, documents)
- Apply Client Portal Customization branding in portal templates (admin customization exists today)
