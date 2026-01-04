"""Add payment terms to quotes

Revision ID: 053
Revises: 052
Create Date: 2025-01-27

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '053'
down_revision = '052'
branch_labels = None
depends_on = None


def upgrade():
    """Add payment_terms field to quotes table"""
    from sqlalchemy import inspect
    bind = op.get_bind()
    inspector = inspect(bind)
    
    existing_tables = inspector.get_table_names()
    if 'quotes' not in existing_tables:
        return
    
    quotes_columns = {c['name'] for c in inspector.get_columns('quotes')}
    
    if 'payment_terms' in quotes_columns:
        print("✓ Column payment_terms already exists in quotes table")
        return
    
    try:
        op.add_column('quotes',
            sa.Column('payment_terms', sa.String(length=100), nullable=True)
        )
        print("✓ Added payment_terms column to quotes table")
    except Exception as e:
        error_msg = str(e)
        if 'already exists' in error_msg.lower() or 'duplicate' in error_msg.lower():
            print("✓ Column payment_terms already exists in quotes table (detected via error)")
        else:
            print(f"✗ Error adding payment_terms column: {e}")
            raise


def downgrade():
    """Remove payment_terms field from quotes table"""
    from sqlalchemy import inspect
    bind = op.get_bind()
    inspector = inspect(bind)
    
    existing_tables = inspector.get_table_names()
    if 'quotes' not in existing_tables:
        return
    
    quotes_columns = {c['name'] for c in inspector.get_columns('quotes')}
    
    if 'payment_terms' not in quotes_columns:
        print("⊘ Column payment_terms does not exist in quotes table, skipping")
        return
    
    try:
        op.drop_column('quotes', 'payment_terms')
        print("✓ Dropped payment_terms column from quotes table")
    except Exception as e:
        error_msg = str(e)
        if 'does not exist' in error_msg.lower() or 'no such column' in error_msg.lower():
            print("⊘ Column payment_terms does not exist in quotes table (detected via error)")
        else:
            print(f"⚠ Warning: Could not drop payment_terms column: {e}")

