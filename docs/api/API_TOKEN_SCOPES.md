# API Token Scopes Reference

## Overview

API tokens use scopes to control access to resources. When creating a token, you select which scopes to grant. This document explains each scope and when to use it.

## Scope Format

Scopes follow the format: `action:resource`

- **action**: `read` or `write`
- **resource**: The resource type (e.g., `projects`, `time_entries`)

Special scopes:
- `admin:all` - Full administrative access to all resources
- `*` - Wildcard (admin only)

## Available Scopes

### Projects

#### `read:projects`
**Grants**: View project information  
**Endpoints**:
- `GET /api/v1/projects` - List projects
- `GET /api/v1/projects/{id}` - Get project details

**Use Cases**:
- Read-only integrations
- Reporting tools
- Dashboard displays
- Project status monitors

**Example**:
```bash
curl -H "Authorization: Bearer YOUR_TOKEN" \
     https://your-domain.com/api/v1/projects
```

#### `write:projects`
**Grants**: Create, update, and archive projects  
**Endpoints**:
- `POST /api/v1/projects` - Create project
- `PUT /api/v1/projects/{id}` - Update project
- `DELETE /api/v1/projects/{id}` - Archive project

**Use Cases**:
- Project management integrations
- Automated project creation
- Bulk project updates
- Project lifecycle automation

**Example**:
```bash
curl -X POST https://your-domain.com/api/v1/projects \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"name": "New Project", "status": "active"}'
```

**Inventory**: Dedicated scopes `read:inventory` and `write:inventory` grant access only to inventory endpoints. For backward compatibility, `read:projects` and `write:projects` also grant the same inventory access.
- **read:inventory** (or **read:projects**): `GET /api/v1/inventory/items`, `GET /api/v1/inventory/warehouses`, `GET /api/v1/inventory/stock-levels`, `GET /api/v1/inventory/transfers`, `GET /api/v1/inventory/transfers/{reference_id}`, `GET /api/v1/inventory/reports/*`, suppliers, purchase orders (read).
- **write:inventory** (or **write:projects**): `POST /api/v1/inventory/transfers`, `POST /api/v1/inventory/movements`, create/update/delete items, suppliers, purchase orders.

Use `read:inventory` / `write:inventory` when you need inventory-only tokens (least privilege).

---

### Time Entries

#### `read:time_entries`
**Grants**: View time entries and timer status  
**Endpoints**:
- `GET /api/v1/time-entries` - List time entries
- `GET /api/v1/time-entries/{id}` - Get time entry details
- `GET /api/v1/timer/status` - Get timer status

**Use Cases**:
- Timesheet exports
- Reporting and analytics
- Invoice generation
- Time tracking dashboards

**Permissions**:
- Non-admin users can only see their own time entries
- Admin users can see all time entries

**Example**:
```bash
curl -H "Authorization: Bearer YOUR_TOKEN" \
     "https://your-domain.com/api/v1/time-entries?start_date=2024-01-01"
```

#### `write:time_entries`
**Grants**: Create, update, and delete time entries; control timer; timesheet periods and time-off requests  
**Endpoints**:
- `POST /api/v1/time-entries` - Create time entry (optional `Idempotency-Key` header for safe retries)
- `POST /api/v1/time-entries/import-csv` - Import time entries from CSV (multipart `file` or JSON/raw body)
- `POST /api/v1/time-entries/bulk` - Bulk delete, billable/paid flags, or tag add/remove
- `PUT /api/v1/time-entries/{id}` - Update time entry
- `DELETE /api/v1/time-entries/{id}` - Delete time entry
- `POST /api/v1/timer/start` - Start timer
- `POST /api/v1/timer/stop` - Stop timer
- `DELETE /api/v1/timesheet-periods/{id}` - Delete timesheet period (draft/rejected only; owner or admin)
- `DELETE /api/v1/time-off/requests/{id}` - Delete time-off request (draft/submitted/cancelled; owner or approver)

**Use Cases**:
- Time tracking integrations
- Automated time entry creation
- Timer control from external apps
- Bulk time entry updates

**Example**:
```bash
curl -X POST https://your-domain.com/api/v1/timer/start \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"project_id": 1}'
```

---

### Tasks

#### `read:tasks`
**Grants**: View task information  
**Endpoints**:
- `GET /api/v1/tasks` - List tasks
- `GET /api/v1/tasks/{id}` - Get task details
- `GET /api/v1/gantt` - Gantt chart data (`read:projects` or `read:tasks`)
- `GET /api/v1/resource-scheduling` - Team schedule / allocations (`read:projects` or `read:tasks`)

**Use Cases**:
- Task management integrations
- Kanban board displays
- Progress tracking
- Task reporting
- Gantt / capacity planning clients

**Example**:
```bash
curl -H "Authorization: Bearer YOUR_TOKEN" \
     "https://your-domain.com/api/v1/tasks?project_id=1&status=todo"
```

#### `write:tasks`
**Grants**: Create, update, and delete tasks  
**Endpoints**:
- `POST /api/v1/tasks` - Create task
- `PUT /api/v1/tasks/{id}` - Update task
- `DELETE /api/v1/tasks/{id}` - Delete task
- `POST /api/v1/resource-scheduling/allocations` - Assign a task to a user/date (`write:tasks` or `write:projects`)

**Use Cases**:
- Task synchronization
- Automated task creation
- Task status updates
- Project planning automation
- Capacity schedule updates

**Example**:
```bash
curl -X POST https://your-domain.com/api/v1/tasks \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"name": "New Task", "project_id": 1, "status": "todo"}'
```

---

### Clients

#### `read:clients`
**Grants**: View client information  
**Endpoints**:
- `GET /api/v1/clients` - List clients
- `GET /api/v1/clients/{id}` - Get client details

**Use Cases**:
- CRM integrations
- Client directories
- Invoice generation
- Contact management

**Example**:
```bash
curl -H "Authorization: Bearer YOUR_TOKEN" \
     https://your-domain.com/api/v1/clients
```

#### `write:clients`
**Grants**: Create, update, and delete clients  
**Endpoints**:
- `POST /api/v1/clients` - Create client
- `PUT /api/v1/clients/{id}` - Update client
- `DELETE /api/v1/clients/{id}` - Delete client

**Use Cases**:
- Client data synchronization
- CRM integration
- Automated client onboarding
- Contact management

**Example**:
```bash
curl -X POST https://your-domain.com/api/v1/clients \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"name": "New Client", "email": "client@example.com"}'
```

---

### Quotes

#### `read:quotes`
**Grants**: List and view quotes  
**Endpoints**:
- `GET /api/v1/quotes` - List quotes
- `GET /api/v1/quotes/{id}` - Get quote details

**Use Cases**:
- Client portal and CRM read integrations
- Quote status dashboards
- External systems that only need quote visibility

#### `write:quotes`
**Grants**: Create, update, and delete quotes  
**Endpoints**:
- `POST /api/v1/quotes` - Create quote
- `PUT /api/v1/quotes/{id}` - Update quote
- `DELETE /api/v1/quotes/{id}` - Delete quote

**Use Cases**:
- Quote generation from external systems
- Automated quote updates and status sync
- Back-office quote lifecycle tools

---

### Invoices

#### `read:invoices`
**Grants**: List and view invoices via the versioned API  
**Endpoints** (non-exhaustive; see OpenAPI at `/api/docs` when enabled):
- `GET /api/v1/invoices` — List invoices
- `GET /api/v1/invoices/{id}` — Get invoice by id
- `GET /api/v1/invoices/{id}/pdf` — PDF download
- `GET /api/v1/invoices/{id}/ubl` — PEPPOL UBL XML
- `GET /api/v1/invoices/{id}/xrechnung` — XRechnung XML
- `GET /api/v1/invoices/{id}/fatturapa` — FatturaPA XML
- `GET /api/v1/credit-notes` / `{id}` / `{id}/pdf` / `{id}/ubl` — Credit notes and downloads

**Use Cases**:
- Billing dashboards and exports
- Integrations that sync invoice status

#### `write:invoices`
**Grants**: Create and update invoices via the versioned API  
**Endpoints** (non-exhaustive):
- `POST /api/v1/invoices` — Create invoice (JSON body)
- `PUT` / `PATCH /api/v1/invoices/{id}` — Update invoice
- `DELETE /api/v1/invoices/{id}` — Cancel invoice
- `POST /api/v1/invoices/{id}/send-email` — Email invoice (optional `recipient_email`, `subject`)
- `POST /api/v1/invoices/{id}/send-peppol` / `send-sdi` — E-invoicing send
- `POST` / `PATCH` / `DELETE /api/v1/credit-notes` — Credit note mutations
- `POST /api/v1/clients/{client_id}/invoice-unbilled` — Create a **draft** invoice from all **unbilled** billable time for that client (line items grouped by project). Requires `write:invoices` when using an API token; the browser UI uses a logged-in session with **Create invoices** permission instead. Successful response JSON: `invoice_id`, `invoice_number`, `total`, `item_count`. Returns **400** when there is no unbilled time, or when any unbilled entry has no `project_id` (assign entries to a project first).

**Use Cases**:
- Automated billing from integrations
- One-shot “invoice everything open” for a client (API or client detail page)

**Example** (API token):
```bash
curl -X POST "https://your-domain.com/api/v1/clients/42/invoice-unbilled" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Accept: application/json"
```

---

### Reports

#### `read:reports`
**Grants**: Access reporting and analytics endpoints; read leave types and holidays  
**Endpoints**:
- `GET /api/v1/reports/summary` - Get summary reports
- `GET /api/v1/time-off/leave-types` - List leave types
- `GET /api/v1/time-off/holidays` - List company holidays

**Use Cases**:
- Business intelligence tools
- Custom reporting
- Analytics dashboards
- Management reporting

**Permissions**:
- Non-admin users can only see their own data
- Admin users can see all data

**Example**:
```bash
curl -H "Authorization: Bearer YOUR_TOKEN" \
     "https://your-domain.com/api/v1/reports/summary?start_date=2024-01-01&end_date=2024-01-31"
```

#### `write:reports`
**Grants**: Create and delete leave types and company holidays (workforce admin)  
**Endpoints**:
- `POST /api/v1/time-off/leave-types` - Create leave type (admin only)
- `DELETE /api/v1/time-off/leave-types/{id}` - Delete leave type (admin only; blocked if it has time-off requests)
- `POST /api/v1/time-off/holidays` - Create company holiday (admin only)
- `DELETE /api/v1/time-off/holidays/{id}` - Delete company holiday (admin only)

**Permissions**: Admin only for these endpoints.

---

### Users

#### `read:users`
**Grants**: View user information  
**Endpoints**:
- `GET /api/v1/users/me` - Get current user
- `GET /api/v1/users` - List all users (admin only)

**Use Cases**:
- User directory
- Profile information
- User management
- Team listings

**Permissions**:
- All users can access `/users/me`
- Only admins can access `/users` (requires `admin:all`)

**Example**:
```bash
curl -H "Authorization: Bearer YOUR_TOKEN" \
     https://your-domain.com/api/v1/users/me
```

---

### Administrative

#### `admin:all`
**Grants**: Full administrative access to all resources  
**Endpoints**: All API endpoints  

**Use Cases**:
- Admin automation scripts
- System integrations
- Backup tools
- Migration scripts

**⚠️ Warning**: This scope grants complete access. Use with extreme caution.

**Example**:
```bash
# Admin can access all user data
curl -H "Authorization: Bearer YOUR_TOKEN" \
     https://your-domain.com/api/v1/users
```

---

## Scope Combinations

### Common Combinations

#### 1. Read-Only Access
```
read:projects
read:time_entries
read:tasks
read:clients
read:reports
```
**Use For**: Dashboards, reporting tools, read-only integrations

#### 2. Time Tracking Integration
```
read:projects
read:time_entries
write:time_entries
read:tasks
```
**Use For**: Time tracking apps, timer integrations

#### 3. Project Management Integration
```
read:projects
write:projects
read:tasks
write:tasks
read:time_entries
```
**Use For**: Project management tools, task synchronization

#### 4. Full User Access (Non-Admin)
```
read:projects
write:projects
read:time_entries
write:time_entries
read:tasks
write:tasks
read:clients
write:clients
read:quotes
write:quotes
read:reports
```
**Use For**: Personal automation, full-featured integrations

#### 5. Admin Access
```
admin:all
```
**Use For**: Administrative tools, system automation

## Scope Checking

### How Scope Checking Works

1. **Token Authentication**: API validates the token
2. **Scope Verification**: Checks if token has required scope
3. **Resource Access**: Verifies access to specific resource
4. **User Permissions**: Applies user-level permissions

### Wildcard Scopes

The API supports wildcard patterns:

- `read:*` - Read access to all resources
- `write:*` - Write access to all resources
- `*` - Full access (equivalent to `admin:all`)

**Note**: Wildcards are only available for admin users.

## Security Best Practices

### Principle of Least Privilege

1. **Grant minimum scopes needed** for the integration
2. **Avoid `admin:all`** unless absolutely necessary
3. **Create separate tokens** for different integrations
4. **Review scopes regularly** and revoke unused permissions

### Token Management

1. **Separate tokens per integration**:
   ```
   Token 1: Time tracking app (read:projects, write:time_entries)
   Token 2: Reporting tool (read:*, read:reports)
   Token 3: Admin script (admin:all)
   ```

2. **Set expiration dates** for temporary integrations

3. **Monitor token usage** in the admin dashboard

4. **Rotate tokens periodically** (create new, delete old)

### Scope Audit

Regularly review tokens and their scopes:

1. Navigate to `/admin/api-tokens`
2. Review each token's scopes
3. Remove unused scopes
4. Delete inactive tokens

## Examples by Use Case

### Dashboard Integration

**Requirements**: Display time tracking statistics  
**Scopes**:
```
read:projects
read:time_entries
read:reports
```

**Why**:
- `read:projects` - Show project names and details
- `read:time_entries` - Display time entries
- `read:reports` - Generate statistics

### Mobile Timer App

**Requirements**: Start/stop timer, create time entries  
**Scopes**:
```
read:projects
read:tasks
read:time_entries
write:time_entries
```

**Why**:
- `read:projects` - Select project for timer
- `read:tasks` - Select task (optional)
- `read:time_entries` - Show existing entries
- `write:time_entries` - Start/stop timer, create entries

### Invoice Generator

**Requirements**: Read time entries and generate invoices (read-only reporting), or call the **invoice unbilled** API (writes a draft invoice)  
**Scopes** (read-only path):
```
read:projects
read:clients
read:time_entries
read:reports
```

**Why**:
- `read:projects` - Get project rates
- `read:clients` - Get client billing information
- `read:time_entries` - Get billable hours
- `read:reports` - Generate summaries

**To create a draft invoice from all unbilled time for one client** via `POST /api/v1/clients/{client_id}/invoice-unbilled`, add **`write:invoices`** (and keep `read:clients` / `read:projects` as needed for your workflow). The Clients and Invoices modules must be enabled for the token’s user.

### Project Management Sync

**Requirements**: Two-way sync with external PM tool  
**Scopes**:
```
read:projects
write:projects
read:tasks
write:tasks
read:time_entries
```

**Why**:
- `read:projects` / `write:projects` - Sync projects
- `read:tasks` / `write:tasks` - Sync tasks
- `read:time_entries` - Import time tracking

## Testing Scopes

### Test Token Scopes

1. Create a test token with limited scopes
2. Try accessing different endpoints
3. Verify proper authorization

**Example**:
```bash
# Create token with only read:projects

# This should work:
curl -H "Authorization: Bearer TOKEN" \
     https://your-domain.com/api/v1/projects

# This should fail (403):
curl -X POST https://your-domain.com/api/v1/projects \
  -H "Authorization: Bearer TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"name": "Test"}'
```

## Troubleshooting

### "Insufficient permissions" Error

**Cause**: Token lacks required scope  
**Solution**:
1. Check error message for `required_scope`
2. Create new token with needed scope
3. Update integration to use new token

**Example Error**:
```json
{
  "error": "Insufficient permissions",
  "message": "This endpoint requires the 'write:projects' scope",
  "required_scope": "write:projects",
  "available_scopes": ["read:projects", "read:time_entries"]
}
```

### Access Denied for Specific Resource

**Cause**: User permissions restrict access  
**Solution**:
- Non-admin users can only access their own resources
- Use admin token for cross-user access
- Verify user has permission to access resource

## Reference Table

| Scope | Read | Write | Admin Required | Notes |
|-------|------|-------|----------------|-------|
| `read:projects` | ✅ | ❌ | ❌ | View projects (and inventory read) |
| `write:projects` | ✅ | ✅ | ❌ | Manage projects (and inventory write) |
| `read:inventory` | ❌ | ❌ | ❌ | View inventory only |
| `write:inventory` | ❌ | ❌ | ❌ | Manage inventory only |
| `read:time_entries` | ✅ | ❌ | ❌ | View own entries |
| `write:time_entries` | ✅ | ✅ | ❌ | Manage own entries |
| `read:tasks` | ✅ | ❌ | ❌ | View tasks |
| `write:tasks` | ✅ | ✅ | ❌ | Manage tasks |
| `read:clients` | ✅ | ❌ | ❌ | View clients |
| `write:clients` | ✅ | ✅ | ❌ | Manage clients |
| `read:quotes` | ✅ | ❌ | ❌ | View quotes |
| `write:quotes` | ✅ | ✅ | ❌ | Manage quotes |
| `read:reports` | ✅ | ❌ | ❌ | View own reports |
| `read:users` | ✅ | ❌ | Partial | `/users/me` for all, `/users` admin only |
| `admin:all` | ✅ | ✅ | ✅ | Full access |

## Additional API coverage notes

### Workflows & team chat
- `GET /api/v1/workflows/templates` and `GET /api/v1/workflows/templates/{id}` — workflow template library (`read:projects`)
- `GET /api/v1/workflows/executions` — workflow run history (`read:projects`)
- `GET|POST /api/v1/team-chat/channels` — list/create channels (`read:projects` / `write:projects`)
- `GET|POST /api/v1/team-chat/channels/{id}/messages` — list/post messages (`read:projects` / `write:projects`)

### Kiosk (web-only)
Time clock **kiosk** mode is intentionally **web-only**. There is no public API v1 surface for kiosk PIN/session flows; use the browser kiosk UI. Do not grant or expect dedicated `kiosk:*` API scopes.

## Need Help?

- 📖 **API Documentation**: `docs/REST_API.md`
- 🚀 **Quick Start**: `docs/REST_API_QUICKSTART.md`
- 🔍 **Interactive Docs**: `/api/docs`
- 📋 **Implementation Summary**: `REST_API_IMPLEMENTATION_SUMMARY.md`
