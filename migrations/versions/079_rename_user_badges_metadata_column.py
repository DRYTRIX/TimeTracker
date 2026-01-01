"""Rename metadata columns to match model definitions

Revision ID: 079_rename_user_badges_metadata
Revises: 078_system_ui_feature_flags
Create Date: 2025-11-29 05:40:00

This migration renames:
- user_badges.metadata -> user_badges.achievement_metadata
- leaderboard_entries.metadata -> leaderboard_entries.entry_metadata
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "079_rename_user_badges_metadata"
down_revision = "078_system_ui_feature_flags"
branch_labels = None
depends_on = None


def upgrade():
    """Rename metadata columns to match model definitions"""
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    is_sqlite = bind.dialect.name == 'sqlite'
    table_names = set(inspector.get_table_names())

    # 1. Rename user_badges.metadata -> user_badges.achievement_metadata
    if 'user_badges' in table_names:
        user_badges_cols = {c['name'] for c in inspector.get_columns('user_badges')}
        if 'metadata' in user_badges_cols and 'achievement_metadata' not in user_badges_cols:
            try:
                if is_sqlite:
                    with op.batch_alter_table('user_badges', schema=None) as batch_op:
                        batch_op.alter_column('metadata', new_column_name='achievement_metadata')
                else:
                    op.alter_column('user_badges', 'metadata', 
                                  new_column_name='achievement_metadata',
                                  existing_type=sa.JSON(),
                                  existing_nullable=True)
                print("✓ Renamed user_badges.metadata to achievement_metadata")
            except Exception as e:
                print(f"⚠ Warning renaming user_badges.metadata column: {e}")
        elif 'achievement_metadata' in user_badges_cols:
            print("✓ Column user_badges.achievement_metadata already exists")
        elif 'metadata' not in user_badges_cols:
            print("⚠ Column user_badges.metadata does not exist, cannot rename")
    else:
        print("⚠ user_badges table does not exist, skipping column rename")

    # 2. Rename leaderboard_entries.metadata -> leaderboard_entries.entry_metadata
    if 'leaderboard_entries' in table_names:
        leaderboard_entries_cols = {c['name'] for c in inspector.get_columns('leaderboard_entries')}
        if 'metadata' in leaderboard_entries_cols and 'entry_metadata' not in leaderboard_entries_cols:
            try:
                if is_sqlite:
                    with op.batch_alter_table('leaderboard_entries', schema=None) as batch_op:
                        batch_op.alter_column('metadata', new_column_name='entry_metadata')
                else:
                    op.alter_column('leaderboard_entries', 'metadata',
                                  new_column_name='entry_metadata',
                                  existing_type=sa.JSON(),
                                  existing_nullable=True)
                print("✓ Renamed leaderboard_entries.metadata to entry_metadata")
            except Exception as e:
                print(f"⚠ Warning renaming leaderboard_entries.metadata column: {e}")
        elif 'entry_metadata' in leaderboard_entries_cols:
            print("✓ Column leaderboard_entries.entry_metadata already exists")
        elif 'metadata' not in leaderboard_entries_cols:
            print("⚠ Column leaderboard_entries.metadata does not exist, cannot rename")
    else:
        print("⚠ leaderboard_entries table does not exist, skipping column rename")


def downgrade():
    """Rename columns back to original metadata names"""
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    is_sqlite = bind.dialect.name == 'sqlite'
    table_names = set(inspector.get_table_names())

    # 1. Rename user_badges.achievement_metadata back to metadata
    if 'user_badges' in table_names:
        user_badges_cols = {c['name'] for c in inspector.get_columns('user_badges')}
        if 'achievement_metadata' in user_badges_cols and 'metadata' not in user_badges_cols:
            try:
                if is_sqlite:
                    with op.batch_alter_table('user_badges', schema=None) as batch_op:
                        batch_op.alter_column('achievement_metadata', new_column_name='metadata')
                else:
                    op.alter_column('user_badges', 'achievement_metadata',
                                  new_column_name='metadata',
                                  existing_type=sa.JSON(),
                                  existing_nullable=True)
                print("✓ Renamed user_badges.achievement_metadata back to metadata")
            except Exception as e:
                print(f"⚠ Warning renaming user_badges.achievement_metadata column: {e}")
        elif 'metadata' in user_badges_cols:
            print("✓ Column user_badges.metadata already exists")
        elif 'achievement_metadata' not in user_badges_cols:
            print("⚠ Column user_badges.achievement_metadata does not exist, cannot rename")
    else:
        print("⚠ user_badges table does not exist, skipping column rename")

    # 2. Rename leaderboard_entries.entry_metadata back to metadata
    if 'leaderboard_entries' in table_names:
        leaderboard_entries_cols = {c['name'] for c in inspector.get_columns('leaderboard_entries')}
        if 'entry_metadata' in leaderboard_entries_cols and 'metadata' not in leaderboard_entries_cols:
            try:
                if is_sqlite:
                    with op.batch_alter_table('leaderboard_entries', schema=None) as batch_op:
                        batch_op.alter_column('entry_metadata', new_column_name='metadata')
                else:
                    op.alter_column('leaderboard_entries', 'entry_metadata',
                                  new_column_name='metadata',
                                  existing_type=sa.JSON(),
                                  existing_nullable=True)
                print("✓ Renamed leaderboard_entries.entry_metadata back to metadata")
            except Exception as e:
                print(f"⚠ Warning renaming leaderboard_entries.entry_metadata column: {e}")
        elif 'metadata' in leaderboard_entries_cols:
            print("✓ Column leaderboard_entries.metadata already exists")
        elif 'entry_metadata' not in leaderboard_entries_cols:
            print("⚠ Column leaderboard_entries.entry_metadata does not exist, cannot rename")
    else:
        print("⚠ leaderboard_entries table does not exist, skipping column rename")

