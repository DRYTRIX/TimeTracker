"""Add mail_test_recipient to settings

Revision ID: 142_add_mail_test_recipient
Revises: 141_add_invoice_number_pattern
Create Date: 2026-03-27
"""

from alembic import op
import sqlalchemy as sa


revision = "142_add_mail_test_recipient"
down_revision = "141_add_invoice_number_pattern"
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    columns = {col["name"] for col in inspector.get_columns("settings")} if "settings" in inspector.get_table_names() else set()
    if "mail_test_recipient" not in columns:
        op.add_column(
            "settings",
            sa.Column("mail_test_recipient", sa.String(length=255), nullable=True),
        )


def downgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    columns = {col["name"] for col in inspector.get_columns("settings")} if "settings" in inspector.get_table_names() else set()
    if "mail_test_recipient" in columns:
        op.drop_column("settings", "mail_test_recipient")
