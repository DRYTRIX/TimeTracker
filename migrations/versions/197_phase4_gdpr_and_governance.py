"""Phase 4: GDPR user anonymization, custom field entity types, multi-level timesheet approval.

Revision ID: 197_phase4_gdpr_and_governance
Revises: 196_add_einvoice_address_and_vat_category
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect

revision = "197_phase4_gdpr_and_governance"
down_revision = "196_add_einvoice_address_and_vat_category"
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

    if not _has_column(inspector, "users", "anonymized_at"):
        op.add_column("users", sa.Column("anonymized_at", sa.DateTime(), nullable=True))

    if not _has_column(inspector, "custom_field_definitions", "entity_type"):
        op.add_column(
            "custom_field_definitions",
            sa.Column("entity_type", sa.String(length=30), nullable=False, server_default="client"),
        )

    if not _has_column(inspector, "timesheet_periods", "secondary_approved_by"):
        op.add_column("timesheet_periods", sa.Column("secondary_approved_by", sa.Integer(), nullable=True))
        op.create_foreign_key(
            "fk_timesheet_periods_secondary_approved_by_users",
            "timesheet_periods",
            "users",
            ["secondary_approved_by"],
            ["id"],
            ondelete="SET NULL",
        )
    if not _has_column(inspector, "timesheet_periods", "secondary_approved_at"):
        op.add_column("timesheet_periods", sa.Column("secondary_approved_at", sa.DateTime(), nullable=True))


def downgrade():
    bind = op.get_bind()
    inspector = inspect(bind)

    if _has_column(inspector, "timesheet_periods", "secondary_approved_at"):
        op.drop_column("timesheet_periods", "secondary_approved_at")
    if _has_column(inspector, "timesheet_periods", "secondary_approved_by"):
        try:
            op.drop_constraint(
                "fk_timesheet_periods_secondary_approved_by_users", "timesheet_periods", type_="foreignkey"
            )
        except Exception:
            pass
        op.drop_column("timesheet_periods", "secondary_approved_by")
    if _has_column(inspector, "custom_field_definitions", "entity_type"):
        op.drop_column("custom_field_definitions", "entity_type")
    if _has_column(inspector, "users", "anonymized_at"):
        op.drop_column("users", "anonymized_at")
