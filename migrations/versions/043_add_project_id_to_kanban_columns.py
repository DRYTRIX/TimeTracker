"""add project_id to kanban_columns table

Revision ID: 043
Revises: 042_client_prepaid_hours
Create Date: 2025-01-20

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import text, inspect


# revision identifiers, used by Alembic.
revision = '043'
down_revision = '042_client_prepaid_hours'
branch_labels = None
depends_on = None


def upgrade():
    """Add project_id column to kanban_columns for per-project kanban workflows"""
    
    conn = op.get_bind()
    inspector = inspect(conn)
    is_sqlite = conn.dialect.name == 'sqlite'
    existing_tables = inspector.get_table_names()
    
    if 'kanban_columns' not in existing_tables:
        # Table doesn't exist, skip migration
        return
    
    # Get existing columns and constraints
    kanban_columns = [col['name'] for col in inspector.get_columns('kanban_columns')]
    kanban_fks = [fk['name'] for fk in inspector.get_foreign_keys('kanban_columns')]
    kanban_indexes = [idx['name'] for idx in inspector.get_indexes('kanban_columns')]
    kanban_unique_constraints = []
    try:
        # Try to get unique constraints (method varies by database)
        if hasattr(inspector, 'get_unique_constraints'):
            kanban_unique_constraints = [uc['name'] for uc in inspector.get_unique_constraints('kanban_columns')]
    except:
        pass
    
    # Drop the old unique constraint on 'key' alone (handle different constraint names)
    for constraint_name in ['kanban_columns_key_key', 'uq_kanban_columns_key']:
        if constraint_name in kanban_unique_constraints:
            try:
                op.drop_constraint(constraint_name, 'kanban_columns', type_='unique')
            except Exception:
                pass
    
    # Add project_id column (nullable, NULL = global columns) - idempotent
    if 'project_id' not in kanban_columns:
        op.add_column('kanban_columns', 
            sa.Column('project_id', sa.Integer(), nullable=True)
        )
    
    # Add foreign key constraint - idempotent
    if 'fk_kanban_columns_project_id' not in kanban_fks:
        if is_sqlite:
            with op.batch_alter_table('kanban_columns', schema=None) as batch_op:
                batch_op.create_foreign_key(
                    'fk_kanban_columns_project_id',
                    'projects',
                    ['project_id'], ['id']
                )
        else:
            op.create_foreign_key(
                'fk_kanban_columns_project_id',
                'kanban_columns', 'projects',
                ['project_id'], ['id'],
                ondelete='CASCADE'
            )
    
    # Create index on project_id for better query performance - idempotent
    if 'idx_kanban_columns_project_id' not in kanban_indexes:
        op.create_index('idx_kanban_columns_project_id', 'kanban_columns', ['project_id'])
    
    # Explicitly set project_id to NULL for existing columns (they are global columns)
    if 'project_id' in kanban_columns:
        try:
            conn.execute(text("UPDATE kanban_columns SET project_id = NULL WHERE project_id IS NULL"))
        except Exception:
            pass
    
    # Create new unique constraint on (key, project_id) - idempotent
    # This allows the same key to exist for different projects, but unique per project
    # Note: PostgreSQL allows multiple NULLs in unique constraints, so global columns can share keys
    if 'uq_kanban_column_key_project' not in kanban_unique_constraints:
        try:
            op.create_unique_constraint(
                'uq_kanban_column_key_project',
                'kanban_columns',
                ['key', 'project_id']
            )
        except Exception:
            # Constraint might already exist with different name, skip
            pass


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

