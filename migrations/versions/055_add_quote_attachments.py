"""Add quote attachments table

Revision ID: 055
Revises: 054
Create Date: 2025-01-27

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '055'
down_revision = '054'
branch_labels = None
depends_on = None


def upgrade():
    """Create quote_attachments table"""
    from sqlalchemy import inspect
    bind = op.get_bind()
    inspector = inspect(bind)
    
    existing_tables = inspector.get_table_names()
    
    if 'quote_attachments' in existing_tables:
        print("✓ Table quote_attachments already exists")
        # Ensure indexes exist
        try:
            existing_indexes = [idx['name'] for idx in inspector.get_indexes('quote_attachments')]
            if 'ix_quote_attachments_quote_id' not in existing_indexes:
                op.create_index('ix_quote_attachments_quote_id', 'quote_attachments', ['quote_id'], unique=False)
            if 'ix_quote_attachments_uploaded_by' not in existing_indexes:
                op.create_index('ix_quote_attachments_uploaded_by', 'quote_attachments', ['uploaded_by'], unique=False)
        except Exception:
            pass
        return
    
    try:
        op.create_table('quote_attachments',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('quote_id', sa.Integer(), nullable=False),
            sa.Column('filename', sa.String(length=255), nullable=False),
            sa.Column('original_filename', sa.String(length=255), nullable=False),
            sa.Column('file_path', sa.String(length=500), nullable=False),
            sa.Column('file_size', sa.Integer(), nullable=False),
            sa.Column('mime_type', sa.String(length=100), nullable=True),
            sa.Column('description', sa.Text(), nullable=True),
            sa.Column('is_visible_to_client', sa.Boolean(), nullable=False, server_default='false'),
            sa.Column('uploaded_by', sa.Integer(), nullable=False),
            sa.Column('uploaded_at', sa.DateTime(), nullable=False),
            sa.ForeignKeyConstraint(['quote_id'], ['quotes.id'], ondelete='CASCADE'),
            sa.ForeignKeyConstraint(['uploaded_by'], ['users.id'], ondelete='CASCADE'),
            sa.PrimaryKeyConstraint('id')
        )
        op.create_index('ix_quote_attachments_quote_id', 'quote_attachments', ['quote_id'], unique=False)
        op.create_index('ix_quote_attachments_uploaded_by', 'quote_attachments', ['uploaded_by'], unique=False)
        print("✓ Created quote_attachments table")
    except Exception as e:
        error_msg = str(e)
        if 'already exists' in error_msg.lower() or 'duplicate' in error_msg.lower():
            print("✓ Table quote_attachments already exists (detected via error)")
        else:
            print(f"✗ Error creating quote_attachments table: {e}")
            raise


def downgrade():
    """Drop quote_attachments table"""
    from sqlalchemy import inspect
    bind = op.get_bind()
    inspector = inspect(bind)
    
    existing_tables = inspector.get_table_names()
    
    if 'quote_attachments' not in existing_tables:
        print("⊘ Table quote_attachments does not exist, skipping")
        return
    
    try:
        existing_indexes = [idx['name'] for idx in inspector.get_indexes('quote_attachments')]
        if 'ix_quote_attachments_uploaded_by' in existing_indexes:
            op.drop_index('ix_quote_attachments_uploaded_by', table_name='quote_attachments')
        if 'ix_quote_attachments_quote_id' in existing_indexes:
            op.drop_index('ix_quote_attachments_quote_id', table_name='quote_attachments')
        op.drop_table('quote_attachments')
        print("✓ Dropped quote_attachments table")
    except Exception as e:
        error_msg = str(e)
        if 'does not exist' in error_msg.lower() or 'no such table' in error_msg.lower():
            print("⊘ Table quote_attachments does not exist (detected via error)")
        else:
            print(f"⚠ Warning: Could not drop quote_attachments table: {e}")

