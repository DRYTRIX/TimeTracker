-- Add allow_analytics column to settings table
-- This script adds the missing column that the application expects

-- Check if column already exists
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM information_schema.columns
        WHERE table_name = 'settings'
        AND column_name = 'allow_analytics'
    ) THEN
        -- Add the new column
        ALTER TABLE settings ADD COLUMN allow_analytics BOOLEAN DEFAULT TRUE;
        RAISE NOTICE 'Added allow_analytics column to settings table';
    ELSE
        RAISE NOTICE 'allow_analytics column already exists in settings table';
    END IF;
END $$;

-- Verify the column was added
SELECT column_name, data_type, is_nullable, column_default
FROM information_schema.columns
WHERE table_name = 'settings'
AND column_name = 'allow_analytics';
