"""Add calendar_default_view to users

Revision ID: 123_add_calendar_default_view
Revises: 122_add_settings_donate_ui_hidden
Create Date: 2026-02-09

User preference for default calendar view (day/week/month). None = use last view (session).
"""
from alembic import op
import sqlalchemy as sa


revision = "123_add_calendar_default_view"
down_revision = "122_add_settings_donate_ui_hidden"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("users") as batch_op:
        batch_op.add_column(
            sa.Column("calendar_default_view", sa.String(length=10), nullable=True)
        )


def downgrade():
    with op.batch_alter_table("users") as batch_op:
        batch_op.drop_column("calendar_default_view")
