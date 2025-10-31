"""Add import/export tracking tables

Revision ID: 040_import_export
Revises: 039_add_budget_alerts_table
Create Date: 2024-10-31 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from datetime import datetime


# revision identifiers, used by Alembic.
revision = '040_import_export'
down_revision = '039_add_budget_alerts'
branch_label = None
depends_on = None


def upgrade():
    """Create import/export tracking tables"""
    
    # Create data_imports table
    op.create_table(
        'data_imports',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('import_type', sa.String(length=50), nullable=False),
        sa.Column('source_file', sa.String(length=500), nullable=True),
        sa.Column('status', sa.String(length=20), nullable=False, server_default='pending'),
        sa.Column('total_records', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('successful_records', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('failed_records', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('error_log', sa.Text(), nullable=True),
        sa.Column('import_summary', sa.Text(), nullable=True),
        sa.Column('started_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('completed_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create indexes for data_imports
    op.create_index('ix_data_imports_user_id', 'data_imports', ['user_id'])
    op.create_index('ix_data_imports_status', 'data_imports', ['status'])
    op.create_index('ix_data_imports_started_at', 'data_imports', ['started_at'])
    
    # Create data_exports table
    op.create_table(
        'data_exports',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('export_type', sa.String(length=50), nullable=False),
        sa.Column('export_format', sa.String(length=20), nullable=False),
        sa.Column('file_path', sa.String(length=500), nullable=True),
        sa.Column('file_size', sa.Integer(), nullable=True),
        sa.Column('status', sa.String(length=20), nullable=False, server_default='pending'),
        sa.Column('filters', sa.Text(), nullable=True),
        sa.Column('record_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('completed_at', sa.DateTime(), nullable=True),
        sa.Column('expires_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create indexes for data_exports
    op.create_index('ix_data_exports_user_id', 'data_exports', ['user_id'])
    op.create_index('ix_data_exports_status', 'data_exports', ['status'])
    op.create_index('ix_data_exports_created_at', 'data_exports', ['created_at'])
    op.create_index('ix_data_exports_expires_at', 'data_exports', ['expires_at'])


def downgrade():
    """Drop import/export tracking tables"""
    
    # Drop indexes
    op.drop_index('ix_data_exports_expires_at', 'data_exports')
    op.drop_index('ix_data_exports_created_at', 'data_exports')
    op.drop_index('ix_data_exports_status', 'data_exports')
    op.drop_index('ix_data_exports_user_id', 'data_exports')
    
    op.drop_index('ix_data_imports_started_at', 'data_imports')
    op.drop_index('ix_data_imports_status', 'data_imports')
    op.drop_index('ix_data_imports_user_id', 'data_imports')
    
    # Drop tables
    op.drop_table('data_exports')
    op.drop_table('data_imports')

