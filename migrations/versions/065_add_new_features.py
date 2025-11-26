"""Add new features: project templates, invoice approval, payment gateways, calendar integration

Revision ID: 065
Revises: 064
Create Date: 2025-01-27

This migration adds:
- Project templates for reusable project configurations
- Invoice approval workflow
- Payment gateway integration (Stripe, PayPal, etc.)
- Calendar integration (Google Calendar, Outlook)
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '065'
down_revision = '064'
branch_labels = None
depends_on = None


def upgrade():
    """Add new feature tables"""
    
    # Project Templates
    op.create_table('project_templates',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(200), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('config', sa.JSON(), nullable=False, server_default='{}'),
        sa.Column('tasks', sa.JSON(), nullable=True, server_default='[]'),
        sa.Column('category', sa.String(100), nullable=True),
        sa.Column('tags', sa.JSON(), nullable=True, server_default='[]'),
        sa.Column('is_public', sa.Boolean(), nullable=False, server_default='0'),
        sa.Column('created_by', sa.Integer(), nullable=False),
        sa.Column('usage_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('last_used_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['created_by'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_project_templates_name'), 'project_templates', ['name'], unique=False)
    op.create_index(op.f('ix_project_templates_category'), 'project_templates', ['category'], unique=False)
    op.create_index(op.f('ix_project_templates_is_public'), 'project_templates', ['is_public'], unique=False)
    op.create_index(op.f('ix_project_templates_created_by'), 'project_templates', ['created_by'], unique=False)
    
    # Invoice Approval Workflow
    op.create_table('invoice_approvals',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('invoice_id', sa.Integer(), nullable=False),
        sa.Column('status', sa.String(20), nullable=False, server_default='pending'),
        sa.Column('stages', sa.JSON(), nullable=False, server_default='[]'),
        sa.Column('current_stage', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('total_stages', sa.Integer(), nullable=False, server_default='1'),
        sa.Column('requested_by', sa.Integer(), nullable=False),
        sa.Column('requested_at', sa.DateTime(), nullable=False),
        sa.Column('approved_by', sa.Integer(), nullable=True),
        sa.Column('approved_at', sa.DateTime(), nullable=True),
        sa.Column('rejected_by', sa.Integer(), nullable=True),
        sa.Column('rejected_at', sa.DateTime(), nullable=True),
        sa.Column('rejection_reason', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['invoice_id'], ['invoices.id'], ),
        sa.ForeignKeyConstraint(['requested_by'], ['users.id'], ),
        sa.ForeignKeyConstraint(['approved_by'], ['users.id'], ),
        sa.ForeignKeyConstraint(['rejected_by'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_invoice_approvals_invoice_id'), 'invoice_approvals', ['invoice_id'], unique=False)
    op.create_index(op.f('ix_invoice_approvals_status'), 'invoice_approvals', ['status'], unique=False)
    op.create_index(op.f('ix_invoice_approvals_requested_by'), 'invoice_approvals', ['requested_by'], unique=False)
    op.create_index(op.f('ix_invoice_approvals_approved_by'), 'invoice_approvals', ['approved_by'], unique=False)
    
    # Payment Gateways
    op.create_table('payment_gateways',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(50), nullable=False),
        sa.Column('provider', sa.String(50), nullable=False),
        sa.Column('config', sa.Text(), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='1'),
        sa.Column('is_test_mode', sa.Boolean(), nullable=False, server_default='0'),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('name')
    )
    op.create_index(op.f('ix_payment_gateways_name'), 'payment_gateways', ['name'], unique=True)
    op.create_index(op.f('ix_payment_gateways_is_active'), 'payment_gateways', ['is_active'], unique=False)
    
    # Payment Transactions
    op.create_table('payment_transactions',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('invoice_id', sa.Integer(), nullable=False),
        sa.Column('gateway_id', sa.Integer(), nullable=False),
        sa.Column('transaction_id', sa.String(200), nullable=False),
        sa.Column('amount', sa.Numeric(10, 2), nullable=False),
        sa.Column('currency', sa.String(3), nullable=False, server_default='EUR'),
        sa.Column('gateway_fee', sa.Numeric(10, 2), nullable=True),
        sa.Column('net_amount', sa.Numeric(10, 2), nullable=True),
        sa.Column('status', sa.String(20), nullable=False),
        sa.Column('payment_method', sa.String(50), nullable=True),
        sa.Column('gateway_response', sa.JSON(), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('error_code', sa.String(50), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.Column('processed_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['invoice_id'], ['invoices.id'], ),
        sa.ForeignKeyConstraint(['gateway_id'], ['payment_gateways.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('transaction_id')
    )
    op.create_index(op.f('ix_payment_transactions_invoice_id'), 'payment_transactions', ['invoice_id'], unique=False)
    op.create_index(op.f('ix_payment_transactions_gateway_id'), 'payment_transactions', ['gateway_id'], unique=False)
    op.create_index(op.f('ix_payment_transactions_transaction_id'), 'payment_transactions', ['transaction_id'], unique=True)
    op.create_index(op.f('ix_payment_transactions_status'), 'payment_transactions', ['status'], unique=False)
    
    # Calendar Integrations
    op.create_table('calendar_integrations',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('provider', sa.String(50), nullable=False),
        sa.Column('access_token', sa.Text(), nullable=False),
        sa.Column('refresh_token', sa.Text(), nullable=True),
        sa.Column('token_expires_at', sa.DateTime(), nullable=True),
        sa.Column('calendar_id', sa.String(200), nullable=True),
        sa.Column('calendar_name', sa.String(200), nullable=True),
        sa.Column('sync_settings', sa.JSON(), nullable=False, server_default='{}'),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='1'),
        sa.Column('last_sync_at', sa.DateTime(), nullable=True),
        sa.Column('last_sync_status', sa.String(20), nullable=True),
        sa.Column('last_sync_error', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_calendar_integrations_user_id'), 'calendar_integrations', ['user_id'], unique=False)
    op.create_index(op.f('ix_calendar_integrations_provider'), 'calendar_integrations', ['provider'], unique=False)
    op.create_index(op.f('ix_calendar_integrations_is_active'), 'calendar_integrations', ['is_active'], unique=False)
    
    # Calendar Sync Events
    op.create_table('calendar_sync_events',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('integration_id', sa.Integer(), nullable=False),
        sa.Column('event_type', sa.String(50), nullable=False),
        sa.Column('time_entry_id', sa.Integer(), nullable=True),
        sa.Column('calendar_event_id', sa.String(200), nullable=True),
        sa.Column('direction', sa.String(20), nullable=False),
        sa.Column('status', sa.String(20), nullable=False),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('synced_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['integration_id'], ['calendar_integrations.id'], ),
        sa.ForeignKeyConstraint(['time_entry_id'], ['time_entries.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_calendar_sync_events_integration_id'), 'calendar_sync_events', ['integration_id'], unique=False)
    op.create_index(op.f('ix_calendar_sync_events_event_type'), 'calendar_sync_events', ['event_type'], unique=False)
    op.create_index(op.f('ix_calendar_sync_events_time_entry_id'), 'calendar_sync_events', ['time_entry_id'], unique=False)
    op.create_index(op.f('ix_calendar_sync_events_calendar_event_id'), 'calendar_sync_events', ['calendar_event_id'], unique=False)
    op.create_index(op.f('ix_calendar_sync_events_status'), 'calendar_sync_events', ['status'], unique=False)


def downgrade():
    """Remove new feature tables"""
    op.drop_table('calendar_sync_events')
    op.drop_table('calendar_integrations')
    op.drop_table('payment_transactions')
    op.drop_table('payment_gateways')
    op.drop_table('invoice_approvals')
    op.drop_table('project_templates')

