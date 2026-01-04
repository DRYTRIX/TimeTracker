"""Add quote versions table for revision history

Revision ID: 058
Revises: 057
Create Date: 2025-01-27

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '058'
down_revision = '057'
branch_labels = None
depends_on = None


def upgrade():
    """Create quote_versions table"""
    from sqlalchemy import inspect
    bind = op.get_bind()
    inspector = inspect(bind)
    
    existing_tables = inspector.get_table_names()
    
    if 'quote_versions' in existing_tables:
        print("✓ Table quote_versions already exists")
        # Ensure indexes exist
        try:
            existing_indexes = [idx['name'] for idx in inspector.get_indexes('quote_versions')]
            if 'ix_quote_versions_quote_id' not in existing_indexes:
                op.create_index('ix_quote_versions_quote_id', 'quote_versions', ['quote_id'], unique=False)
            if 'ix_quote_versions_changed_by' not in existing_indexes:
                op.create_index('ix_quote_versions_changed_by', 'quote_versions', ['changed_by'], unique=False)
            if 'ix_quote_versions_version_number' not in existing_indexes:
                op.create_index('ix_quote_versions_version_number', 'quote_versions', ['quote_id', 'version_number'], unique=True)
        except Exception:
            pass
        return
    
    try:
        op.create_table('quote_versions',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('quote_id', sa.Integer(), nullable=False),
            sa.Column('version_number', sa.Integer(), nullable=False),
            sa.Column('quote_data', sa.Text(), nullable=False),
            sa.Column('changed_by', sa.Integer(), nullable=False),
            sa.Column('changed_at', sa.DateTime(), nullable=False),
            sa.Column('change_summary', sa.String(length=500), nullable=True),
            sa.Column('fields_changed', sa.String(length=500), nullable=True),
            sa.ForeignKeyConstraint(['quote_id'], ['quotes.id'], ondelete='CASCADE'),
            sa.ForeignKeyConstraint(['changed_by'], ['users.id'], ondelete='CASCADE'),
            sa.PrimaryKeyConstraint('id')
        )
        op.create_index('ix_quote_versions_quote_id', 'quote_versions', ['quote_id'], unique=False)
        op.create_index('ix_quote_versions_changed_by', 'quote_versions', ['changed_by'], unique=False)
        op.create_index('ix_quote_versions_version_number', 'quote_versions', ['quote_id', 'version_number'], unique=True)
        print("✓ Created quote_versions table")
    except Exception as e:
        error_msg = str(e)
        if 'already exists' in error_msg.lower() or 'duplicate' in error_msg.lower():
            print("✓ Table quote_versions already exists (detected via error)")
        else:
            print(f"✗ Error creating quote_versions table: {e}")
            raise


def downgrade():
    """Drop quote_versions table"""
    from sqlalchemy import inspect
    bind = op.get_bind()
    inspector = inspect(bind)
    
    existing_tables = inspector.get_table_names()
    
    if 'quote_versions' not in existing_tables:
        print("⊘ Table quote_versions does not exist, skipping")
        return
    
    try:
        existing_indexes = [idx['name'] for idx in inspector.get_indexes('quote_versions')]
        if 'ix_quote_versions_version_number' in existing_indexes:
            op.drop_index('ix_quote_versions_version_number', table_name='quote_versions')
        if 'ix_quote_versions_changed_by' in existing_indexes:
            op.drop_index('ix_quote_versions_changed_by', table_name='quote_versions')
        if 'ix_quote_versions_quote_id' in existing_indexes:
            op.drop_index('ix_quote_versions_quote_id', table_name='quote_versions')
        op.drop_table('quote_versions')
        print("✓ Dropped quote_versions table")
    except Exception as e:
        error_msg = str(e)
        if 'does not exist' in error_msg.lower() or 'no such table' in error_msg.lower():
            print("⊘ Table quote_versions does not exist (detected via error)")
        else:
            print(f"⚠ Warning: Could not drop quote_versions table: {e}")

