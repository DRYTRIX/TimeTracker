"""Add digital signature fields to quotes.

Revision ID: 181_add_quote_signature
Revises: 180_add_milestones
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect

revision = "181_add_quote_signature"
down_revision = "180_add_milestones"
branch_labels = None
depends_on = None


def _has_column(inspector, table_name, column_name):
    try:
        return column_name in {c["name"] for c in inspector.get_columns(table_name)}
    except Exception:
        return False


def upgrade():
    bind = op.get_bind()
    inspector = inspect(bind)
    if "quotes" not in inspector.get_table_names():
        return
    columns = [
        ("signature_data", sa.Text(), True),
        ("signed_at", sa.DateTime(), True),
        ("signed_by_name", sa.String(200), True),
        ("signed_by_email", sa.String(200), True),
        ("signed_ip", sa.String(50), True),
    ]
    for name, col_type, nullable in columns:
        if not _has_column(inspector, "quotes", name):
            op.add_column("quotes", sa.Column(name, col_type, nullable=nullable))
            inspector = inspect(bind)


def downgrade():
    bind = op.get_bind()
    inspector = inspect(bind)
    for name in ("signed_ip", "signed_by_email", "signed_by_name", "signed_at", "signature_data"):
        if _has_column(inspector, "quotes", name):
            op.drop_column("quotes", name)
            inspector = inspect(bind)
