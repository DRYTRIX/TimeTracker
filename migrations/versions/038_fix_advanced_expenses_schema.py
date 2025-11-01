"""Fix advanced expenses schema

Revision ID: 038_fix_expenses_schema
Revises: 037_advanced_expenses
Create Date: 2025-10-30 15:05:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '038_fix_expenses_schema'
down_revision = '037_advanced_expenses'
branch_labels = None
depends_on = None


def upgrade():
    # Fix mileage table - rename columns and add missing ones
    op.alter_column('mileage', 'trip_purpose', new_column_name='purpose', existing_type=sa.Text(), existing_nullable=False)
    op.alter_column('mileage', 'vehicle_registration', new_column_name='license_plate', existing_type=sa.String(20), existing_nullable=True)
    op.alter_column('mileage', 'total_amount', new_column_name='calculated_amount', existing_type=sa.Numeric(10, 2), existing_nullable=True)
    
    # Add missing columns to mileage
    op.add_column('mileage', sa.Column('description', sa.Text(), nullable=True))
    op.add_column('mileage', sa.Column('start_odometer', sa.Numeric(precision=10, scale=2), nullable=True))
    op.add_column('mileage', sa.Column('end_odometer', sa.Numeric(precision=10, scale=2), nullable=True))
    op.add_column('mileage', sa.Column('distance_miles', sa.Numeric(precision=10, scale=2), nullable=True))
    op.add_column('mileage', sa.Column('rate_per_mile', sa.Numeric(precision=10, scale=4), nullable=True))
    op.add_column('mileage', sa.Column('vehicle_description', sa.String(length=200), nullable=True))
    op.add_column('mileage', sa.Column('is_round_trip', sa.Boolean(), nullable=False, server_default='false'))
    op.add_column('mileage', sa.Column('reimbursed', sa.Boolean(), nullable=False, server_default='false'))
    op.add_column('mileage', sa.Column('reimbursed_at', sa.DateTime(), nullable=True))
    op.add_column('mileage', sa.Column('currency_code', sa.String(length=3), nullable=False, server_default='EUR'))
    
    # Make rate_per_km NOT NULL (it's required)
    op.alter_column('mileage', 'rate_per_km', nullable=False, server_default='0.30')
    
    # Fix per_diem_rates table - rename columns
    op.alter_column('per_diem_rates', 'location', new_column_name='city', existing_type=sa.String(255), existing_nullable=True)
    op.alter_column('per_diem_rates', 'valid_from', new_column_name='effective_from', existing_type=sa.Date(), existing_nullable=False)
    op.alter_column('per_diem_rates', 'valid_to', new_column_name='effective_to', existing_type=sa.Date(), existing_nullable=True)
    
    # Add missing columns to per_diem_rates
    op.add_column('per_diem_rates', sa.Column('full_day_rate', sa.Numeric(precision=10, scale=2), nullable=False, server_default='0'))
    op.add_column('per_diem_rates', sa.Column('half_day_rate', sa.Numeric(precision=10, scale=2), nullable=False, server_default='0'))
    op.add_column('per_diem_rates', sa.Column('breakfast_rate', sa.Numeric(precision=10, scale=2), nullable=True))
    op.add_column('per_diem_rates', sa.Column('lunch_rate', sa.Numeric(precision=10, scale=2), nullable=True))
    op.add_column('per_diem_rates', sa.Column('dinner_rate', sa.Numeric(precision=10, scale=2), nullable=True))
    op.add_column('per_diem_rates', sa.Column('incidental_rate', sa.Numeric(precision=10, scale=2), nullable=True))
    op.add_column('per_diem_rates', sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')))
    
    # Rename country_code to country
    op.alter_column('per_diem_rates', 'country_code', new_column_name='country', existing_type=sa.String(2), existing_nullable=False)
    
    # Drop old rate_per_day column after copying to full_day_rate
    op.execute("UPDATE per_diem_rates SET full_day_rate = rate_per_day, half_day_rate = rate_per_day * 0.5")
    op.drop_column('per_diem_rates', 'rate_per_day')
    op.drop_column('per_diem_rates', 'breakfast_deduction')
    op.drop_column('per_diem_rates', 'lunch_deduction')
    op.drop_column('per_diem_rates', 'dinner_deduction')
    
    # Fix per_diems table - rename columns
    op.alter_column('per_diems', 'trip_start_date', new_column_name='start_date', existing_type=sa.Date(), existing_nullable=False)
    op.alter_column('per_diems', 'trip_end_date', new_column_name='end_date', existing_type=sa.Date(), existing_nullable=False)
    op.alter_column('per_diems', 'destination_country', new_column_name='country', existing_type=sa.String(2), existing_nullable=False)
    op.alter_column('per_diems', 'destination_location', new_column_name='city', existing_type=sa.String(255), existing_nullable=True)
    op.alter_column('per_diems', 'number_of_days', new_column_name='full_days', existing_type=sa.Integer(), existing_nullable=False)
    op.alter_column('per_diems', 'total_amount', new_column_name='calculated_amount', existing_type=sa.Numeric(10, 2), existing_nullable=True)
    
    # Add missing columns to per_diems
    op.add_column('per_diems', sa.Column('trip_purpose', sa.String(length=255), nullable=False, server_default='Business trip'))
    op.add_column('per_diems', sa.Column('description', sa.Text(), nullable=True))
    op.add_column('per_diems', sa.Column('departure_time', sa.Time(), nullable=True))
    op.add_column('per_diems', sa.Column('return_time', sa.Time(), nullable=True))
    op.add_column('per_diems', sa.Column('half_days', sa.Integer(), nullable=False, server_default='0'))
    op.add_column('per_diems', sa.Column('total_days', sa.Numeric(precision=5, scale=2), nullable=False, server_default='0'))
    op.add_column('per_diems', sa.Column('full_day_rate', sa.Numeric(precision=10, scale=2), nullable=False, server_default='0'))
    op.add_column('per_diems', sa.Column('half_day_rate', sa.Numeric(precision=10, scale=2), nullable=False, server_default='0'))
    op.add_column('per_diems', sa.Column('breakfast_deduction', sa.Numeric(precision=10, scale=2), nullable=False, server_default='0'))
    op.add_column('per_diems', sa.Column('lunch_deduction', sa.Numeric(precision=10, scale=2), nullable=False, server_default='0'))
    op.add_column('per_diems', sa.Column('dinner_deduction', sa.Numeric(precision=10, scale=2), nullable=False, server_default='0'))
    op.add_column('per_diems', sa.Column('reimbursed', sa.Boolean(), nullable=False, server_default='false'))
    op.add_column('per_diems', sa.Column('reimbursed_at', sa.DateTime(), nullable=True))
    op.add_column('per_diems', sa.Column('approval_notes', sa.Text(), nullable=True))


def downgrade():
    # Revert per_diems changes
    op.drop_column('per_diems', 'approval_notes')
    op.drop_column('per_diems', 'reimbursed_at')
    op.drop_column('per_diems', 'reimbursed')
    op.drop_column('per_diems', 'dinner_deduction')
    op.drop_column('per_diems', 'lunch_deduction')
    op.drop_column('per_diems', 'breakfast_deduction')
    op.drop_column('per_diems', 'half_day_rate')
    op.drop_column('per_diems', 'full_day_rate')
    op.drop_column('per_diems', 'total_days')
    op.drop_column('per_diems', 'half_days')
    op.drop_column('per_diems', 'return_time')
    op.drop_column('per_diems', 'departure_time')
    op.drop_column('per_diems', 'description')
    op.drop_column('per_diems', 'trip_purpose')
    
    op.alter_column('per_diems', 'calculated_amount', new_column_name='total_amount')
    op.alter_column('per_diems', 'full_days', new_column_name='number_of_days')
    op.alter_column('per_diems', 'city', new_column_name='destination_location')
    op.alter_column('per_diems', 'country', new_column_name='destination_country')
    op.alter_column('per_diems', 'end_date', new_column_name='trip_end_date')
    op.alter_column('per_diems', 'start_date', new_column_name='trip_start_date')
    
    # Revert per_diem_rates changes
    op.add_column('per_diem_rates', sa.Column('rate_per_day', sa.Numeric(precision=10, scale=2), nullable=False, server_default='0'))
    op.add_column('per_diem_rates', sa.Column('breakfast_deduction', sa.Numeric(precision=10, scale=2), nullable=True))
    op.add_column('per_diem_rates', sa.Column('lunch_deduction', sa.Numeric(precision=10, scale=2), nullable=True))
    op.add_column('per_diem_rates', sa.Column('dinner_deduction', sa.Numeric(precision=10, scale=2), nullable=True))
    op.execute("UPDATE per_diem_rates SET rate_per_day = full_day_rate")
    op.drop_column('per_diem_rates', 'updated_at')
    op.drop_column('per_diem_rates', 'incidental_rate')
    op.drop_column('per_diem_rates', 'dinner_rate')
    op.drop_column('per_diem_rates', 'lunch_rate')
    op.drop_column('per_diem_rates', 'breakfast_rate')
    op.drop_column('per_diem_rates', 'half_day_rate')
    op.drop_column('per_diem_rates', 'full_day_rate')
    
    op.alter_column('per_diem_rates', 'country', new_column_name='country_code')
    op.alter_column('per_diem_rates', 'effective_to', new_column_name='valid_to')
    op.alter_column('per_diem_rates', 'effective_from', new_column_name='valid_from')
    op.alter_column('per_diem_rates', 'city', new_column_name='location')
    
    # Revert mileage changes
    op.drop_column('mileage', 'currency_code')
    op.drop_column('mileage', 'reimbursed_at')
    op.drop_column('mileage', 'reimbursed')
    op.drop_column('mileage', 'is_round_trip')
    op.drop_column('mileage', 'vehicle_description')
    op.drop_column('mileage', 'rate_per_mile')
    op.drop_column('mileage', 'distance_miles')
    op.drop_column('mileage', 'end_odometer')
    op.drop_column('mileage', 'start_odometer')
    op.drop_column('mileage', 'description')
    
    op.alter_column('mileage', 'rate_per_km', nullable=True)
    op.alter_column('mileage', 'calculated_amount', new_column_name='total_amount')
    op.alter_column('mileage', 'license_plate', new_column_name='vehicle_registration')
    op.alter_column('mileage', 'purpose', new_column_name='trip_purpose')

