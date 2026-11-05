"""add user preferred_language column

Revision ID: 011
Revises: 010
Create Date: 2025-09-11 00:00:00
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "011"
down_revision = "010"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if "users" not in inspector.get_table_names():
        return
    # Check existing columns defensively
    columns = {c["name"] for c in inspector.get_columns("users")}
    if "preferred_language" not in columns:
        op.add_column("users", sa.Column("preferred_language", sa.String(length=8), nullable=True))


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if "users" not in inspector.get_table_names():
        return
    columns = {c["name"] for c in inspector.get_columns("users")}
    if "preferred_language" in columns:
        try:
            op.drop_column("users", "preferred_language")
        except Exception:
            # Some backends might fail if column involved in indexes; ignore for safety
            pass
