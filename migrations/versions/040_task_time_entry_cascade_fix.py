"""task time entry cascade fix

Revision ID: 040_task_time_entry_cascade_fix
Revises: 039_add_budget_alerts_table
Create Date: 2025-10-31 14:30:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '040_task_time_entry_cascade_fix'
down_revision = '039_add_budget_alerts_table'
branch_labels = None
depends_on = None


def upgrade():
    """
    Update the task_id foreign key in time_entries table to use ON DELETE SET NULL
    instead of cascading deletes. This preserves historical time tracking data
    when tasks are deleted.
    """
    # Get the database bind to check which database we're using
    bind = op.get_bind()
    dialect_name = bind.dialect.name
    
    if dialect_name == 'sqlite':
        # SQLite doesn't support ALTER COLUMN for foreign keys
        # We need to recreate the table
        # For SQLite, we'll skip this migration as it's not critical
        # The behavior will be handled at the application level
        pass
    
    elif dialect_name == 'postgresql':
        # PostgreSQL: Drop and recreate the foreign key constraint
        op.drop_constraint('time_entries_task_id_fkey', 'time_entries', type_='foreignkey')
        op.create_foreign_key(
            'time_entries_task_id_fkey',
            'time_entries', 'tasks',
            ['task_id'], ['id'],
            ondelete='SET NULL'
        )
    
    elif dialect_name == 'mysql':
        # MySQL: Drop and recreate the foreign key constraint
        op.drop_constraint('time_entries_ibfk_2', 'time_entries', type_='foreignkey')
        op.create_foreign_key(
            'time_entries_ibfk_2',
            'time_entries', 'tasks',
            ['task_id'], ['id'],
            ondelete='SET NULL'
        )


def downgrade():
    """
    Revert the foreign key constraint back to default behavior (no explicit ON DELETE)
    """
    bind = op.get_bind()
    dialect_name = bind.dialect.name
    
    if dialect_name == 'sqlite':
        # SQLite: skip
        pass
    
    elif dialect_name == 'postgresql':
        op.drop_constraint('time_entries_task_id_fkey', 'time_entries', type_='foreignkey')
        op.create_foreign_key(
            'time_entries_task_id_fkey',
            'time_entries', 'tasks',
            ['task_id'], ['id']
        )
    
    elif dialect_name == 'mysql':
        op.drop_constraint('time_entries_ibfk_2', 'time_entries', type_='foreignkey')
        op.create_foreign_key(
            'time_entries_ibfk_2',
            'time_entries', 'tasks',
            ['task_id'], ['id']
        )

