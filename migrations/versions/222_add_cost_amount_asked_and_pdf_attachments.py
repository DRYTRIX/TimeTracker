"""Recurring costs that ask for their amount, and receipts and bills attached to the invoice PDF.

- ``recurring_project_costs.ask_amount``: the generator makes no cost; each draft of a period the
  recurring cost falls in asks for the amount.
- ``recurring_project_costs.start_date``: the first day it was due, from which such a recurring cost
  counts its days. Filled for existing ones: the date of its first cost, else its next run date.
- ``invoices.attach_receipts`` and ``invoices.attach_bills``: the invoice PDF is followed by the
  expenses' receipts and the project costs' supplier bills.

Revision ID: 222_add_cost_amount_asked_and_pdf_attachments
Revises: 221_add_project_cost_invoice_lines
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect

revision = "222_add_cost_amount_asked_and_pdf_attachments"
down_revision = "221_add_project_cost_invoice_lines"
branch_labels = None
depends_on = None


def _columns(inspector, table_name):
    try:
        return {c["name"] for c in inspector.get_columns(table_name)}
    except Exception:
        return set()


def _new_columns():
    return [
        ("recurring_project_costs", sa.Column("ask_amount", sa.Boolean(), nullable=False, server_default=sa.false())),
        ("recurring_project_costs", sa.Column("start_date", sa.Date(), nullable=True)),
        ("invoices", sa.Column("attach_receipts", sa.Boolean(), nullable=False, server_default=sa.false())),
        ("invoices", sa.Column("attach_bills", sa.Boolean(), nullable=False, server_default=sa.false())),
    ]


def upgrade():
    # Plain ADD COLUMN (no batch copy): SQLite keeps the tables, so foreign keys pointing at them stay valid
    inspector = inspect(op.get_bind())
    for table_name, column in _new_columns():
        existing = _columns(inspector, table_name)
        if existing and column.name not in existing:
            op.add_column(table_name, column)
    _fill_start_dates(op.get_bind(), inspect(op.get_bind()))


def _fill_start_dates(bind, inspector):
    """Existing recurring costs start on the date of their first cost, else on their next run date."""
    if "start_date" not in _columns(inspector, "recurring_project_costs"):
        return
    if "recurring_cost_id" in _columns(inspector, "project_costs"):
        bind.execute(
            sa.text(
                "UPDATE recurring_project_costs SET start_date = ("
                "SELECT MIN(pc.cost_date) FROM project_costs pc WHERE pc.recurring_cost_id = recurring_project_costs.id"
                ") WHERE start_date IS NULL"
            )
        )
    bind.execute(sa.text("UPDATE recurring_project_costs SET start_date = next_run_date WHERE start_date IS NULL"))


def downgrade():
    inspector = inspect(op.get_bind())
    for table_name, column in reversed(_new_columns()):
        if column.name in _columns(inspector, table_name):
            op.drop_column(table_name, column.name)
