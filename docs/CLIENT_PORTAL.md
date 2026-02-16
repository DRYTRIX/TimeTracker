# Client Portal Feature

## Overview

The Client Portal provides a simplified, read-only interface for client users to view their projects, invoices, and time entries. This feature allows you to grant clients access to view their own data without exposing internal system functionality or other clients' information.

**Related:** For internal users (e.g. subcontractors) who should see only certain clients and projects in the **main app**, use the **Subcontractor** role and assigned clients instead. See [SUBCONTRACTOR_ROLE.md](SUBCONTRACTOR_ROLE.md).

## Features

- **Dashboard**: Overview of projects, invoices, and time entries
- **Projects View**: List of all active projects with statistics
- **Invoices View**: List of invoices with filtering options (all, paid, unpaid, overdue)
- **Invoice Details**: Detailed view of individual invoices
- **Time Entries**: View time entries for projects with filtering capabilities

## Enabling Client Portal Access

### For Administrators

1. Navigate to **Admin** → **Users**
2. Click **Edit** on the user you want to grant portal access to
3. Scroll to the **Client Portal Access** section
4. Check **Enable Client Portal**
5. Select the **Client** from the dropdown
6. Click **Save**

The user will now have access to the client portal at `/client-portal`.

### User Requirements

For a user to access the client portal:
- `client_portal_enabled` must be `True`
- `client_id` must be set to a valid client ID
- The user must be active (`is_active = True`)

## Access Control

- Client portal users can only see data for their assigned client
- They cannot access:
  - Other clients' data
  - Internal admin functions
  - User management
  - System settings
- All portal routes require authentication and portal access verification

## Portal Routes

### Dashboard
- **URL**: `/client-portal` or `/client-portal/dashboard`
- **Description**: Overview page showing statistics and recent activity

### Projects
- **URL**: `/client-portal/projects`
- **Description**: List of all active projects for the client

### Invoices
- **URL**: `/client-portal/invoices`
- **Query Parameters**:
  - `status`: Filter by status (`all`, `paid`, `unpaid`, `overdue`)
- **Description**: List of invoices with filtering options

### Invoice Detail
- **URL**: `/client-portal/invoices/<invoice_id>`
- **Description**: Detailed view of a specific invoice

### Time Entries
- **URL**: `/client-portal/time-entries`
- **Query Parameters**:
  - `project_id`: Filter by project
  - `date_from`: Filter entries from this date (YYYY-MM-DD)
  - `date_to`: Filter entries to this date (YYYY-MM-DD)
- **Description**: List of time entries with filtering capabilities

## Database Schema

### User Model Changes

Two new fields were added to the `users` table:

```sql
client_portal_enabled BOOLEAN NOT NULL DEFAULT 0
client_id INTEGER REFERENCES clients(id) ON DELETE SET NULL
```

### Migration

The migration `047_add_client_portal_fields.py` adds these fields. Run:

```bash
alembic upgrade head
```

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
- Validation to ensure a client is selected when enabling portal access

## Security Considerations

1. **Access Control**: All portal routes verify that:
   - User is authenticated
   - User has `client_portal_enabled = True`
   - User has a valid `client_id`

2. **Data Isolation**: Portal users can only see:
   - Projects belonging to their assigned client
   - Invoices for their assigned client
   - Time entries for projects belonging to their assigned client

3. **Read-Only Access**: The portal is read-only - users cannot modify any data

4. **Invoice Access**: Users can only view invoices that belong to their assigned client

## Testing

Comprehensive tests are available in `tests/test_client_portal.py`:

- Model tests for user portal properties
- Route tests for access control
- Admin interface tests for enabling/disabling portal access
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
4. Check that the client exists and is active

### Portal Shows No Data

1. Verify the client has active projects
2. Check that invoices exist for the client
3. Verify time entries exist for the client's projects

### Admin Cannot Enable Portal

1. Ensure a client is selected when enabling portal access
2. Verify the client exists and is active
3. Check for database errors in server logs

## Future Enhancements

Potential future improvements:
- Email notifications for new invoices
- PDF invoice downloads
- Export time entries to CSV
- Project status updates
- Comments/notes on projects
- Custom branding per client

