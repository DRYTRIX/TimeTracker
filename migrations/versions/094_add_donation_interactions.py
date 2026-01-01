"""Add donation_interactions table

Revision ID: 094_add_donation_interactions
Revises: 093_remove_ui_allow_flags
Create Date: 2025-01-27 12:00:00

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = "094_add_donation_interactions"
down_revision = "093_remove_ui_allow_flags"
branch_labels = None
depends_on = None


def upgrade():
    """Create donation_interactions table to track user interactions with donation prompts"""
    from sqlalchemy import inspect
    bind = op.get_bind()
    inspector = inspect(bind)
    
    # Add missing ui_show_issues column to users table if it doesn't exist
    # This column was missing from migration 077 and should have been in 092
    existing_tables = inspector.get_table_names()
    if 'users' in existing_tables:
        users_columns = {c['name'] for c in inspector.get_columns('users')}
        if 'ui_show_issues' not in users_columns:
            dialect_name = bind.dialect.name if bind else 'generic'
            bool_true_default = '1' if dialect_name == 'sqlite' else ('true' if dialect_name == 'postgresql' else '1')
            try:
                op.add_column('users', sa.Column('ui_show_issues', sa.Boolean(), nullable=False, server_default=sa.text(bool_true_default)))
                print("✓ Added ui_show_issues column to users table")
            except Exception as e:
                error_msg = str(e)
                if 'already exists' in error_msg.lower() or 'duplicate' in error_msg.lower():
                    print("✓ Column ui_show_issues already exists in users table (detected via error)")
                else:
                    print(f"⚠ Warning adding ui_show_issues column: {e}")
    
    # Create donation_interactions table (idempotent)
    if 'donation_interactions' not in existing_tables:
        op.create_table(
            "donation_interactions",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("user_id", sa.Integer(), nullable=False),
            sa.Column("interaction_type", sa.String(length=50), nullable=False),
            sa.Column("source", sa.String(length=100), nullable=True),
            sa.Column("time_entries_count", sa.Integer(), nullable=True),
            sa.Column("days_since_signup", sa.Integer(), nullable=True),
            sa.Column("total_hours", sa.Float(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
            sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("id"),
        )
        # Create index (idempotent)
        try:
            op.create_index("idx_donation_interactions_user_id", "donation_interactions", ["user_id"])
        except Exception:
            pass  # Index might already exist
    else:
        # Table exists, ensure index exists
        try:
            existing_indexes = [idx['name'] for idx in inspector.get_indexes('donation_interactions')]
            if 'idx_donation_interactions_user_id' not in existing_indexes:
                op.create_index("idx_donation_interactions_user_id", "donation_interactions", ["user_id"])
        except Exception:
            pass


def downgrade():
    """Drop donation_interactions table"""
    op.drop_index("idx_donation_interactions_user_id", table_name="donation_interactions")
    op.drop_table("donation_interactions")

