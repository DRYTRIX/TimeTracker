# Advanced Permission Handling System

## Overview

TimeTracker now includes a comprehensive, role-based permission system that allows administrators to control access to various features and functionality at a granular level. This system replaces the simple "admin" vs "user" model with a flexible role-based access control (RBAC) system.

## Key Concepts

### Permissions

**Permissions** are individual capabilities or actions that a user can perform in the system. Examples include:
- `view_all_time_entries` - View time entries from all users
- `create_projects` - Create new projects
- `edit_invoices` - Edit invoice details
- `manage_settings` - Access and modify system settings

Each permission has:
- **Name**: A unique identifier (e.g., `edit_projects`)
- **Description**: Human-readable explanation of what the permission allows
- **Category**: Logical grouping (e.g., `projects`, `invoices`, `system`)

### Roles

**Roles** are collections of permissions that can be assigned to users. Instead of granting individual permissions to each user, you assign roles that bundle related permissions together.

Examples of roles:
- **Super Admin**: Full system access with all permissions
- **Admin**: Most administrative capabilities except role management
- **Manager**: Can oversee projects, tasks, and team members
- **User**: Standard access for time tracking and personal data
- **Viewer**: Read-only access

Each role has:
- **Name**: Unique identifier
- **Description**: Explanation of the role's purpose
- **System Role Flag**: Indicates whether the role is built-in (cannot be deleted)
- **Permissions**: Collection of permissions assigned to the role

### Users and Roles

Users can be assigned one or more roles. A user's effective permissions are the union of all permissions from their assigned roles.

## Default Roles and Permissions

### System Roles

The following system roles are created by default:

#### Super Admin
- **All permissions** in the system
- Can manage roles and permissions themselves
- Intended for system administrators

#### Admin
- All permissions except role/permission management
- Can manage users, projects, invoices, settings
- Cannot modify the permission system itself

#### Manager
- Oversight capabilities for teams and projects
- Can view all time entries and reports
- Can create and edit projects, tasks, and clients
- Can create and send invoices
- Cannot delete users or modify system settings

#### User
- Standard time tracking capabilities
- Can create and edit own time entries
- Can create and manage own tasks
- View-only access to projects and clients
- Can view own reports and invoices

#### Viewer
- Read-only access
- Can view own time entries, tasks, and reports
- Cannot create or modify anything

#### Subcontractor
- Same capabilities as User but **restricted to assigned clients and their projects only**
- Admins assign one or more clients to the user in Admin → Users → Edit user (section "Assigned Clients (Subcontractor)")
- The user sees only those clients, their projects, and related time entries, invoices, and reports
- Direct access to other clients or projects returns 403 Forbidden
- See [Subcontractor role and assigned clients](SUBCONTRACTOR_ROLE.md) for full details

### Permission Categories

Permissions are organized into the following categories:

#### Time Entries
- `view_own_time_entries`
- `view_all_time_entries`
- `create_time_entries`
- `edit_own_time_entries`
- `edit_all_time_entries`
- `delete_own_time_entries`
- `delete_all_time_entries`

#### Projects
- `view_projects`
- `create_projects`
- `edit_projects`
- `delete_projects`
- `archive_projects`
- `manage_project_costs`

#### Tasks
- `view_own_tasks`
- `view_all_tasks`
- `create_tasks`
- `edit_own_tasks`
- `edit_all_tasks`
- `delete_own_tasks`
- `delete_all_tasks`
- `assign_tasks`

#### Clients
- `view_clients`
- `create_clients`
- `edit_clients`
- `delete_clients`
- `manage_client_notes`

#### Invoices
- `view_own_invoices`
- `view_all_invoices`
- `create_invoices`
- `edit_invoices`
- `delete_invoices`
- `send_invoices`
- `manage_payments`

#### Reports
- `view_own_reports`
- `view_all_reports`
- `export_reports`
- `create_saved_reports`

#### User Management
- `view_users`
- `create_users`
- `edit_users`
- `delete_users`
- `manage_user_roles`

#### System
- `manage_settings`
- `view_system_info`
- `manage_backups`
- `manage_telemetry`
- `view_audit_logs`

#### Administration (Super Admin Only)
- `manage_roles`
- `manage_permissions`
- `view_permissions`

## Using the Permission System

### For Administrators

#### Viewing Roles

1. Navigate to **Admin Dashboard** → **Roles & Permissions**
2. View all available roles with their permission counts
3. Click on a role to see detailed information and assigned users

#### Creating Custom Roles

1. Go to **Admin Dashboard** → **Roles & Permissions**
2. Click **Create Role**
3. Enter:
   - Role name (e.g., "Project Manager")
   - Description (optional)
4. Select permissions by category
5. Click **Create Role**

**Note**: Custom roles can be modified or deleted. System roles cannot be deleted but serve as templates for custom roles.

#### Editing Roles

1. Navigate to the role list
2. Click **Edit** on a custom role (system roles cannot be edited)
3. Modify name, description, or permissions
4. Click **Update Role**

#### Assigning Roles to Users

1. Go to **Admin Dashboard** → **Manage Users**
2. Click **Edit** on a user
3. Click **Manage Roles & Permissions**
4. Select the roles to assign
5. Click **Update Roles**

Users can have multiple roles. Their effective permissions will be the combination of all assigned roles.

#### Viewing User Permissions

1. Edit a user in the admin panel
2. Click **Manage Roles & Permissions**
3. Scroll to "Current Effective Permissions" to see all permissions the user has

### For Developers

#### Checking Permissions in Code

Use the permission checking methods on the User model:

```python
from flask_login import current_user

# Check single permission
if current_user.has_permission('edit_projects'):
    # Allow editing

# Check if user has ANY of the permissions
if current_user.has_any_permission('edit_projects', 'delete_projects'):
    # Allow action

# Check if user has ALL of the permissions
if current_user.has_all_permissions('create_invoices', 'send_invoices'):
    # Allow action
```

#### Using Permission Decorators

Protect routes with permission decorators:

```python
from app.utils.permissions import permission_required

@app.route('/projects/<id>/edit')
@login_required
@permission_required('edit_projects')
def edit_project(id):
    # Only users with edit_projects permission can access
    pass

# Require multiple permissions (user needs ANY of them)
@app.route('/reports/export')
@login_required
@permission_required('view_all_reports', 'export_reports')
def export_report():
    pass

# Require ALL permissions
@app.route('/admin/critical')
@login_required
@permission_required('manage_settings', 'manage_backups', require_all=True)
def critical_admin_action():
    pass
```

#### Admin or Permission Required

For gradual migration, use the `admin_or_permission_required` decorator:

```python
from app.utils.permissions import admin_or_permission_required

@app.route('/projects/delete')
@login_required
@admin_or_permission_required('delete_projects')
def delete_project():
    # Admins OR users with delete_projects permission can access
    pass
```

#### Checking Permissions in Templates

Use the template helpers to conditionally show UI elements:

```html
{% if has_permission('edit_projects') %}
    <a href="{{ url_for('projects.edit', id=project.id) }}">Edit Project</a>
{% endif %}

{% if has_any_permission('create_invoices', 'edit_invoices') %}
    <button>Manage Invoices</button>
{% endif %}

{% if has_all_permissions('view_all_reports', 'export_reports') %}
    <a href="{{ url_for('reports.export') }}">Export All Reports</a>
{% endif %}
```

## Migration from Legacy System

### Backward Compatibility

The new permission system is fully backward compatible with the existing "role" field:

- Users with `role='admin'` are automatically recognized as administrators
- Legacy admin users have all permissions (even without assigned roles)
- The `is_admin` property checks both the legacy role field and new role assignments

### Migrating Existing Users

To migrate users to the new system:

1. Run the migration command:
   ```bash
   flask seed_permissions_cmd
   ```

2. This will:
   - Create all default permissions
   - Create all default roles
   - Migrate existing users:
     - Users with `role='admin'` get the "admin" role
     - Users with `role='user'` get the "user" role

3. Optionally, review and adjust role assignments in the admin panel

### Updating Permissions After Updates

If new permissions are added in a system update:

```bash
flask update_permissions
```

This command updates permissions and roles without affecting user assignments.

## Database Schema

### Tables

#### `permissions`
- `id` - Primary key
- `name` - Unique permission identifier
- `description` - Human-readable description
- `category` - Permission category
- `created_at` - Timestamp

#### `roles`
- `id` - Primary key
- `name` - Unique role identifier
- `description` - Role description
- `is_system_role` - Boolean flag
- `created_at` - Creation timestamp
- `updated_at` - Last update timestamp

#### `role_permissions` (Association Table)
- `role_id` - Foreign key to roles
- `permission_id` - Foreign key to permissions
- `created_at` - Assignment timestamp

#### `user_roles` (Association Table)
- `user_id` - Foreign key to users
- `role_id` - Foreign key to roles
- `assigned_at` - Assignment timestamp

## API Endpoints

### Get User Permissions
```
GET /api/users/<user_id>/permissions
```

Returns:
```json
{
  "user_id": 1,
  "username": "john",
  "roles": [
    {"id": 1, "name": "manager"}
  ],
  "permissions": [
    {"id": 1, "name": "view_all_time_entries", "description": "..."},
    {"id": 2, "name": "create_projects", "description": "..."}
  ]
}
```

### Get Role Permissions
```
GET /api/roles/<role_id>/permissions
```

Returns:
```json
{
  "role_id": 1,
  "name": "manager",
  "description": "Team Manager with oversight capabilities",
  "is_system_role": true,
  "permissions": [
    {"id": 1, "name": "view_all_time_entries", "category": "time_entries", "description": "..."}
  ]
}
```

## Best Practices

### Creating Custom Roles

1. **Start with a system role**: Use system roles as templates
2. **Be specific**: Create roles for specific job functions (e.g., "Invoice Manager", "Project Lead")
3. **Least privilege**: Grant only the permissions needed for the role's purpose
4. **Document**: Add clear descriptions to custom roles

### Permission Naming

- Use snake_case: `create_projects`, not `CreateProjects`
- Action first: `edit_invoices`, not `invoices_edit`
- Be specific: `view_all_time_entries` vs `view_own_time_entries`

### Testing Permissions

Always test permission changes:

1. Create a test user
2. Assign the role
3. Log in as that user
4. Verify they can/cannot access expected features

## Troubleshooting

### User Cannot Access Feature

1. Check user's assigned roles
2. Verify the roles have the required permission
3. Check if the feature requires multiple permissions
4. Ensure user account is active

### Cannot Edit/Delete Role

- System roles cannot be edited or deleted
- Roles assigned to users cannot be deleted (reassign users first)

### Legacy Admin Lost Permissions

If a legacy admin user (with `role='admin'`) loses permissions:

1. Verify their `role` field is still 'admin'
2. If using new role system, assign them the "super_admin" or "admin" role
3. The system checks both legacy role and new roles

### Permission Changes Not Taking Effect

- Log out and log back in
- Permissions are loaded on login
- Check browser cache/session

## Security Considerations

- **Super Admin Role**: Assign sparingly - it has full system access
- **Regular Audits**: Review user role assignments periodically
- **Separation of Duties**: Don't assign conflicting roles (e.g., invoice creation + approval)
- **Testing**: Always test in a non-production environment first

## Future Enhancements

Planned features:
- **Permission inheritance**: Hierarchical permissions
- **Time-based roles**: Temporary role assignments
- **Audit logging**: Track permission changes
- **Role templates**: Exportable role configurations
- **API keys with permissions**: Scoped API access

## Support

For issues or questions about the permission system:
1. Check this documentation
2. Review the test files: `tests/test_permissions.py` and `tests/test_permissions_routes.py`
3. Check the implementation: `app/models/permission.py` and `app/utils/permissions.py`

