"""Utility module for seeding default permissions and roles"""

from app import db
from app.models import Permission, Role, User
from sqlalchemy.exc import IntegrityError


# Define all available permissions organized by category
DEFAULT_PERMISSIONS = [
    # Time Entry Permissions
    {"name": "view_own_time_entries", "description": "View own time entries", "category": "time_entries"},
    {
        "name": "view_all_time_entries",
        "description": "View all time entries from all users",
        "category": "time_entries",
    },
    {"name": "create_time_entries", "description": "Create time entries", "category": "time_entries"},
    {"name": "edit_own_time_entries", "description": "Edit own time entries", "category": "time_entries"},
    {"name": "edit_all_time_entries", "description": "Edit time entries from all users", "category": "time_entries"},
    {"name": "delete_own_time_entries", "description": "Delete own time entries", "category": "time_entries"},
    {
        "name": "delete_all_time_entries",
        "description": "Delete time entries from all users",
        "category": "time_entries",
    },
    # Project Permissions
    {"name": "view_projects", "description": "View projects", "category": "projects"},
    {"name": "create_projects", "description": "Create new projects", "category": "projects"},
    {"name": "edit_projects", "description": "Edit project details", "category": "projects"},
    {"name": "delete_projects", "description": "Delete projects", "category": "projects"},
    {"name": "archive_projects", "description": "Archive/unarchive projects", "category": "projects"},
    {"name": "manage_project_costs", "description": "Manage project costs and budgets", "category": "projects"},
    # Task Permissions
    {"name": "view_own_tasks", "description": "View own tasks", "category": "tasks"},
    {"name": "view_all_tasks", "description": "View all tasks", "category": "tasks"},
    {"name": "create_tasks", "description": "Create tasks", "category": "tasks"},
    {"name": "edit_own_tasks", "description": "Edit own tasks", "category": "tasks"},
    {"name": "edit_all_tasks", "description": "Edit all tasks", "category": "tasks"},
    {"name": "delete_own_tasks", "description": "Delete own tasks", "category": "tasks"},
    {"name": "delete_all_tasks", "description": "Delete all tasks", "category": "tasks"},
    {"name": "assign_tasks", "description": "Assign tasks to users", "category": "tasks"},
    # Client Permissions
    {"name": "view_clients", "description": "View clients", "category": "clients"},
    {"name": "create_clients", "description": "Create new clients", "category": "clients"},
    {"name": "edit_clients", "description": "Edit client details", "category": "clients"},
    {"name": "delete_clients", "description": "Delete clients", "category": "clients"},
    {"name": "manage_client_notes", "description": "Manage client notes", "category": "clients"},
    # Issue Permissions
    {"name": "view_all_issues", "description": "View all issues from all clients", "category": "issues"},
    {"name": "view_own_issues", "description": "View issues for assigned clients/projects", "category": "issues"},
    {"name": "create_issues", "description": "Create new issues", "category": "issues"},
    {"name": "edit_all_issues", "description": "Edit all issues", "category": "issues"},
    {"name": "edit_own_issues", "description": "Edit issues for assigned clients/projects", "category": "issues"},
    {"name": "delete_issues", "description": "Delete issues", "category": "issues"},
    # Invoice Permissions
    {"name": "view_own_invoices", "description": "View own invoices", "category": "invoices"},
    {"name": "view_all_invoices", "description": "View all invoices", "category": "invoices"},
    {"name": "create_invoices", "description": "Create invoices", "category": "invoices"},
    {"name": "edit_invoices", "description": "Edit invoices", "category": "invoices"},
    {"name": "delete_invoices", "description": "Delete invoices", "category": "invoices"},
    {"name": "send_invoices", "description": "Send invoices to clients", "category": "invoices"},
    {"name": "manage_payments", "description": "Manage invoice payments", "category": "invoices"},
    {"name": "manage_payment_gateways", "description": "Manage payment gateway configurations", "category": "invoices"},
    # Report Permissions
    {"name": "view_own_reports", "description": "View own reports", "category": "reports"},
    {"name": "view_all_reports", "description": "View reports for all users", "category": "reports"},
    {"name": "export_reports", "description": "Export reports to CSV/PDF", "category": "reports"},
    {"name": "create_saved_reports", "description": "Create and save custom reports", "category": "reports"},
    # User Management Permissions
    {"name": "view_users", "description": "View users list", "category": "users"},
    {"name": "create_users", "description": "Create new users", "category": "users"},
    {"name": "edit_users", "description": "Edit user details", "category": "users"},
    {"name": "delete_users", "description": "Delete users", "category": "users"},
    {"name": "manage_user_roles", "description": "Assign roles to users", "category": "users"},
    # System Permissions
    {"name": "manage_settings", "description": "Manage system settings", "category": "system"},
    {"name": "view_system_info", "description": "View system information", "category": "system"},
    {"name": "manage_backups", "description": "Create and restore backups", "category": "system"},
    {"name": "manage_telemetry", "description": "Manage telemetry settings", "category": "system"},
    {"name": "view_audit_logs", "description": "View audit logs", "category": "system"},
    # Role & Permission Management (Super Admin only)
    {"name": "manage_roles", "description": "Create, edit, and delete roles", "category": "administration"},
    {"name": "manage_permissions", "description": "Assign permissions to roles", "category": "administration"},
    {"name": "view_permissions", "description": "View permissions and roles", "category": "administration"},
    # Inventory Management Permissions
    {"name": "view_inventory", "description": "View inventory items and stock levels", "category": "inventory"},
    {"name": "manage_stock_items", "description": "Create, edit, and delete stock items", "category": "inventory"},
    {"name": "manage_warehouses", "description": "Create, edit, and delete warehouses", "category": "inventory"},
    {"name": "view_stock_levels", "description": "View current stock levels", "category": "inventory"},
    {
        "name": "manage_stock_movements",
        "description": "Record stock movements and adjustments",
        "category": "inventory",
    },
    {"name": "transfer_stock", "description": "Transfer stock between warehouses", "category": "inventory"},
    {"name": "view_stock_history", "description": "View stock movement history", "category": "inventory"},
    {
        "name": "manage_stock_reservations",
        "description": "Create and manage stock reservations",
        "category": "inventory",
    },
    {"name": "view_inventory_reports", "description": "View inventory reports", "category": "inventory"},
    {
        "name": "approve_stock_adjustments",
        "description": "Approve stock adjustments (if approval workflow enabled)",
        "category": "inventory",
    },
    {"name": "manage_suppliers", "description": "Create, edit, and delete suppliers", "category": "inventory"},
    {
        "name": "manage_purchase_orders",
        "description": "Create, edit, and manage purchase orders",
        "category": "inventory",
    },
]


# Define default roles with their permissions
DEFAULT_ROLES = {
    "super_admin": {
        "description": "Super Administrator with full system access",
        "is_system_role": True,
        "permissions": [p["name"] for p in DEFAULT_PERMISSIONS],  # All permissions
    },
    "admin": {
        "description": "Administrator with most privileges",
        "is_system_role": True,
        "permissions": [
            # Time entries
            "view_all_time_entries",
            "create_time_entries",
            "edit_all_time_entries",
            "delete_all_time_entries",
            # Projects
            "view_projects",
            "create_projects",
            "edit_projects",
            "delete_projects",
            "archive_projects",
            "manage_project_costs",
            # Tasks
            "view_all_tasks",
            "create_tasks",
            "edit_all_tasks",
            "delete_all_tasks",
            "assign_tasks",
            # Clients
            "view_clients",
            "create_clients",
            "edit_clients",
            "delete_clients",
            "manage_client_notes",
            # Invoices
            "view_all_invoices",
            "create_invoices",
            "edit_invoices",
            "delete_invoices",
            "send_invoices",
            "manage_payments",
            "manage_payment_gateways",
            # Reports
            "view_all_reports",
            "export_reports",
            "create_saved_reports",
            # Users
            "view_users",
            "create_users",
            "edit_users",
            "delete_users",
            # System
            "manage_settings",
            "view_system_info",
            "manage_backups",
            "manage_telemetry",
            "view_audit_logs",
            # Inventory
            "view_inventory",
            "manage_stock_items",
            "manage_warehouses",
            "view_stock_levels",
            "manage_stock_movements",
            "transfer_stock",
            "view_stock_history",
            "manage_stock_reservations",
            "view_inventory_reports",
            "approve_stock_adjustments",
            "manage_suppliers",
            "manage_purchase_orders",
            # Issues
            "view_all_issues",
            "create_issues",
            "edit_all_issues",
        ],
    },
    "manager": {
        "description": "Team Manager with oversight capabilities",
        "is_system_role": True,
        "permissions": [
            # Time entries
            "view_all_time_entries",
            "create_time_entries",
            "edit_own_time_entries",
            "delete_own_time_entries",
            # Projects
            "view_projects",
            "create_projects",
            "edit_projects",
            "delete_projects",
            "manage_project_costs",
            # Tasks
            "view_all_tasks",
            "create_tasks",
            "edit_all_tasks",
            "assign_tasks",
            # Clients
            "view_clients",
            "create_clients",
            "edit_clients",
            "manage_client_notes",
            # Invoices
            "view_all_invoices",
            "create_invoices",
            "edit_invoices",
            "delete_invoices",
            "send_invoices",
            "manage_payments",
            "manage_payment_gateways",
            # Reports
            "view_all_reports",
            "export_reports",
            "create_saved_reports",
            # Users
            "view_users",
            # Issues
            "view_all_issues",
            "create_issues",
            "edit_all_issues",
            # Inventory
            "view_inventory",
            "manage_stock_items",
            "view_stock_levels",
            "manage_stock_movements",
            "transfer_stock",
            "view_stock_history",
            "manage_stock_reservations",
            "view_inventory_reports",
            "approve_stock_adjustments",
        ],
    },
    "user": {
        "description": "Standard User",
        "is_system_role": True,
        "permissions": [
            # Time entries
            "view_own_time_entries",
            "create_time_entries",
            "edit_own_time_entries",
            "delete_own_time_entries",
            # Projects
            "view_projects",
            # Tasks
            "view_own_tasks",
            "create_tasks",
            "edit_own_tasks",
            "delete_own_tasks",
            # Clients
            "view_clients",
            # Invoices
            "view_own_invoices",
            # Reports
            "view_own_reports",
            "export_reports",
            # Inventory
            "view_inventory",
            "view_stock_levels",
        ],
    },
    "viewer": {
        "description": "Read-only User",
        "is_system_role": True,
        "permissions": [
            "view_own_time_entries",
            "view_projects",
            "view_own_tasks",
            "view_clients",
            "view_own_invoices",
            "view_own_reports",
            # Inventory
            "view_inventory",
            "view_stock_levels",
        ],
    },
}


def seed_permissions():
    """Seed default permissions into the database"""
    print("Seeding permissions...")
    created_count = 0
    existing_count = 0

    for perm_data in DEFAULT_PERMISSIONS:
        # Check if permission already exists
        existing = Permission.query.filter_by(name=perm_data["name"]).first()
        if existing:
            existing_count += 1
            # Update description if it changed
            if existing.description != perm_data["description"]:
                existing.description = perm_data["description"]
                existing.category = perm_data["category"]
            continue

        # Create new permission
        permission = Permission(
            name=perm_data["name"], description=perm_data["description"], category=perm_data["category"]
        )
        db.session.add(permission)
        created_count += 1

    try:
        db.session.commit()
        print(f"Permissions seeded: {created_count} created, {existing_count} already existed")
        return True
    except IntegrityError as e:
        db.session.rollback()
        print(f"Error seeding permissions: {e}")
        return False


def seed_roles():
    """Seed default roles with their permissions"""
    print("Seeding roles...")
    created_count = 0
    existing_count = 0

    for role_name, role_data in DEFAULT_ROLES.items():
        # Check if role already exists
        existing = Role.query.filter_by(name=role_name).first()

        if existing:
            existing_count += 1
            # Update description if it changed
            if existing.description != role_data["description"]:
                existing.description = role_data["description"]
            role = existing
        else:
            # Create new role
            role = Role(
                name=role_name, description=role_data["description"], is_system_role=role_data["is_system_role"]
            )
            db.session.add(role)
            created_count += 1

        # Assign permissions to role
        for perm_name in role_data["permissions"]:
            permission = Permission.query.filter_by(name=perm_name).first()
            if permission and not role.has_permission(perm_name):
                role.add_permission(permission)

    try:
        db.session.commit()
        print(f"Roles seeded: {created_count} created, {existing_count} already existed")
        return True
    except IntegrityError as e:
        db.session.rollback()
        print(f"Error seeding roles: {e}")
        return False


def migrate_legacy_users():
    """Migrate users with legacy 'role' field to new role system"""
    print("Migrating legacy users to new role system...")
    migrated_count = 0

    # Get all users
    users = User.query.all()

    for user in users:
        # Skip if user already has roles assigned
        if len(user.roles) > 0:
            continue

        # Map legacy role to new role system
        if user.role == "admin":
            admin_role = Role.query.filter_by(name="admin").first()
            if admin_role:
                user.add_role(admin_role)
                migrated_count += 1
        else:  # user.role == 'user' or any other value
            user_role = Role.query.filter_by(name="user").first()
            if user_role:
                user.add_role(user_role)
                migrated_count += 1

    try:
        db.session.commit()
        print(f"Migrated {migrated_count} users to new role system")
        return True
    except Exception as e:
        db.session.rollback()
        print(f"Error migrating users: {e}")
        return False


def seed_all():
    """Seed all permissions, roles, and migrate users"""
    print("Starting permission system seeding...")

    if not seed_permissions():
        return False

    if not seed_roles():
        return False

    if not migrate_legacy_users():
        return False

    print("Permission system seeding completed successfully!")
    return True
