"""add invoice_pdf_design_json to settings

Revision ID: 036_add_pdf_design_json
Revises: 035_enhance_payments
Create Date: 2025-10-29 12:00:00
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '036_add_pdf_design_json'
down_revision = '035_enhance_payments'
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if 'settings' not in inspector.get_table_names():
        return
    columns = {c['name'] for c in inspector.get_columns('settings')}
    if 'invoice_pdf_design_json' not in columns:
        op.add_column('settings', sa.Column('invoice_pdf_design_json', sa.Text(), nullable=True))


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if 'settings' not in inspector.get_table_names():
        return
    columns = {c['name'] for c in inspector.get_columns('settings')}
    if 'invoice_pdf_design_json' in columns:
        try:
            op.drop_column('settings', 'invoice_pdf_design_json')
        except Exception:
            pass


