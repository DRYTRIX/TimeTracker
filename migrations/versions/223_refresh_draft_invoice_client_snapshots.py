"""Refresh draft invoice client_name/email/address from the linked Client.

Issued and sent invoices keep their document snapshot. Drafts re-read the live
client so renames (e.g. after a Harvest import cleanup) show correctly on save
and when the invoice is issued.

Revision ID: 223_refresh_draft_invoice_client_snapshots
Revises: 222_add_cost_amount_asked_and_pdf_attachments
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect

revision = "223_refresh_draft_invoice_client_snapshots"
down_revision = "222_add_cost_amount_asked_and_pdf_attachments"
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    inspector = inspect(bind)
    tables = set(inspector.get_table_names())
    if "invoices" not in tables or "clients" not in tables:
        return

    rows = bind.execute(
        sa.text(
            """
            SELECT i.id, c.name, c.email, c.address
            FROM invoices AS i
            JOIN clients AS c ON c.id = i.client_id
            WHERE i.status = 'draft'
            """
        )
    ).fetchall()

    update = sa.text(
        """
        UPDATE invoices
        SET client_name = :name,
            client_email = :email,
            client_address = :address
        WHERE id = :id
        """
    )
    for row in rows:
        bind.execute(
            update,
            {"id": row[0], "name": row[1], "email": row[2], "address": row[3]},
        )


def downgrade():
    # Snapshot refresh is not reversible; issued documents were never changed.
    pass
