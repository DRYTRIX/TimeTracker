"""Add client billing support to time entries

Revision ID: 076_client_billing_time_entries
Revises: 075_custom_fields_link_templates
Create Date: 2025-01-27

This migration adds:
- Makes project_id nullable in time_entries table
- Adds client_id column to time_entries table for direct client billing
- Adds check constraint to ensure either project_id or client_id is provided
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = '076_client_billing_time_entries'
down_revision = '075_custom_fields_link_templates'
branch_labels = None
depends_on = None


def _has_column(inspector, table_name: str, column_name: str) -> bool:
    """Check if a column exists in a table"""
    try:
        return column_name in [col['name'] for col in inspector.get_columns(table_name)]
    except Exception:
        return False


def upgrade():
    """Add client_id to time_entries and make project_id nullable"""
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if 'time_entries' not in inspector.get_table_names():
        return

    # Drop existing foreign key constraint on project_id if it exists
    # We'll need to recreate it as nullable
    try:
        # Get foreign key constraints
        fk_constraints = [
            fk['name'] for fk in inspector.get_foreign_keys('time_entries')
            if 'project_id' in [col for col in fk.get('constrained_columns', [])]
        ]
        for fk_name in fk_constraints:
            op.drop_constraint(fk_name, 'time_entries', type_='foreignkey')
    except Exception:
        pass

    conn = op.get_bind()
    is_sqlite = conn.dialect.name == 'sqlite'
    
    # Make project_id nullable
    if is_sqlite:
        with op.batch_alter_table('time_entries', schema=None) as batch_op:
            batch_op.alter_column('project_id', nullable=True)
            
            # Add client_id column if it doesn't exist
            if not _has_column(inspector, 'time_entries', 'client_id'):
                batch_op.add_column(sa.Column('client_id', sa.Integer(), nullable=True))
            
            # Recreate foreign key constraint for project_id (nullable)
            batch_op.create_foreign_key(
                'fk_time_entries_project_id',
                'projects',
                ['project_id'], ['id']
            )
            
            # Add foreign key constraint for client_id
            if _has_column(inspector, 'time_entries', 'client_id'):
                batch_op.create_foreign_key(
                    'fk_time_entries_client_id',
                    'clients',
                    ['client_id'], ['id']
                )
    else:
        op.alter_column('time_entries', 'project_id',
                        existing_type=sa.Integer(),
                        nullable=True)

        # Add client_id column if it doesn't exist
        if not _has_column(inspector, 'time_entries', 'client_id'):
            op.add_column('time_entries', sa.Column('client_id', sa.Integer(), nullable=True))
            op.create_index('idx_time_entries_client_id', 'time_entries', ['client_id'])

        # Recreate foreign key constraint for project_id (nullable)
        op.create_foreign_key(
            'fk_time_entries_project_id',
            'time_entries', 'projects',
            ['project_id'], ['id'],
            ondelete='CASCADE'
        )

        # Add foreign key constraint for client_id
        op.create_foreign_key(
            'fk_time_entries_client_id',
            'time_entries', 'clients',
            ['client_id'], ['id'],
            ondelete='CASCADE'
        )

    # Add check constraint to ensure either project_id or client_id is provided
    # Note: PostgreSQL check constraints can't directly check for NULL, so we use a function
    # For SQLite/MySQL compatibility, we'll handle this in application logic
    # But we can add a PostgreSQL-specific check if needed
    try:
        op.execute("""
            ALTER TABLE time_entries 
            ADD CONSTRAINT chk_time_entries_project_or_client 
            CHECK (project_id IS NOT NULL OR client_id IS NOT NULL)
        """)
    except Exception:
        # If constraint creation fails (e.g., existing data violates it), 
        # we'll handle validation in application code
        pass


def downgrade():
    """Remove client_id and make project_id required again"""
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if 'time_entries' not in inspector.get_table_names():
        return

    # Remove check constraint
    try:
        op.drop_constraint('chk_time_entries_project_or_client', 'time_entries', type_='check')
    except Exception:
        pass

    # Remove client_id foreign key and column
    if _has_column(inspector, 'time_entries', 'client_id'):
        try:
            op.drop_constraint('fk_time_entries_client_id', 'time_entries', type_='foreignkey')
        except Exception:
            pass
        try:
            op.drop_index('idx_time_entries_client_id', table_name='time_entries')
        except Exception:
            pass
        op.drop_column('time_entries', 'client_id')

    # Make project_id required again
    # First, ensure all entries have a project_id (set to a default if needed)
    # In practice, you might want to migrate data first
    op.alter_column('time_entries', 'project_id',
                    existing_type=sa.Integer(),
                    nullable=False)

    # Recreate foreign key constraint for project_id (non-nullable)
    try:
        op.drop_constraint('fk_time_entries_project_id', 'time_entries', type_='foreignkey')
    except Exception:
        pass
    
    op.create_foreign_key(
        'fk_time_entries_project_id',
        'time_entries', 'projects',
        ['project_id'], ['id'],
        ondelete='CASCADE'
    )

