"""Seed Overtime leave type for take-overtime-as-paid-leave (Issue #560)

Revision ID: 136_seed_overtime_leave_type
Revises: 135_remind_to_log
Create Date: 2026-03-11

Creates a leave type with code 'overtime' if it does not exist, so users can
request time off from their accumulated overtime (YTD) as paid leave.
"""
from alembic import op
import sqlalchemy as sa


revision = "136_seed_overtime_leave_type"
down_revision = "135_remind_to_log"
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if "leave_types" not in inspector.get_table_names():
        return
    # Insert Overtime leave type only if not present (by code)
    if bind.dialect.name == "sqlite":
        op.execute(
            sa.text("""
                INSERT INTO leave_types (name, code, is_paid, annual_allowance_hours, accrual_hours_per_month, enabled, created_at, updated_at)
                SELECT 'Overtime', 'overtime', 1, NULL, NULL, 1, datetime('now'), datetime('now')
                WHERE NOT EXISTS (SELECT 1 FROM leave_types WHERE code = 'overtime')
            """)
        )
    else:
        op.execute(
            sa.text("""
                INSERT INTO leave_types (name, code, is_paid, annual_allowance_hours, accrual_hours_per_month, enabled, created_at, updated_at)
                SELECT 'Overtime', 'overtime', true, NULL, NULL, true, now(), now()
                WHERE NOT EXISTS (SELECT 1 FROM leave_types WHERE code = 'overtime')
            """)
        )


def downgrade():
    # Remove the seeded leave type (may break if time-off requests reference it)
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if "leave_types" not in inspector.get_table_names():
        return
    op.execute(sa.text("DELETE FROM leave_types WHERE code = 'overtime'"))
