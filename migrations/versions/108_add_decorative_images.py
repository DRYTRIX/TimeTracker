"""Add decorative images for invoices and quotes

Revision ID: 108_add_decorative_images
Revises: 107_increase_invoice_prefix_length
Create Date: 2025-01-30

This migration adds:
- invoice_images table for decorative images in invoices
- quote_images table for decorative images in quotes
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '108_add_decorative_images'
down_revision = '107_increase_invoice_prefix_length'
branch_labels = None
depends_on = None


def upgrade():
    """Create invoice_images and quote_images tables"""
    from sqlalchemy import inspect
    bind = op.get_bind()
    inspector = inspect(bind)
    
    existing_tables = inspector.get_table_names()
    
    # Create invoice_images table
    if 'invoice_images' in existing_tables:
        print("✓ Table invoice_images already exists")
        # Ensure indexes exist
        try:
            existing_indexes = [idx['name'] for idx in inspector.get_indexes('invoice_images')]
            for idx_name, cols in [
                ('ix_invoice_images_invoice_id', ['invoice_id']),
                ('ix_invoice_images_uploaded_by', ['uploaded_by']),
            ]:
                if idx_name not in existing_indexes:
                    try:
                        op.create_index(idx_name, 'invoice_images', cols, unique=False)
                    except Exception:
                        pass
        except Exception:
            pass
    else:
        try:
            op.create_table('invoice_images',
                sa.Column('id', sa.Integer(), nullable=False),
                sa.Column('invoice_id', sa.Integer(), nullable=False),
                sa.Column('filename', sa.String(length=255), nullable=False),
                sa.Column('original_filename', sa.String(length=255), nullable=False),
                sa.Column('file_path', sa.String(length=500), nullable=False),
                sa.Column('file_size', sa.Integer(), nullable=False),
                sa.Column('mime_type', sa.String(length=100), nullable=True),
                sa.Column('position_x', sa.Numeric(precision=10, scale=2), nullable=False, server_default='0'),
                sa.Column('position_y', sa.Numeric(precision=10, scale=2), nullable=False, server_default='0'),
                sa.Column('width', sa.Numeric(precision=10, scale=2), nullable=True),
                sa.Column('height', sa.Numeric(precision=10, scale=2), nullable=True),
                sa.Column('opacity', sa.Numeric(precision=3, scale=2), nullable=False, server_default='1.0'),
                sa.Column('z_index', sa.Integer(), nullable=False, server_default='0'),
                sa.Column('uploaded_by', sa.Integer(), nullable=False),
                sa.Column('uploaded_at', sa.DateTime(), nullable=False),
                sa.ForeignKeyConstraint(['invoice_id'], ['invoices.id'], ondelete='CASCADE'),
                sa.ForeignKeyConstraint(['uploaded_by'], ['users.id'], ondelete='CASCADE'),
                sa.PrimaryKeyConstraint('id')
            )
            op.create_index('ix_invoice_images_invoice_id', 'invoice_images', ['invoice_id'], unique=False)
            op.create_index('ix_invoice_images_uploaded_by', 'invoice_images', ['uploaded_by'], unique=False)
            print("✓ Created invoice_images table")
        except Exception as e:
            error_msg = str(e)
            if 'already exists' in error_msg.lower() or 'duplicate' in error_msg.lower():
                print("✓ Table invoice_images already exists (detected via error)")
            else:
                print(f"✗ Error creating invoice_images table: {e}")
                raise

    # Create quote_images table
    if 'quote_images' in existing_tables:
        print("✓ Table quote_images already exists")
        # Ensure indexes exist
        try:
            existing_indexes = [idx['name'] for idx in inspector.get_indexes('quote_images')]
            for idx_name, cols in [
                ('ix_quote_images_quote_id', ['quote_id']),
                ('ix_quote_images_uploaded_by', ['uploaded_by']),
            ]:
                if idx_name not in existing_indexes:
                    try:
                        op.create_index(idx_name, 'quote_images', cols, unique=False)
                    except Exception:
                        pass
        except Exception:
            pass
    else:
        try:
            op.create_table('quote_images',
                sa.Column('id', sa.Integer(), nullable=False),
                sa.Column('quote_id', sa.Integer(), nullable=False),
                sa.Column('filename', sa.String(length=255), nullable=False),
                sa.Column('original_filename', sa.String(length=255), nullable=False),
                sa.Column('file_path', sa.String(length=500), nullable=False),
                sa.Column('file_size', sa.Integer(), nullable=False),
                sa.Column('mime_type', sa.String(length=100), nullable=True),
                sa.Column('position_x', sa.Numeric(precision=10, scale=2), nullable=False, server_default='0'),
                sa.Column('position_y', sa.Numeric(precision=10, scale=2), nullable=False, server_default='0'),
                sa.Column('width', sa.Numeric(precision=10, scale=2), nullable=True),
                sa.Column('height', sa.Numeric(precision=10, scale=2), nullable=True),
                sa.Column('opacity', sa.Numeric(precision=3, scale=2), nullable=False, server_default='1.0'),
                sa.Column('z_index', sa.Integer(), nullable=False, server_default='0'),
                sa.Column('uploaded_by', sa.Integer(), nullable=False),
                sa.Column('uploaded_at', sa.DateTime(), nullable=False),
                sa.ForeignKeyConstraint(['quote_id'], ['quotes.id'], ondelete='CASCADE'),
                sa.ForeignKeyConstraint(['uploaded_by'], ['users.id'], ondelete='CASCADE'),
                sa.PrimaryKeyConstraint('id')
            )
            op.create_index('ix_quote_images_quote_id', 'quote_images', ['quote_id'], unique=False)
            op.create_index('ix_quote_images_uploaded_by', 'quote_images', ['uploaded_by'], unique=False)
            print("✓ Created quote_images table")
        except Exception as e:
            error_msg = str(e)
            if 'already exists' in error_msg.lower() or 'duplicate' in error_msg.lower():
                print("✓ Table quote_images already exists (detected via error)")
            else:
                print(f"✗ Error creating quote_images table: {e}")
                raise


def downgrade():
    """Drop invoice_images and quote_images tables"""
    from sqlalchemy import inspect
    bind = op.get_bind()
    inspector = inspect(bind)
    
    existing_tables = inspector.get_table_names()
    
    if 'quote_images' in existing_tables:
        try:
            existing_indexes = [idx['name'] for idx in inspector.get_indexes('quote_images')]
            for idx_name in ['ix_quote_images_uploaded_by', 'ix_quote_images_quote_id']:
                if idx_name in existing_indexes:
                    try:
                        op.drop_index(idx_name, table_name='quote_images')
                    except Exception:
                        pass
            op.drop_table('quote_images')
            print("✓ Dropped quote_images table")
        except Exception as e:
            error_msg = str(e)
            if 'does not exist' in error_msg.lower() or 'no such table' in error_msg.lower():
                print("⊘ Table quote_images does not exist (detected via error)")
            else:
                print(f"⚠ Warning: Could not drop quote_images table: {e}")
    
    if 'invoice_images' in existing_tables:
        try:
            existing_indexes = [idx['name'] for idx in inspector.get_indexes('invoice_images')]
            for idx_name in ['ix_invoice_images_uploaded_by', 'ix_invoice_images_invoice_id']:
                if idx_name in existing_indexes:
                    try:
                        op.drop_index(idx_name, table_name='invoice_images')
                    except Exception:
                        pass
            op.drop_table('invoice_images')
            print("✓ Dropped invoice_images table")
        except Exception as e:
            error_msg = str(e)
            if 'does not exist' in error_msg.lower() or 'no such table' in error_msg.lower():
                print("⊘ Table invoice_images does not exist (detected via error)")
            else:
                print(f"⚠ Warning: Could not drop invoice_images table: {e}")
