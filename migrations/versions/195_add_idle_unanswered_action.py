"""Add idle_unanswered_action to settings.

Controls what happens when the "Still working?" grace window expires
unanswered: "review" (flag and keep running) or "auto_stop" (stop credited
to last activity + idle timeout). Issue #722.

Revision ID: 195_add_idle_unanswered_action
Revises: 194_roadmap_features
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect

revision = "195_add_idle_unanswered_action"
down_revision = "194_roadmap_features"
branch_labels = None
depends_on = None


def _has_column(inspector, table_name: str, column_name: str) -> bool:
    try:
        return column_name in {c["name"] for c in inspector.get_columns(table_name)}
    except Exception:
        return False


def upgrade():
    bind = op.get_bind()
    inspector = inspect(bind)
    if not _has_column(inspector, "settings", "idle_unanswered_action"):
        op.add_column(
            "settings",
            sa.Column(
                "idle_unanswered_action",
                sa.String(length=16),
                nullable=False,
                server_default="review",
            ),
        )


def downgrade():
    bind = op.get_bind()
    inspector = inspect(bind)
    if _has_column(inspector, "settings", "idle_unanswered_action"):
        op.drop_column("settings", "idle_unanswered_action")
