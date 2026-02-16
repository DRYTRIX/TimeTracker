# RBAC Permission Model (Route-Level)

This document describes how route-level access control is applied across the application. For the full role and permission system (roles, permissions, categories), see [ADVANCED_PERMISSIONS.md](../ADVANCED_PERMISSIONS.md).

## Two patterns

### 1. Permission-scoped routes

These blueprints protect routes with `@admin_or_permission_required("permission_name")` in addition to `@login_required`. Only users who are admins or have the given permission can access the route.

**Blueprints using permission decorators:**

- **admin** – `access_admin`, `view_users`, `create_users`, `edit_users`, `delete_users`, `manage_telemetry`, `manage_settings`, `manage_backups`, `view_system_info`, `manage_oidc`, `manage_api_tokens`, `manage_integrations`
- **audit_logs** – `view_audit_logs`
- **per_diem** – `per_diem_rates.view`, `per_diem_rates.create`, `per_diem_rates.edit`, `per_diem_rates.delete`
- **inventory** – `view_inventory`, `manage_stock_items`, `manage_warehouses`, `view_stock_levels`, `view_stock_history`, `manage_stock_movements`, `transfer_stock`, `manage_stock_reservations`, `manage_suppliers`, `manage_purchase_orders`, `view_inventory_reports`
- **clients** – permission checks where applicable
- **projects** – `create_projects` (and others where applied)
- **kanban** – permission checks where applied
- **webhooks** – permission checks where applied
- **project_templates** – permission checks where applied
- **quotes** – permission checks where applied
- **custom_field_definitions** – permission checks where applied
- **invoice_approvals** – permission checks where applied
- **payment_gateways** – permission checks where applied
- **kiosk** – permission checks where applied
- **offers** – permission checks where applied
- **link_templates** – permission checks where applied
- **expense_categories** – permission checks where applied

### 2. All authenticated users (with optional scope)

These blueprints use only `@login_required`. Any logged-in user can access the routes. **Scope-restricted users** (e.g. users with the **Subcontractor** role) see only data for their assigned clients and projects: list and detail routes for clients, projects, time entries, reports, invoices, and API v1 apply scope filters and return 403 for direct access to out-of-scope resources. See [SUBCONTRACTOR_ROLE.md](../SUBCONTRACTOR_ROLE.md).

**Examples:** deals, leads, invoices (main routes), timer, reports, calendar, expenses (main routes), main dashboard, time_approvals, contacts, tasks, client_notes, budget_alerts, payments, recurring_invoices, etc.

## When to add permission decorators

- **New admin-only or sensitive feature:** Use `@admin_or_permission_required("appropriate_permission")` and define the permission in the permission system if it does not exist.
- **New feature for all users:** Use only `@login_required`.
- **Existing “login only” route:** Leave as-is unless you are explicitly tightening access; then add a permission and document it in ADVANCED_PERMISSIONS.md.

## API v1 (REST)

REST API v1 uses API token scopes (e.g. `read:deals`, `write:time_entries`) rather than web permission names. See [API Token Scopes](../api/API_TOKEN_SCOPES.md) and [REST_API.md](../api/REST_API.md).
