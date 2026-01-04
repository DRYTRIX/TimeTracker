"""Add salesman email mapping table

Revision ID: 087_salesman_email_mapping
Revises: 086_project_client_attachments
Create Date: 2025-01-29

This migration adds:
- salesman_email_mappings table for mapping salesman initials to email addresses
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '087_salesman_email_mapping'
down_revision = '086_project_client_attachments'
branch_labels = None
depends_on = None


def upgrade():
    """Create salesman_email_mappings table"""
    from sqlalchemy import inspect
    bind = op.get_bind()
    inspector = inspect(bind)
    
    existing_tables = inspector.get_table_names()
    
    if 'salesman_email_mappings' in existing_tables:
        print("✓ Table salesman_email_mappings already exists")
        # Ensure indexes exist
        try:
            existing_indexes = [idx['name'] for idx in inspector.get_indexes('salesman_email_mappings')]
            for idx_name, cols in [
                ('ix_salesman_email_mappings_initial', ['salesman_initial']),
                ('ix_salesman_email_mappings_active', ['is_active']),
            ]:
                if idx_name not in existing_indexes:
                    try:
                        op.create_index(idx_name, 'salesman_email_mappings', cols, unique=False)
                    except Exception:
                        pass
        except Exception:
            pass
        return
    
    try:
        op.create_table('salesman_email_mappings',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('salesman_initial', sa.String(length=20), nullable=False),
        sa.Column('email_address', sa.String(length=255), nullable=True),
        sa.Column('email_pattern', sa.String(length=255), nullable=True),  # e.g., '{value}@test.de'
        sa.Column('domain', sa.String(length=255), nullable=True),  # e.g., 'test.de' for pattern-based emails
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
            sa.UniqueConstraint('salesman_initial', name='uq_salesman_email_mapping_initial')
        )
        op.create_index('ix_salesman_email_mappings_initial', 'salesman_email_mappings', ['salesman_initial'], unique=False)
        op.create_index('ix_salesman_email_mappings_active', 'salesman_email_mappings', ['is_active'], unique=False)
        print("✓ Created salesman_email_mappings table")
    except Exception as e:
        error_msg = str(e)
        if 'already exists' in error_msg.lower() or 'duplicate' in error_msg.lower():
            print("✓ Table salesman_email_mappings already exists (detected via error)")
        else:
            print(f"✗ Error creating salesman_email_mappings table: {e}")
            raise


def downgrade():
    """Drop salesman_email_mappings table"""
    from sqlalchemy import inspect
    bind = op.get_bind()
    inspector = inspect(bind)
    
    existing_tables = inspector.get_table_names()
    
    if 'salesman_email_mappings' not in existing_tables:
        print("⊘ Table salesman_email_mappings does not exist, skipping")
        return
    
    try:
        existing_indexes = [idx['name'] for idx in inspector.get_indexes('salesman_email_mappings')]
        for idx_name in ['ix_salesman_email_mappings_active', 'ix_salesman_email_mappings_initial']:
            if idx_name in existing_indexes:
                try:
                    op.drop_index(idx_name, table_name='salesman_email_mappings')
                except Exception:
                    pass
        op.drop_table('salesman_email_mappings')
        print("✓ Dropped salesman_email_mappings table")
    except Exception as e:
        error_msg = str(e)
        if 'does not exist' in error_msg.lower() or 'no such table' in error_msg.lower():
            print("⊘ Table salesman_email_mappings does not exist (detected via error)")
        else:
            print(f"⚠ Warning: Could not drop salesman_email_mappings table: {e}")

