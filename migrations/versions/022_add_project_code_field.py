"""Add short project code field for compact identifiers

Revision ID: 023
Revises: 022
Create Date: 2025-10-23 00:00:00

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '023'
down_revision = '022'
branch_labels = None
depends_on = None


def upgrade():
    from sqlalchemy import inspect
    bind = op.get_bind()
    inspector = inspect(bind)
    existing_tables = inspector.get_table_names()
    
    if 'projects' not in existing_tables:
        return
    
    projects_columns = [col['name'] for col in inspector.get_columns('projects')]
    projects_indexes = [idx['name'] for idx in inspector.get_indexes('projects')]
    projects_unique_constraints = []
    try:
        if hasattr(inspector, 'get_unique_constraints'):
            projects_unique_constraints = [uc['name'] for uc in inspector.get_unique_constraints('projects')]
    except:
        pass

    # Add code column if not present (idempotent)
    if 'code' not in projects_columns:
        with op.batch_alter_table('projects') as batch_op:
            batch_op.add_column(sa.Column('code', sa.String(length=20), nullable=True))
            try:
                batch_op.create_unique_constraint('uq_projects_code', ['code'])
            except Exception:
                # Some dialects may not support unique with NULLs the same way; ignore if exists
                pass
            try:
                batch_op.create_index('ix_projects_code', ['code'])
            except Exception:
                pass
    else:
        # Column exists, but ensure constraint and index exist
        with op.batch_alter_table('projects') as batch_op:
            if 'uq_projects_code' not in projects_unique_constraints:
                try:
                    batch_op.create_unique_constraint('uq_projects_code', ['code'])
                except Exception:
                    pass
            if 'ix_projects_code' not in projects_indexes:
                try:
                    batch_op.create_index('ix_projects_code', ['code'])
                except Exception:
                    pass


def downgrade():
    with op.batch_alter_table('projects') as batch_op:
        try:
            batch_op.drop_index('ix_projects_code')
        except Exception:
            pass
        try:
            batch_op.drop_constraint('uq_projects_code', type_='unique')
        except Exception:
            pass
        try:
            batch_op.drop_column('code')
        except Exception:
            pass


