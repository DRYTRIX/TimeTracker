"""Merge migration heads 118_add_role_hidden_module_ids and 128_add_invoices_zugferd_pdf

Revision ID: 129_merge_118_128_heads
Revises: 118_add_role_hidden_module_ids, 128_add_invoices_zugferd_pdf
Create Date: 2026-02-16

Resolves multiple heads so 'alembic upgrade head' / 'flask db upgrade' can run.
"""
from alembic import op


revision = "129_merge_118_128_heads"
down_revision = ("118_add_role_hidden_module_ids", "128_add_invoices_zugferd_pdf")
branch_labels = None
depends_on = None


def upgrade():
    """No schema changes - merge only."""
    pass


def downgrade():
    """No schema changes - merge only."""
    pass
