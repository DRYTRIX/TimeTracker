"""Add leitweg_id to clients for XRechnung BT-10.

Revision ID: 202_add_client_leitweg_id
Revises: 201_add_time_entries_custom_fields
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect

revision = "202_add_client_leitweg_id"
down_revision = "201_add_time_entries_custom_fields"
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    inspector = inspect(bind)
    cols = {c["name"] for c in inspector.get_columns("clients")}
    if "leitweg_id" not in cols:
        op.add_column("clients", sa.Column("leitweg_id", sa.String(length=100), nullable=True))


def downgrade():
    bind = op.get_bind()
    inspector = inspect(bind)
    cols = {c["name"] for c in inspector.get_columns("clients")}
    if "leitweg_id" in cols:
        op.drop_column("clients", "leitweg_id")
