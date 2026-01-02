"""Add workflow automation tables

Revision ID: 069_add_workflow_automation
Revises: 068_add_user_password_hash
Create Date: 2025-01-27

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '069_add_workflow_automation'
down_revision = '068_add_user_password_hash'
branch_labels = None
depends_on = None


def upgrade():
    """Create workflow_rules and workflow_executions tables"""
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    dialect_name = bind.dialect.name if bind else "generic"
    bool_true_default = '1' if dialect_name == 'sqlite' else ('true' if dialect_name == 'postgresql' else '1')

    # Create workflow_rules table
    if 'workflow_rules' not in inspector.get_table_names():
        op.create_table(
            'workflow_rules',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('name', sa.String(length=200), nullable=False),
            sa.Column('description', sa.Text(), nullable=True),
            sa.Column('trigger_type', sa.String(length=50), nullable=False),
            # Use portable JSON type for cross-db compatibility (SQLite + PostgreSQL).
            sa.Column('trigger_conditions', sa.JSON(), nullable=True),
            sa.Column('actions', sa.JSON(), nullable=False),
            sa.Column('enabled', sa.Boolean(), nullable=False, server_default=sa.text(bool_true_default)),
            sa.Column('priority', sa.Integer(), nullable=False, server_default='0'),
            sa.Column('user_id', sa.Integer(), nullable=False),
            sa.Column('created_by', sa.Integer(), nullable=False),
            sa.Column('created_at', sa.DateTime(), nullable=False),
            sa.Column('updated_at', sa.DateTime(), nullable=False),
            sa.Column('last_executed_at', sa.DateTime(), nullable=True),
            sa.Column('execution_count', sa.Integer(), nullable=False, server_default='0'),
            sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
            sa.ForeignKeyConstraint(['created_by'], ['users.id'], ),
            sa.PrimaryKeyConstraint('id')
        )
        op.create_index(op.f('ix_workflow_rules_user_id'), 'workflow_rules', ['user_id'], unique=False)

    # Create workflow_executions table
    if 'workflow_executions' not in inspector.get_table_names():
        op.create_table(
            'workflow_executions',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('rule_id', sa.Integer(), nullable=False),
            sa.Column('executed_at', sa.DateTime(), nullable=False),
            sa.Column('success', sa.Boolean(), nullable=False),
            sa.Column('error_message', sa.Text(), nullable=True),
            sa.Column('result', sa.JSON(), nullable=True),
            sa.Column('trigger_event', sa.JSON(), nullable=True),
            sa.Column('execution_time_ms', sa.Integer(), nullable=True),
            sa.ForeignKeyConstraint(['rule_id'], ['workflow_rules.id'], ),
            sa.PrimaryKeyConstraint('id')
        )
        op.create_index(op.f('ix_workflow_executions_rule_id'), 'workflow_executions', ['rule_id'], unique=False)
        op.create_index(op.f('ix_workflow_executions_executed_at'), 'workflow_executions', ['executed_at'], unique=False)


def downgrade():
    """Drop workflow tables"""
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if 'workflow_executions' in inspector.get_table_names():
        op.drop_index(op.f('ix_workflow_executions_executed_at'), table_name='workflow_executions')
        op.drop_index(op.f('ix_workflow_executions_rule_id'), table_name='workflow_executions')
        op.drop_table('workflow_executions')

    if 'workflow_rules' in inspector.get_table_names():
        op.drop_index(op.f('ix_workflow_rules_user_id'), table_name='workflow_rules')
        op.drop_table('workflow_rules')

