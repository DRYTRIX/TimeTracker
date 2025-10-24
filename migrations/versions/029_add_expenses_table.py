"""Add expenses table for expense tracking

Revision ID: 029
Revises: 028
Create Date: 2025-10-24 00:00:00

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '029'
down_revision = '028'
branch_labels = None
depends_on = None


def _has_table(inspector, name: str) -> bool:
    """Check if a table exists"""
    try:
        return name in inspector.get_table_names()
    except Exception:
        return False


def upgrade() -> None:
    """Create expenses table"""
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    
    # Determine database dialect for proper default values
    dialect_name = bind.dialect.name
    print(f"[Migration 029] Running on {dialect_name} database")
    
    # Set appropriate boolean defaults based on database
    if dialect_name == 'sqlite':
        bool_true_default = '1'
        bool_false_default = '0'
        timestamp_default = "(datetime('now'))"
    elif dialect_name == 'postgresql':
        bool_true_default = 'true'
        bool_false_default = 'false'
        timestamp_default = 'CURRENT_TIMESTAMP'
    else:  # MySQL/MariaDB and others
        bool_true_default = '1'
        bool_false_default = '0'
        timestamp_default = 'CURRENT_TIMESTAMP'
    
    # Create expenses table if it doesn't exist
    if not _has_table(inspector, 'expenses'):
        print("[Migration 029] Creating expenses table...")
        try:
            # Check if related tables exist for conditional FKs
            has_projects = _has_table(inspector, 'projects')
            has_clients = _has_table(inspector, 'clients')
            has_invoices = _has_table(inspector, 'invoices')
            has_users = _has_table(inspector, 'users')
            
            # Build foreign key constraints
            fk_constraints = []
            
            if has_users:
                fk_constraints.extend([
                    sa.ForeignKeyConstraint(['user_id'], ['users.id'], name='fk_expenses_user_id', ondelete='CASCADE'),
                    sa.ForeignKeyConstraint(['approved_by'], ['users.id'], name='fk_expenses_approved_by', ondelete='SET NULL'),
                ])
                print("[Migration 029]   Including user FKs")
            else:
                print("[Migration 029]   ⚠ Skipping user FKs (users table doesn't exist)")
            
            if has_projects:
                fk_constraints.append(
                    sa.ForeignKeyConstraint(['project_id'], ['projects.id'], name='fk_expenses_project_id', ondelete='SET NULL')
                )
                print("[Migration 029]   Including project_id FK")
            else:
                print("[Migration 029]   ⚠ Skipping project_id FK (projects table doesn't exist)")
            
            if has_clients:
                fk_constraints.append(
                    sa.ForeignKeyConstraint(['client_id'], ['clients.id'], name='fk_expenses_client_id', ondelete='SET NULL')
                )
                print("[Migration 029]   Including client_id FK")
            else:
                print("[Migration 029]   ⚠ Skipping client_id FK (clients table doesn't exist)")
            
            if has_invoices:
                fk_constraints.append(
                    sa.ForeignKeyConstraint(['invoice_id'], ['invoices.id'], name='fk_expenses_invoice_id', ondelete='SET NULL')
                )
                print("[Migration 029]   Including invoice_id FK")
            else:
                print("[Migration 029]   ⚠ Skipping invoice_id FK (invoices table doesn't exist)")
            
            op.create_table(
                'expenses',
                sa.Column('id', sa.Integer(), primary_key=True),
                sa.Column('user_id', sa.Integer(), nullable=False),
                sa.Column('project_id', sa.Integer(), nullable=True),
                sa.Column('client_id', sa.Integer(), nullable=True),
                sa.Column('title', sa.String(length=200), nullable=False),
                sa.Column('description', sa.Text(), nullable=True),
                sa.Column('category', sa.String(length=50), nullable=False),
                sa.Column('amount', sa.Numeric(precision=10, scale=2), nullable=False),
                sa.Column('currency_code', sa.String(length=3), nullable=False, server_default='EUR'),
                sa.Column('tax_amount', sa.Numeric(precision=10, scale=2), nullable=True, server_default='0'),
                sa.Column('tax_rate', sa.Numeric(precision=5, scale=2), nullable=True, server_default='0'),
                sa.Column('payment_method', sa.String(length=50), nullable=True),
                sa.Column('payment_date', sa.Date(), nullable=True),
                sa.Column('status', sa.String(length=20), nullable=False, server_default='pending'),
                sa.Column('approved_by', sa.Integer(), nullable=True),
                sa.Column('approved_at', sa.DateTime(), nullable=True),
                sa.Column('rejection_reason', sa.Text(), nullable=True),
                sa.Column('billable', sa.Boolean(), nullable=False, server_default=sa.text(bool_false_default)),
                sa.Column('reimbursable', sa.Boolean(), nullable=False, server_default=sa.text(bool_true_default)),
                sa.Column('invoiced', sa.Boolean(), nullable=False, server_default=sa.text(bool_false_default)),
                sa.Column('invoice_id', sa.Integer(), nullable=True),
                sa.Column('reimbursed', sa.Boolean(), nullable=False, server_default=sa.text(bool_false_default)),
                sa.Column('reimbursed_at', sa.DateTime(), nullable=True),
                sa.Column('expense_date', sa.Date(), nullable=False),
                sa.Column('receipt_path', sa.String(length=500), nullable=True),
                sa.Column('receipt_number', sa.String(length=100), nullable=True),
                sa.Column('vendor', sa.String(length=200), nullable=True),
                sa.Column('notes', sa.Text(), nullable=True),
                sa.Column('tags', sa.String(length=500), nullable=True),
                sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text(timestamp_default)),
                sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text(timestamp_default)),
                *fk_constraints  # Include FKs during table creation for SQLite compatibility
            )
            print("[Migration 029] ✓ Table created with foreign keys")
        except Exception as e:
            print(f"[Migration 029] ✗ Error creating table: {e}")
            raise
        
        # Create indexes
        print("[Migration 029] Creating indexes...")
        try:
            op.create_index('ix_expenses_user_id', 'expenses', ['user_id'])
            op.create_index('ix_expenses_project_id', 'expenses', ['project_id'])
            op.create_index('ix_expenses_client_id', 'expenses', ['client_id'])
            op.create_index('ix_expenses_approved_by', 'expenses', ['approved_by'])
            op.create_index('ix_expenses_invoice_id', 'expenses', ['invoice_id'])
            op.create_index('ix_expenses_expense_date', 'expenses', ['expense_date'])
            
            # Composite indexes for common query patterns
            op.create_index('ix_expenses_user_date', 'expenses', ['user_id', 'expense_date'])
            op.create_index('ix_expenses_status_date', 'expenses', ['status', 'expense_date'])
            op.create_index('ix_expenses_project_date', 'expenses', ['project_id', 'expense_date'])
            
            print("[Migration 029] ✓ Indexes created")
        except Exception as e:
            print(f"[Migration 029] ✗ Error creating indexes: {e}")
            raise
        
        print("[Migration 029] ✓ Migration completed successfully")
    else:
        print("[Migration 029] ⚠ Table already exists, skipping")


def downgrade() -> None:
    """Drop expenses table"""
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    
    if _has_table(inspector, 'expenses'):
        print("[Migration 029] Dropping expenses table...")
        try:
            # Drop indexes first
            try:
                op.drop_index('ix_expenses_project_date', 'expenses')
                op.drop_index('ix_expenses_status_date', 'expenses')
                op.drop_index('ix_expenses_user_date', 'expenses')
                op.drop_index('ix_expenses_expense_date', 'expenses')
                op.drop_index('ix_expenses_invoice_id', 'expenses')
                op.drop_index('ix_expenses_approved_by', 'expenses')
                op.drop_index('ix_expenses_client_id', 'expenses')
                op.drop_index('ix_expenses_project_id', 'expenses')
                op.drop_index('ix_expenses_user_id', 'expenses')
            except Exception:
                pass
            
            # Drop table
            op.drop_table('expenses')
            print("[Migration 029] ✓ Table dropped")
        except Exception as e:
            print(f"[Migration 029] ✗ Error dropping table: {e}")

