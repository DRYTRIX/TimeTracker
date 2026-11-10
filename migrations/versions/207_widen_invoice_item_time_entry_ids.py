"""Widen invoice_items.time_entry_ids so a grouped line can hold many entries.

Revision ID: 207_invoice_item_time_entry_ids
Revises: 206_add_bank_transactions
"""

import sqlalchemy as sa
from alembic import op

revision = "207_invoice_item_time_entry_ids"
down_revision = "206_add_bank_transactions"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("invoice_items") as batch_op:
        batch_op.alter_column("time_entry_ids", existing_type=sa.String(length=500), type_=sa.Text())


def downgrade():
    with op.batch_alter_table("invoice_items") as batch_op:
        batch_op.alter_column("time_entry_ids", existing_type=sa.Text(), type_=sa.String(length=500))
