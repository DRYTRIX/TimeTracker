"""Add issues table for client-reported issues/bug tracking

Revision ID: 101_add_issues_table
Revises: 100_add_comment_attachments
Create Date: 2026-01-05

This migration creates the issues table that was missing from the database.
The Issue model exists in the codebase but no migration had created the table.
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '101_add_issues_table'
down_revision = '100_add_comment_attachments'
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
    """Create issues table if it doesn't exist"""
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    
    # Determine database dialect for proper default values
    dialect_name = bind.dialect.name if bind else 'generic'
    print(f"[Migration 101] Running on {dialect_name} database")
    
    # Set appropriate boolean defaults based on database
    if dialect_name == 'sqlite':
        bool_true_default = '1'
        bool_false_default = '0'
        timestamp_default = "(datetime('now'))"
    elif dialect_name == 'postgresql':
        bool_true_default = 'true'
        bool_false_default = 'false'
        timestamp_default = 'CURRENT_TIMESTAMP'
    else:  # MySQL/MariaDB and others
        bool_true_default = '1'
        bool_false_default = '0'
        timestamp_default = 'CURRENT_TIMESTAMP'
    
    # Create issues table if it doesn't exist
    if not _has_table(inspector, 'issues'):
        print("[Migration 101] Creating issues table...")
        try:
            # Check if required tables exist for foreign keys
            has_clients = _has_table(inspector, 'clients')
            has_projects = _has_table(inspector, 'projects')
            has_tasks = _has_table(inspector, 'tasks')
            has_users = _has_table(inspector, 'users')
            
            # Build foreign key constraints
            fk_constraints = []
            
            if has_clients:
                fk_constraints.append(
                    sa.ForeignKeyConstraint(['client_id'], ['clients.id'], name='fk_issues_client_id', ondelete='CASCADE')
                )
                print("[Migration 101]   Including client_id FK")
            else:
                print("[Migration 101]   ⚠ Skipping client_id FK (clients table doesn't exist)")
            
            if has_projects:
                fk_constraints.append(
                    sa.ForeignKeyConstraint(['project_id'], ['projects.id'], name='fk_issues_project_id', ondelete='CASCADE')
                )
                print("[Migration 101]   Including project_id FK")
            else:
                print("[Migration 101]   ⚠ Skipping project_id FK (projects table doesn't exist)")
            
            if has_tasks:
                fk_constraints.append(
                    sa.ForeignKeyConstraint(['task_id'], ['tasks.id'], name='fk_issues_task_id', ondelete='SET NULL')
                )
                print("[Migration 101]   Including task_id FK")
            else:
                print("[Migration 101]   ⚠ Skipping task_id FK (tasks table doesn't exist)")
            
            if has_users:
                fk_constraints.append(
                    sa.ForeignKeyConstraint(['assigned_to'], ['users.id'], name='fk_issues_assigned_to', ondelete='SET NULL')
                )
                fk_constraints.append(
                    sa.ForeignKeyConstraint(['created_by'], ['users.id'], name='fk_issues_created_by', ondelete='SET NULL')
                )
                print("[Migration 101]   Including user FKs (assigned_to, created_by)")
            else:
                print("[Migration 101]   ⚠ Skipping user FKs (users table doesn't exist)")
            
            op.create_table(
                'issues',
                sa.Column('id', sa.Integer(), nullable=False),
                sa.Column('client_id', sa.Integer(), nullable=False),
                sa.Column('project_id', sa.Integer(), nullable=True),
                sa.Column('task_id', sa.Integer(), nullable=True),
                sa.Column('title', sa.String(length=200), nullable=False),
                sa.Column('description', sa.Text(), nullable=True),
                sa.Column('status', sa.String(length=20), nullable=False, server_default='open'),
                sa.Column('priority', sa.String(length=20), nullable=False, server_default='medium'),
                sa.Column('submitted_by_client', sa.Boolean(), nullable=False, server_default=sa.text(bool_true_default)),
                sa.Column('client_submitter_name', sa.String(length=200), nullable=True),
                sa.Column('client_submitter_email', sa.String(length=200), nullable=True),
                sa.Column('assigned_to', sa.Integer(), nullable=True),
                sa.Column('created_by', sa.Integer(), nullable=True),
                sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text(timestamp_default)),
                sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text(timestamp_default)),
                sa.Column('resolved_at', sa.DateTime(), nullable=True),
                sa.Column('closed_at', sa.DateTime(), nullable=True),
                *fk_constraints,  # Include FKs during table creation for SQLite compatibility
                sa.PrimaryKeyConstraint('id')
            )
            print("[Migration 101] ✓ Table created with foreign keys")
        except Exception as e:
            print(f"[Migration 101] ✗ Error creating table: {e}")
            raise
        
        # Create indexes
        print("[Migration 101] Creating indexes...")
        try:
            # Indexes as defined in the Issue model
            op.create_index('ix_issues_client_id', 'issues', ['client_id'])
            op.create_index('ix_issues_project_id', 'issues', ['project_id'])
            op.create_index('ix_issues_task_id', 'issues', ['task_id'])
            op.create_index('ix_issues_title', 'issues', ['title'])
            op.create_index('ix_issues_status', 'issues', ['status'])
            op.create_index('ix_issues_assigned_to', 'issues', ['assigned_to'])
            op.create_index('ix_issues_created_by', 'issues', ['created_by'])
            print("[Migration 101] ✓ Indexes created")
        except Exception as e:
            print(f"[Migration 101] ⚠ Warning: Could not create all indexes: {e}")
            # Don't fail the migration if indexes fail - they can be added later
    else:
        print("[Migration 101] ✓ Issues table already exists, skipping creation")
        
        # Verify all columns exist (in case table was partially created)
        if _has_table(inspector, 'issues'):
            required_columns = [
                'id', 'client_id', 'project_id', 'task_id', 'title', 'description',
                'status', 'priority', 'submitted_by_client', 'client_submitter_name',
                'client_submitter_email', 'assigned_to', 'created_by', 'created_at',
                'updated_at', 'resolved_at', 'closed_at'
            ]
            missing_columns = []
            for col in required_columns:
                if not _has_column(inspector, 'issues', col):
                    missing_columns.append(col)
            
            if missing_columns:
                print(f"[Migration 101] ⚠ Warning: Issues table exists but is missing columns: {missing_columns}")
                print("[Migration 101]   You may need to manually add these columns or recreate the table")
    
    print("[Migration 101] ✓ Migration completed successfully")


def downgrade():
    """Drop issues table"""
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    
    if _has_table(inspector, 'issues'):
        print("[Migration 101] Dropping issues table...")
        try:
            # Drop indexes first
            indexes_to_drop = [
                'ix_issues_created_by',
                'ix_issues_assigned_to',
                'ix_issues_status',
                'ix_issues_title',
                'ix_issues_task_id',
                'ix_issues_project_id',
                'ix_issues_client_id',
            ]
            for idx_name in indexes_to_drop:
                try:
                    if _has_index(inspector, 'issues', idx_name):
                        op.drop_index(idx_name, table_name='issues')
                except Exception:
                    pass  # Index might not exist or already dropped
            
            op.drop_table('issues')
            print("[Migration 101] ✓ Issues table dropped")
        except Exception as e:
            print(f"[Migration 101] ⚠ Warning: Could not drop issues table: {e}")
    else:
        print("[Migration 101] ⊘ Issues table does not exist, skipping drop")
