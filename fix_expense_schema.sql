-- Fix Advanced Expense Management Schema
-- Run this manually to fix the column name mismatches

-- Fix mileage table
ALTER TABLE mileage RENAME COLUMN trip_purpose TO purpose;
ALTER TABLE mileage RENAME COLUMN vehicle_registration TO license_plate;
ALTER TABLE mileage RENAME COLUMN total_amount TO calculated_amount;

-- Add missing columns to mileage
ALTER TABLE mileage ADD COLUMN IF NOT EXISTS description TEXT;
ALTER TABLE mileage ADD COLUMN IF NOT EXISTS start_odometer NUMERIC(10, 2);
ALTER TABLE mileage ADD COLUMN IF NOT EXISTS end_odometer NUMERIC(10, 2);
ALTER TABLE mileage ADD COLUMN IF NOT EXISTS distance_miles NUMERIC(10, 2);
ALTER TABLE mileage ADD COLUMN IF NOT EXISTS rate_per_mile NUMERIC(10, 4);
ALTER TABLE mileage ADD COLUMN IF NOT EXISTS vehicle_description VARCHAR(200);
ALTER TABLE mileage ADD COLUMN IF NOT EXISTS is_round_trip BOOLEAN NOT NULL DEFAULT false;
ALTER TABLE mileage ADD COLUMN IF NOT EXISTS reimbursed BOOLEAN NOT NULL DEFAULT false;
ALTER TABLE mileage ADD COLUMN IF NOT EXISTS reimbursed_at TIMESTAMP;
ALTER TABLE mileage ADD COLUMN IF NOT EXISTS currency_code VARCHAR(3) NOT NULL DEFAULT 'EUR';

-- Make rate_per_km NOT NULL
ALTER TABLE mileage ALTER COLUMN rate_per_km SET NOT NULL;
ALTER TABLE mileage ALTER COLUMN rate_per_km SET DEFAULT 0.30;

-- Fix per_diem_rates table
ALTER TABLE per_diem_rates RENAME COLUMN location TO city;
ALTER TABLE per_diem_rates RENAME COLUMN valid_from TO effective_from;
ALTER TABLE per_diem_rates RENAME COLUMN valid_to TO effective_to;
ALTER TABLE per_diem_rates RENAME COLUMN country_code TO country;

-- Add missing columns to per_diem_rates
ALTER TABLE per_diem_rates ADD COLUMN IF NOT EXISTS full_day_rate NUMERIC(10, 2) NOT NULL DEFAULT 0;
ALTER TABLE per_diem_rates ADD COLUMN IF NOT EXISTS half_day_rate NUMERIC(10, 2) NOT NULL DEFAULT 0;
ALTER TABLE per_diem_rates ADD COLUMN IF NOT EXISTS breakfast_rate NUMERIC(10, 2);
ALTER TABLE per_diem_rates ADD COLUMN IF NOT EXISTS lunch_rate NUMERIC(10, 2);
ALTER TABLE per_diem_rates ADD COLUMN IF NOT EXISTS dinner_rate NUMERIC(10, 2);
ALTER TABLE per_diem_rates ADD COLUMN IF NOT EXISTS incidental_rate NUMERIC(10, 2);
ALTER TABLE per_diem_rates ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP;

-- Copy rate_per_day to full_day_rate and calculate half_day_rate
UPDATE per_diem_rates SET full_day_rate = rate_per_day, half_day_rate = rate_per_day * 0.5 WHERE full_day_rate = 0;

-- Drop old columns from per_diem_rates
ALTER TABLE per_diem_rates DROP COLUMN IF EXISTS rate_per_day;
ALTER TABLE per_diem_rates DROP COLUMN IF EXISTS breakfast_deduction;
ALTER TABLE per_diem_rates DROP COLUMN IF EXISTS lunch_deduction;
ALTER TABLE per_diem_rates DROP COLUMN IF EXISTS dinner_deduction;

-- Fix per_diems table
ALTER TABLE per_diems RENAME COLUMN trip_start_date TO start_date;
ALTER TABLE per_diems RENAME COLUMN trip_end_date TO end_date;
ALTER TABLE per_diems RENAME COLUMN destination_country TO country;
ALTER TABLE per_diems RENAME COLUMN destination_location TO city;
ALTER TABLE per_diems RENAME COLUMN number_of_days TO full_days;
ALTER TABLE per_diems RENAME COLUMN total_amount TO calculated_amount;

-- Add missing columns to per_diems
ALTER TABLE per_diems ADD COLUMN IF NOT EXISTS trip_purpose VARCHAR(255) NOT NULL DEFAULT 'Business trip';
ALTER TABLE per_diems ADD COLUMN IF NOT EXISTS description TEXT;
ALTER TABLE per_diems ADD COLUMN IF NOT EXISTS departure_time TIME;
ALTER TABLE per_diems ADD COLUMN IF NOT EXISTS return_time TIME;
ALTER TABLE per_diems ADD COLUMN IF NOT EXISTS half_days INTEGER NOT NULL DEFAULT 0;
ALTER TABLE per_diems ADD COLUMN IF NOT EXISTS total_days NUMERIC(5, 2) NOT NULL DEFAULT 0;
ALTER TABLE per_diems ADD COLUMN IF NOT EXISTS full_day_rate NUMERIC(10, 2) NOT NULL DEFAULT 0;
ALTER TABLE per_diems ADD COLUMN IF NOT EXISTS half_day_rate NUMERIC(10, 2) NOT NULL DEFAULT 0;
ALTER TABLE per_diems ADD COLUMN IF NOT EXISTS breakfast_deduction NUMERIC(10, 2) NOT NULL DEFAULT 0;
ALTER TABLE per_diems ADD COLUMN IF NOT EXISTS lunch_deduction NUMERIC(10, 2) NOT NULL DEFAULT 0;
ALTER TABLE per_diems ADD COLUMN IF NOT EXISTS dinner_deduction NUMERIC(10, 2) NOT NULL DEFAULT 0;
ALTER TABLE per_diems ADD COLUMN IF NOT EXISTS reimbursed BOOLEAN NOT NULL DEFAULT false;
ALTER TABLE per_diems ADD COLUMN IF NOT EXISTS reimbursed_at TIMESTAMP;
ALTER TABLE per_diems ADD COLUMN IF NOT EXISTS approval_notes TEXT;

-- Mark migration as applied (optional)
-- UPDATE alembic_version SET version_num = '038_fix_expenses_schema';

SELECT 'Schema fixed successfully!' AS result;

