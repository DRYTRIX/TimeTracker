"""Allow auto-imported time entries without project or client

Revision ID: 089_allow_auto_entries_no_project
Revises: 088_salesman_splitting_reports
Create Date: 2026-01-07

This migration updates the check constraint to allow time entries with
both project_id and client_id as NULL when source='auto' (for auto-imported
entries from calendar integrations).
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '089_allow_auto_entries_no_project'
down_revision = '088_salesman_splitting_reports'
branch_labels = None
depends_on = None


def upgrade():
    """Update check constraint to allow NULL project_id and client_id for auto entries"""
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if 'time_entries' not in inspector.get_table_names():
        return

    conn = op.get_bind()
    is_sqlite = conn.dialect.name == 'sqlite'
    
    # Drop existing constraint
    try:
        op.drop_constraint('chk_time_entries_project_or_client', 'time_entries', type_='check')
    except Exception:
        # Constraint might not exist or have different name
        pass

    # Add new constraint that allows NULL for both when source='auto'
    # For PostgreSQL
    if not is_sqlite:
        try:
            op.execute("""
                ALTER TABLE time_entries 
                ADD CONSTRAINT chk_time_entries_project_or_client 
                CHECK (project_id IS NOT NULL OR client_id IS NOT NULL OR source = 'auto')
            """)
        except Exception as e:
            # If constraint creation fails, log but continue
            # Application-level validation will handle it
            print(f"Warning: Could not create check constraint: {e}")
    # For SQLite, we rely on application-level validation
    # SQLite doesn't support complex CHECK constraints well


def downgrade():
    """Revert to original constraint requiring project_id or client_id"""
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if 'time_entries' not in inspector.get_table_names():
        return

    # Drop new constraint
    try:
        op.drop_constraint('chk_time_entries_project_or_client', 'time_entries', type_='check')
    except Exception:
        pass

    # Recreate original constraint
    conn = op.get_bind()
    is_sqlite = conn.dialect.name == 'sqlite'
    
    if not is_sqlite:
        try:
            op.execute("""
                ALTER TABLE time_entries 
                ADD CONSTRAINT chk_time_entries_project_or_client 
                CHECK (project_id IS NOT NULL OR client_id IS NOT NULL)
            """)
        except Exception:
            pass
