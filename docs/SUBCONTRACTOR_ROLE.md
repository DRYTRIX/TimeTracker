# Subcontractor Role and Assigned Clients

## Overview

The **Subcontractor** role lets you restrict specific users to only see and work with **assigned clients** and their projects. This is useful for:

- External or part-time staff who should not see other clients
- Confidentiality: limit visibility to only the clients a user works with
- Multi-tenant-style usage where each user has a clear subset of clients

Subcontractors use the **main application** (same UI as regular users). This is different from the **Client Portal**, which is a separate read-only portal for a single client (see [CLIENT_PORTAL.md](CLIENT_PORTAL.md)).

## How It Works

1. **Role**: Assign the user the **Subcontractor** role (Admin → Users → Edit user → Role: Subcontractor).
2. **Assigned clients**: In the same form, when the role is Subcontractor, the section **Assigned Clients (Subcontractor)** appears. Select one or more clients. Save.
3. **Scope**: That user then sees only those clients, their projects, and related data everywhere in the app (clients list, projects list, time entries, reports, invoices, timer, API). Access to any other client or project returns **403 Forbidden**.

## Enabling Subcontractor Access

### For Administrators

1. Go to **Admin** → **Users**.
2. Click **Edit** on the user.
3. Set **Role** to **Subcontractor**.
4. The section **Assigned Clients (Subcontractor)** appears. Select all clients this user should have access to (multi-select; hold Ctrl/Cmd to select multiple).
5. Click **Save**.

If you change the role away from Subcontractor, assigned clients are cleared. If you set the role back to Subcontractor, you can assign clients again.

### Requirements

- The user must have the **Subcontractor** role (system role, created by `flask seed_permissions_cmd` if missing).
- At least one client should be assigned. If none are assigned, the user will see no clients or projects.

## Where Scope Is Applied

- **Clients**: List and detail views; edit client. Other clients are hidden and direct URLs return 403.
- **Projects**: List, export, view, edit. Only projects belonging to assigned clients are shown; others 403.
- **Time entries**: Timer (manual entry, edit), time entries report and exports. Only entries for allowed projects are included.
- **Invoices**: Create invoice (project dropdown), and invoice data for reports.
- **Reports**: All report screens and export form use scoped clients and projects; time entries report only includes allowed projects.
- **API v1**: List/get clients and projects, global search, and client contacts are scoped; direct access to other resources returns 403.

Admins and users with other roles are not restricted; only users with the Subcontractor role are scoped to their assigned clients.

## Technical Details

### Data Model

- **Table**: `user_clients` (association: `user_id`, `client_id`). Migration: `127_add_user_clients_table`.
- **User model**: `User.assigned_clients` (many-to-many with `Client`). Helpers: `get_allowed_client_ids()`, `get_allowed_project_ids()`, `is_scope_restricted`.

### Scope Helpers

The module `app.utils.scope_filter` provides:

- `apply_client_scope_to_model(Client, user)` – filter expression for client queries (or `None` for full access).
- `apply_project_scope_to_model(Project, user)` – filter expression for project queries.
- `user_can_access_client(user, client_id)`, `user_can_access_project(user, project_id)` – for 403 checks on direct access.

### Seeding the Subcontractor Role

If the role does not exist, run:

```bash
flask seed_permissions_cmd
```

This creates the default roles, including **Subcontractor**, and syncs permissions.

## Related

- [CLIENT_PORTAL.md](CLIENT_PORTAL.md) – Single-client, read-only portal (different use case).
- [ADVANCED_PERMISSIONS.md](ADVANCED_PERMISSIONS.md) – Roles and permissions overview.
- [RBAC_PERMISSION_MODEL.md](development/RBAC_PERMISSION_MODEL.md) – Route-level access and scope-restricted users.
