"""reporting and invoicing extensions

Revision ID: 017
Revises: 016
Create Date: 2025-10-06 00:00:00
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '017'
down_revision = '016'
branch_labels = None
depends_on = None


def _has_table(inspector, name: str) -> bool:
    try:
        return name in inspector.get_table_names()
    except Exception:
        return False


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    # currencies
    if not _has_table(inspector, 'currencies'):
        op.create_table(
            'currencies',
            sa.Column('code', sa.String(length=3), primary_key=True),
            sa.Column('name', sa.String(length=64), nullable=False),
            sa.Column('symbol', sa.String(length=8), nullable=True),
            sa.Column('decimal_places', sa.Integer(), nullable=False, server_default='2'),
            sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.text('true')),
            sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
            sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        )

    if not _has_table(inspector, 'exchange_rates'):
        op.create_table(
            'exchange_rates',
            sa.Column('id', sa.Integer(), primary_key=True),
            sa.Column('base_code', sa.String(length=3), sa.ForeignKey('currencies.code'), nullable=False, index=True),
            sa.Column('quote_code', sa.String(length=3), sa.ForeignKey('currencies.code'), nullable=False, index=True),
            sa.Column('rate', sa.Numeric(18, 8), nullable=False),
            sa.Column('date', sa.Date(), nullable=False),
            sa.Column('source', sa.String(length=50), nullable=True),
            sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
            sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
            sa.UniqueConstraint('base_code', 'quote_code', 'date', name='uq_exchange_rate_day'),
        )

    # tax rules
    if not _has_table(inspector, 'tax_rules'):
        op.create_table(
            'tax_rules',
            sa.Column('id', sa.Integer(), primary_key=True),
            sa.Column('name', sa.String(length=100), nullable=False),
            sa.Column('country', sa.String(length=2), nullable=True),
            sa.Column('region', sa.String(length=50), nullable=True),
            sa.Column('client_id', sa.Integer(), sa.ForeignKey('clients.id'), nullable=True),
            sa.Column('project_id', sa.Integer(), sa.ForeignKey('projects.id'), nullable=True),
            sa.Column('tax_code', sa.String(length=50), nullable=True),
            sa.Column('rate_percent', sa.Numeric(7, 4), nullable=False, server_default='0'),
            sa.Column('compound', sa.Boolean(), nullable=False, server_default=sa.text('false')),
            sa.Column('inclusive', sa.Boolean(), nullable=False, server_default=sa.text('false')),
            sa.Column('start_date', sa.Date(), nullable=True),
            sa.Column('end_date', sa.Date(), nullable=True),
            sa.Column('active', sa.Boolean(), nullable=False, server_default=sa.text('true')),
            sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
            sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        )

    # invoice templates
    if not _has_table(inspector, 'invoice_templates'):
        op.create_table(
            'invoice_templates',
            sa.Column('id', sa.Integer(), primary_key=True),
            sa.Column('name', sa.String(length=100), nullable=False, unique=True),
            sa.Column('description', sa.String(length=255), nullable=True),
            sa.Column('html', sa.Text(), nullable=True),
            sa.Column('css', sa.Text(), nullable=True),
            sa.Column('is_default', sa.Boolean(), nullable=False, server_default=sa.text('false')),
            sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
            sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        )

    # payments, credit notes, reminders
    if not _has_table(inspector, 'payments'):
        op.create_table(
            'payments',
            sa.Column('id', sa.Integer(), primary_key=True),
            sa.Column('invoice_id', sa.Integer(), sa.ForeignKey('invoices.id', ondelete='CASCADE'), nullable=False),
            sa.Column('amount', sa.Numeric(10, 2), nullable=False),
            sa.Column('currency', sa.String(length=3), nullable=True),
            sa.Column('payment_date', sa.Date(), nullable=False, server_default=sa.text('CURRENT_DATE')),
            sa.Column('method', sa.String(length=50), nullable=True),
            sa.Column('reference', sa.String(length=100), nullable=True),
            sa.Column('notes', sa.Text(), nullable=True),
            sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
            sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        )

    if not _has_table(inspector, 'credit_notes'):
        op.create_table(
            'credit_notes',
            sa.Column('id', sa.Integer(), primary_key=True),
            sa.Column('invoice_id', sa.Integer(), sa.ForeignKey('invoices.id', ondelete='CASCADE'), nullable=False),
            sa.Column('credit_number', sa.String(length=50), nullable=False, unique=True),
            sa.Column('amount', sa.Numeric(10, 2), nullable=False),
            sa.Column('reason', sa.Text(), nullable=True),
            sa.Column('created_by', sa.Integer(), sa.ForeignKey('users.id'), nullable=False),
            sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
            sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        )

    if not _has_table(inspector, 'invoice_reminder_schedules'):
        op.create_table(
            'invoice_reminder_schedules',
            sa.Column('id', sa.Integer(), primary_key=True),
            sa.Column('invoice_id', sa.Integer(), sa.ForeignKey('invoices.id', ondelete='CASCADE'), nullable=False),
            sa.Column('days_offset', sa.Integer(), nullable=False),
            sa.Column('recipients', sa.Text(), nullable=True),
            sa.Column('template_name', sa.String(length=100), nullable=True),
            sa.Column('active', sa.Boolean(), nullable=False, server_default=sa.text('true')),
            sa.Column('last_sent_at', sa.DateTime(), nullable=True),
            sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
            sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        )

    # reporting saved views and schedules
    if not _has_table(inspector, 'saved_report_views'):
        op.create_table(
            'saved_report_views',
            sa.Column('id', sa.Integer(), primary_key=True),
            sa.Column('name', sa.String(length=120), nullable=False),
            sa.Column('owner_id', sa.Integer(), sa.ForeignKey('users.id'), nullable=False),
            sa.Column('scope', sa.String(length=20), nullable=False, server_default='private'),
            sa.Column('config_json', sa.Text(), nullable=False),
            sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
            sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        )

    if not _has_table(inspector, 'report_email_schedules'):
        op.create_table(
            'report_email_schedules',
            sa.Column('id', sa.Integer(), primary_key=True),
            sa.Column('saved_view_id', sa.Integer(), sa.ForeignKey('saved_report_views.id', ondelete='CASCADE'), nullable=False),
            sa.Column('recipients', sa.Text(), nullable=False),
            sa.Column('cadence', sa.String(length=20), nullable=False),
            sa.Column('cron', sa.String(length=120), nullable=True),
            sa.Column('timezone', sa.String(length=50), nullable=True),
            sa.Column('next_run_at', sa.DateTime(), nullable=True),
            sa.Column('last_run_at', sa.DateTime(), nullable=True),
            sa.Column('active', sa.Boolean(), nullable=False, server_default=sa.text('true')),
            sa.Column('created_by', sa.Integer(), sa.ForeignKey('users.id'), nullable=False),
            sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
            sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        )

    # alter invoices: currency_code, template_id
    if 'invoices' in inspector.get_table_names():
        columns = {c['name'] for c in inspector.get_columns('invoices')}
        if 'currency_code' not in columns:
            op.add_column('invoices', sa.Column('currency_code', sa.String(length=3), nullable=False, server_default='EUR'))
            # Only drop default on PostgreSQL (SQLite doesn't support ALTER COLUMN DROP DEFAULT)
            if bind.dialect.name == 'postgresql':
                # Use batch mode for portability audit + compatibility.
                with op.batch_alter_table('invoices') as batch_op:
                    batch_op.alter_column('currency_code', server_default=None)
        if 'template_id' not in columns:
            op.add_column('invoices', sa.Column('template_id', sa.Integer(), nullable=True))
            try:
                op.create_index('ix_invoices_template_id', 'invoices', ['template_id'])
            except Exception:
                pass


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    # remove added invoice columns
    if 'invoices' in inspector.get_table_names():
        columns = {c['name'] for c in inspector.get_columns('invoices')}
        if 'template_id' in columns:
            try:
                op.drop_index('ix_invoices_template_id', table_name='invoices')
            except Exception:
                pass
            try:
                op.drop_column('invoices', 'template_id')
            except Exception:
                pass
        if 'currency_code' in columns:
            try:
                op.drop_column('invoices', 'currency_code')
            except Exception:
                pass

    # drop tables (reverse order due FK dependencies)
    for table in [
        'report_email_schedules',
        'saved_report_views',
        'invoice_reminder_schedules',
        'credit_notes',
        'payments',
        'invoice_templates',
        'tax_rules',
        'exchange_rates',
        'currencies',
    ]:
        if _has_table(inspector, table):
            try:
                op.drop_table(table)
            except Exception:
                pass


