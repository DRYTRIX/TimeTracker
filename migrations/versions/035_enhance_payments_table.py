"""enhance payments table with tracking features

Revision ID: 035_enhance_payments
Revises: 034_add_calendar_events
Create Date: 2025-10-27 00:00:00
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '035_enhance_payments'
down_revision = '034_add_calendar_events'
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    
    # Create payments table if it doesn't exist
    if 'payments' not in inspector.get_table_names():
        op.create_table(
            'payments',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('invoice_id', sa.Integer(), nullable=False),
            sa.Column('amount', sa.Numeric(10, 2), nullable=False),
            sa.Column('currency', sa.String(3), nullable=True),
            sa.Column('payment_date', sa.Date(), nullable=False),
            sa.Column('method', sa.String(50), nullable=True),
            sa.Column('reference', sa.String(100), nullable=True),
            sa.Column('notes', sa.Text(), nullable=True),
            sa.Column('status', sa.String(20), nullable=False, server_default='completed'),
            sa.Column('received_by', sa.Integer(), nullable=True),
            sa.Column('gateway_transaction_id', sa.String(255), nullable=True),
            sa.Column('gateway_fee', sa.Numeric(10, 2), nullable=True),
            sa.Column('net_amount', sa.Numeric(10, 2), nullable=True),
            sa.Column('created_at', sa.DateTime(), nullable=False),
            sa.Column('updated_at', sa.DateTime(), nullable=False),
            sa.PrimaryKeyConstraint('id'),
            sa.ForeignKeyConstraint(['invoice_id'], ['invoices.id'], ondelete='CASCADE'),
            sa.ForeignKeyConstraint(['received_by'], ['users.id'], ondelete='SET NULL')
        )
        
        # Create indexes
        op.create_index('ix_payments_invoice_id', 'payments', ['invoice_id'])
        op.create_index('ix_payments_payment_date', 'payments', ['payment_date'])
        op.create_index('ix_payments_status', 'payments', ['status'])
        op.create_index('ix_payments_received_by', 'payments', ['received_by'])
    else:
        # Table exists, add new columns if they don't exist
        existing_columns = [col['name'] for col in inspector.get_columns('payments')]
        
        if 'status' not in existing_columns:
            op.add_column('payments', sa.Column('status', sa.String(20), nullable=False, server_default='completed'))
        
        if 'received_by' not in existing_columns:
            op.add_column('payments', sa.Column('received_by', sa.Integer(), nullable=True))
            try:
                op.create_foreign_key('fk_payments_received_by', 'payments', 'users', ['received_by'], ['id'], ondelete='SET NULL')
            except:
                pass
        
        if 'gateway_transaction_id' not in existing_columns:
            op.add_column('payments', sa.Column('gateway_transaction_id', sa.String(255), nullable=True))
        
        if 'gateway_fee' not in existing_columns:
            op.add_column('payments', sa.Column('gateway_fee', sa.Numeric(10, 2), nullable=True))
        
        if 'net_amount' not in existing_columns:
            op.add_column('payments', sa.Column('net_amount', sa.Numeric(10, 2), nullable=True))
        
        # Create indexes if they don't exist
        try:
            op.create_index('ix_payments_status', 'payments', ['status'])
        except:
            pass
        
        try:
            op.create_index('ix_payments_received_by', 'payments', ['received_by'])
        except:
            pass
        
        try:
            op.create_index('ix_payments_payment_date', 'payments', ['payment_date'])
        except:
            pass


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    
    if 'payments' in inspector.get_table_names():
        existing_columns = [col['name'] for col in inspector.get_columns('payments')]
        
        # Drop indexes
        try:
            op.drop_index('ix_payments_received_by', table_name='payments')
        except:
            pass
        
        try:
            op.drop_index('ix_payments_status', table_name='payments')
        except:
            pass
        
        # Drop new columns if they exist
        columns_to_drop = ['net_amount', 'gateway_fee', 'gateway_transaction_id', 'received_by', 'status']
        
        for column in columns_to_drop:
            if column in existing_columns:
                try:
                    op.drop_column('payments', column)
                except Exception as e:
                    print(f"Warning: Could not drop column {column}: {e}")
                    pass

