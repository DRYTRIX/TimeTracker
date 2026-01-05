"""Add all missing columns to quotes table

Revision ID: 104_add_missing_quotes_columns
Revises: 103_add_missing_quotes_quote_number
Create Date: 2026-01-05

This migration adds all missing columns to the quotes table that are expected
by the Quote model. Some migrations may have failed or been skipped, leaving
the database schema incomplete. This migration is idempotent and safe to run
multiple times.
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect

# revision identifiers, used by Alembic.
revision = '104_add_missing_quotes_columns'
down_revision = '103_add_missing_quotes_quote_number'
branch_labels = None
depends_on = None


def _has_table(inspector, name: str) -> bool:
    """Check if a table exists"""
    try:
        return name in inspector.get_table_names()
    except Exception:
        return False


def _has_column(inspector, table_name: str, column_name: str) -> bool:
    """Check if a column exists in a table"""
    try:
        return column_name in {c["name"] for c in inspector.get_columns(table_name)}
    except Exception:
        return False


def _has_index(inspector, table_name: str, index_name: str) -> bool:
    """Check if an index exists"""
    try:
        indexes = inspector.get_indexes(table_name)
        return any((idx.get("name") or "") == index_name for idx in indexes)
    except Exception:
        return False


def upgrade():
    """Add all missing columns to quotes table"""
    bind = op.get_bind()
    inspector = inspect(bind)
    
    dialect_name = bind.dialect.name if bind else 'generic'
    print(f"[Migration 104] Running on {dialect_name} database")
    
    # Check if quotes table exists
    if not _has_table(inspector, 'quotes'):
        print("[Migration 104] ⊘ Quotes table does not exist, skipping")
        return
    
    quotes_columns = {c["name"] for c in inspector.get_columns('quotes')}
    print(f"[Migration 104] Found {len(quotes_columns)} existing columns in quotes table")
    
    # Define all columns that should exist based on the Quote model
    columns_to_add = []
    
    # Financial columns (from migration 051)
    if 'subtotal' not in quotes_columns:
        columns_to_add.append(('subtotal', sa.Column('subtotal', sa.Numeric(precision=10, scale=2), nullable=False, server_default='0')))
    
    if 'tax_amount' not in quotes_columns:
        columns_to_add.append(('tax_amount', sa.Column('tax_amount', sa.Numeric(precision=10, scale=2), nullable=False, server_default='0')))
    
    # Visibility column (from migration 051)
    if 'visible_to_client' not in quotes_columns:
        columns_to_add.append(('visible_to_client', sa.Column('visible_to_client', sa.Boolean(), nullable=False, server_default='false')))
    
    # Discount columns (from migration 052)
    if 'discount_type' not in quotes_columns:
        columns_to_add.append(('discount_type', sa.Column('discount_type', sa.String(length=20), nullable=True)))
    
    if 'discount_amount' not in quotes_columns:
        columns_to_add.append(('discount_amount', sa.Column('discount_amount', sa.Numeric(precision=10, scale=2), nullable=True, server_default='0')))
    
    if 'discount_reason' not in quotes_columns:
        columns_to_add.append(('discount_reason', sa.Column('discount_reason', sa.String(length=500), nullable=True)))
    
    if 'coupon_code' not in quotes_columns:
        columns_to_add.append(('coupon_code', sa.Column('coupon_code', sa.String(length=50), nullable=True)))
    
    # Payment terms (from migration 053)
    if 'payment_terms' not in quotes_columns:
        columns_to_add.append(('payment_terms', sa.Column('payment_terms', sa.String(length=100), nullable=True)))
    
    # Approval workflow columns (from migration 056)
    if 'approval_status' not in quotes_columns:
        columns_to_add.append(('approval_status', sa.Column('approval_status', sa.String(length=20), nullable=False, server_default='not_required')))
    
    if 'approved_by' not in quotes_columns:
        columns_to_add.append(('approved_by', sa.Column('approved_by', sa.Integer(), nullable=True)))
    
    if 'approved_at' not in quotes_columns:
        columns_to_add.append(('approved_at', sa.Column('approved_at', sa.DateTime(), nullable=True)))
    
    if 'rejected_by' not in quotes_columns:
        columns_to_add.append(('rejected_by', sa.Column('rejected_by', sa.Integer(), nullable=True)))
    
    if 'rejection_reason' not in quotes_columns:
        columns_to_add.append(('rejection_reason', sa.Column('rejection_reason', sa.Text(), nullable=True)))
    
    # Add all missing columns
    if columns_to_add:
        print(f"[Migration 104] Adding {len(columns_to_add)} missing columns...")
        for col_name, col_def in columns_to_add:
            try:
                print(f"[Migration 104]   Adding column: {col_name}")
                op.add_column('quotes', col_def)
                print(f"[Migration 104]   ✓ {col_name} added")
            except Exception as e:
                # Column might have been added concurrently, check again
                if _has_column(inspector, 'quotes', col_name):
                    print(f"[Migration 104]   ✓ {col_name} already exists (concurrent add)")
                else:
                    print(f"[Migration 104]   ✗ Error adding {col_name}: {e}")
                    raise
    else:
        print("[Migration 104] ✓ All expected columns already exist")
    
    # Refresh inspector after adding columns
    inspector = inspect(bind)
    quotes_columns = {c["name"] for c in inspector.get_columns('quotes')}
    
    # Create missing indexes
    indexes_to_add = []
    
    if 'coupon_code' in quotes_columns and not _has_index(inspector, 'quotes', 'ix_quotes_coupon_code'):
        indexes_to_add.append(('ix_quotes_coupon_code', ['coupon_code'], False))
    
    if 'approval_status' in quotes_columns and not _has_index(inspector, 'quotes', 'ix_quotes_approval_status'):
        indexes_to_add.append(('ix_quotes_approval_status', ['approval_status'], False))
    
    if 'approved_by' in quotes_columns and not _has_index(inspector, 'quotes', 'ix_quotes_approved_by'):
        indexes_to_add.append(('ix_quotes_approved_by', ['approved_by'], False))
    
    # Add missing indexes
    if indexes_to_add:
        print(f"[Migration 104] Creating {len(indexes_to_add)} missing indexes...")
        for idx_name, idx_columns, is_unique in indexes_to_add:
            try:
                print(f"[Migration 104]   Creating index: {idx_name}")
                op.create_index(idx_name, 'quotes', idx_columns, unique=is_unique)
                print(f"[Migration 104]   ✓ {idx_name} created")
            except Exception as e:
                if _has_index(inspector, 'quotes', idx_name):
                    print(f"[Migration 104]   ✓ {idx_name} already exists (concurrent create)")
                else:
                    print(f"[Migration 104]   ⚠ Warning: Could not create index {idx_name}: {e}")
    else:
        print("[Migration 104] ✓ All expected indexes already exist")
    
    # Add missing foreign keys
    inspector = inspect(bind)
    quotes_fks = {fk.get("name") for fk in inspector.get_foreign_keys('quotes')}
    
    fks_to_add = []
    
    if 'approved_by' in quotes_columns and 'fk_quotes_approved_by' not in quotes_fks:
        fks_to_add.append(('fk_quotes_approved_by', 'approved_by', 'users', 'id'))
    
    if 'rejected_by' in quotes_columns and 'fk_quotes_rejected_by' not in quotes_fks:
        fks_to_add.append(('fk_quotes_rejected_by', 'rejected_by', 'users', 'id'))
    
    # Add missing foreign keys
    if fks_to_add:
        print(f"[Migration 104] Creating {len(fks_to_add)} missing foreign keys...")
        for fk_name, col_name, ref_table, ref_col in fks_to_add:
            try:
                print(f"[Migration 104]   Creating foreign key: {fk_name}")
                if dialect_name == 'sqlite':
                    with op.batch_alter_table('quotes', schema=None) as batch_op:
                        batch_op.create_foreign_key(fk_name, ref_table, [col_name], [ref_col])
                else:
                    op.create_foreign_key(fk_name, 'quotes', ref_table, [col_name], [ref_col], ondelete='SET NULL')
                print(f"[Migration 104]   ✓ {fk_name} created")
            except Exception as e:
                # Check if FK was added concurrently
                inspector = inspect(bind)
                current_fks = {fk.get("name") for fk in inspector.get_foreign_keys('quotes')}
                if fk_name in current_fks:
                    print(f"[Migration 104]   ✓ {fk_name} already exists (concurrent create)")
                else:
                    print(f"[Migration 104]   ⚠ Warning: Could not create foreign key {fk_name}: {e}")
    else:
        print("[Migration 104] ✓ All expected foreign keys already exist")
    
    print("[Migration 104] ✓ Migration completed successfully")


def downgrade():
    """Remove columns added by this migration"""
    bind = op.get_bind()
    inspector = inspect(bind)
    
    if not _has_table(inspector, 'quotes'):
        print("[Migration 104] ⊘ Quotes table does not exist, skipping downgrade")
        return
    
    quotes_columns = {c["name"] for c in inspector.get_columns('quotes')}
    
    # Remove foreign keys first
    quotes_fks = {fk.get("name") for fk in inspector.get_foreign_keys('quotes')}
    
    if 'fk_quotes_rejected_by' in quotes_fks:
        try:
            op.drop_constraint('fk_quotes_rejected_by', 'quotes', type_='foreignkey')
            print("[Migration 104] ✓ Dropped fk_quotes_rejected_by")
        except Exception as e:
            print(f"[Migration 104] ⚠ Warning: Could not drop fk_quotes_rejected_by: {e}")
    
    if 'fk_quotes_approved_by' in quotes_fks:
        try:
            op.drop_constraint('fk_quotes_approved_by', 'quotes', type_='foreignkey')
            print("[Migration 104] ✓ Dropped fk_quotes_approved_by")
        except Exception as e:
            print(f"[Migration 104] ⚠ Warning: Could not drop fk_quotes_approved_by: {e}")
    
    # Remove indexes
    if _has_index(inspector, 'quotes', 'ix_quotes_approved_by'):
        try:
            op.drop_index('ix_quotes_approved_by', table_name='quotes')
            print("[Migration 104] ✓ Dropped ix_quotes_approved_by")
        except Exception as e:
            print(f"[Migration 104] ⚠ Warning: Could not drop index: {e}")
    
    if _has_index(inspector, 'quotes', 'ix_quotes_approval_status'):
        try:
            op.drop_index('ix_quotes_approval_status', table_name='quotes')
            print("[Migration 104] ✓ Dropped ix_quotes_approval_status")
        except Exception as e:
            print(f"[Migration 104] ⚠ Warning: Could not drop index: {e}")
    
    if _has_index(inspector, 'quotes', 'ix_quotes_coupon_code'):
        try:
            op.drop_index('ix_quotes_coupon_code', table_name='quotes')
            print("[Migration 104] ✓ Dropped ix_quotes_coupon_code")
        except Exception as e:
            print(f"[Migration 104] ⚠ Warning: Could not drop index: {e}")
    
    # Remove columns (in reverse order of dependencies)
    columns_to_remove = [
        'rejection_reason', 'rejected_by', 'approved_at', 'approved_by', 'approval_status',
        'payment_terms',
        'coupon_code', 'discount_reason', 'discount_amount', 'discount_type',
        'visible_to_client', 'tax_amount', 'subtotal'
    ]
    
    for col_name in columns_to_remove:
        if col_name in quotes_columns:
            try:
                op.drop_column('quotes', col_name)
                print(f"[Migration 104] ✓ Dropped {col_name}")
            except Exception as e:
                print(f"[Migration 104] ⚠ Warning: Could not drop {col_name}: {e}")
