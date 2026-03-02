"""Add variant column to donation_interactions for A/B test segmentation

Revision ID: 131_add_donation_variant
Revises: 130_add_peppol_transport_mode_and_native
Create Date: 2026-03-02

Enables segmenting support CTA experiments (e.g. control, key_first, cta_alt).
"""
from alembic import op
import sqlalchemy as sa


revision = "131_add_donation_variant"
down_revision = "130_add_peppol_transport_mode_and_native"
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if "donation_interactions" not in inspector.get_table_names():
        return
    cols = {c["name"] for c in inspector.get_columns("donation_interactions")}
    if "variant" in cols:
        return
    op.add_column(
        "donation_interactions",
        sa.Column("variant", sa.String(50), nullable=True),
    )


def downgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if "donation_interactions" not in inspector.get_table_names():
        return
    cols = {c["name"] for c in inspector.get_columns("donation_interactions")}
    if "variant" not in cols:
        return
    op.drop_column("donation_interactions", "variant")
