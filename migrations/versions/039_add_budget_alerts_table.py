"""Add budget_alerts table for project budget tracking and notifications

Revision ID: 039_add_budget_alerts
Revises: 038_fix_expenses_schema
Create Date: 2025-10-31

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '039_add_budget_alerts'
down_revision = '038_fix_expenses_schema'
branch_labels = None
depends_on = None


def upgrade():
    """Create budget_alerts table (idempotent)"""
    from sqlalchemy import inspect
    
    conn = op.get_bind()
    inspector = inspect(conn)
    existing_tables = inspector.get_table_names()
    
    if 'budget_alerts' not in existing_tables:
        op.create_table(
            'budget_alerts',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('project_id', sa.Integer(), nullable=False),
            sa.Column('alert_type', sa.String(length=20), nullable=False),
            sa.Column('alert_level', sa.String(length=20), nullable=False),
            sa.Column('budget_consumed_percent', sa.Numeric(precision=5, scale=2), nullable=False),
            sa.Column('budget_amount', sa.Numeric(precision=10, scale=2), nullable=False),
            sa.Column('consumed_amount', sa.Numeric(precision=10, scale=2), nullable=False),
            sa.Column('message', sa.Text(), nullable=False),
            sa.Column('is_acknowledged', sa.Boolean(), nullable=False, server_default='0'),
            sa.Column('acknowledged_by', sa.Integer(), nullable=True),
            sa.Column('acknowledged_at', sa.DateTime(), nullable=True),
            sa.Column('created_at', sa.DateTime(), nullable=False),
            sa.ForeignKeyConstraint(['project_id'], ['projects.id'], name='fk_budget_alerts_project_id', ondelete='CASCADE'),
            sa.ForeignKeyConstraint(['acknowledged_by'], ['users.id'], name='fk_budget_alerts_acknowledged_by', ondelete='SET NULL'),
            sa.PrimaryKeyConstraint('id')
        )
        
        # Create indexes for better query performance
        with op.batch_alter_table('budget_alerts', schema=None) as batch_op:
            batch_op.create_index('ix_budget_alerts_project_id', ['project_id'])
            batch_op.create_index('ix_budget_alerts_acknowledged_by', ['acknowledged_by'])
            batch_op.create_index('ix_budget_alerts_created_at', ['created_at'])
            batch_op.create_index('ix_budget_alerts_is_acknowledged', ['is_acknowledged'])
            batch_op.create_index('ix_budget_alerts_alert_type', ['alert_type'])


def downgrade():
    """Drop budget_alerts table"""
    op.drop_table('budget_alerts')

