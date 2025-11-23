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
    
    # Time entries - composite indexes for common queries
    # Index for user time entries with date filtering
    op.create_index(
        'ix_time_entries_user_start_time',
        'time_entries',
        ['user_id', 'start_time'],
        unique=False
    )
    
    # Index for project time entries with date filtering
    op.create_index(
        'ix_time_entries_project_start_time',
        'time_entries',
        ['project_id', 'start_time'],
        unique=False
    )
    
    # Index for billable entries lookup
    op.create_index(
        'ix_time_entries_billable_start_time',
        'time_entries',
        ['billable', 'start_time'],
        unique=False
    )
    
    # Index for active timer lookup (user_id + end_time IS NULL)
    # Note: PostgreSQL supports partial indexes, SQLite doesn't
    # This is a best-effort index
    op.create_index(
        'ix_time_entries_user_end_time',
        'time_entries',
        ['user_id', 'end_time'],
        unique=False
    )
    
    # Projects - composite indexes
    # Index for active projects by client
    op.create_index(
        'ix_projects_client_status',
        'projects',
        ['client_id', 'status'],
        unique=False
    )
    
    # Index for billable active projects
    op.create_index(
        'ix_projects_billable_status',
        'projects',
        ['billable', 'status'],
        unique=False
    )
    
    # Invoices - composite indexes
    # Index for invoices by status and date
    op.create_index(
        'ix_invoices_status_due_date',
        'invoices',
        ['status', 'due_date'],
        unique=False
    )
    
    # Index for client invoices
    op.create_index(
        'ix_invoices_client_status',
        'invoices',
        ['client_id', 'status'],
        unique=False
    )
    
    # Index for project invoices
    op.create_index(
        'ix_invoices_project_issue_date',
        'invoices',
        ['project_id', 'issue_date'],
        unique=False
    )
    
    # Tasks - composite indexes
    # Index for project tasks by status
    op.create_index(
        'ix_tasks_project_status',
        'tasks',
        ['project_id', 'status'],
        unique=False
    )
    
    # Index for user tasks
    op.create_index(
        'ix_tasks_assignee_id_status',
        'tasks',
        ['assignee_id', 'status'],
        unique=False
    )
    
    # Expenses - composite indexes
    # Index for project expenses by date
    op.create_index(
        'ix_expenses_project_date',
        'expenses',
        ['project_id', 'date'],
        unique=False
    )
    
    # Index for billable expenses
    op.create_index(
        'ix_expenses_billable_date',
        'expenses',
        ['billable', 'date'],
        unique=False
    )
    
    # Payments - composite indexes
    # Index for invoice payments
    op.create_index(
        'ix_payments_invoice_date',
        'payments',
        ['invoice_id', 'payment_date'],
        unique=False
    )
    
    # Comments - composite indexes
    # Index for task comments
    op.create_index(
        'ix_comments_task_created',
        'comments',
        ['task_id', 'created_at'],
        unique=False
    )
    
    # Index for project comments
    op.create_index(
        'ix_comments_project_created',
        'comments',
        ['project_id', 'created_at'],
        unique=False
    )


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
    op.drop_index('ix_tasks_assignee_id_status', table_name='tasks')
    
    op.drop_index('ix_expenses_project_date', table_name='expenses')
    op.drop_index('ix_expenses_billable_date', table_name='expenses')
    
    op.drop_index('ix_payments_invoice_date', table_name='payments')
    
    op.drop_index('ix_comments_task_created', table_name='comments')
    op.drop_index('ix_comments_project_created', table_name='comments')

