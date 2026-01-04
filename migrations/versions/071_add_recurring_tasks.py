"""Add recurring tasks table

Revision ID: 071_add_recurring_tasks
Revises: 070_add_time_entry_approvals
Create Date: 2025-01-27

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '071_add_recurring_tasks'
down_revision = '070_add_time_entry_approvals'
branch_labels = None
depends_on = None


def upgrade():
    """Create recurring_tasks table"""
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if 'recurring_tasks' not in inspector.get_table_names():
        op.create_table(
            'recurring_tasks',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('name', sa.String(length=200), nullable=False),
            sa.Column('project_id', sa.Integer(), nullable=False),
            sa.Column('frequency', sa.String(length=20), nullable=False),
            sa.Column('interval', sa.Integer(), nullable=False, server_default='1'),
            sa.Column('next_run_date', sa.Date(), nullable=False),
            sa.Column('end_date', sa.Date(), nullable=True),
            sa.Column('task_name_template', sa.String(length=500), nullable=False),
            sa.Column('description', sa.Text(), nullable=True),
            sa.Column('priority', sa.String(length=20), nullable=False, server_default='medium'),
            sa.Column('estimated_hours', sa.Numeric(10, 2), nullable=True),
            sa.Column('assigned_to', sa.Integer(), nullable=True),
            sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
            sa.Column('auto_assign', sa.Boolean(), nullable=False, server_default='false'),
            sa.Column('created_by', sa.Integer(), nullable=False),
            sa.Column('created_at', sa.DateTime(), nullable=False),
            sa.Column('updated_at', sa.DateTime(), nullable=False),
            sa.Column('last_created_at', sa.DateTime(), nullable=True),
            sa.Column('tasks_created_count', sa.Integer(), nullable=False, server_default='0'),
            sa.ForeignKeyConstraint(['project_id'], ['projects.id'], ),
            sa.ForeignKeyConstraint(['assigned_to'], ['users.id'], ),
            sa.ForeignKeyConstraint(['created_by'], ['users.id'], ),
            sa.PrimaryKeyConstraint('id')
        )
        # Create indexes (idempotent)
        try:
            existing_indexes = [idx['name'] for idx in inspector.get_indexes('recurring_tasks')]
            if op.f('ix_recurring_tasks_project_id') not in existing_indexes:
                op.create_index(op.f('ix_recurring_tasks_project_id'), 'recurring_tasks', ['project_id'], unique=False)
            if op.f('ix_recurring_tasks_assigned_to') not in existing_indexes:
                op.create_index(op.f('ix_recurring_tasks_assigned_to'), 'recurring_tasks', ['assigned_to'], unique=False)
        except Exception:
            # If we can't check, try to create indexes anyway
            try:
                op.create_index(op.f('ix_recurring_tasks_project_id'), 'recurring_tasks', ['project_id'], unique=False)
                op.create_index(op.f('ix_recurring_tasks_assigned_to'), 'recurring_tasks', ['assigned_to'], unique=False)
            except Exception:
                pass  # Indexes might already exist


def downgrade():
    """Drop recurring_tasks table"""
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if 'recurring_tasks' in inspector.get_table_names():
        op.drop_index(op.f('ix_recurring_tasks_assigned_to'), table_name='recurring_tasks')
        op.drop_index(op.f('ix_recurring_tasks_project_id'), table_name='recurring_tasks')
        op.drop_table('recurring_tasks')

