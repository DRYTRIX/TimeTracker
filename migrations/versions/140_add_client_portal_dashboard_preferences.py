"""Add client_portal_dashboard_preferences table for dashboard widget customization

Revision ID: 140_client_portal_dashboard_prefs
Revises: 139_keyboard_shortcuts
Create Date: 2026-03-16

"""
from alembic import op
import sqlalchemy as sa


revision = "140_client_portal_dashboard_prefs"
down_revision = "139_keyboard_shortcuts"
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if "client_portal_dashboard_preferences" in inspector.get_table_names():
        return
    op.create_table(
        "client_portal_dashboard_preferences",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("client_id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=True),
        sa.Column("widget_ids", sa.JSON(), nullable=False),
        sa.Column("widget_order", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["client_id"], ["clients.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_client_portal_dashboard_preferences_client_id"),
        "client_portal_dashboard_preferences",
        ["client_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_client_portal_dashboard_preferences_user_id"),
        "client_portal_dashboard_preferences",
        ["user_id"],
        unique=False,
    )
    op.create_unique_constraint(
        "uq_client_portal_dashboard_pref_client_user",
        "client_portal_dashboard_preferences",
        ["client_id", "user_id"],
    )


def downgrade():
    op.drop_table("client_portal_dashboard_preferences")
