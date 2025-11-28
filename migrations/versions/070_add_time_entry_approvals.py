"""Add time entry approval workflow tables

Revision ID: 070_add_time_entry_approvals
Revises: 069_add_workflow_automation
Create Date: 2025-01-27

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '070_add_time_entry_approvals'
down_revision = '069_add_workflow_automation'
branch_labels = None
depends_on = None


def upgrade():
    """Create time_entry_approvals and approval_policies tables"""
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    # Create approval_status enum if using PostgreSQL (check if it exists first)
    if bind.dialect.name == 'postgresql':
        # Ensure the enum type exists - create only if it doesn't exist using DO block
        # This prevents SQLAlchemy from trying to create it later
        op.execute("""
            DO $$ BEGIN
                IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'approvalstatus') THEN
                    CREATE TYPE approvalstatus AS ENUM ('pending', 'approved', 'rejected', 'cancelled');
                END IF;
            END $$;
        """)

    # Create time_entry_approvals table
    if 'time_entry_approvals' not in inspector.get_table_names():
        # Use raw SQL to create table to avoid SQLAlchemy enum type creation issues
        if bind.dialect.name == 'postgresql':
            op.execute("""
                CREATE TABLE time_entry_approvals (
                    id SERIAL PRIMARY KEY,
                    time_entry_id INTEGER NOT NULL REFERENCES time_entries(id),
                    status approvalstatus NOT NULL DEFAULT 'pending',
                    requested_by INTEGER NOT NULL REFERENCES users(id),
                    approved_by INTEGER REFERENCES users(id),
                    requested_at TIMESTAMP NOT NULL,
                    approved_at TIMESTAMP,
                    rejected_at TIMESTAMP,
                    request_comment TEXT,
                    approval_comment TEXT,
                    rejection_reason TEXT,
                    parent_approval_id INTEGER REFERENCES time_entry_approvals(id),
                    approval_level INTEGER NOT NULL DEFAULT 1,
                    created_at TIMESTAMP NOT NULL,
                    updated_at TIMESTAMP NOT NULL
                )
            """)
            op.execute("CREATE INDEX ix_time_entry_approvals_time_entry_id ON time_entry_approvals(time_entry_id)")
            op.execute("CREATE INDEX ix_time_entry_approvals_status ON time_entry_approvals(status)")
            op.execute("CREATE INDEX ix_time_entry_approvals_requested_by ON time_entry_approvals(requested_by)")
            op.execute("CREATE INDEX ix_time_entry_approvals_approved_by ON time_entry_approvals(approved_by)")
        else:
            # For non-PostgreSQL databases, use SQLAlchemy
            op.create_table(
                'time_entry_approvals',
                sa.Column('id', sa.Integer(), nullable=False),
                sa.Column('time_entry_id', sa.Integer(), nullable=False),
                sa.Column('status', sa.String(20), nullable=False),
                sa.Column('requested_by', sa.Integer(), nullable=False),
                sa.Column('approved_by', sa.Integer(), nullable=True),
                sa.Column('requested_at', sa.DateTime(), nullable=False),
                sa.Column('approved_at', sa.DateTime(), nullable=True),
                sa.Column('rejected_at', sa.DateTime(), nullable=True),
                sa.Column('request_comment', sa.Text(), nullable=True),
                sa.Column('approval_comment', sa.Text(), nullable=True),
                sa.Column('rejection_reason', sa.Text(), nullable=True),
                sa.Column('parent_approval_id', sa.Integer(), nullable=True),
                sa.Column('approval_level', sa.Integer(), nullable=False, server_default='1'),
                sa.Column('created_at', sa.DateTime(), nullable=False),
                sa.Column('updated_at', sa.DateTime(), nullable=False),
                sa.ForeignKeyConstraint(['time_entry_id'], ['time_entries.id'], ),
                sa.ForeignKeyConstraint(['requested_by'], ['users.id'], ),
                sa.ForeignKeyConstraint(['approved_by'], ['users.id'], ),
                sa.ForeignKeyConstraint(['parent_approval_id'], ['time_entry_approvals.id'], ),
                sa.PrimaryKeyConstraint('id')
            )
            op.create_index(op.f('ix_time_entry_approvals_time_entry_id'), 'time_entry_approvals', ['time_entry_id'], unique=False)
            op.create_index(op.f('ix_time_entry_approvals_status'), 'time_entry_approvals', ['status'], unique=False)
            op.create_index(op.f('ix_time_entry_approvals_requested_by'), 'time_entry_approvals', ['requested_by'], unique=False)
            op.create_index(op.f('ix_time_entry_approvals_approved_by'), 'time_entry_approvals', ['approved_by'], unique=False)

    # Create approval_policies table
    if 'approval_policies' not in inspector.get_table_names():
        op.create_table(
            'approval_policies',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('project_id', sa.Integer(), nullable=True),
            sa.Column('user_id', sa.Integer(), nullable=True),
            sa.Column('applies_to_all', sa.Boolean(), nullable=False, server_default='false'),
            sa.Column('requires_approval', sa.Boolean(), nullable=False, server_default='true'),
            sa.Column('approval_levels', sa.Integer(), nullable=False, server_default='1'),
            sa.Column('approver_user_ids', sa.String(length=500), nullable=True),
            sa.Column('min_hours', sa.Numeric(10, 2), nullable=True),
            sa.Column('billable_only', sa.Boolean(), nullable=False, server_default='false'),
            sa.Column('auto_approve_after_hours', sa.Integer(), nullable=True),
            sa.Column('auto_approve_for_admins', sa.Boolean(), nullable=False, server_default='false'),
            sa.Column('enabled', sa.Boolean(), nullable=False, server_default='true'),
            sa.Column('created_at', sa.DateTime(), nullable=False),
            sa.Column('updated_at', sa.DateTime(), nullable=False),
            sa.ForeignKeyConstraint(['project_id'], ['projects.id'], ),
            sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
            sa.PrimaryKeyConstraint('id')
        )
        op.create_index(op.f('ix_approval_policies_project_id'), 'approval_policies', ['project_id'], unique=False)
        op.create_index(op.f('ix_approval_policies_user_id'), 'approval_policies', ['user_id'], unique=False)


def downgrade():
    """Drop approval tables"""
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if 'approval_policies' in inspector.get_table_names():
        op.drop_index(op.f('ix_approval_policies_user_id'), table_name='approval_policies')
        op.drop_index(op.f('ix_approval_policies_project_id'), table_name='approval_policies')
        op.drop_table('approval_policies')

    if 'time_entry_approvals' in inspector.get_table_names():
        op.drop_index(op.f('ix_time_entry_approvals_approved_by'), table_name='time_entry_approvals')
        op.drop_index(op.f('ix_time_entry_approvals_requested_by'), table_name='time_entry_approvals')
        op.drop_index(op.f('ix_time_entry_approvals_status'), table_name='time_entry_approvals')
        op.drop_index(op.f('ix_time_entry_approvals_time_entry_id'), table_name='time_entry_approvals')
        op.drop_table('time_entry_approvals')

    # Drop enum if using PostgreSQL
    if bind.dialect.name == 'postgresql':
        op.execute("DROP TYPE IF EXISTS approvalstatus")

