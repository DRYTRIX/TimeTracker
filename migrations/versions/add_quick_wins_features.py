"""Add quick wins features: time entry templates, activity feed, user preferences

Revision ID: quick_wins_001
Revises: 
Create Date: 2025-01-22 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '022'
down_revision = '021'
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    def _has_table(name: str) -> bool:
        try:
            return name in inspector.get_table_names()
        except Exception:
            return False

    def _has_index(table_name: str, index_name: str) -> bool:
        try:
            return any((idx.get("name") or "") == index_name for idx in inspector.get_indexes(table_name))
        except Exception:
            return False

    def _has_column(table_name: str, column_name: str) -> bool:
        try:
            return column_name in {c["name"] for c in inspector.get_columns(table_name)}
        except Exception:
            return False

    # Create time_entry_templates table
    if not _has_table('time_entry_templates'):
        op.create_table('time_entry_templates',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('user_id', sa.Integer(), nullable=False),
            sa.Column('name', sa.String(length=200), nullable=False),
            sa.Column('description', sa.Text(), nullable=True),
            sa.Column('project_id', sa.Integer(), nullable=False),
            sa.Column('task_id', sa.Integer(), nullable=True),
            sa.Column('default_duration_minutes', sa.Integer(), nullable=True),
            sa.Column('default_notes', sa.Text(), nullable=True),
            sa.Column('tags', sa.String(length=500), nullable=True),
            sa.Column('billable', sa.Boolean(), nullable=False, server_default='true'),
            sa.Column('usage_count', sa.Integer(), nullable=False, server_default='0'),
            sa.Column('last_used_at', sa.DateTime(), nullable=True),
            sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
            sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
            sa.ForeignKeyConstraint(['project_id'], ['projects.id'], ),
            sa.ForeignKeyConstraint(['task_id'], ['tasks.id'], ),
            sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
            sa.PrimaryKeyConstraint('id')
        )
    else:
        print("[Migration 022] ℹ Table time_entry_templates already exists, skipping creation")

    # Ensure indexes exist (best-effort / idempotent)
    idx_te_project = op.f('ix_time_entry_templates_project_id')
    idx_te_task = op.f('ix_time_entry_templates_task_id')
    idx_te_user = op.f('ix_time_entry_templates_user_id')
    if _has_table('time_entry_templates'):
        if not _has_index('time_entry_templates', idx_te_project):
            try:
                op.create_index(idx_te_project, 'time_entry_templates', ['project_id'], unique=False)
            except Exception:
                pass
        if not _has_index('time_entry_templates', idx_te_task):
            try:
                op.create_index(idx_te_task, 'time_entry_templates', ['task_id'], unique=False)
            except Exception:
                pass
        if not _has_index('time_entry_templates', idx_te_user):
            try:
                op.create_index(idx_te_user, 'time_entry_templates', ['user_id'], unique=False)
            except Exception:
                pass
    
    # Create activities table
    if not _has_table('activities'):
        op.create_table('activities',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('user_id', sa.Integer(), nullable=False),
            sa.Column('action', sa.String(length=50), nullable=False),
            sa.Column('entity_type', sa.String(length=50), nullable=False),
            sa.Column('entity_id', sa.Integer(), nullable=False),
            sa.Column('entity_name', sa.String(length=500), nullable=True),
            sa.Column('description', sa.Text(), nullable=True),
            sa.Column('extra_data', sa.JSON(), nullable=True),
            sa.Column('ip_address', sa.String(length=45), nullable=True),
            sa.Column('user_agent', sa.Text(), nullable=True),
            sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
            sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
            sa.PrimaryKeyConstraint('id')
        )
    else:
        print("[Migration 022] ℹ Table activities already exists, skipping creation")

    # Ensure indexes exist (best-effort / idempotent)
    if _has_table('activities'):
        for idx_name, cols in [
            (op.f('ix_activities_action'), ['action']),
            (op.f('ix_activities_created_at'), ['created_at']),
            (op.f('ix_activities_entity_id'), ['entity_id']),
            (op.f('ix_activities_entity_type'), ['entity_type']),
            (op.f('ix_activities_user_id'), ['user_id']),
            ('ix_activities_user_created', ['user_id', 'created_at']),
            ('ix_activities_entity', ['entity_type', 'entity_id']),
        ]:
            if not _has_index('activities', idx_name):
                try:
                    op.create_index(idx_name, 'activities', cols, unique=False)
                except Exception:
                    pass
    
    # Add user preference columns to users table
    with op.batch_alter_table('users', schema=None) as batch_op:
        if _has_table('users'):
            if not _has_column('users', 'email_notifications'):
                batch_op.add_column(sa.Column('email_notifications', sa.Boolean(), nullable=False, server_default='true'))
            if not _has_column('users', 'notification_overdue_invoices'):
                batch_op.add_column(sa.Column('notification_overdue_invoices', sa.Boolean(), nullable=False, server_default='true'))
            if not _has_column('users', 'notification_task_assigned'):
                batch_op.add_column(sa.Column('notification_task_assigned', sa.Boolean(), nullable=False, server_default='true'))
            if not _has_column('users', 'notification_task_comments'):
                batch_op.add_column(sa.Column('notification_task_comments', sa.Boolean(), nullable=False, server_default='true'))
            if not _has_column('users', 'notification_weekly_summary'):
                batch_op.add_column(sa.Column('notification_weekly_summary', sa.Boolean(), nullable=False, server_default='false'))
            if not _has_column('users', 'timezone'):
                batch_op.add_column(sa.Column('timezone', sa.String(length=50), nullable=True))
            if not _has_column('users', 'date_format'):
                batch_op.add_column(sa.Column('date_format', sa.String(length=20), nullable=False, server_default='YYYY-MM-DD'))
            if not _has_column('users', 'time_format'):
                batch_op.add_column(sa.Column('time_format', sa.String(length=10), nullable=False, server_default='24h'))
            if not _has_column('users', 'week_start_day'):
                batch_op.add_column(sa.Column('week_start_day', sa.Integer(), nullable=False, server_default='1'))


def downgrade():
    # Remove user preference columns
    with op.batch_alter_table('users', schema=None) as batch_op:
        batch_op.drop_column('week_start_day')
        batch_op.drop_column('time_format')
        batch_op.drop_column('date_format')
        batch_op.drop_column('timezone')
        batch_op.drop_column('notification_weekly_summary')
        batch_op.drop_column('notification_task_comments')
        batch_op.drop_column('notification_task_assigned')
        batch_op.drop_column('notification_overdue_invoices')
        batch_op.drop_column('email_notifications')
    
    # Drop activities table
    op.drop_index('ix_activities_entity', table_name='activities')
    op.drop_index('ix_activities_user_created', table_name='activities')
    op.drop_index(op.f('ix_activities_user_id'), table_name='activities')
    op.drop_index(op.f('ix_activities_entity_type'), table_name='activities')
    op.drop_index(op.f('ix_activities_entity_id'), table_name='activities')
    op.drop_index(op.f('ix_activities_created_at'), table_name='activities')
    op.drop_index(op.f('ix_activities_action'), table_name='activities')
    op.drop_table('activities')
    
    # Drop time_entry_templates table
    op.drop_index(op.f('ix_time_entry_templates_user_id'), table_name='time_entry_templates')
    op.drop_index(op.f('ix_time_entry_templates_task_id'), table_name='time_entry_templates')
    op.drop_index(op.f('ix_time_entry_templates_project_id'), table_name='time_entry_templates')
    op.drop_table('time_entry_templates')

