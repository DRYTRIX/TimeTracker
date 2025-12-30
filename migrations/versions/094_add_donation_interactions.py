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
    op.create_index("idx_donation_interactions_user_id", "donation_interactions", ["user_id"])


def downgrade():
    """Drop donation_interactions table"""
    op.drop_index("idx_donation_interactions_user_id", table_name="donation_interactions")
    op.drop_table("donation_interactions")

