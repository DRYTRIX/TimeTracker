"""Add default break rules to settings (Issue #561)

Revision ID: 138_add_break_rules
Revises: 137_add_break_time
Create Date: 2026-03-11

Optional default break rules (e.g. Germany: >6h = 30 min, >9h = 45 min).
"""
from alembic import op
import sqlalchemy as sa


revision = "138_add_break_rules"
down_revision = "137_add_break_time"
branch_labels = None
depends_on = None


def upgrade():
    from sqlalchemy import inspect

    bind = op.get_bind()
    inspector = inspect(bind)
    if "settings" not in inspector.get_table_names():
        return
    columns = {c["name"] for c in inspector.get_columns("settings")}

    if "break_after_hours_1" not in columns:
        op.add_column("settings", sa.Column("break_after_hours_1", sa.Float(), nullable=True, server_default="6"))
    if "break_minutes_1" not in columns:
        op.add_column("settings", sa.Column("break_minutes_1", sa.Integer(), nullable=True, server_default="30"))
    if "break_after_hours_2" not in columns:
        op.add_column("settings", sa.Column("break_after_hours_2", sa.Float(), nullable=True, server_default="9"))
    if "break_minutes_2" not in columns:
        op.add_column("settings", sa.Column("break_minutes_2", sa.Integer(), nullable=True, server_default="45"))


def downgrade():
    from sqlalchemy import inspect

    bind = op.get_bind()
    inspector = inspect(bind)
    if "settings" not in inspector.get_table_names():
        return
    columns = {c["name"] for c in inspector.get_columns("settings")}
    for name in ["break_after_hours_2", "break_minutes_2", "break_after_hours_1", "break_minutes_1"]:
        if name in columns:
            op.drop_column("settings", name)
