"""Add user favorite projects functionality

Revision ID: 024
Revises: 023
Create Date: 2025-10-23 00:00:00

"""
from alembic import op
import sqlalchemy as sa
from datetime import datetime


# revision identifiers, used by Alembic.
revision = '024'
down_revision = '023'
branch_labels = None
depends_on = None


def upgrade():
    """Create user_favorite_projects association table"""
    bind = op.get_bind()
    dialect_name = bind.dialect.name if bind else 'generic'
    
    # Create the user_favorite_projects table
    try:
        op.create_table(
            'user_favorite_projects',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('user_id', sa.Integer(), nullable=False),
            sa.Column('project_id', sa.Integer(), nullable=False),
            sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
            sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
            sa.ForeignKeyConstraint(['project_id'], ['projects.id'], ondelete='CASCADE'),
            sa.PrimaryKeyConstraint('id'),
            sa.UniqueConstraint('user_id', 'project_id', name='uq_user_project_favorite')
        )
        
        # Create indexes for faster lookups
        op.create_index('ix_user_favorite_projects_user_id', 'user_favorite_projects', ['user_id'])
        op.create_index('ix_user_favorite_projects_project_id', 'user_favorite_projects', ['project_id'])
        
        print("✓ Created user_favorite_projects table")
    except Exception as e:
        print(f"⚠ Warning creating user_favorite_projects table: {e}")


def downgrade():
    """Drop user_favorite_projects association table"""
    try:
        op.drop_index('ix_user_favorite_projects_project_id', table_name='user_favorite_projects')
    except Exception:
        pass
    
    try:
        op.drop_index('ix_user_favorite_projects_user_id', table_name='user_favorite_projects')
    except Exception:
        pass
    
    try:
        op.drop_table('user_favorite_projects')
        print("✓ Dropped user_favorite_projects table")
    except Exception as e:
        print(f"⚠ Warning dropping user_favorite_projects table: {e}")

