-- Fix script for settings table column issues
-- Run this in your PostgreSQL database to resolve the schema mismatch

-- Step 1: Rename the old column to the new name
ALTER TABLE settings RENAME COLUMN company_logo_path TO company_logo_filename;

-- Step 2: Add any missing columns (these will be skipped if they already exist)
DO $$
BEGIN
    -- Company branding columns
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'settings' AND column_name = 'company_name') THEN
        ALTER TABLE settings ADD COLUMN company_name VARCHAR(200) DEFAULT 'Your Company Name' NOT NULL;
    END IF;
    
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'settings' AND column_name = 'company_address') THEN
        ALTER TABLE settings ADD COLUMN company_address TEXT DEFAULT 'Your Company Address' NOT NULL;
    END IF;
    
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'settings' AND column_name = 'company_email') THEN
        ALTER TABLE settings ADD COLUMN company_email VARCHAR(200) DEFAULT 'info@yourcompany.com' NOT NULL;
    END IF;
    
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'settings' AND column_name = 'company_phone') THEN
        ALTER TABLE settings ADD COLUMN company_phone VARCHAR(50) DEFAULT '+1 (555) 123-4567' NOT NULL;
    END IF;
    
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'settings' AND column_name = 'company_website') THEN
        ALTER TABLE settings ADD COLUMN company_website VARCHAR(200) DEFAULT 'www.yourcompany.com' NOT NULL;
    END IF;
    
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'settings' AND column_name = 'company_tax_id') THEN
        ALTER TABLE settings ADD COLUMN company_tax_id VARCHAR(100) DEFAULT '' NOT NULL;
    END IF;
    
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'settings' AND column_name = 'company_bank_info') THEN
        ALTER TABLE settings ADD COLUMN company_bank_info TEXT DEFAULT '' NOT NULL;
    END IF;
    
    -- Invoice default columns
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'settings' AND column_name = 'invoice_prefix') THEN
        ALTER TABLE settings ADD COLUMN invoice_prefix VARCHAR(50) DEFAULT 'INV' NOT NULL;
    END IF;
    
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'settings' AND column_name = 'invoice_number_pattern') THEN
        ALTER TABLE settings ADD COLUMN invoice_number_pattern VARCHAR(120) DEFAULT '{PREFIX}-{YYYY}{MM}{DD}-{SEQ}' NOT NULL;
    END IF;
    
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'settings' AND column_name = 'invoice_start_number') THEN
        ALTER TABLE settings ADD COLUMN invoice_start_number INTEGER DEFAULT 1000 NOT NULL;
    END IF;
    
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'settings' AND column_name = 'invoice_terms') THEN
        ALTER TABLE settings ADD COLUMN invoice_terms TEXT DEFAULT 'Payment is due within 30 days of invoice date.' NOT NULL;
    END IF;
    
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'settings' AND column_name = 'invoice_notes') THEN
        ALTER TABLE settings ADD COLUMN invoice_notes TEXT DEFAULT 'Thank you for your business!' NOT NULL;
    END IF;
END $$;

-- Step 3: Update existing settings with default values
UPDATE settings SET 
    company_name = COALESCE(company_name, 'Your Company Name'),
    company_address = COALESCE(company_address, 'Your Company Address'),
    company_email = COALESCE(company_email, 'info@yourcompany.com'),
    company_phone = COALESCE(company_phone, '+1 (555) 123-4567'),
    company_website = COALESCE(company_website, 'www.yourcompany.com'),
    company_logo_filename = COALESCE(company_logo_filename, ''),
    company_tax_id = COALESCE(company_tax_id, ''),
    company_bank_info = COALESCE(company_bank_info, ''),
    invoice_prefix = COALESCE(invoice_prefix, 'INV'),
    invoice_number_pattern = COALESCE(invoice_number_pattern, '{PREFIX}-{YYYY}{MM}{DD}-{SEQ}'),
    invoice_start_number = COALESCE(invoice_start_number, 1000),
    invoice_terms = COALESCE(invoice_terms, 'Payment is due within 30 days of invoice date.'),
    invoice_notes = COALESCE(invoice_notes, 'Thank you for your business!')
WHERE id = (SELECT id FROM settings LIMIT 1);

-- Step 4: Verify the fix
SELECT 'Settings table fixed successfully!' as status;
SELECT column_name FROM information_schema.columns WHERE table_name = 'settings' ORDER BY column_name;
