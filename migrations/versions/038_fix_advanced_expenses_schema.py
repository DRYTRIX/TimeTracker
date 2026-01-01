"""Fix advanced expenses schema

Revision ID: 038_fix_expenses_schema
Revises: 037_advanced_expenses
Create Date: 2025-10-30 15:05:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect

# revision identifiers, used by Alembic.
revision = '038_fix_expenses_schema'
down_revision = '037_advanced_expenses'
branch_labels = None
depends_on = None


def upgrade():
    conn = op.get_bind()
    is_sqlite = conn.dialect.name == 'sqlite'
    inspector = inspect(conn)
    
    # Check if tables exist (idempotent)
    existing_tables = inspector.get_table_names()
    
    # Fix mileage table - rename columns and add missing ones
    if 'mileage' in existing_tables:
        mileage_columns = [col['name'] for col in inspector.get_columns('mileage')]
        
        if is_sqlite:
            with op.batch_alter_table('mileage', schema=None) as batch_op:
                # Rename columns
                if 'trip_purpose' in mileage_columns and 'purpose' not in mileage_columns:
                    batch_op.alter_column('trip_purpose', new_column_name='purpose')
                if 'vehicle_registration' in mileage_columns and 'license_plate' not in mileage_columns:
                    batch_op.alter_column('vehicle_registration', new_column_name='license_plate')
                if 'total_amount' in mileage_columns and 'calculated_amount' not in mileage_columns:
                    batch_op.alter_column('total_amount', new_column_name='calculated_amount')
                
                # Add missing columns
                if 'description' not in mileage_columns:
                    batch_op.add_column(sa.Column('description', sa.Text(), nullable=True))
                if 'start_odometer' not in mileage_columns:
                    batch_op.add_column(sa.Column('start_odometer', sa.Numeric(precision=10, scale=2), nullable=True))
                if 'end_odometer' not in mileage_columns:
                    batch_op.add_column(sa.Column('end_odometer', sa.Numeric(precision=10, scale=2), nullable=True))
                if 'distance_miles' not in mileage_columns:
                    batch_op.add_column(sa.Column('distance_miles', sa.Numeric(precision=10, scale=2), nullable=True))
                if 'rate_per_mile' not in mileage_columns:
                    batch_op.add_column(sa.Column('rate_per_mile', sa.Numeric(precision=10, scale=4), nullable=True))
                if 'vehicle_description' not in mileage_columns:
                    batch_op.add_column(sa.Column('vehicle_description', sa.String(length=200), nullable=True))
                if 'is_round_trip' not in mileage_columns:
                    batch_op.add_column(sa.Column('is_round_trip', sa.Boolean(), nullable=False, server_default='false'))
                if 'reimbursed' not in mileage_columns:
                    batch_op.add_column(sa.Column('reimbursed', sa.Boolean(), nullable=False, server_default='false'))
                if 'reimbursed_at' not in mileage_columns:
                    batch_op.add_column(sa.Column('reimbursed_at', sa.DateTime(), nullable=True))
                if 'currency_code' not in mileage_columns:
                    batch_op.add_column(sa.Column('currency_code', sa.String(length=3), nullable=False, server_default='EUR'))
                
                # Make rate_per_km NOT NULL if it exists and is nullable
                if 'rate_per_km' in mileage_columns:
                    # Check current nullability
                    rate_col = next((col for col in inspector.get_columns('mileage') if col['name'] == 'rate_per_km'), None)
                    if rate_col and rate_col.get('nullable', True):
                        # Set default for NULL values first
                        conn.execute(sa.text("UPDATE mileage SET rate_per_km = 0.30 WHERE rate_per_km IS NULL"))
                        batch_op.alter_column('rate_per_km', nullable=False, server_default='0.30')
        else:
            # PostgreSQL and other databases
            if 'trip_purpose' in mileage_columns and 'purpose' not in mileage_columns:
                op.alter_column('mileage', 'trip_purpose', new_column_name='purpose', existing_type=sa.Text(), existing_nullable=False)
            if 'vehicle_registration' in mileage_columns and 'license_plate' not in mileage_columns:
                op.alter_column('mileage', 'vehicle_registration', new_column_name='license_plate', existing_type=sa.String(20), existing_nullable=True)
            if 'total_amount' in mileage_columns and 'calculated_amount' not in mileage_columns:
                op.alter_column('mileage', 'total_amount', new_column_name='calculated_amount', existing_type=sa.Numeric(10, 2), existing_nullable=True)
            
            # Add missing columns
            if 'description' not in mileage_columns:
                op.add_column('mileage', sa.Column('description', sa.Text(), nullable=True))
            if 'start_odometer' not in mileage_columns:
                op.add_column('mileage', sa.Column('start_odometer', sa.Numeric(precision=10, scale=2), nullable=True))
            if 'end_odometer' not in mileage_columns:
                op.add_column('mileage', sa.Column('end_odometer', sa.Numeric(precision=10, scale=2), nullable=True))
            if 'distance_miles' not in mileage_columns:
                op.add_column('mileage', sa.Column('distance_miles', sa.Numeric(precision=10, scale=2), nullable=True))
            if 'rate_per_mile' not in mileage_columns:
                op.add_column('mileage', sa.Column('rate_per_mile', sa.Numeric(precision=10, scale=4), nullable=True))
            if 'vehicle_description' not in mileage_columns:
                op.add_column('mileage', sa.Column('vehicle_description', sa.String(length=200), nullable=True))
            if 'is_round_trip' not in mileage_columns:
                op.add_column('mileage', sa.Column('is_round_trip', sa.Boolean(), nullable=False, server_default='false'))
            if 'reimbursed' not in mileage_columns:
                op.add_column('mileage', sa.Column('reimbursed', sa.Boolean(), nullable=False, server_default='false'))
            if 'reimbursed_at' not in mileage_columns:
                op.add_column('mileage', sa.Column('reimbursed_at', sa.DateTime(), nullable=True))
            if 'currency_code' not in mileage_columns:
                op.add_column('mileage', sa.Column('currency_code', sa.String(length=3), nullable=False, server_default='EUR'))
            
            # Make rate_per_km NOT NULL
            if 'rate_per_km' in mileage_columns:
                rate_col = next((col for col in inspector.get_columns('mileage') if col['name'] == 'rate_per_km'), None)
                if rate_col and rate_col.get('nullable', True):
                    conn.execute(sa.text("UPDATE mileage SET rate_per_km = 0.30 WHERE rate_per_km IS NULL"))
                    op.alter_column('mileage', 'rate_per_km', nullable=False, server_default='0.30')
    
    # Fix per_diem_rates table - rename columns
    if 'per_diem_rates' in existing_tables:
        per_diem_rates_columns = [col['name'] for col in inspector.get_columns('per_diem_rates')]
        
        if is_sqlite:
            with op.batch_alter_table('per_diem_rates', schema=None) as batch_op:
                # Rename columns
                if 'location' in per_diem_rates_columns and 'city' not in per_diem_rates_columns:
                    batch_op.alter_column('location', new_column_name='city')
                if 'valid_from' in per_diem_rates_columns and 'effective_from' not in per_diem_rates_columns:
                    batch_op.alter_column('valid_from', new_column_name='effective_from')
                if 'valid_to' in per_diem_rates_columns and 'effective_to' not in per_diem_rates_columns:
                    batch_op.alter_column('valid_to', new_column_name='effective_to')
                if 'country_code' in per_diem_rates_columns and 'country' not in per_diem_rates_columns:
                    batch_op.alter_column('country_code', new_column_name='country')
                
                # Add missing columns
                if 'full_day_rate' not in per_diem_rates_columns:
                    batch_op.add_column(sa.Column('full_day_rate', sa.Numeric(precision=10, scale=2), nullable=False, server_default='0'))
                if 'half_day_rate' not in per_diem_rates_columns:
                    batch_op.add_column(sa.Column('half_day_rate', sa.Numeric(precision=10, scale=2), nullable=False, server_default='0'))
                if 'breakfast_rate' not in per_diem_rates_columns:
                    batch_op.add_column(sa.Column('breakfast_rate', sa.Numeric(precision=10, scale=2), nullable=True))
                if 'lunch_rate' not in per_diem_rates_columns:
                    batch_op.add_column(sa.Column('lunch_rate', sa.Numeric(precision=10, scale=2), nullable=True))
                if 'dinner_rate' not in per_diem_rates_columns:
                    batch_op.add_column(sa.Column('dinner_rate', sa.Numeric(precision=10, scale=2), nullable=True))
                if 'incidental_rate' not in per_diem_rates_columns:
                    batch_op.add_column(sa.Column('incidental_rate', sa.Numeric(precision=10, scale=2), nullable=True))
                if 'updated_at' not in per_diem_rates_columns:
                    batch_op.add_column(sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')))
                
                # Drop old columns (SQLite 3.35.0+ supports DROP COLUMN)
                # Copy data first
                if 'rate_per_day' in per_diem_rates_columns and 'full_day_rate' in per_diem_rates_columns:
                    conn.execute(sa.text("UPDATE per_diem_rates SET full_day_rate = rate_per_day, half_day_rate = rate_per_day * 0.5 WHERE full_day_rate = 0"))
                if 'rate_per_day' in per_diem_rates_columns:
                    batch_op.drop_column('rate_per_day')
                if 'breakfast_deduction' in per_diem_rates_columns:
                    batch_op.drop_column('breakfast_deduction')
                if 'lunch_deduction' in per_diem_rates_columns:
                    batch_op.drop_column('lunch_deduction')
                if 'dinner_deduction' in per_diem_rates_columns:
                    batch_op.drop_column('dinner_deduction')
        else:
            # PostgreSQL and other databases
            if 'location' in per_diem_rates_columns and 'city' not in per_diem_rates_columns:
                op.alter_column('per_diem_rates', 'location', new_column_name='city', existing_type=sa.String(255), existing_nullable=True)
            if 'valid_from' in per_diem_rates_columns and 'effective_from' not in per_diem_rates_columns:
                op.alter_column('per_diem_rates', 'valid_from', new_column_name='effective_from', existing_type=sa.Date(), existing_nullable=False)
            if 'valid_to' in per_diem_rates_columns and 'effective_to' not in per_diem_rates_columns:
                op.alter_column('per_diem_rates', 'valid_to', new_column_name='effective_to', existing_type=sa.Date(), existing_nullable=True)
            if 'country_code' in per_diem_rates_columns and 'country' not in per_diem_rates_columns:
                op.alter_column('per_diem_rates', 'country_code', new_column_name='country', existing_type=sa.String(2), existing_nullable=False)
            
            # Add missing columns
            if 'full_day_rate' not in per_diem_rates_columns:
                op.add_column('per_diem_rates', sa.Column('full_day_rate', sa.Numeric(precision=10, scale=2), nullable=False, server_default='0'))
            if 'half_day_rate' not in per_diem_rates_columns:
                op.add_column('per_diem_rates', sa.Column('half_day_rate', sa.Numeric(precision=10, scale=2), nullable=False, server_default='0'))
            if 'breakfast_rate' not in per_diem_rates_columns:
                op.add_column('per_diem_rates', sa.Column('breakfast_rate', sa.Numeric(precision=10, scale=2), nullable=True))
            if 'lunch_rate' not in per_diem_rates_columns:
                op.add_column('per_diem_rates', sa.Column('lunch_rate', sa.Numeric(precision=10, scale=2), nullable=True))
            if 'dinner_rate' not in per_diem_rates_columns:
                op.add_column('per_diem_rates', sa.Column('dinner_rate', sa.Numeric(precision=10, scale=2), nullable=True))
            if 'incidental_rate' not in per_diem_rates_columns:
                op.add_column('per_diem_rates', sa.Column('incidental_rate', sa.Numeric(precision=10, scale=2), nullable=True))
            if 'updated_at' not in per_diem_rates_columns:
                op.add_column('per_diem_rates', sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')))
            
            # Drop old columns after copying data
            if 'rate_per_day' in per_diem_rates_columns:
                conn.execute(sa.text("UPDATE per_diem_rates SET full_day_rate = rate_per_day, half_day_rate = rate_per_day * 0.5"))
                op.drop_column('per_diem_rates', 'rate_per_day')
            if 'breakfast_deduction' in per_diem_rates_columns:
                op.drop_column('per_diem_rates', 'breakfast_deduction')
            if 'lunch_deduction' in per_diem_rates_columns:
                op.drop_column('per_diem_rates', 'lunch_deduction')
            if 'dinner_deduction' in per_diem_rates_columns:
                op.drop_column('per_diem_rates', 'dinner_deduction')
    
    # Fix per_diems table - rename columns
    if 'per_diems' in existing_tables:
        per_diems_columns = [col['name'] for col in inspector.get_columns('per_diems')]
        
        if is_sqlite:
            with op.batch_alter_table('per_diems', schema=None) as batch_op:
                # Rename columns
                if 'trip_start_date' in per_diems_columns and 'start_date' not in per_diems_columns:
                    batch_op.alter_column('trip_start_date', new_column_name='start_date')
                if 'trip_end_date' in per_diems_columns and 'end_date' not in per_diems_columns:
                    batch_op.alter_column('trip_end_date', new_column_name='end_date')
                if 'destination_country' in per_diems_columns and 'country' not in per_diems_columns:
                    batch_op.alter_column('destination_country', new_column_name='country')
                if 'destination_location' in per_diems_columns and 'city' not in per_diems_columns:
                    batch_op.alter_column('destination_location', new_column_name='city')
                if 'number_of_days' in per_diems_columns and 'full_days' not in per_diems_columns:
                    batch_op.alter_column('number_of_days', new_column_name='full_days')
                if 'total_amount' in per_diems_columns and 'calculated_amount' not in per_diems_columns:
                    batch_op.alter_column('total_amount', new_column_name='calculated_amount')
                
                # Add missing columns
                if 'trip_purpose' not in per_diems_columns:
                    batch_op.add_column(sa.Column('trip_purpose', sa.String(length=255), nullable=False, server_default='Business trip'))
                if 'description' not in per_diems_columns:
                    batch_op.add_column(sa.Column('description', sa.Text(), nullable=True))
                if 'departure_time' not in per_diems_columns:
                    batch_op.add_column(sa.Column('departure_time', sa.Time(), nullable=True))
                if 'return_time' not in per_diems_columns:
                    batch_op.add_column(sa.Column('return_time', sa.Time(), nullable=True))
                if 'half_days' not in per_diems_columns:
                    batch_op.add_column(sa.Column('half_days', sa.Integer(), nullable=False, server_default='0'))
                if 'total_days' not in per_diems_columns:
                    batch_op.add_column(sa.Column('total_days', sa.Numeric(precision=5, scale=2), nullable=False, server_default='0'))
                if 'full_day_rate' not in per_diems_columns:
                    batch_op.add_column(sa.Column('full_day_rate', sa.Numeric(precision=10, scale=2), nullable=False, server_default='0'))
                if 'half_day_rate' not in per_diems_columns:
                    batch_op.add_column(sa.Column('half_day_rate', sa.Numeric(precision=10, scale=2), nullable=False, server_default='0'))
                if 'breakfast_deduction' not in per_diems_columns:
                    batch_op.add_column(sa.Column('breakfast_deduction', sa.Numeric(precision=10, scale=2), nullable=False, server_default='0'))
                if 'lunch_deduction' not in per_diems_columns:
                    batch_op.add_column(sa.Column('lunch_deduction', sa.Numeric(precision=10, scale=2), nullable=False, server_default='0'))
                if 'dinner_deduction' not in per_diems_columns:
                    batch_op.add_column(sa.Column('dinner_deduction', sa.Numeric(precision=10, scale=2), nullable=False, server_default='0'))
                if 'reimbursed' not in per_diems_columns:
                    batch_op.add_column(sa.Column('reimbursed', sa.Boolean(), nullable=False, server_default='false'))
                if 'reimbursed_at' not in per_diems_columns:
                    batch_op.add_column(sa.Column('reimbursed_at', sa.DateTime(), nullable=True))
                if 'approval_notes' not in per_diems_columns:
                    batch_op.add_column(sa.Column('approval_notes', sa.Text(), nullable=True))
        else:
            # PostgreSQL and other databases
            if 'trip_start_date' in per_diems_columns and 'start_date' not in per_diems_columns:
                op.alter_column('per_diems', 'trip_start_date', new_column_name='start_date', existing_type=sa.Date(), existing_nullable=False)
            if 'trip_end_date' in per_diems_columns and 'end_date' not in per_diems_columns:
                op.alter_column('per_diems', 'trip_end_date', new_column_name='end_date', existing_type=sa.Date(), existing_nullable=False)
            if 'destination_country' in per_diems_columns and 'country' not in per_diems_columns:
                op.alter_column('per_diems', 'destination_country', new_column_name='country', existing_type=sa.String(2), existing_nullable=False)
            if 'destination_location' in per_diems_columns and 'city' not in per_diems_columns:
                op.alter_column('per_diems', 'destination_location', new_column_name='city', existing_type=sa.String(255), existing_nullable=True)
            if 'number_of_days' in per_diems_columns and 'full_days' not in per_diems_columns:
                op.alter_column('per_diems', 'number_of_days', new_column_name='full_days', existing_type=sa.Integer(), existing_nullable=False)
            if 'total_amount' in per_diems_columns and 'calculated_amount' not in per_diems_columns:
                op.alter_column('per_diems', 'total_amount', new_column_name='calculated_amount', existing_type=sa.Numeric(10, 2), existing_nullable=True)
            
            # Add missing columns
            if 'trip_purpose' not in per_diems_columns:
                op.add_column('per_diems', sa.Column('trip_purpose', sa.String(length=255), nullable=False, server_default='Business trip'))
            if 'description' not in per_diems_columns:
                op.add_column('per_diems', sa.Column('description', sa.Text(), nullable=True))
            if 'departure_time' not in per_diems_columns:
                op.add_column('per_diems', sa.Column('departure_time', sa.Time(), nullable=True))
            if 'return_time' not in per_diems_columns:
                op.add_column('per_diems', sa.Column('return_time', sa.Time(), nullable=True))
            if 'half_days' not in per_diems_columns:
                op.add_column('per_diems', sa.Column('half_days', sa.Integer(), nullable=False, server_default='0'))
            if 'total_days' not in per_diems_columns:
                op.add_column('per_diems', sa.Column('total_days', sa.Numeric(precision=5, scale=2), nullable=False, server_default='0'))
            if 'full_day_rate' not in per_diems_columns:
                op.add_column('per_diems', sa.Column('full_day_rate', sa.Numeric(precision=10, scale=2), nullable=False, server_default='0'))
            if 'half_day_rate' not in per_diems_columns:
                op.add_column('per_diems', sa.Column('half_day_rate', sa.Numeric(precision=10, scale=2), nullable=False, server_default='0'))
            if 'breakfast_deduction' not in per_diems_columns:
                op.add_column('per_diems', sa.Column('breakfast_deduction', sa.Numeric(precision=10, scale=2), nullable=False, server_default='0'))
            if 'lunch_deduction' not in per_diems_columns:
                op.add_column('per_diems', sa.Column('lunch_deduction', sa.Numeric(precision=10, scale=2), nullable=False, server_default='0'))
            if 'dinner_deduction' not in per_diems_columns:
                op.add_column('per_diems', sa.Column('dinner_deduction', sa.Numeric(precision=10, scale=2), nullable=False, server_default='0'))
            if 'reimbursed' not in per_diems_columns:
                op.add_column('per_diems', sa.Column('reimbursed', sa.Boolean(), nullable=False, server_default='false'))
            if 'reimbursed_at' not in per_diems_columns:
                op.add_column('per_diems', sa.Column('reimbursed_at', sa.DateTime(), nullable=True))
            if 'approval_notes' not in per_diems_columns:
                op.add_column('per_diems', sa.Column('approval_notes', sa.Text(), nullable=True))


def downgrade():
    # Note: Downgrade is complex and may not work perfectly in SQLite
    # For production, consider backing up before downgrading
    conn = op.get_bind()
    is_sqlite = conn.dialect.name == 'sqlite'
    inspector = inspect(conn)
    existing_tables = inspector.get_table_names()
    
    # Revert per_diems changes
    if 'per_diems' in existing_tables:
        per_diems_columns = [col['name'] for col in inspector.get_columns('per_diems')]
        
        # Drop added columns
        for col in ['approval_notes', 'reimbursed_at', 'reimbursed', 'dinner_deduction', 'lunch_deduction', 
                   'breakfast_deduction', 'half_day_rate', 'full_day_rate', 'total_days', 'half_days',
                   'return_time', 'departure_time', 'description', 'trip_purpose']:
            if col in per_diems_columns:
                if is_sqlite:
                    with op.batch_alter_table('per_diems', schema=None) as batch_op:
                        batch_op.drop_column(col)
                else:
                    op.drop_column('per_diems', col)
        
        # Rename columns back
        if is_sqlite:
            with op.batch_alter_table('per_diems', schema=None) as batch_op:
                if 'calculated_amount' in per_diems_columns:
                    batch_op.alter_column('calculated_amount', new_column_name='total_amount')
                if 'full_days' in per_diems_columns:
                    batch_op.alter_column('full_days', new_column_name='number_of_days')
                if 'city' in per_diems_columns:
                    batch_op.alter_column('city', new_column_name='destination_location')
                if 'country' in per_diems_columns:
                    batch_op.alter_column('country', new_column_name='destination_country')
                if 'end_date' in per_diems_columns:
                    batch_op.alter_column('end_date', new_column_name='trip_end_date')
                if 'start_date' in per_diems_columns:
                    batch_op.alter_column('start_date', new_column_name='trip_start_date')
        else:
            if 'calculated_amount' in per_diems_columns:
                op.alter_column('per_diems', 'calculated_amount', new_column_name='total_amount')
            if 'full_days' in per_diems_columns:
                op.alter_column('per_diems', 'full_days', new_column_name='number_of_days')
            if 'city' in per_diems_columns:
                op.alter_column('per_diems', 'city', new_column_name='destination_location')
            if 'country' in per_diems_columns:
                op.alter_column('per_diems', 'country', new_column_name='destination_country')
            if 'end_date' in per_diems_columns:
                op.alter_column('per_diems', 'end_date', new_column_name='trip_end_date')
            if 'start_date' in per_diems_columns:
                op.alter_column('per_diems', 'start_date', new_column_name='trip_start_date')
    
    # Revert per_diem_rates changes
    if 'per_diem_rates' in existing_tables:
        per_diem_rates_columns = [col['name'] for col in inspector.get_columns('per_diem_rates')]
        
        # Add back old columns
        if 'rate_per_day' not in per_diem_rates_columns:
            if is_sqlite:
                with op.batch_alter_table('per_diem_rates', schema=None) as batch_op:
                    batch_op.add_column(sa.Column('rate_per_day', sa.Numeric(precision=10, scale=2), nullable=False, server_default='0'))
            else:
                op.add_column('per_diem_rates', sa.Column('rate_per_day', sa.Numeric(precision=10, scale=2), nullable=False, server_default='0'))
        
        # Copy data back
        if 'rate_per_day' in inspector.get_table_names() and 'full_day_rate' in per_diem_rates_columns:
            conn.execute(sa.text("UPDATE per_diem_rates SET rate_per_day = full_day_rate"))
        
        # Drop new columns and rename back
        if is_sqlite:
            with op.batch_alter_table('per_diem_rates', schema=None) as batch_op:
                for col in ['updated_at', 'incidental_rate', 'dinner_rate', 'lunch_rate', 'breakfast_rate', 
                           'half_day_rate', 'full_day_rate']:
                    if col in per_diem_rates_columns:
                        batch_op.drop_column(col)
                
                if 'country' in per_diem_rates_columns:
                    batch_op.alter_column('country', new_column_name='country_code')
                if 'effective_to' in per_diem_rates_columns:
                    batch_op.alter_column('effective_to', new_column_name='valid_to')
                if 'effective_from' in per_diem_rates_columns:
                    batch_op.alter_column('effective_from', new_column_name='valid_from')
                if 'city' in per_diem_rates_columns:
                    batch_op.alter_column('city', new_column_name='location')
        else:
            for col in ['updated_at', 'incidental_rate', 'dinner_rate', 'lunch_rate', 'breakfast_rate', 
                       'half_day_rate', 'full_day_rate']:
                if col in per_diem_rates_columns:
                    op.drop_column('per_diem_rates', col)
            
            if 'country' in per_diem_rates_columns:
                op.alter_column('per_diem_rates', 'country', new_column_name='country_code')
            if 'effective_to' in per_diem_rates_columns:
                op.alter_column('per_diem_rates', 'effective_to', new_column_name='valid_to')
            if 'effective_from' in per_diem_rates_columns:
                op.alter_column('per_diem_rates', 'effective_from', new_column_name='valid_from')
            if 'city' in per_diem_rates_columns:
                op.alter_column('per_diem_rates', 'city', new_column_name='location')
    
    # Revert mileage changes
    if 'mileage' in existing_tables:
        mileage_columns = [col['name'] for col in inspector.get_columns('mileage')]
        
        # Drop added columns
        for col in ['currency_code', 'reimbursed_at', 'reimbursed', 'is_round_trip', 'vehicle_description',
                   'rate_per_mile', 'distance_miles', 'end_odometer', 'start_odometer', 'description']:
            if col in mileage_columns:
                if is_sqlite:
                    with op.batch_alter_table('mileage', schema=None) as batch_op:
                        batch_op.drop_column(col)
                else:
                    op.drop_column('mileage', col)
        
        # Rename columns back and revert nullability
        if is_sqlite:
            with op.batch_alter_table('mileage', schema=None) as batch_op:
                if 'rate_per_km' in mileage_columns:
                    batch_op.alter_column('rate_per_km', nullable=True, server_default=None)
                if 'calculated_amount' in mileage_columns:
                    batch_op.alter_column('calculated_amount', new_column_name='total_amount')
                if 'license_plate' in mileage_columns:
                    batch_op.alter_column('license_plate', new_column_name='vehicle_registration')
                if 'purpose' in mileage_columns:
                    batch_op.alter_column('purpose', new_column_name='trip_purpose')
        else:
            if 'rate_per_km' in mileage_columns:
                op.alter_column('mileage', 'rate_per_km', nullable=True)
            if 'calculated_amount' in mileage_columns:
                op.alter_column('mileage', 'calculated_amount', new_column_name='total_amount')
            if 'license_plate' in mileage_columns:
                op.alter_column('mileage', 'license_plate', new_column_name='vehicle_registration')
            if 'purpose' in mileage_columns:
                op.alter_column('mileage', 'purpose', new_column_name='trip_purpose')
