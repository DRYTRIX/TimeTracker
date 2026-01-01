"""Add advanced expense management

Revision ID: 037_advanced_expenses
Revises: 036_add_pdf_design_json
Create Date: 2025-10-30 14:30:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '037_advanced_expenses'
down_revision = '036_add_pdf_design_json'
branch_labels = None
depends_on = None


def upgrade():
    # Import for checking table existence
    from sqlalchemy import inspect
    
    conn = op.get_bind()
    inspector = inspect(conn)
    existing_tables = inspector.get_table_names()
    
    # Create expense_categories table (idempotent)
    if 'expense_categories' not in existing_tables:
        op.create_table(
            'expense_categories',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('name', sa.String(length=100), nullable=False),
            sa.Column('description', sa.Text(), nullable=True),
            sa.Column('code', sa.String(length=20), nullable=True),
            sa.Column('color', sa.String(length=7), nullable=True),
            sa.Column('icon', sa.String(length=50), nullable=True),
            sa.Column('monthly_budget', sa.Numeric(precision=10, scale=2), nullable=True),
            sa.Column('quarterly_budget', sa.Numeric(precision=10, scale=2), nullable=True),
            sa.Column('yearly_budget', sa.Numeric(precision=10, scale=2), nullable=True),
            sa.Column('budget_threshold_percent', sa.Integer(), nullable=False, server_default='80'),
            sa.Column('requires_receipt', sa.Boolean(), nullable=False, server_default='true'),
            sa.Column('requires_approval', sa.Boolean(), nullable=False, server_default='true'),
            sa.Column('default_tax_rate', sa.Numeric(precision=5, scale=2), nullable=True),
            sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
            sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
            sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
            sa.PrimaryKeyConstraint('id'),
            sa.UniqueConstraint('name'),
            sa.UniqueConstraint('code')
        )
        op.create_index('ix_expense_categories_name', 'expense_categories', ['name'], unique=True)
        op.create_index('ix_expense_categories_code', 'expense_categories', ['code'], unique=True)
    
    # Create mileage table (without expense_id FK initially) (idempotent)
    if 'mileage' not in existing_tables:
        op.create_table(
            'mileage',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('user_id', sa.Integer(), nullable=False),
            sa.Column('project_id', sa.Integer(), nullable=True),
            sa.Column('client_id', sa.Integer(), nullable=True),
            sa.Column('expense_id', sa.Integer(), nullable=True),
            sa.Column('trip_date', sa.Date(), nullable=False),
            sa.Column('trip_purpose', sa.Text(), nullable=False),
            sa.Column('start_location', sa.String(length=255), nullable=False),
            sa.Column('end_location', sa.String(length=255), nullable=False),
            sa.Column('distance_km', sa.Numeric(precision=10, scale=2), nullable=False),
            sa.Column('vehicle_type', sa.String(length=50), nullable=True),
            sa.Column('vehicle_registration', sa.String(length=20), nullable=True),
            sa.Column('rate_per_km', sa.Numeric(precision=10, scale=4), nullable=True),
            sa.Column('total_amount', sa.Numeric(precision=10, scale=2), nullable=True),
            sa.Column('status', sa.String(length=20), nullable=False, server_default='pending'),
            sa.Column('approved_by', sa.Integer(), nullable=True),
            sa.Column('approved_at', sa.DateTime(), nullable=True),
            sa.Column('rejection_reason', sa.Text(), nullable=True),
            sa.Column('notes', sa.Text(), nullable=True),
            sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
            sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
            sa.PrimaryKeyConstraint('id'),
            sa.ForeignKeyConstraint(['user_id'], ['users.id']),
            sa.ForeignKeyConstraint(['project_id'], ['projects.id']),
            sa.ForeignKeyConstraint(['client_id'], ['clients.id']),
            sa.ForeignKeyConstraint(['approved_by'], ['users.id'])
        )
        op.create_index('ix_mileage_user_id', 'mileage', ['user_id'])
        op.create_index('ix_mileage_trip_date', 'mileage', ['trip_date'])
    
    # Create per_diem_rates table (idempotent)
    if 'per_diem_rates' not in existing_tables:
        op.create_table(
            'per_diem_rates',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('country_code', sa.String(length=2), nullable=False),
            sa.Column('location', sa.String(length=255), nullable=True),
            sa.Column('rate_per_day', sa.Numeric(precision=10, scale=2), nullable=False),
            sa.Column('breakfast_deduction', sa.Numeric(precision=10, scale=2), nullable=True),
            sa.Column('lunch_deduction', sa.Numeric(precision=10, scale=2), nullable=True),
            sa.Column('dinner_deduction', sa.Numeric(precision=10, scale=2), nullable=True),
            sa.Column('valid_from', sa.Date(), nullable=False),
            sa.Column('valid_to', sa.Date(), nullable=True),
            sa.Column('currency_code', sa.String(length=3), nullable=False),
            sa.Column('notes', sa.Text(), nullable=True),
            sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
            sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
            sa.PrimaryKeyConstraint('id')
        )
        op.create_index('ix_per_diem_rates_country', 'per_diem_rates', ['country_code'])
        op.create_index('ix_per_diem_rates_valid_from', 'per_diem_rates', ['valid_from'])
    
    # Create per_diems table (without expense_id FK initially) (idempotent)
    if 'per_diems' not in existing_tables:
        op.create_table(
            'per_diems',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('user_id', sa.Integer(), nullable=False),
            sa.Column('project_id', sa.Integer(), nullable=True),
            sa.Column('client_id', sa.Integer(), nullable=True),
            sa.Column('expense_id', sa.Integer(), nullable=True),
            sa.Column('trip_start_date', sa.Date(), nullable=False),
            sa.Column('trip_end_date', sa.Date(), nullable=False),
            sa.Column('destination_country', sa.String(length=2), nullable=False),
            sa.Column('destination_location', sa.String(length=255), nullable=True),
            sa.Column('per_diem_rate_id', sa.Integer(), nullable=True),
            sa.Column('number_of_days', sa.Integer(), nullable=False),
            sa.Column('breakfast_provided', sa.Integer(), nullable=False, server_default='0'),
            sa.Column('lunch_provided', sa.Integer(), nullable=False, server_default='0'),
            sa.Column('dinner_provided', sa.Integer(), nullable=False, server_default='0'),
            sa.Column('total_amount', sa.Numeric(precision=10, scale=2), nullable=True),
            sa.Column('currency_code', sa.String(length=3), nullable=False),
            sa.Column('status', sa.String(length=20), nullable=False, server_default='pending'),
            sa.Column('approved_by', sa.Integer(), nullable=True),
            sa.Column('approved_at', sa.DateTime(), nullable=True),
            sa.Column('rejection_reason', sa.Text(), nullable=True),
            sa.Column('notes', sa.Text(), nullable=True),
            sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
            sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
            sa.PrimaryKeyConstraint('id'),
            sa.ForeignKeyConstraint(['user_id'], ['users.id']),
            sa.ForeignKeyConstraint(['project_id'], ['projects.id']),
            sa.ForeignKeyConstraint(['client_id'], ['clients.id']),
            sa.ForeignKeyConstraint(['per_diem_rate_id'], ['per_diem_rates.id']),
            sa.ForeignKeyConstraint(['approved_by'], ['users.id'])
        )
        op.create_index('ix_per_diems_user_id', 'per_diems', ['user_id'])
        op.create_index('ix_per_diems_trip_start', 'per_diems', ['trip_start_date'])
    
    # Check database dialect for SQLite batch mode
    is_sqlite = conn.dialect.name == 'sqlite'
    
    # Add new columns to expenses table (idempotent)
    if 'expenses' in existing_tables:
        existing_columns = [col['name'] for col in inspector.get_columns('expenses')]
        
        if 'ocr_data' not in existing_columns:
            op.add_column('expenses', sa.Column('ocr_data', sa.Text(), nullable=True))
        if 'mileage_id' not in existing_columns:
            op.add_column('expenses', sa.Column('mileage_id', sa.Integer(), nullable=True))
        if 'per_diem_id' not in existing_columns:
            op.add_column('expenses', sa.Column('per_diem_id', sa.Integer(), nullable=True))
        
        # Add foreign keys from expenses to mileage and per_diems (idempotent)
        existing_fks = [fk['name'] for fk in inspector.get_foreign_keys('expenses')]
        
        # SQLite requires batch mode for adding constraints to existing tables
        if is_sqlite:
            with op.batch_alter_table('expenses', schema=None) as batch_op:
                if 'fk_expenses_mileage' not in existing_fks:
                    batch_op.create_foreign_key('fk_expenses_mileage', 'mileage', ['mileage_id'], ['id'])
                if 'fk_expenses_per_diem' not in existing_fks:
                    batch_op.create_foreign_key('fk_expenses_per_diem', 'per_diems', ['per_diem_id'], ['id'])
        else:
            # PostgreSQL and other databases can add constraints directly
            if 'fk_expenses_mileage' not in existing_fks:
                op.create_foreign_key('fk_expenses_mileage', 'expenses', 'mileage', ['mileage_id'], ['id'])
            if 'fk_expenses_per_diem' not in existing_fks:
                op.create_foreign_key('fk_expenses_per_diem', 'expenses', 'per_diems', ['per_diem_id'], ['id'])
    
    # Now add the circular foreign keys from mileage and per_diems back to expenses (idempotent)
    # Re-check inspector after potential table creations
    conn = op.get_bind()
    inspector = inspect(conn)
    
    if 'mileage' in inspector.get_table_names():
        mileage_columns = [col['name'] for col in inspector.get_columns('mileage')]
        mileage_fks = [fk['name'] for fk in inspector.get_foreign_keys('mileage')]
        
        # Ensure expense_id column exists before adding FK
        if 'expense_id' in mileage_columns and 'fk_mileage_expense' not in mileage_fks:
            if is_sqlite:
                with op.batch_alter_table('mileage', schema=None) as batch_op:
                    batch_op.create_foreign_key('fk_mileage_expense', 'expenses', ['expense_id'], ['id'])
            else:
                op.create_foreign_key('fk_mileage_expense', 'mileage', 'expenses', ['expense_id'], ['id'])
    
    if 'per_diems' in inspector.get_table_names():
        per_diems_columns = [col['name'] for col in inspector.get_columns('per_diems')]
        per_diems_fks = [fk['name'] for fk in inspector.get_foreign_keys('per_diems')]
        
        # Ensure expense_id column exists before adding FK
        if 'expense_id' in per_diems_columns and 'fk_per_diems_expense' not in per_diems_fks:
            if is_sqlite:
                with op.batch_alter_table('per_diems', schema=None) as batch_op:
                    batch_op.create_foreign_key('fk_per_diems_expense', 'expenses', ['expense_id'], ['id'])
            else:
                op.create_foreign_key('fk_per_diems_expense', 'per_diems', 'expenses', ['expense_id'], ['id'])
    
    # Insert default expense categories (idempotent)
    # Re-check table existence since tables may have been created in this migration
    current_tables = inspector.get_table_names()
    
    # Determine database type for SQL syntax differences
    is_postgresql = conn.dialect.name == 'postgresql'
    
    if 'expense_categories' in current_tables:
        # Use database-specific syntax for upsert
        
        if is_postgresql:
            # PostgreSQL syntax
            op.execute("""
                INSERT INTO expense_categories (name, code, color, icon, requires_receipt, requires_approval, is_active)
                VALUES 
                    ('Travel', 'TRAVEL', '#4CAF50', '✈️', true, true, true),
                    ('Meals', 'MEALS', '#FF9800', '🍽️', true, false, true),
                    ('Accommodation', 'ACCOM', '#2196F3', '🏨', true, true, true),
                    ('Office Supplies', 'OFFICE', '#9C27B0', '📎', false, false, true),
                    ('Equipment', 'EQUIP', '#F44336', '💻', true, true, true),
                    ('Mileage', 'MILE', '#00BCD4', '🚗', false, false, true),
                    ('Per Diem', 'PERDIEM', '#8BC34A', '📅', false, false, true)
                ON CONFLICT (name) DO NOTHING
            """)
        else:
            # SQLite syntax
            op.execute("""
                INSERT OR IGNORE INTO expense_categories (name, code, color, icon, requires_receipt, requires_approval, is_active)
                VALUES 
                    ('Travel', 'TRAVEL', '#4CAF50', '✈️', 1, 1, 1),
                    ('Meals', 'MEALS', '#FF9800', '🍽️', 1, 0, 1),
                    ('Accommodation', 'ACCOM', '#2196F3', '🏨', 1, 1, 1),
                    ('Office Supplies', 'OFFICE', '#9C27B0', '📎', 0, 0, 1),
                    ('Equipment', 'EQUIP', '#F44336', '💻', 1, 1, 1),
                    ('Mileage', 'MILE', '#00BCD4', '🚗', 0, 0, 1),
                    ('Per Diem', 'PERDIEM', '#8BC34A', '📅', 0, 0, 1)
            """)
    
    # Insert default per diem rates (idempotent)
    if 'per_diem_rates' in current_tables:
        # Check if any records exist to avoid duplicates
        result = conn.execute(sa.text("SELECT COUNT(*) FROM per_diem_rates"))
        count = result.scalar()
        
        if count == 0:
            # Only insert if table is empty
            if is_postgresql:
                # PostgreSQL syntax
                op.execute("""
                    INSERT INTO per_diem_rates (country_code, location, rate_per_day, breakfast_deduction, lunch_deduction, dinner_deduction, valid_from, currency_code, is_active)
                    VALUES 
                        ('US', 'General', 55.00, 13.00, 16.00, 26.00, '2025-01-01', 'USD', true),
                        ('GB', 'General', 45.00, 10.00, 13.00, 22.00, '2025-01-01', 'GBP', true),
                        ('DE', 'General', 24.00, 5.00, 8.00, 11.00, '2025-01-01', 'EUR', true),
                        ('FR', 'General', 20.00, 4.00, 7.00, 9.00, '2025-01-01', 'EUR', true)
                """)
            else:
                # SQLite syntax
                op.execute("""
                    INSERT INTO per_diem_rates (country_code, location, rate_per_day, breakfast_deduction, lunch_deduction, dinner_deduction, valid_from, currency_code, is_active)
                    VALUES 
                        ('US', 'General', 55.00, 13.00, 16.00, 26.00, '2025-01-01', 'USD', 1),
                        ('GB', 'General', 45.00, 10.00, 13.00, 22.00, '2025-01-01', 'GBP', 1),
                        ('DE', 'General', 24.00, 5.00, 8.00, 11.00, '2025-01-01', 'EUR', 1),
                        ('FR', 'General', 20.00, 4.00, 7.00, 9.00, '2025-01-01', 'EUR', 1)
                """)


def downgrade():
    # Remove circular foreign keys first
    op.drop_constraint('fk_per_diems_expense', 'per_diems', type_='foreignkey')
    op.drop_constraint('fk_mileage_expense', 'mileage', type_='foreignkey')
    
    # Remove foreign keys from expenses
    op.drop_constraint('fk_expenses_per_diem', 'expenses', type_='foreignkey')
    op.drop_constraint('fk_expenses_mileage', 'expenses', type_='foreignkey')
    
    # Remove columns from expenses table
    op.drop_column('expenses', 'per_diem_id')
    op.drop_column('expenses', 'mileage_id')
    op.drop_column('expenses', 'ocr_data')
    
    # Drop tables in reverse order
    op.drop_index('ix_per_diems_trip_start', table_name='per_diems')
    op.drop_index('ix_per_diems_user_id', table_name='per_diems')
    op.drop_table('per_diems')
    
    op.drop_index('ix_per_diem_rates_valid_from', table_name='per_diem_rates')
    op.drop_index('ix_per_diem_rates_country', table_name='per_diem_rates')
    op.drop_table('per_diem_rates')
    
    op.drop_index('ix_mileage_trip_date', table_name='mileage')
    op.drop_index('ix_mileage_user_id', table_name='mileage')
    op.drop_table('mileage')
    
    op.drop_index('ix_expense_categories_code', table_name='expense_categories')
    op.drop_index('ix_expense_categories_name', table_name='expense_categories')
    op.drop_table('expense_categories')

