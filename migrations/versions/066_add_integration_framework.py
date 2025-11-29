"""add integration framework

Revision ID: 066_integration_framework
Revises: 065_add_new_features
Create Date: 2024-01-01 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '066_integration_framework'
down_revision = '065'
branch_labels = None
depends_on = None


def upgrade():
    # Create integrations table
    op.create_table('integrations',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('provider', sa.String(length=50), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False),
        sa.Column('config', sa.JSON(), nullable=True),
        sa.Column('last_sync_at', sa.DateTime(), nullable=True),
        sa.Column('last_sync_status', sa.String(length=20), nullable=True),
        sa.Column('last_error', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_integrations_provider'), 'integrations', ['provider'], unique=False)
    op.create_index(op.f('ix_integrations_user_id'), 'integrations', ['user_id'], unique=False)

    # Create integration_credentials table
    op.create_table('integration_credentials',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('integration_id', sa.Integer(), nullable=False),
        sa.Column('access_token', sa.Text(), nullable=True),
        sa.Column('refresh_token', sa.Text(), nullable=True),
        sa.Column('token_type', sa.String(length=20), nullable=False),
        sa.Column('expires_at', sa.DateTime(), nullable=True),
        sa.Column('scope', sa.String(length=500), nullable=True),
        sa.Column('extra_data', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['integration_id'], ['integrations.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_integration_credentials_integration_id'), 'integration_credentials', ['integration_id'], unique=False)

    # Create integration_events table
    op.create_table('integration_events',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('integration_id', sa.Integer(), nullable=False),
        sa.Column('event_type', sa.String(length=50), nullable=False),
        sa.Column('status', sa.String(length=20), nullable=False),
        sa.Column('message', sa.Text(), nullable=True),
        sa.Column('event_metadata', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['integration_id'], ['integrations.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_integration_events_integration_id'), 'integration_events', ['integration_id'], unique=False)
    op.create_index(op.f('ix_integration_events_created_at'), 'integration_events', ['created_at'], unique=False)


def downgrade():
    op.drop_index(op.f('ix_integration_events_created_at'), table_name='integration_events')
    op.drop_index(op.f('ix_integration_events_integration_id'), table_name='integration_events')
    op.drop_table('integration_events')
    op.drop_index(op.f('ix_integration_credentials_integration_id'), table_name='integration_credentials')
    op.drop_table('integration_credentials')
    op.drop_index(op.f('ix_integrations_user_id'), table_name='integrations')
    op.drop_index(op.f('ix_integrations_provider'), table_name='integrations')
    op.drop_table('integrations')

