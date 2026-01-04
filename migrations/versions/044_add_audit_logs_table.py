"""Add audit_logs table for tracking changes

Revision ID: 044
Revises: 043
Create Date: 2025-01-21

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = '044'
down_revision = '043'
branch_labels = None
depends_on = None


def upgrade():
    """Create audit_logs table for comprehensive change tracking"""
    from sqlalchemy import inspect
    bind = op.get_bind()
    inspector = inspect(bind)
    
    existing_tables = inspector.get_table_names()
    
    if 'audit_logs' in existing_tables:
        print("✓ Table audit_logs already exists")
        # Ensure indexes exist
        try:
            existing_indexes = [idx['name'] for idx in inspector.get_indexes('audit_logs')]
            indexes_to_create = [
                ('ix_audit_logs_entity', ['entity_type', 'entity_id']),
                ('ix_audit_logs_user_created', ['user_id', 'created_at']),
                ('ix_audit_logs_created_at', ['created_at']),
                ('ix_audit_logs_action', ['action']),
                ('ix_audit_logs_entity_type', ['entity_type']),
                ('ix_audit_logs_entity_id', ['entity_id']),
                ('ix_audit_logs_user_id', ['user_id']),
                ('ix_audit_logs_field_name', ['field_name']),
            ]
            for idx_name, cols in indexes_to_create:
                if idx_name not in existing_indexes:
                    try:
                        op.create_index(idx_name, 'audit_logs', cols, unique=False)
                    except Exception:
                        pass
        except Exception:
            pass
        return
    
    try:
        op.create_table('audit_logs',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('user_id', sa.Integer(), nullable=True),
            sa.Column('entity_type', sa.String(length=50), nullable=False),
            sa.Column('entity_id', sa.Integer(), nullable=False),
            sa.Column('entity_name', sa.String(length=500), nullable=True),
            sa.Column('action', sa.String(length=20), nullable=False),
            sa.Column('field_name', sa.String(length=100), nullable=True),
            sa.Column('old_value', sa.Text(), nullable=True),
            sa.Column('new_value', sa.Text(), nullable=True),
            sa.Column('change_description', sa.Text(), nullable=True),
            sa.Column('ip_address', sa.String(length=45), nullable=True),
            sa.Column('user_agent', sa.Text(), nullable=True),
            sa.Column('request_path', sa.String(length=500), nullable=True),
            sa.Column('created_at', sa.DateTime(), nullable=False),
            sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='SET NULL'),
            sa.PrimaryKeyConstraint('id')
        )
        
        # Create indexes for common queries
        op.create_index('ix_audit_logs_entity', 'audit_logs', ['entity_type', 'entity_id'])
        op.create_index('ix_audit_logs_user_created', 'audit_logs', ['user_id', 'created_at'])
        op.create_index('ix_audit_logs_created_at', 'audit_logs', ['created_at'])
        op.create_index('ix_audit_logs_action', 'audit_logs', ['action'])
        op.create_index('ix_audit_logs_entity_type', 'audit_logs', ['entity_type'])
        op.create_index('ix_audit_logs_entity_id', 'audit_logs', ['entity_id'])
        op.create_index('ix_audit_logs_user_id', 'audit_logs', ['user_id'])
        op.create_index('ix_audit_logs_field_name', 'audit_logs', ['field_name'])
        print("✓ Created audit_logs table")
    except Exception as e:
        error_msg = str(e)
        if 'already exists' in error_msg.lower() or 'duplicate' in error_msg.lower():
            print("✓ Table audit_logs already exists (detected via error)")
        else:
            print(f"✗ Error creating audit_logs table: {e}")
            raise


def downgrade():
    """Remove audit_logs table"""
    from sqlalchemy import inspect
    bind = op.get_bind()
    inspector = inspect(bind)
    
    existing_tables = inspector.get_table_names()
    
    if 'audit_logs' not in existing_tables:
        print("⊘ Table audit_logs does not exist, skipping")
        return
    
    try:
        existing_indexes = [idx['name'] for idx in inspector.get_indexes('audit_logs')]
        indexes_to_drop = [
            'ix_audit_logs_field_name',
            'ix_audit_logs_user_id',
            'ix_audit_logs_entity_id',
            'ix_audit_logs_entity_type',
            'ix_audit_logs_action',
            'ix_audit_logs_created_at',
            'ix_audit_logs_user_created',
            'ix_audit_logs_entity',
        ]
        for idx_name in indexes_to_drop:
            if idx_name in existing_indexes:
                try:
                    op.drop_index(idx_name, table_name='audit_logs')
                except Exception:
                    pass
        op.drop_table('audit_logs')
        print("✓ Dropped audit_logs table")
    except Exception as e:
        error_msg = str(e)
        if 'does not exist' in error_msg.lower() or 'no such table' in error_msg.lower():
            print("⊘ Table audit_logs does not exist (detected via error)")
        else:
            print(f"⚠ Warning: Could not drop audit_logs table: {e}")

