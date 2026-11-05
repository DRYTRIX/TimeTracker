"""add pdf template fields to settings

Revision ID: 012
Revises: 011
Create Date: 2025-09-12 00:00:00
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "012"
down_revision = "011"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if "settings" not in inspector.get_table_names():
        return
    columns = {c["name"] for c in inspector.get_columns("settings")}
    if "invoice_pdf_template_html" not in columns:
        op.add_column("settings", sa.Column("invoice_pdf_template_html", sa.Text(), nullable=True))
    if "invoice_pdf_template_css" not in columns:
        op.add_column("settings", sa.Column("invoice_pdf_template_css", sa.Text(), nullable=True))


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if "settings" not in inspector.get_table_names():
        return
    columns = {c["name"] for c in inspector.get_columns("settings")}
    if "invoice_pdf_template_css" in columns:
        try:
            op.drop_column("settings", "invoice_pdf_template_css")
        except Exception:
            pass
    if "invoice_pdf_template_html" in columns:
        try:
            op.drop_column("settings", "invoice_pdf_template_html")
        except Exception:
            pass
