"""Add AI features and GPS tracking tables

Revision ID: 073_ai_features_gps_tracking
Revises: 072_client_portal_team_chat
Create Date: 2025-01-27

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '073_ai_features_gps_tracking'
down_revision = '072_client_portal_team_chat'
branch_labels = None
depends_on = None


def upgrade():
    """Create custom report configs, gamification, and GPS tracking tables"""
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    # Create custom_report_configs table
    if 'custom_report_configs' not in inspector.get_table_names():
        op.create_table(
            'custom_report_configs',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('name', sa.String(length=200), nullable=False),
            sa.Column('owner_id', sa.Integer(), nullable=False),
            sa.Column('report_type', sa.String(length=50), nullable=False),
            sa.Column('builder_config', sa.JSON(), nullable=False),
            sa.Column('layout_config', sa.JSON(), nullable=True),
            sa.Column('scope', sa.String(length=20), nullable=False, server_default='private'),
            sa.Column('shared_with', sa.JSON(), nullable=True),
            sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
            sa.Column('created_at', sa.DateTime(), nullable=False),
            sa.Column('updated_at', sa.DateTime(), nullable=False),
            sa.ForeignKeyConstraint(['owner_id'], ['users.id'], ),
            sa.PrimaryKeyConstraint('id')
        )
        op.create_index(op.f('ix_custom_report_configs_owner_id'), 'custom_report_configs', ['owner_id'], unique=False)

    # Create badges table
    if 'badges' not in inspector.get_table_names():
        op.create_table(
            'badges',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('name', sa.String(length=200), nullable=False),
            sa.Column('description', sa.Text(), nullable=True),
            sa.Column('icon', sa.String(length=100), nullable=True),
            sa.Column('badge_type', sa.String(length=50), nullable=False),
            sa.Column('criteria', sa.JSON(), nullable=False),
            sa.Column('points', sa.Integer(), nullable=False, server_default='0'),
            sa.Column('rarity', sa.String(length=20), nullable=False, server_default='common'),
            sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
            sa.Column('created_at', sa.DateTime(), nullable=False),
            sa.Column('updated_at', sa.DateTime(), nullable=False),
            sa.PrimaryKeyConstraint('id'),
            sa.UniqueConstraint('name')
        )

    # Create user_badges table
    if 'user_badges' not in inspector.get_table_names():
        op.create_table(
            'user_badges',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('user_id', sa.Integer(), nullable=False),
            sa.Column('badge_id', sa.Integer(), nullable=False),
            sa.Column('earned_at', sa.DateTime(), nullable=False),
            sa.Column('progress', sa.Integer(), nullable=False, server_default='100'),
            sa.Column('metadata', sa.JSON(), nullable=True),
            sa.ForeignKeyConstraint(['badge_id'], ['badges.id'], ),
            sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
            sa.PrimaryKeyConstraint('id'),
            sa.UniqueConstraint('user_id', 'badge_id', name='uq_user_badge')
        )
        op.create_index(op.f('ix_user_badges_user_id'), 'user_badges', ['user_id'], unique=False)
        op.create_index(op.f('ix_user_badges_badge_id'), 'user_badges', ['badge_id'], unique=False)
        op.create_index('ix_user_badges_user_earned', 'user_badges', ['user_id', 'earned_at'], unique=False)

    # Create leaderboards table
    if 'leaderboards' not in inspector.get_table_names():
        op.create_table(
            'leaderboards',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('name', sa.String(length=200), nullable=False),
            sa.Column('description', sa.Text(), nullable=True),
            sa.Column('leaderboard_type', sa.String(length=50), nullable=False),
            sa.Column('period', sa.String(length=20), nullable=False, server_default='all_time'),
            sa.Column('scope', sa.String(length=50), nullable=True),
            sa.Column('config', sa.JSON(), nullable=True),
            sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
            sa.Column('created_at', sa.DateTime(), nullable=False),
            sa.Column('updated_at', sa.DateTime(), nullable=False),
            sa.PrimaryKeyConstraint('id')
        )

    # Create leaderboard_entries table
    if 'leaderboard_entries' not in inspector.get_table_names():
        op.create_table(
            'leaderboard_entries',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('leaderboard_id', sa.Integer(), nullable=False),
            sa.Column('user_id', sa.Integer(), nullable=False),
            sa.Column('rank', sa.Integer(), nullable=False),
            sa.Column('score', sa.Numeric(10, 2), nullable=False),
            sa.Column('period_start', sa.DateTime(), nullable=False),
            sa.Column('period_end', sa.DateTime(), nullable=False),
            sa.Column('metadata', sa.JSON(), nullable=True),
            sa.Column('calculated_at', sa.DateTime(), nullable=False),
            sa.ForeignKeyConstraint(['leaderboard_id'], ['leaderboards.id'], ),
            sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
            sa.PrimaryKeyConstraint('id')
        )
        op.create_index(op.f('ix_leaderboard_entries_leaderboard_id'), 'leaderboard_entries', ['leaderboard_id'], unique=False)
        op.create_index(op.f('ix_leaderboard_entries_user_id'), 'leaderboard_entries', ['user_id'], unique=False)
        op.create_index('ix_leaderboard_entries_leaderboard_period', 'leaderboard_entries', ['leaderboard_id', 'period_start'], unique=False)
        op.create_index('ix_leaderboard_entries_user_period', 'leaderboard_entries', ['user_id', 'period_start'], unique=False)

    # Create mileage_tracks table
    if 'mileage_tracks' not in inspector.get_table_names():
        op.create_table(
            'mileage_tracks',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('expense_id', sa.Integer(), nullable=True),
            sa.Column('user_id', sa.Integer(), nullable=False),
            sa.Column('start_location', sa.String(length=200), nullable=True),
            sa.Column('end_location', sa.String(length=200), nullable=True),
            sa.Column('start_latitude', sa.Numeric(10, 8), nullable=True),
            sa.Column('start_longitude', sa.Numeric(11, 8), nullable=True),
            sa.Column('end_latitude', sa.Numeric(10, 8), nullable=True),
            sa.Column('end_longitude', sa.Numeric(11, 8), nullable=True),
            sa.Column('distance_km', sa.Numeric(10, 2), nullable=True),
            sa.Column('distance_miles', sa.Numeric(10, 2), nullable=True),
            sa.Column('track_points', sa.JSON(), nullable=True),
            sa.Column('started_at', sa.DateTime(), nullable=False),
            sa.Column('ended_at', sa.DateTime(), nullable=True),
            sa.Column('duration_seconds', sa.Integer(), nullable=True),
            sa.Column('method', sa.String(length=50), nullable=False, server_default='gps'),
            sa.Column('notes', sa.Text(), nullable=True),
            sa.Column('created_at', sa.DateTime(), nullable=False),
            sa.Column('updated_at', sa.DateTime(), nullable=False),
            sa.ForeignKeyConstraint(['expense_id'], ['expenses.id'], ),
            sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
            sa.PrimaryKeyConstraint('id')
        )
        op.create_index(op.f('ix_mileage_tracks_expense_id'), 'mileage_tracks', ['expense_id'], unique=False)
        op.create_index(op.f('ix_mileage_tracks_user_id'), 'mileage_tracks', ['user_id'], unique=False)
        op.create_index('ix_mileage_tracks_user_started', 'mileage_tracks', ['user_id', 'started_at'], unique=False)


def downgrade():
    """Drop tables"""
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    for table in ['mileage_tracks', 'leaderboard_entries', 'leaderboards', 
                  'user_badges', 'badges', 'custom_report_configs']:
        if table in inspector.get_table_names():
            op.drop_table(table)

