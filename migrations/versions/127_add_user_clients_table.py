"""Add user_clients table for subcontractor scope

Revision ID: 127_add_user_clients
Revises: 126_add_overtime_include_weekends
Create Date: 2026-02-16

Allows assigning clients to users (e.g. subcontractors) so they only see those clients/projects.
"""
from alembic import op
import sqlalchemy as sa

revision = "127_add_user_clients"
down_revision = "126_add_overtime_include_weekends"
branch_labels = None
depends_on = None


def upgrade():
    from sqlalchemy import inspect

    bind = op.get_bind()
    inspector = inspect(bind)
    if "user_clients" in inspector.get_table_names():
        return

    op.create_table(
        "user_clients",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("client_id", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.ForeignKeyConstraint(["client_id"], ["clients.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "client_id", name="uq_user_client"),
    )
    op.create_index(op.f("ix_user_clients_client_id"), "user_clients", ["client_id"], unique=False)
    op.create_index(op.f("ix_user_clients_user_id"), "user_clients", ["user_id"], unique=False)


def downgrade():
    from sqlalchemy import inspect

    bind = op.get_bind()
    inspector = inspect(bind)
    if "user_clients" not in inspector.get_table_names():
        return
    op.drop_index(op.f("ix_user_clients_user_id"), table_name="user_clients")
    op.drop_index(op.f("ix_user_clients_client_id"), table_name="user_clients")
    op.drop_table("user_clients")
