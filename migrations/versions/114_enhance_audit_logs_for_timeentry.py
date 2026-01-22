"""Enhance audit_logs table for TimeEntry comprehensive tracking

Revision ID: 114_enhance_audit_logs_timeentry
Revises: 113_add_invoice_buyer_reference
Create Date: 2025-01-30

Adds columns for reason, entity_metadata, full_old_state, and full_new_state
to support comprehensive TimeEntry audit logging.
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = '114_enhance_audit_logs_timeentry'
down_revision = '113_add_invoice_buyer_reference'
branch_labels = None
depends_on = None


def upgrade():
    """Add new columns to audit_logs table for enhanced TimeEntry tracking"""
    from sqlalchemy import inspect
    bind = op.get_bind()
    inspector = inspect(bind)
    
    existing_tables = inspector.get_table_names()
    
    if 'audit_logs' not in existing_tables:
        print("⊘ Table audit_logs does not exist, skipping enhancement")
        return
    
    # Check which columns already exist
    existing_columns = [col['name'] for col in inspector.get_columns('audit_logs')]
    
    # Add reason column
    if 'reason' not in existing_columns:
        try:
            op.add_column('audit_logs', sa.Column('reason', sa.Text(), nullable=True))
            print("✓ Added reason column to audit_logs")
        except Exception as e:
            print(f"⚠ Could not add reason column: {e}")
    
    # Add entity_metadata column (JSON for flexibility)
    if 'entity_metadata' not in existing_columns:
        try:
            # Use JSON for PostgreSQL, Text for SQLite
            conn = op.get_bind()
            is_postgres = conn.dialect.name == 'postgresql'
            
            if is_postgres:
                op.add_column('audit_logs', sa.Column('entity_metadata', postgresql.JSON(astext_type=sa.Text()), nullable=True))
            else:
                op.add_column('audit_logs', sa.Column('entity_metadata', sa.Text(), nullable=True))
            print("✓ Added entity_metadata column to audit_logs")
        except Exception as e:
            print(f"⚠ Could not add entity_metadata column: {e}")
    
    # Add full_old_state column
    if 'full_old_state' not in existing_columns:
        try:
            op.add_column('audit_logs', sa.Column('full_old_state', sa.Text(), nullable=True))
            print("✓ Added full_old_state column to audit_logs")
        except Exception as e:
            print(f"⚠ Could not add full_old_state column: {e}")
    
    # Add full_new_state column
    if 'full_new_state' not in existing_columns:
        try:
            op.add_column('audit_logs', sa.Column('full_new_state', sa.Text(), nullable=True))
            print("✓ Added full_new_state column to audit_logs")
        except Exception as e:
            print(f"⚠ Could not add full_new_state column: {e}")


def downgrade():
    """Remove enhanced columns from audit_logs table"""
    from sqlalchemy import inspect
    bind = op.get_bind()
    inspector = inspect(bind)
    
    existing_tables = inspector.get_table_names()
    
    if 'audit_logs' not in existing_tables:
        print("⊘ Table audit_logs does not exist, skipping")
        return
    
    existing_columns = [col['name'] for col in inspector.get_columns('audit_logs')]
    
    # Remove columns in reverse order
    columns_to_remove = ['full_new_state', 'full_old_state', 'entity_metadata', 'reason']
    
    for col_name in columns_to_remove:
        if col_name in existing_columns:
            try:
                op.drop_column('audit_logs', col_name)
                print(f"✓ Removed {col_name} column from audit_logs")
            except Exception as e:
                print(f"⚠ Could not remove {col_name} column: {e}")
