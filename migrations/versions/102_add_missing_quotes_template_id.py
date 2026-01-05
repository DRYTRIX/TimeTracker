"""Add missing template_id column to quotes table

Revision ID: 102_add_missing_quotes_template_id
Revises: 101_add_issues_table
Create Date: 2026-01-05

This migration adds the missing template_id column to the quotes table.
The column was supposed to be added in migration 051, but some databases
may have missed it due to migration execution order or partial failures.
This migration is idempotent and safe to run multiple times.
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect

# revision identifiers, used by Alembic.
revision = '102_add_missing_quotes_template_id'
down_revision = '101_add_issues_table'
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


def _has_foreign_key(inspector, table_name: str, fk_name: str) -> bool:
    """Check if a foreign key constraint exists"""
    try:
        fks = inspector.get_foreign_keys(table_name)
        return any((fk.get("name") or "") == fk_name for fk in fks)
    except Exception:
        return False


def upgrade():
    """Add template_id column to quotes table if it doesn't exist"""
    bind = op.get_bind()
    inspector = inspect(bind)
    
    dialect_name = bind.dialect.name if bind else 'generic'
    print(f"[Migration 102] Running on {dialect_name} database")
    
    # Check if quotes table exists
    if not _has_table(inspector, 'quotes'):
        print("[Migration 102] ⊘ Quotes table does not exist, skipping")
        return
    
    # Check if template_id column already exists
    if _has_column(inspector, 'quotes', 'template_id'):
        print("[Migration 102] ✓ template_id column already exists in quotes table")
        
        # Verify index exists
        if not _has_index(inspector, 'quotes', 'ix_quotes_template_id'):
            print("[Migration 102] Creating missing index ix_quotes_template_id...")
            try:
                op.create_index('ix_quotes_template_id', 'quotes', ['template_id'])
                print("[Migration 102] ✓ Index created")
            except Exception as e:
                print(f"[Migration 102] ⚠ Warning: Could not create index: {e}")
        
        # Verify foreign key exists (only if quote_pdf_templates table exists)
        if _has_table(inspector, 'quote_pdf_templates'):
            if not _has_foreign_key(inspector, 'quotes', 'fk_quotes_template_id'):
                print("[Migration 102] Creating missing foreign key fk_quotes_template_id...")
                try:
                    if dialect_name == 'sqlite':
                        # SQLite requires batch operations for foreign keys
                        with op.batch_alter_table('quotes', schema=None) as batch_op:
                            batch_op.create_foreign_key(
                                'fk_quotes_template_id',
                                'quote_pdf_templates',
                                ['template_id'],
                                ['id']
                            )
                    else:
                        # PostgreSQL and others
                        op.create_foreign_key(
                            'fk_quotes_template_id',
                            'quotes',
                            'quote_pdf_templates',
                            ['template_id'],
                            ['id'],
                            ondelete='SET NULL'
                        )
                    print("[Migration 102] ✓ Foreign key created")
                except Exception as e:
                    print(f"[Migration 102] ⚠ Warning: Could not create foreign key: {e}")
        
        return
    
    # Column doesn't exist, add it
    print("[Migration 102] Adding template_id column to quotes table...")
    try:
        op.add_column('quotes',
            sa.Column('template_id', sa.Integer(), nullable=True)
        )
        print("[Migration 102] ✓ Column added")
    except Exception as e:
        print(f"[Migration 102] ✗ Error adding column: {e}")
        raise
    
    # Create index
    print("[Migration 102] Creating index ix_quotes_template_id...")
    try:
        op.create_index('ix_quotes_template_id', 'quotes', ['template_id'])
        print("[Migration 102] ✓ Index created")
    except Exception as e:
        print(f"[Migration 102] ⚠ Warning: Could not create index: {e}")
    
    # Create foreign key if quote_pdf_templates table exists
    if _has_table(inspector, 'quote_pdf_templates'):
        print("[Migration 102] Creating foreign key fk_quotes_template_id...")
        try:
            if dialect_name == 'sqlite':
                # SQLite requires batch operations for foreign keys
                with op.batch_alter_table('quotes', schema=None) as batch_op:
                    batch_op.create_foreign_key(
                        'fk_quotes_template_id',
                        'quote_pdf_templates',
                        ['template_id'],
                        ['id']
                    )
            else:
                # PostgreSQL and others
                op.create_foreign_key(
                    'fk_quotes_template_id',
                    'quotes',
                    'quote_pdf_templates',
                    ['template_id'],
                    ['id'],
                    ondelete='SET NULL'
                )
            print("[Migration 102] ✓ Foreign key created")
        except Exception as e:
            print(f"[Migration 102] ⚠ Warning: Could not create foreign key: {e}")
    else:
        print("[Migration 102] ⚠ quote_pdf_templates table does not exist, skipping foreign key")
    
    print("[Migration 102] ✓ Migration completed successfully")


def downgrade():
    """Remove template_id column from quotes table"""
    bind = op.get_bind()
    inspector = inspect(bind)
    
    if not _has_table(inspector, 'quotes'):
        print("[Migration 102] ⊘ Quotes table does not exist, skipping downgrade")
        return
    
    if not _has_column(inspector, 'quotes', 'template_id'):
        print("[Migration 102] ⊘ template_id column does not exist, skipping downgrade")
        return
    
    print("[Migration 102] Removing template_id column from quotes table...")
    try:
        # Drop foreign key first
        if _has_foreign_key(inspector, 'quotes', 'fk_quotes_template_id'):
            try:
                op.drop_constraint('fk_quotes_template_id', 'quotes', type_='foreignkey')
                print("[Migration 102] ✓ Foreign key dropped")
            except Exception as e:
                print(f"[Migration 102] ⚠ Warning: Could not drop foreign key: {e}")
        
        # Drop index
        if _has_index(inspector, 'quotes', 'ix_quotes_template_id'):
            try:
                op.drop_index('ix_quotes_template_id', table_name='quotes')
                print("[Migration 102] ✓ Index dropped")
            except Exception as e:
                print(f"[Migration 102] ⚠ Warning: Could not drop index: {e}")
        
        # Drop column
        op.drop_column('quotes', 'template_id')
        print("[Migration 102] ✓ Column dropped")
    except Exception as e:
        print(f"[Migration 102] ✗ Error during downgrade: {e}")
        raise
