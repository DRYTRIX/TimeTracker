"""Add missing quote_number column to quotes table

Revision ID: 103_add_missing_quotes_quote_number
Revises: 102_add_missing_quotes_template_id
Create Date: 2026-01-05

This migration adds the missing quote_number column to the quotes table.
The column was supposed to be added/renamed in migration 051, but some databases
may have missed it due to migration execution order or partial failures.
This migration is idempotent and safe to run multiple times.
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect

# revision identifiers, used by Alembic.
revision = '103_add_missing_quotes_quote_number'
down_revision = '102_add_missing_quotes_template_id'
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
    """Add quote_number column to quotes table if it doesn't exist"""
    bind = op.get_bind()
    inspector = inspect(bind)
    
    dialect_name = bind.dialect.name if bind else 'generic'
    print(f"[Migration 103] Running on {dialect_name} database")
    
    # Check if quotes table exists
    if not _has_table(inspector, 'quotes'):
        print("[Migration 103] ⊘ Quotes table does not exist, skipping")
        return
    
    quotes_columns = {c["name"] for c in inspector.get_columns('quotes')}
    
    # Check if quote_number column already exists
    if 'quote_number' in quotes_columns:
        print("[Migration 103] ✓ quote_number column already exists in quotes table")
        
        # Verify index exists
        if not _has_index(inspector, 'quotes', 'ix_quotes_quote_number'):
            print("[Migration 103] Creating missing index ix_quotes_quote_number...")
            try:
                op.create_index('ix_quotes_quote_number', 'quotes', ['quote_number'], unique=True)
                print("[Migration 103] ✓ Index created")
            except Exception as e:
                print(f"[Migration 103] ⚠ Warning: Could not create index: {e}")
        
        return
    
    # Check if offer_number exists (old column name from before migration 051)
    if 'offer_number' in quotes_columns:
        print("[Migration 103] Found offer_number column, renaming to quote_number...")
        try:
            if dialect_name == 'sqlite':
                # SQLite requires batch operations for column renames
                with op.batch_alter_table('quotes', schema=None) as batch_op:
                    batch_op.alter_column('offer_number', new_column_name='quote_number')
            else:
                # PostgreSQL and others
                op.alter_column('quotes', 'offer_number', new_column_name='quote_number', 
                              existing_type=sa.String(length=50), existing_nullable=False)
            print("[Migration 103] ✓ Column renamed")
            
            # Rename index if it exists
            if _has_index(inspector, 'quotes', 'ix_offers_offer_number'):
                try:
                    op.drop_index('ix_offers_offer_number', table_name='quotes')
                    print("[Migration 103] ✓ Old index dropped")
                except Exception as e:
                    print(f"[Migration 103] ⚠ Warning: Could not drop old index: {e}")
            
            # Create new index
            if not _has_index(inspector, 'quotes', 'ix_quotes_quote_number'):
                try:
                    op.create_index('ix_quotes_quote_number', 'quotes', ['quote_number'], unique=True)
                    print("[Migration 103] ✓ New index created")
                except Exception as e:
                    print(f"[Migration 103] ⚠ Warning: Could not create index: {e}")
            
            return
        except Exception as e:
            print(f"[Migration 103] ✗ Error renaming column: {e}")
            raise
    
    # Neither column exists, add quote_number
    print("[Migration 103] Adding quote_number column to quotes table...")
    try:
        # Check if there are existing quotes - if so, we need to generate numbers for them
        conn = bind.connect()
        result = conn.execute(sa.text("SELECT COUNT(*) FROM quotes"))
        count = result.scalar()
        conn.close()
        
        if count > 0:
            # There are existing quotes, we need to populate quote_number
            # First add the column as nullable
            op.add_column('quotes',
                sa.Column('quote_number', sa.String(length=50), nullable=True)
            )
            print("[Migration 103] ✓ Column added (nullable)")
            
            # Generate quote numbers for existing quotes
            print(f"[Migration 103] Generating quote numbers for {count} existing quotes...")
            conn = bind.connect()
            # Use a simple numbering scheme: QUO-{id}
            # Handle different database dialects
            if dialect_name == 'postgresql':
                conn.execute(sa.text("""
                    UPDATE quotes 
                    SET quote_number = 'QUO-' || id::text 
                    WHERE quote_number IS NULL
                """))
            elif dialect_name == 'sqlite':
                conn.execute(sa.text("""
                    UPDATE quotes 
                    SET quote_number = 'QUO-' || CAST(id AS TEXT)
                    WHERE quote_number IS NULL
                """))
            else:
                # Generic SQL for other databases
                conn.execute(sa.text("""
                    UPDATE quotes 
                    SET quote_number = CONCAT('QUO-', CAST(id AS CHAR))
                    WHERE quote_number IS NULL
                """))
            conn.commit()
            conn.close()
            print("[Migration 103] ✓ Quote numbers generated")
            
            # Now make it NOT NULL
            print("[Migration 103] Making quote_number NOT NULL...")
            op.alter_column('quotes', 'quote_number', nullable=False)
            print("[Migration 103] ✓ Column set to NOT NULL")
        else:
            # No existing quotes, can add as NOT NULL directly
            op.add_column('quotes',
                sa.Column('quote_number', sa.String(length=50), nullable=False)
            )
            print("[Migration 103] ✓ Column added")
    except Exception as e:
        print(f"[Migration 103] ✗ Error adding column: {e}")
        raise
    
    # Create unique index
    print("[Migration 103] Creating unique index ix_quotes_quote_number...")
    try:
        op.create_index('ix_quotes_quote_number', 'quotes', ['quote_number'], unique=True)
        print("[Migration 103] ✓ Index created")
    except Exception as e:
        print(f"[Migration 103] ⚠ Warning: Could not create index: {e}")
    
    print("[Migration 103] ✓ Migration completed successfully")


def downgrade():
    """Remove quote_number column from quotes table (or rename back to offer_number)"""
    bind = op.get_bind()
    inspector = inspect(bind)
    
    if not _has_table(inspector, 'quotes'):
        print("[Migration 103] ⊘ Quotes table does not exist, skipping downgrade")
        return
    
    if not _has_column(inspector, 'quotes', 'quote_number'):
        print("[Migration 103] ⊘ quote_number column does not exist, skipping downgrade")
        return
    
    print("[Migration 103] Removing quote_number column from quotes table...")
    try:
        # Drop index first
        if _has_index(inspector, 'quotes', 'ix_quotes_quote_number'):
            try:
                op.drop_index('ix_quotes_quote_number', table_name='quotes')
                print("[Migration 103] ✓ Index dropped")
            except Exception as e:
                print(f"[Migration 103] ⚠ Warning: Could not drop index: {e}")
        
        # Drop column
        op.drop_column('quotes', 'quote_number')
        print("[Migration 103] ✓ Column dropped")
    except Exception as e:
        print(f"[Migration 103] ✗ Error during downgrade: {e}")
        raise
