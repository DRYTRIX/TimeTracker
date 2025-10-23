"""Add extra goods table for tracking additional products/goods

Revision ID: 021
Revises: 020
Create Date: 2025-01-22 00:00:00

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '021'
down_revision = '020'
branch_labels = None
depends_on = None


def _has_table(inspector, name: str) -> bool:
    """Check if a table exists"""
    try:
        return name in inspector.get_table_names()
    except Exception:
        return False


def upgrade() -> None:
    """Create extra_goods table"""
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    
    # Determine database dialect for proper default values
    dialect_name = bind.dialect.name
    print(f"[Migration 021] Running on {dialect_name} database")
    
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
    
    # Create extra_goods table if it doesn't exist
    if not _has_table(inspector, 'extra_goods'):
        print("[Migration 021] Creating extra_goods table...")
        try:
            # Check if required tables exist for conditional FKs
            has_projects = _has_table(inspector, 'projects')
            has_invoices = _has_table(inspector, 'invoices')
            has_users = _has_table(inspector, 'users')
            
            # Build foreign key constraints - include in table creation for SQLite compatibility
            fk_constraints = []
            
            if has_projects:
                fk_constraints.append(
                    sa.ForeignKeyConstraint(['project_id'], ['projects.id'], name='fk_extra_goods_project_id', ondelete='CASCADE')
                )
                print("[Migration 021]   Including project_id FK")
            else:
                print("[Migration 021]   ⚠ Skipping project_id FK (projects table doesn't exist)")
            
            if has_invoices:
                fk_constraints.append(
                    sa.ForeignKeyConstraint(['invoice_id'], ['invoices.id'], name='fk_extra_goods_invoice_id', ondelete='CASCADE')
                )
                print("[Migration 021]   Including invoice_id FK")
            else:
                print("[Migration 021]   ⚠ Skipping invoice_id FK (invoices table doesn't exist)")
            
            if has_users:
                fk_constraints.append(
                    sa.ForeignKeyConstraint(['created_by'], ['users.id'], name='fk_extra_goods_created_by', ondelete='CASCADE')
                )
                print("[Migration 021]   Including created_by FK")
            else:
                print("[Migration 021]   ⚠ Skipping created_by FK (users table doesn't exist)")
            
            op.create_table(
                'extra_goods',
                sa.Column('id', sa.Integer(), primary_key=True),
                sa.Column('project_id', sa.Integer(), nullable=True),
                sa.Column('invoice_id', sa.Integer(), nullable=True),
                sa.Column('name', sa.String(length=200), nullable=False),
                sa.Column('description', sa.Text(), nullable=True),
                sa.Column('category', sa.String(length=50), nullable=False),
                sa.Column('quantity', sa.Numeric(precision=10, scale=2), nullable=False, server_default='1'),
                sa.Column('unit_price', sa.Numeric(precision=10, scale=2), nullable=False),
                sa.Column('total_amount', sa.Numeric(precision=10, scale=2), nullable=False),
                sa.Column('currency_code', sa.String(length=3), nullable=False, server_default='EUR'),
                sa.Column('billable', sa.Boolean(), nullable=False, server_default=sa.text(bool_true_default)),
                sa.Column('sku', sa.String(length=100), nullable=True),
                sa.Column('created_by', sa.Integer(), nullable=False),
                sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text(timestamp_default)),
                sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text(timestamp_default)),
                *fk_constraints  # Include FKs during table creation for SQLite compatibility
            )
            print("[Migration 021] ✓ Table created with foreign keys")
        except Exception as e:
            print(f"[Migration 021] ✗ Error creating table: {e}")
            raise
        
        # Create indexes
        print("[Migration 021] Creating indexes...")
        try:
            op.create_index('ix_extra_goods_project_id', 'extra_goods', ['project_id'])
            op.create_index('ix_extra_goods_invoice_id', 'extra_goods', ['invoice_id'])
            op.create_index('ix_extra_goods_created_by', 'extra_goods', ['created_by'])
            print("[Migration 021] ✓ Indexes created")
        except Exception as e:
            print(f"[Migration 021] ✗ Error creating indexes: {e}")
            raise
        
        print("[Migration 021] ✓ Migration completed successfully")
    else:
        print("[Migration 021] ⚠ Table already exists, skipping")


def downgrade() -> None:
    """Drop extra_goods table"""
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    
    if _has_table(inspector, 'extra_goods'):
        try:
            op.drop_table('extra_goods')
        except Exception:
            pass

