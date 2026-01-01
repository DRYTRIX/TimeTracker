"""Fix metadata column names if migration 079 didn't rename them

Revision ID: 080_fix_metadata_column_names
Revises: 079_rename_user_badges_metadata
Create Date: 2025-11-29 05:49:00

This migration ensures that:
- user_badges has achievement_metadata column (renames from metadata if needed)
- leaderboard_entries has entry_metadata column (renames from metadata if needed)

This handles cases where migration 079 ran but tables didn't exist yet.
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "080_fix_metadata_column_names"
down_revision = "079_rename_user_badges_metadata"
branch_labels = None
depends_on = None


def upgrade():
    """Ensure metadata columns have correct names"""
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    is_sqlite = bind.dialect.name == 'sqlite'
    table_names = set(inspector.get_table_names())

    # 1. Fix user_badges.achievement_metadata
    if 'user_badges' in table_names:
        user_badges_cols = {c['name'] for c in inspector.get_columns('user_badges')}
        
        if 'achievement_metadata' in user_badges_cols:
            print("✓ Column user_badges.achievement_metadata already exists")
        elif 'metadata' in user_badges_cols:
            # Rename metadata to achievement_metadata
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
                print(f"⚠ Error renaming user_badges.metadata: {e}")
                # If rename fails, try adding the column instead
                try:
                    if is_sqlite:
                        with op.batch_alter_table('user_badges', schema=None) as batch_op:
                            batch_op.add_column(sa.Column('achievement_metadata', sa.JSON(), nullable=True))
                    else:
                        op.add_column('user_badges',
                                    sa.Column('achievement_metadata', sa.JSON(), nullable=True))
                    print("✓ Added user_badges.achievement_metadata column")
                except Exception as e2:
                    print(f"⚠ Error adding user_badges.achievement_metadata: {e2}")
        else:
            # Neither column exists, add the correct one
            try:
                if is_sqlite:
                    with op.batch_alter_table('user_badges', schema=None) as batch_op:
                        batch_op.add_column(sa.Column('achievement_metadata', sa.JSON(), nullable=True))
                else:
                    op.add_column('user_badges',
                                sa.Column('achievement_metadata', sa.JSON(), nullable=True))
                print("✓ Added user_badges.achievement_metadata column")
            except Exception as e:
                print(f"⚠ Error adding user_badges.achievement_metadata: {e}")

    # 2. Fix leaderboard_entries.entry_metadata
    if 'leaderboard_entries' in table_names:
        leaderboard_entries_cols = {c['name'] for c in inspector.get_columns('leaderboard_entries')}
        
        if 'entry_metadata' in leaderboard_entries_cols:
            print("✓ Column leaderboard_entries.entry_metadata already exists")
        elif 'metadata' in leaderboard_entries_cols:
            # Rename metadata to entry_metadata
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
                print(f"⚠ Error renaming leaderboard_entries.metadata: {e}")
                # If rename fails, try adding the column instead
                try:
                    if is_sqlite:
                        with op.batch_alter_table('leaderboard_entries', schema=None) as batch_op:
                            batch_op.add_column(sa.Column('entry_metadata', sa.JSON(), nullable=True))
                    else:
                        op.add_column('leaderboard_entries',
                                    sa.Column('entry_metadata', sa.JSON(), nullable=True))
                    print("✓ Added leaderboard_entries.entry_metadata column")
                except Exception as e2:
                    print(f"⚠ Error adding leaderboard_entries.entry_metadata: {e2}")
        else:
            # Neither column exists, add the correct one
            try:
                if is_sqlite:
                    with op.batch_alter_table('leaderboard_entries', schema=None) as batch_op:
                        batch_op.add_column(sa.Column('entry_metadata', sa.JSON(), nullable=True))
                else:
                    op.add_column('leaderboard_entries',
                                sa.Column('entry_metadata', sa.JSON(), nullable=True))
                print("✓ Added leaderboard_entries.entry_metadata column")
            except Exception as e:
                print(f"⚠ Error adding leaderboard_entries.entry_metadata: {e}")


def downgrade():
    """Revert column names back to metadata (if needed)"""
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    is_sqlite = bind.dialect.name == 'sqlite'
    table_names = set(inspector.get_table_names())

    # 1. Revert user_badges.achievement_metadata back to metadata
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
                print(f"⚠ Error reverting user_badges.achievement_metadata: {e}")

    # 2. Revert leaderboard_entries.entry_metadata back to metadata
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
                print(f"⚠ Error reverting leaderboard_entries.entry_metadata: {e}")

