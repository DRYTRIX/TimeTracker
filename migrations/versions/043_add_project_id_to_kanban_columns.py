"""add project_id to kanban_columns table

Revision ID: 043
Revises: 042_client_prepaid_hours
Create Date: 2025-01-20

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import text


# revision identifiers, used by Alembic.
revision = '043'
down_revision = '042_client_prepaid_hours'
branch_labels = None
depends_on = None


def upgrade():
    """Add project_id column to kanban_columns for per-project kanban workflows"""
    
    # Drop the old unique constraint on 'key' alone (handle different constraint names)
    try:
        op.drop_constraint('kanban_columns_key_key', 'kanban_columns', type_='unique')
    except Exception:
        # Try alternative constraint name that might exist
        try:
            op.drop_constraint('uq_kanban_columns_key', 'kanban_columns', type_='unique')
        except Exception:
            # Constraint might not exist or have different name, continue
            pass
    
    # Add project_id column (nullable, NULL = global columns)
    op.add_column('kanban_columns', 
        sa.Column('project_id', sa.Integer(), nullable=True)
    )
    
    # Add foreign key constraint
    op.create_foreign_key(
        'fk_kanban_columns_project_id',
        'kanban_columns', 'projects',
        ['project_id'], ['id'],
        ondelete='CASCADE'
    )
    
    # Create index on project_id for better query performance
    op.create_index('idx_kanban_columns_project_id', 'kanban_columns', ['project_id'])
    
    # Explicitly set project_id to NULL for existing columns (they are global columns)
    connection = op.get_bind()
    connection.execute(text("UPDATE kanban_columns SET project_id = NULL WHERE project_id IS NULL"))
    
    # Create new unique constraint on (key, project_id)
    # This allows the same key to exist for different projects, but unique per project
    # Note: PostgreSQL allows multiple NULLs in unique constraints, so global columns can share keys
    op.create_unique_constraint(
        'uq_kanban_column_key_project',
        'kanban_columns',
        ['key', 'project_id']
    )


def downgrade():
    """Remove project_id column from kanban_columns"""
    
    # Drop the new unique constraint
    op.drop_constraint('uq_kanban_column_key_project', 'kanban_columns', type_='unique')
    
    # Drop index
    op.drop_index('idx_kanban_columns_project_id', table_name='kanban_columns')
    
    # Drop foreign key
    op.drop_constraint('fk_kanban_columns_project_id', 'kanban_columns', type_='foreignkey')
    
    # Remove project_id column
    op.drop_column('kanban_columns', 'project_id')
    
    # Restore the old unique constraint on 'key' alone
    op.create_unique_constraint('kanban_columns_key_key', 'kanban_columns', ['key'])

