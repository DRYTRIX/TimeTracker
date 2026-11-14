"""Add reminder_policies, reminder_policy_levels tables; FK on clients/invoices;
late_fee_amount on invoices.

Revision ID: 211_invoice_reminder_policies
Revises: 210_invoice_line_tax_discounts
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect

revision = "211_invoice_reminder_policies"
down_revision = "210_invoice_line_tax_discounts"
branch_labels = None
depends_on = None


def _has_table(inspector, name: str) -> bool:
    try:
        return name in inspector.get_table_names()
    except Exception:
        return False


def _has_column(inspector, table_name: str, column_name: str) -> bool:
    try:
        return column_name in {c["name"] for c in inspector.get_columns(table_name)}
    except Exception:
        return False


def _add_column_if_missing(inspector, table_name: str, column: sa.Column) -> None:
    if not _has_column(inspector, table_name, column.name):
        op.add_column(table_name, column)


def upgrade():
    bind = op.get_bind()
    inspector = inspect(bind)

    # ── reminder_policies ───────────────────────────────────────────────────
    if not _has_table(inspector, "reminder_policies"):
        op.create_table(
            "reminder_policies",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("name", sa.String(length=100), nullable=False),
            sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.true()),
            sa.Column("is_default", sa.Boolean(), nullable=False, server_default=sa.false()),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("updated_at", sa.DateTime(), nullable=False),
            sa.PrimaryKeyConstraint("id"),
        )

    # ── reminder_policy_levels ───────────────────────────────────────────────
    if not _has_table(inspector, "reminder_policy_levels"):
        op.create_table(
            "reminder_policy_levels",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("policy_id", sa.Integer(), nullable=False),
            sa.Column("days_offset", sa.Integer(), nullable=False),
            sa.Column("template_name", sa.String(length=100), nullable=True),
            sa.Column(
                "late_fee_type",
                sa.String(length=20),
                nullable=True,
            ),  # 'fixed' | 'percent_annual' | null
            sa.Column("late_fee_value", sa.Numeric(10, 2), nullable=True),
            sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.true()),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("updated_at", sa.DateTime(), nullable=False),
            sa.ForeignKeyConstraint(["policy_id"], ["reminder_policies.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("id"),
        )

    # ── clients.reminder_policy_id (nullable FK) ─────────────────────────────
    _add_column_if_missing(
        inspector,
        "clients",
        sa.Column("reminder_policy_id", sa.Integer(), sa.ForeignKey("reminder_policies.id"), nullable=True),
    )

    # ── invoices.reminder_policy_id (nullable FK) ────────────────────────────
    _add_column_if_missing(
        inspector,
        "invoices",
        sa.Column("reminder_policy_id", sa.Integer(), sa.ForeignKey("reminder_policies.id"), nullable=True),
    )

    # ── invoices.late_fee_amount ──────────────────────────────────────────────
    _add_column_if_missing(
        inspector,
        "invoices",
        sa.Column("late_fee_amount", sa.Numeric(10, 2), nullable=False, server_default="0"),
    )


def downgrade():
    bind = op.get_bind()
    inspector = inspect(bind)

    if _has_column(inspector, "invoices", "late_fee_amount"):
        op.drop_column("invoices", "late_fee_amount")

    if _has_column(inspector, "invoices", "reminder_policy_id"):
        op.drop_column("invoices", "reminder_policy_id")

    if _has_column(inspector, "clients", "reminder_policy_id"):
        op.drop_column("clients", "reminder_policy_id")

    if _has_table(inspector, "reminder_policy_levels"):
        op.drop_table("reminder_policy_levels")

    if _has_table(inspector, "reminder_policies"):
        op.drop_table("reminder_policies")
