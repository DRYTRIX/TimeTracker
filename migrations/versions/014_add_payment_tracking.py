"""add payment status tracking to invoices

Revision ID: 014
Revises: 013
Create Date: 2025-09-19 00:00:00
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '014'
down_revision = '013'
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    
    # Check if invoices table exists
    if 'invoices' in inspector.get_table_names():
        existing_columns = [col['name'] for col in inspector.get_columns('invoices')]
        
        # Add payment tracking columns to invoices table if they don't exist
        if 'payment_date' not in existing_columns:
            op.add_column('invoices', sa.Column('payment_date', sa.Date(), nullable=True))
        
        if 'payment_method' not in existing_columns:
            op.add_column('invoices', sa.Column('payment_method', sa.String(50), nullable=True))
        
        if 'payment_reference' not in existing_columns:
            op.add_column('invoices', sa.Column('payment_reference', sa.String(100), nullable=True))
        
        if 'payment_notes' not in existing_columns:
            op.add_column('invoices', sa.Column('payment_notes', sa.Text(), nullable=True))
        
        if 'amount_paid' not in existing_columns:
            # Add the column as nullable first
            op.add_column('invoices', sa.Column('amount_paid', sa.Numeric(10, 2), nullable=True))
            
            # Update existing records to have 0 as default amount_paid
            bind = op.get_bind()
            bind.execute(sa.text("UPDATE invoices SET amount_paid = 0 WHERE amount_paid IS NULL"))
        
        if 'payment_status' not in existing_columns:
            # Check if we're using SQLite or PostgreSQL
            bind = op.get_bind()
            dialect_name = bind.dialect.name
            
            if dialect_name == 'sqlite':
                # SQLite: Add column with default value directly (NOT NULL with default works)
                op.add_column('invoices', sa.Column('payment_status', sa.String(20), nullable=False, server_default='unpaid'))
                
                # Update existing records based on their current status
                bind.execute(sa.text("""
                    UPDATE invoices SET payment_status = CASE 
                        WHEN status = 'paid' THEN 'fully_paid'
                        ELSE 'unpaid'
                    END
                """))
                
                # For invoices marked as 'paid', also set amount_paid to total_amount
                bind.execute(sa.text("""
                    UPDATE invoices SET amount_paid = total_amount, payment_date = DATE('now')
                    WHERE status = 'paid' AND amount_paid = 0
                """))
                
                # Remove the server default after data is populated
                # Note: SQLite doesn't support removing server defaults via ALTER COLUMN
                # The default will remain but won't affect new records since we set explicit values
                try:
                    # Use batch mode for SQLite compatibility (even though this may still be unsupported
                    # depending on SQLite version; we keep it best-effort).
                    with op.batch_alter_table('invoices') as batch_op:
                        batch_op.alter_column('payment_status', server_default=None)
                except:
                    # SQLite doesn't support this operation, but it's not critical
                    pass
            else:
                # PostgreSQL: Use the original approach
                # Add the column as nullable first
                op.add_column('invoices', sa.Column('payment_status', sa.String(20), nullable=True))
                
                # Update existing records based on their current status
                bind.execute(sa.text("""
                    UPDATE invoices SET payment_status = CASE 
                        WHEN status = 'paid' THEN 'fully_paid'
                        ELSE 'unpaid'
                    END 
                    WHERE payment_status IS NULL
                """))
                
                # For invoices marked as 'paid', also set amount_paid to total_amount
                bind.execute(sa.text("""
                    UPDATE invoices SET amount_paid = total_amount, payment_date = CURRENT_DATE 
                    WHERE status = 'paid' AND amount_paid = 0
                """))
                
                # Now make the column NOT NULL
                # Use batch mode so this migration remains SQLite-safe if logic changes,
                # and to satisfy portability audits.
                with op.batch_alter_table('invoices') as batch_op:
                    batch_op.alter_column('payment_status', nullable=False)
        
        # Create indexes for better performance
        try:
            op.create_index('ix_invoices_payment_date', 'invoices', ['payment_date'], unique=False)
        except:
            pass  # Index might already exist
        
        try:
            op.create_index('ix_invoices_payment_status', 'invoices', ['payment_status'], unique=False)
        except:
            pass  # Index might already exist


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    
    # Check if invoices table exists
    if 'invoices' in inspector.get_table_names():
        try:
            # Drop indexes first
            op.drop_index('ix_invoices_payment_status', table_name='invoices')
            op.drop_index('ix_invoices_payment_date', table_name='invoices')
        except:
            pass  # Indexes might not exist
        
        existing_columns = [col['name'] for col in inspector.get_columns('invoices')]
        
        # Remove payment tracking columns if they exist
        # SQLite supports DROP COLUMN since version 3.35.0 (2021), but we'll be safe
        columns_to_drop = ['payment_status', 'amount_paid', 'payment_notes', 
                          'payment_reference', 'payment_method', 'payment_date']
        
        for column in columns_to_drop:
            if column in existing_columns:
                try:
                    op.drop_column('invoices', column)
                except Exception as e:
                    # If dropping fails (older SQLite), log but continue
                    print(f"Warning: Could not drop column {column}: {e}")
                    pass
