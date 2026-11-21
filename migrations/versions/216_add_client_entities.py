"""Add client legal entities and the invoice "Bill to" link.

Revision ID: 216_add_client_entities
Revises: 215_add_billing_entities
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect

revision = "216_add_client_entities"
down_revision = "215_add_billing_entities"
branch_labels = None
depends_on = None


def _has_table(inspector, name):
    return name in inspector.get_table_names()


def _has_column(inspector, table_name, column_name):
    try:
        return column_name in {c["name"] for c in inspector.get_columns(table_name)}
    except Exception:
        return False


def upgrade():
    bind = op.get_bind()
    inspector = inspect(bind)

    if not _has_table(inspector, "client_entities"):
        op.create_table(
            "client_entities",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column(
                "client_id",
                sa.Integer(),
                sa.ForeignKey("clients.id", name="fk_client_entities_client_id", ondelete="CASCADE"),
                nullable=False,
            ),
            sa.Column("legal_name", sa.String(length=255), nullable=False),
            sa.Column("registration_number", sa.String(length=100), nullable=True),
            sa.Column("vat_number", sa.String(length=100), nullable=True),
            sa.Column("country", sa.String(length=2), nullable=True),
            sa.Column("address", sa.Text(), nullable=True),
            sa.Column("email", sa.String(length=200), nullable=True),
            sa.Column("status", sa.String(length=20), nullable=False, server_default="active"),
            sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
            sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        )
        op.create_index("ix_client_entities_client_id", "client_entities", ["client_id"])
        op.create_index("ix_client_entities_status", "client_entities", ["status"])

    inspector = inspect(bind)
    with op.batch_alter_table("invoices") as batch:
        if not _has_column(inspector, "invoices", "client_entity_id"):
            batch.add_column(sa.Column("client_entity_id", sa.Integer(), nullable=True))
            batch.create_foreign_key(
                "fk_invoices_client_entity_id", "client_entities", ["client_entity_id"], ["id"], ondelete="SET NULL"
            )
            batch.create_index("ix_invoices_client_entity_id", ["client_entity_id"])
        if not _has_column(inspector, "invoices", "buyer_snapshot"):
            batch.add_column(sa.Column("buyer_snapshot", sa.JSON(), nullable=True))


def downgrade():
    bind = op.get_bind()
    inspector = inspect(bind)

    with op.batch_alter_table("invoices") as batch:
        if _has_column(inspector, "invoices", "buyer_snapshot"):
            batch.drop_column("buyer_snapshot")
        if _has_column(inspector, "invoices", "client_entity_id"):
            batch.drop_index("ix_invoices_client_entity_id")
            batch.drop_constraint("fk_invoices_client_entity_id", type_="foreignkey")
            batch.drop_column("client_entity_id")

    inspector = inspect(bind)
    if _has_table(inspector, "client_entities"):
        op.drop_table("client_entities")
