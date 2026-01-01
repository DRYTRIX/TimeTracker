"""Add permission system with roles and permissions

Revision ID: 030
Revises: 029
Create Date: 2025-10-24 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from datetime import datetime
from sqlalchemy import Table, Column, Integer, String, Boolean, DateTime, MetaData
from sqlalchemy.sql import table, column

# revision identifiers, used by Alembic.
revision = '030'
down_revision = '029'
branch_labels = None
depends_on = None


def upgrade():
    """Create tables for advanced permission system"""
    
    # Get connection to check if tables exist
    connection = op.get_bind()
    
    # Check if permissions table already exists (idempotent migration)
    inspector = sa.inspect(connection)
    existing_tables = inspector.get_table_names()
    
    # Create permissions table
    if 'permissions' not in existing_tables:
        op.create_table('permissions',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('name', sa.String(length=100), nullable=False),
            sa.Column('description', sa.String(length=255), nullable=True),
            sa.Column('category', sa.String(length=50), nullable=False),
            sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
            sa.PrimaryKeyConstraint('id')
        )
        op.create_index('idx_permissions_name', 'permissions', ['name'], unique=True)
        op.create_index('idx_permissions_category', 'permissions', ['category'])
    else:
        # Table exists, skip creation but ensure indexes exist (SQLite doesn't support if_not_exists)
        try:
            # Try to create index, ignore if it already exists
            connection.execute(sa.text("CREATE INDEX IF NOT EXISTS idx_permissions_name ON permissions(name)"))
        except:
            pass  # Index might already exist
        try:
            connection.execute(sa.text("CREATE INDEX IF NOT EXISTS idx_permissions_category ON permissions(category)"))
        except:
            pass  # Index might already exist
    
    # Create roles table
    if 'roles' not in existing_tables:
        op.create_table('roles',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('name', sa.String(length=50), nullable=False),
            sa.Column('description', sa.String(length=255), nullable=True),
            sa.Column('is_system_role', sa.Boolean(), nullable=False, server_default='false'),
            sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
            sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
            sa.PrimaryKeyConstraint('id')
        )
        op.create_index('idx_roles_name', 'roles', ['name'], unique=True)
    else:
        # Table exists, skip creation but ensure index exists
        try:
            connection.execute(sa.text("CREATE INDEX IF NOT EXISTS idx_roles_name ON roles(name)"))
        except:
            pass  # Index might already exist
    
    # Create role_permissions association table
    if 'role_permissions' not in existing_tables:
        op.create_table('role_permissions',
            sa.Column('role_id', sa.Integer(), nullable=False),
            sa.Column('permission_id', sa.Integer(), nullable=False),
            sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
            sa.ForeignKeyConstraint(['permission_id'], ['permissions.id'], ondelete='CASCADE'),
            sa.ForeignKeyConstraint(['role_id'], ['roles.id'], ondelete='CASCADE'),
            sa.PrimaryKeyConstraint('role_id', 'permission_id')
        )
    
    # Create user_roles association table
    if 'user_roles' not in existing_tables:
        op.create_table('user_roles',
            sa.Column('user_id', sa.Integer(), nullable=False),
            sa.Column('role_id', sa.Integer(), nullable=False),
            sa.Column('assigned_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
            sa.ForeignKeyConstraint(['role_id'], ['roles.id'], ondelete='CASCADE'),
            sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
            sa.PrimaryKeyConstraint('user_id', 'role_id')
        )
    
    # Seed default permissions and roles (only if tables were just created or are empty)
    # Check if permissions table has data
    if 'permissions' in existing_tables:
        try:
            result = connection.execute(sa.text("SELECT COUNT(*) FROM permissions")).scalar()
            if result == 0:
                # Table exists but is empty, seed it
                seed_permissions_and_roles()
        except:
            # If we can't check, assume it needs seeding (safer)
            pass
    else:
        # Tables were just created, seed them
        seed_permissions_and_roles()


def seed_permissions_and_roles():
    """Seed default permissions and roles into the database"""
    
    # Define permissions table for bulk insert
    permissions_table = table('permissions',
        column('id', Integer),
        column('name', String),
        column('description', String),
        column('category', String),
        column('created_at', DateTime)
    )
    
    # Define roles table for bulk insert
    roles_table = table('roles',
        column('id', Integer),
        column('name', String),
        column('description', String),
        column('is_system_role', Boolean),
        column('created_at', DateTime),
        column('updated_at', DateTime)
    )
    
    # Define role_permissions association table
    role_permissions_table = table('role_permissions',
        column('role_id', Integer),
        column('permission_id', Integer),
        column('created_at', DateTime)
    )
    
    # Define user_roles association table
    user_roles_table = table('user_roles',
        column('user_id', Integer),
        column('role_id', Integer),
        column('assigned_at', DateTime)
    )
    
    now = datetime.utcnow()
    
    # Default permissions data
    permissions_data = [
        # Time Entry Permissions (1-7)
        {'id': 1, 'name': 'view_own_time_entries', 'description': 'View own time entries', 'category': 'time_entries'},
        {'id': 2, 'name': 'view_all_time_entries', 'description': 'View all time entries from all users', 'category': 'time_entries'},
        {'id': 3, 'name': 'create_time_entries', 'description': 'Create time entries', 'category': 'time_entries'},
        {'id': 4, 'name': 'edit_own_time_entries', 'description': 'Edit own time entries', 'category': 'time_entries'},
        {'id': 5, 'name': 'edit_all_time_entries', 'description': 'Edit time entries from all users', 'category': 'time_entries'},
        {'id': 6, 'name': 'delete_own_time_entries', 'description': 'Delete own time entries', 'category': 'time_entries'},
        {'id': 7, 'name': 'delete_all_time_entries', 'description': 'Delete time entries from all users', 'category': 'time_entries'},
        
        # Project Permissions (8-13)
        {'id': 8, 'name': 'view_projects', 'description': 'View projects', 'category': 'projects'},
        {'id': 9, 'name': 'create_projects', 'description': 'Create new projects', 'category': 'projects'},
        {'id': 10, 'name': 'edit_projects', 'description': 'Edit project details', 'category': 'projects'},
        {'id': 11, 'name': 'delete_projects', 'description': 'Delete projects', 'category': 'projects'},
        {'id': 12, 'name': 'archive_projects', 'description': 'Archive/unarchive projects', 'category': 'projects'},
        {'id': 13, 'name': 'manage_project_costs', 'description': 'Manage project costs and budgets', 'category': 'projects'},
        
        # Task Permissions (14-21)
        {'id': 14, 'name': 'view_own_tasks', 'description': 'View own tasks', 'category': 'tasks'},
        {'id': 15, 'name': 'view_all_tasks', 'description': 'View all tasks', 'category': 'tasks'},
        {'id': 16, 'name': 'create_tasks', 'description': 'Create tasks', 'category': 'tasks'},
        {'id': 17, 'name': 'edit_own_tasks', 'description': 'Edit own tasks', 'category': 'tasks'},
        {'id': 18, 'name': 'edit_all_tasks', 'description': 'Edit all tasks', 'category': 'tasks'},
        {'id': 19, 'name': 'delete_own_tasks', 'description': 'Delete own tasks', 'category': 'tasks'},
        {'id': 20, 'name': 'delete_all_tasks', 'description': 'Delete all tasks', 'category': 'tasks'},
        {'id': 21, 'name': 'assign_tasks', 'description': 'Assign tasks to users', 'category': 'tasks'},
        
        # Client Permissions (22-26)
        {'id': 22, 'name': 'view_clients', 'description': 'View clients', 'category': 'clients'},
        {'id': 23, 'name': 'create_clients', 'description': 'Create new clients', 'category': 'clients'},
        {'id': 24, 'name': 'edit_clients', 'description': 'Edit client details', 'category': 'clients'},
        {'id': 25, 'name': 'delete_clients', 'description': 'Delete clients', 'category': 'clients'},
        {'id': 26, 'name': 'manage_client_notes', 'description': 'Manage client notes', 'category': 'clients'},
        
        # Invoice Permissions (27-33)
        {'id': 27, 'name': 'view_own_invoices', 'description': 'View own invoices', 'category': 'invoices'},
        {'id': 28, 'name': 'view_all_invoices', 'description': 'View all invoices', 'category': 'invoices'},
        {'id': 29, 'name': 'create_invoices', 'description': 'Create invoices', 'category': 'invoices'},
        {'id': 30, 'name': 'edit_invoices', 'description': 'Edit invoices', 'category': 'invoices'},
        {'id': 31, 'name': 'delete_invoices', 'description': 'Delete invoices', 'category': 'invoices'},
        {'id': 32, 'name': 'send_invoices', 'description': 'Send invoices to clients', 'category': 'invoices'},
        {'id': 33, 'name': 'manage_payments', 'description': 'Manage invoice payments', 'category': 'invoices'},
        
        # Report Permissions (34-37)
        {'id': 34, 'name': 'view_own_reports', 'description': 'View own reports', 'category': 'reports'},
        {'id': 35, 'name': 'view_all_reports', 'description': 'View reports for all users', 'category': 'reports'},
        {'id': 36, 'name': 'export_reports', 'description': 'Export reports to CSV/PDF', 'category': 'reports'},
        {'id': 37, 'name': 'create_saved_reports', 'description': 'Create and save custom reports', 'category': 'reports'},
        
        # User Management Permissions (38-42)
        {'id': 38, 'name': 'view_users', 'description': 'View users list', 'category': 'users'},
        {'id': 39, 'name': 'create_users', 'description': 'Create new users', 'category': 'users'},
        {'id': 40, 'name': 'edit_users', 'description': 'Edit user details', 'category': 'users'},
        {'id': 41, 'name': 'delete_users', 'description': 'Delete users', 'category': 'users'},
        {'id': 42, 'name': 'manage_user_roles', 'description': 'Assign roles to users', 'category': 'users'},
        
        # System Permissions (43-47)
        {'id': 43, 'name': 'manage_settings', 'description': 'Manage system settings', 'category': 'system'},
        {'id': 44, 'name': 'view_system_info', 'description': 'View system information', 'category': 'system'},
        {'id': 45, 'name': 'manage_backups', 'description': 'Create and restore backups', 'category': 'system'},
        {'id': 46, 'name': 'manage_telemetry', 'description': 'Manage telemetry settings', 'category': 'system'},
        {'id': 47, 'name': 'view_audit_logs', 'description': 'View audit logs', 'category': 'system'},
        
        # Administration Permissions (48-50)
        {'id': 48, 'name': 'manage_roles', 'description': 'Create, edit, and delete roles', 'category': 'administration'},
        {'id': 49, 'name': 'manage_permissions', 'description': 'Assign permissions to roles', 'category': 'administration'},
        {'id': 50, 'name': 'view_permissions', 'description': 'View permissions and roles', 'category': 'administration'},
    ]
    
    # Get connection for executing queries
    connection = op.get_bind()
    
    # Check if permissions already exist (idempotent)
    try:
        existing_perms = connection.execute(sa.text("SELECT COUNT(*) FROM permissions")).scalar()
        if existing_perms == 0:
            # Insert permissions
            for perm in permissions_data:
                perm['created_at'] = now
            op.bulk_insert(permissions_table, permissions_data)
    except:
        # If table doesn't exist or error, try to insert anyway
        for perm in permissions_data:
            perm['created_at'] = now
        try:
            op.bulk_insert(permissions_table, permissions_data)
        except:
            pass  # Permissions might already exist
    
    # Default roles data
    roles_data = [
        {'id': 1, 'name': 'super_admin', 'description': 'Super Administrator with full system access', 'is_system_role': True},
        {'id': 2, 'name': 'admin', 'description': 'Administrator with most privileges', 'is_system_role': True},
        {'id': 3, 'name': 'manager', 'description': 'Team Manager with oversight capabilities', 'is_system_role': True},
        {'id': 4, 'name': 'user', 'description': 'Standard User', 'is_system_role': True},
        {'id': 5, 'name': 'viewer', 'description': 'Read-only User', 'is_system_role': True},
    ]
    
    # Check if roles already exist (idempotent)
    try:
        existing_roles = connection.execute(sa.text("SELECT COUNT(*) FROM roles")).scalar()
        if existing_roles == 0:
            # Insert roles
            for role in roles_data:
                role['created_at'] = now
                role['updated_at'] = now
            op.bulk_insert(roles_table, roles_data)
    except:
        # If table doesn't exist or error, try to insert anyway
        for role in roles_data:
            role['created_at'] = now
            role['updated_at'] = now
        try:
            op.bulk_insert(roles_table, roles_data)
        except:
            pass  # Roles might already exist
    
    # Fix sequences after bulk insert to prevent duplicate key errors (PostgreSQL only)
    # Check if we're using PostgreSQL
    if connection.dialect.name == 'postgresql':
        # Fix roles sequence - set to max(id) + 1
        try:
            connection.execute(sa.text("""
                DO $$
                BEGIN
                    CREATE SEQUENCE IF NOT EXISTS roles_id_seq;
                    IF NOT EXISTS (
                        SELECT 1 FROM pg_depend 
                        WHERE objid = 'roles_id_seq'::regclass 
                        AND refobjid = 'roles'::regclass
                    ) THEN
                        ALTER TABLE roles ALTER COLUMN id SET DEFAULT nextval('roles_id_seq');
                        ALTER SEQUENCE roles_id_seq OWNED BY roles.id;
                    END IF;
                    PERFORM setval('roles_id_seq', 
                        COALESCE((SELECT MAX(id) FROM roles), 0) + 1, 
                        false);
                END $$;
            """))
        except:
            pass  # Sequence might already be set
        
        # Fix permissions sequence - set to max(id) + 1
        try:
            connection.execute(sa.text("""
                DO $$
                BEGIN
                    CREATE SEQUENCE IF NOT EXISTS permissions_id_seq;
                    IF NOT EXISTS (
                        SELECT 1 FROM pg_depend 
                        WHERE objid = 'permissions_id_seq'::regclass 
                        AND refobjid = 'permissions'::regclass
                    ) THEN
                        ALTER TABLE permissions ALTER COLUMN id SET DEFAULT nextval('permissions_id_seq');
                        ALTER SEQUENCE permissions_id_seq OWNED BY permissions.id;
                    END IF;
                    PERFORM setval('permissions_id_seq', 
                        COALESCE((SELECT MAX(id) FROM permissions), 0) + 1, 
                        false);
                END $$;
            """))
        except:
            pass  # Sequence might already be set
    
    # Define role-permission mappings
    role_permission_mappings = []
    
    # Super Admin - All permissions (1-50)
    for perm_id in range(1, 51):
        role_permission_mappings.append({'role_id': 1, 'permission_id': perm_id, 'created_at': now})
    
    # Admin - All except role/permission management (1-47)
    for perm_id in range(1, 48):
        role_permission_mappings.append({'role_id': 2, 'permission_id': perm_id, 'created_at': now})
    
    # Manager - Oversight permissions
    manager_perms = [2, 3, 4, 6, 8, 9, 10, 13, 15, 16, 18, 21, 22, 23, 24, 26, 28, 29, 30, 32, 35, 36, 37, 38]
    for perm_id in manager_perms:
        role_permission_mappings.append({'role_id': 3, 'permission_id': perm_id, 'created_at': now})
    
    # User - Standard permissions
    user_perms = [1, 3, 4, 6, 8, 14, 16, 17, 19, 22, 27, 34, 36]
    for perm_id in user_perms:
        role_permission_mappings.append({'role_id': 4, 'permission_id': perm_id, 'created_at': now})
    
    # Viewer - Read-only permissions
    viewer_perms = [1, 8, 14, 22, 27, 34]
    for perm_id in viewer_perms:
        role_permission_mappings.append({'role_id': 5, 'permission_id': perm_id, 'created_at': now})
    
    # Insert role-permission mappings (only if they don't exist)
    try:
        existing_mappings = connection.execute(sa.text("SELECT COUNT(*) FROM role_permissions")).scalar()
        if existing_mappings == 0:
            op.bulk_insert(role_permissions_table, role_permission_mappings)
    except:
        # If table doesn't exist or error, try to insert anyway
        try:
            op.bulk_insert(role_permissions_table, role_permission_mappings)
        except:
            pass  # Mappings might already exist
    
    # Migrate existing users to new role system
    try:
        # Check if user_roles table has data
        existing_user_roles = connection.execute(sa.text("SELECT COUNT(*) FROM user_roles")).scalar()
        if existing_user_roles == 0:
            # Find all users with role='admin' and assign them the 'admin' role
            admin_users = connection.execute(sa.text("SELECT id FROM users WHERE role = 'admin'")).fetchall()
            admin_role_assignments = [{'user_id': user[0], 'role_id': 2, 'assigned_at': now} for user in admin_users]
            if admin_role_assignments:
                op.bulk_insert(user_roles_table, admin_role_assignments)
            
            # Find all users with role='user' and assign them the 'user' role
            regular_users = connection.execute(sa.text("SELECT id FROM users WHERE role = 'user'")).fetchall()
            user_role_assignments = [{'user_id': user[0], 'role_id': 4, 'assigned_at': now} for user in regular_users]
            if user_role_assignments:
                op.bulk_insert(user_roles_table, user_role_assignments)
    except:
        pass  # User roles might already be assigned


def downgrade():
    """Remove permission system tables"""
    op.drop_table('user_roles')
    op.drop_table('role_permissions')
    op.drop_index('idx_roles_name', table_name='roles')
    op.drop_table('roles')
    op.drop_index('idx_permissions_category', table_name='permissions')
    op.drop_index('idx_permissions_name', table_name='permissions')
    op.drop_table('permissions')

