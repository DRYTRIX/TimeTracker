"""Add use_last_month_dates to report_email_schedules

Revision ID: 111_add_use_last_month_dates
Revises: 110_add_disabled_module_ids
Create Date: 2025-01-30

For monthly cadence: when use_last_month_dates is True, the report uses
the previous calendar month as the date range at run time.
"""
from alembic import op
import sqlalchemy as sa


revision = "111_add_use_last_month_dates"
down_revision = "110_add_disabled_module_ids"
branch_labels = None
depends_on = None


def _has_column(inspector, table_name: str, column_name: str) -> bool:
    try:
        return column_name in [col["name"] for col in inspector.get_columns(table_name)]
    except Exception:
        return False


def upgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if "report_email_schedules" not in inspector.get_table_names():
        return
    if _has_column(inspector, "report_email_schedules", "use_last_month_dates"):
        return
    op.add_column(
        "report_email_schedules",
        sa.Column("use_last_month_dates", sa.Boolean(), nullable=False, server_default=sa.false()),
    )


def downgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if "report_email_schedules" not in inspector.get_table_names():
        return
    if _has_column(inspector, "report_email_schedules", "use_last_month_dates"):
        op.drop_column("report_email_schedules", "use_last_month_dates")
