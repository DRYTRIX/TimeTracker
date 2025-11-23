"""Add performance indexes for common queries

Revision ID: 062
Revises: 061
Create Date: 2025-01-27

This migration adds indexes to improve query performance for common operations:
- Time entry lookups by date ranges
- Project lookups by status and client
- Invoice lookups by status and date
- Composite indexes for frequently queried combinations
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '062'
down_revision = '061'
branch_labels = None
depends_on = None


def upgrade():
    """Add performance indexes"""
    
    # Create inspector once for reuse in conditional index creation
    from sqlalchemy import inspect
    bind = op.get_bind()
    inspector = inspect(bind)
    
    def index_exists(table_name, index_name):
        """Check if an index exists"""
        try:
            indexes = [idx['name'] for idx in inspector.get_indexes(table_name)]
            return index_name in indexes
        except Exception:
            return False
    
    def create_index_safe(index_name, table_name, columns):
        """Safely create an index if it doesn't exist"""
        try:
            if not index_exists(table_name, index_name):
                op.create_index(index_name, table_name, columns, unique=False)
        except Exception:
            # Index might already exist or table might not exist - skip
            pass
    
    # Time entries - composite indexes for common queries
    # Index for user time entries with date filtering
    create_index_safe('ix_time_entries_user_start_time', 'time_entries', ['user_id', 'start_time'])
    
    # Index for project time entries with date filtering
    create_index_safe('ix_time_entries_project_start_time', 'time_entries', ['project_id', 'start_time'])
    
    # Index for billable entries lookup
    create_index_safe('ix_time_entries_billable_start_time', 'time_entries', ['billable', 'start_time'])
    
    # Index for active timer lookup (user_id + end_time IS NULL)
    # Note: PostgreSQL supports partial indexes, SQLite doesn't
    # This is a best-effort index
    create_index_safe('ix_time_entries_user_end_time', 'time_entries', ['user_id', 'end_time'])
    
    # Projects - composite indexes
    # Index for active projects by client
    create_index_safe('ix_projects_client_status', 'projects', ['client_id', 'status'])
    
    # Index for billable active projects
    create_index_safe('ix_projects_billable_status', 'projects', ['billable', 'status'])
    
    # Invoices - composite indexes
    # Index for invoices by status and date
    create_index_safe('ix_invoices_status_due_date', 'invoices', ['status', 'due_date'])
    
    # Index for client invoices
    create_index_safe('ix_invoices_client_status', 'invoices', ['client_id', 'status'])
    
    # Index for project invoices
    create_index_safe('ix_invoices_project_issue_date', 'invoices', ['project_id', 'issue_date'])
    
    # Tasks - composite indexes
    # Index for project tasks by status
    create_index_safe('ix_tasks_project_status', 'tasks', ['project_id', 'status'])
    
    # Index for user tasks (using assigned_to, not assignee_id)
    # Check if column exists before creating index
    try:
        columns = [col['name'] for col in inspector.get_columns('tasks')]
        
        if 'assigned_to' in columns:
            create_index_safe('ix_tasks_assigned_to_status', 'tasks', ['assigned_to', 'status'])
        elif 'assignee_id' in columns:
            create_index_safe('ix_tasks_assignee_id_status', 'tasks', ['assignee_id', 'status'])
    except Exception:
        # If we can't check, skip this index (it's not critical)
        pass
    
    # Expenses - composite indexes
    # Index for project expenses by date
    # Check if expenses table exists and has expense_date column
    try:
        if 'expenses' in inspector.get_table_names():
            columns = [col['name'] for col in inspector.get_columns('expenses')]
            if 'expense_date' in columns:
                create_index_safe('ix_expenses_project_date', 'expenses', ['project_id', 'expense_date'])
                create_index_safe('ix_expenses_billable_date', 'expenses', ['billable', 'expense_date'])
    except Exception:
        # If we can't check or expenses table doesn't exist, skip these indexes
        pass
    
    # Payments - composite indexes
    # Index for invoice payments
    try:
        if 'payments' in inspector.get_table_names():
            columns = [col['name'] for col in inspector.get_columns('payments')]
            if 'invoice_id' in columns and 'payment_date' in columns:
                create_index_safe('ix_payments_invoice_date', 'payments', ['invoice_id', 'payment_date'])
    except Exception:
        # If we can't check or payments table doesn't exist, skip this index
        pass
    
    # Comments - composite indexes
    # Index for task comments
    try:
        if 'comments' in inspector.get_table_names():
            columns = [col['name'] for col in inspector.get_columns('comments')]
            if 'task_id' in columns and 'created_at' in columns:
                create_index_safe('ix_comments_task_created', 'comments', ['task_id', 'created_at'])
            if 'project_id' in columns and 'created_at' in columns:
                create_index_safe('ix_comments_project_created', 'comments', ['project_id', 'created_at'])
    except Exception:
        # If we can't check or comments table doesn't exist, skip these indexes
        pass


def downgrade():
    """Remove performance indexes"""
    
    op.drop_index('ix_time_entries_user_start_time', table_name='time_entries')
    op.drop_index('ix_time_entries_project_start_time', table_name='time_entries')
    op.drop_index('ix_time_entries_billable_start_time', table_name='time_entries')
    op.drop_index('ix_time_entries_user_end_time', table_name='time_entries')
    
    op.drop_index('ix_projects_client_status', table_name='projects')
    op.drop_index('ix_projects_billable_status', table_name='projects')
    
    op.drop_index('ix_invoices_status_due_date', table_name='invoices')
    op.drop_index('ix_invoices_client_status', table_name='invoices')
    op.drop_index('ix_invoices_project_issue_date', table_name='invoices')
    
    op.drop_index('ix_tasks_project_status', table_name='tasks')
    # Drop index if it exists (may be named differently)
    try:
        op.drop_index('ix_tasks_assigned_to_status', table_name='tasks')
    except Exception:
        try:
            op.drop_index('ix_tasks_assignee_id_status', table_name='tasks')
        except Exception:
            pass  # Index may not exist
    
    # Drop expense indexes if they exist
    try:
        op.drop_index('ix_expenses_project_date', table_name='expenses')
    except Exception:
        pass
    try:
        op.drop_index('ix_expenses_billable_date', table_name='expenses')
    except Exception:
        pass
    
    # Drop payment indexes if they exist
    try:
        op.drop_index('ix_payments_invoice_date', table_name='payments')
    except Exception:
        pass
    
    # Drop comment indexes if they exist
    try:
        op.drop_index('ix_comments_task_created', table_name='comments')
    except Exception:
        pass
    try:
        op.drop_index('ix_comments_project_created', table_name='comments')
    except Exception:
        pass

