#!/usr/bin/env python3
"""
Database initialization script for TimeTracker using raw SQL
This script creates tables and initial data without depending on Flask models
"""

import os
import sys
import time
from sqlalchemy import create_engine, text, inspect

def wait_for_database(url, max_attempts=30, delay=2):
    """Wait for database to be ready"""
    print(f"Waiting for database to be ready...")
    
    for attempt in range(max_attempts):
        try:
            engine = create_engine(url, pool_pre_ping=True)
            with engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            print("Database connection established successfully")
            return engine
        except Exception as e:
            print(f"Waiting for database... (attempt {attempt+1}/{max_attempts}): {e}")
            if attempt < max_attempts - 1:
                time.sleep(delay)
            else:
                print("Database not ready after waiting, exiting...")
                sys.exit(1)
    
    return None

def create_tables_sql(engine):
    """Create tables using raw SQL"""
    print("Creating tables using SQL...")
    
    # SQL statements to create tables
    create_tables_sql = """
    -- Create users table
    CREATE TABLE IF NOT EXISTS users (
        id SERIAL PRIMARY KEY,
        username VARCHAR(80) UNIQUE NOT NULL,
        role VARCHAR(20) DEFAULT 'user' NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
        last_login TIMESTAMP,
        is_active BOOLEAN DEFAULT true NOT NULL,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL
    );

    -- Create projects table
    CREATE TABLE IF NOT EXISTS projects (
        id SERIAL PRIMARY KEY,
        name VARCHAR(200) NOT NULL,
        client VARCHAR(200) NOT NULL,
        description TEXT,
        billable BOOLEAN DEFAULT true NOT NULL,
        hourly_rate NUMERIC(9, 2),
        billing_ref VARCHAR(100),
        status VARCHAR(20) DEFAULT 'active' NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );

    -- Create time_entries table
    CREATE TABLE IF NOT EXISTS time_entries (
        id SERIAL PRIMARY KEY,
        user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
        project_id INTEGER REFERENCES projects(id) ON DELETE CASCADE,
        task_id INTEGER,
        start_time TIMESTAMP NOT NULL,
        end_time TIMESTAMP,
        duration_seconds INTEGER,
        notes TEXT,
        tags VARCHAR(500),
        source VARCHAR(20) DEFAULT 'manual' NOT NULL,
        billable BOOLEAN DEFAULT true NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );

    -- Create invoices table
    CREATE TABLE IF NOT EXISTS invoices (
        id SERIAL PRIMARY KEY,
        invoice_number VARCHAR(50) UNIQUE NOT NULL,
        client_id INTEGER NOT NULL REFERENCES clients(id) ON DELETE CASCADE,
        project_id INTEGER REFERENCES projects(id) ON DELETE CASCADE,
        client_name VARCHAR(200) NOT NULL,
        client_email VARCHAR(200),
        client_address TEXT,
        issue_date DATE NOT NULL,
        due_date DATE NOT NULL,
        status VARCHAR(20) DEFAULT 'draft' NOT NULL,
        subtotal NUMERIC(10, 2) NOT NULL DEFAULT 0,
        tax_rate NUMERIC(5, 2) NOT NULL DEFAULT 0,
        tax_amount NUMERIC(10, 2) NOT NULL DEFAULT 0,
        total_amount NUMERIC(10, 2) NOT NULL DEFAULT 0,
        notes TEXT,
        terms TEXT,
        created_by INTEGER REFERENCES users(id) ON DELETE CASCADE,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );

    -- Create invoice_items table
    CREATE TABLE IF NOT EXISTS invoice_items (
        id SERIAL PRIMARY KEY,
        invoice_id INTEGER REFERENCES invoices(id) ON DELETE CASCADE,
        description VARCHAR(500) NOT NULL,
        quantity NUMERIC(10, 2) NOT NULL DEFAULT 1,
        unit_price NUMERIC(10, 2) NOT NULL,
        total_amount NUMERIC(10, 2) NOT NULL,
        time_entry_ids VARCHAR(500),
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );

    -- Create tasks table
    CREATE TABLE IF NOT EXISTS tasks (
        id SERIAL PRIMARY KEY,
        project_id INTEGER REFERENCES projects(id) ON DELETE CASCADE NOT NULL,
        name VARCHAR(200) NOT NULL,
        description TEXT,
        status VARCHAR(20) DEFAULT 'pending' NOT NULL,
        priority VARCHAR(20) DEFAULT 'medium' NOT NULL,
        assigned_to INTEGER REFERENCES users(id),
        created_by INTEGER REFERENCES users(id) NOT NULL,
        due_date DATE,
        estimated_hours NUMERIC(5,2),
        actual_hours NUMERIC(5,2),
        started_at TIMESTAMP,
        completed_at TIMESTAMP,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL
    );

    -- Create settings table
    CREATE TABLE IF NOT EXISTS settings (
        id SERIAL PRIMARY KEY,
        timezone VARCHAR(50) DEFAULT 'Europe/Rome' NOT NULL,
        currency VARCHAR(3) DEFAULT 'EUR' NOT NULL,
        rounding_minutes INTEGER DEFAULT 1 NOT NULL,
        single_active_timer BOOLEAN DEFAULT true NOT NULL,
        allow_self_register BOOLEAN DEFAULT true NOT NULL,
        idle_timeout_minutes INTEGER DEFAULT 30 NOT NULL,
        backup_retention_days INTEGER DEFAULT 30 NOT NULL,
        backup_time VARCHAR(5) DEFAULT '02:00' NOT NULL,
        export_delimiter VARCHAR(1) DEFAULT ',' NOT NULL,
        
        -- Company branding for invoices
        company_name VARCHAR(200) DEFAULT 'Your Company Name' NOT NULL,
        company_address TEXT DEFAULT 'Your Company Address' NOT NULL,
        company_email VARCHAR(200) DEFAULT 'info@yourcompany.com' NOT NULL,
        company_phone VARCHAR(50) DEFAULT '+1 (555) 123-4567' NOT NULL,
        company_website VARCHAR(200) DEFAULT 'www.yourcompany.com' NOT NULL,
        company_logo_filename VARCHAR(255) DEFAULT '' NOT NULL,
        company_tax_id VARCHAR(100) DEFAULT '' NOT NULL,
        company_bank_info TEXT DEFAULT '' NOT NULL,
        
        -- Invoice defaults
        invoice_prefix VARCHAR(10) DEFAULT 'INV' NOT NULL,
        invoice_start_number INTEGER DEFAULT 1000 NOT NULL,
        invoice_terms TEXT DEFAULT 'Payment is due within 30 days of invoice date.' NOT NULL,
        invoice_notes TEXT DEFAULT 'Thank you for your business!' NOT NULL,
        
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL
    );
    """
    
    try:
        with engine.connect() as conn:
            # Execute the SQL statements
            conn.execute(text(create_tables_sql))
            conn.commit()
        
        print("✓ Tables created successfully")
        return True
        
    except Exception as e:
        print(f"✗ Error creating tables: {e}")
        return False

def create_indexes(engine):
    """Create indexes for better performance"""
    print("Creating indexes...")
    
    indexes_sql = """
    CREATE INDEX IF NOT EXISTS idx_time_entries_user_id ON time_entries(user_id);
    CREATE INDEX IF NOT EXISTS idx_time_entries_project_id ON time_entries(project_id);
    CREATE INDEX IF NOT EXISTS idx_time_entries_start_time ON time_entries(start_time);
    CREATE INDEX IF NOT EXISTS idx_invoices_client_id ON invoices(client_id);
    """
    
    try:
        with engine.connect() as conn:
            conn.execute(text(indexes_sql))
            conn.commit()
        
        print("✓ Indexes created successfully")
        return True
        
    except Exception as e:
        print(f"✗ Error creating indexes: {e}")
        return False

def create_triggers(engine):
    """Create triggers for automatic timestamp updates"""
    print("Creating triggers...")
    
    # Execute each statement separately to avoid semicolon splitting issues
    try:
        with engine.connect() as conn:
            # Create function
            conn.execute(text("""
                CREATE OR REPLACE FUNCTION update_updated_at_column()
                RETURNS TRIGGER AS $$
                BEGIN
                    NEW.updated_at = CURRENT_TIMESTAMP;
                    RETURN NEW;
                END;
                $$ language 'plpgsql';
            """))
            
            # Create triggers
            conn.execute(text("""
                DROP TRIGGER IF EXISTS update_users_updated_at ON users;
                CREATE TRIGGER update_users_updated_at BEFORE UPDATE ON users FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
            """))
            
            conn.execute(text("""
                DROP TRIGGER IF EXISTS update_projects_updated_at ON projects;
                CREATE TRIGGER update_projects_updated_at BEFORE UPDATE ON projects FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
            """))
            
            conn.execute(text("""
                DROP TRIGGER IF EXISTS update_time_entries_updated_at ON time_entries;
                CREATE TRIGGER update_time_entries_updated_at BEFORE UPDATE ON time_entries FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
            """))
            
            conn.execute(text("""
                DROP TRIGGER IF EXISTS update_settings_updated_at ON settings;
                CREATE TRIGGER update_settings_updated_at BEFORE UPDATE ON settings FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
            """))
            
            conn.execute(text("""
                DROP TRIGGER IF EXISTS update_tasks_updated_at ON tasks;
                CREATE TRIGGER update_tasks_updated_at BEFORE UPDATE ON tasks FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
            """))
            
            conn.commit()
        
        print("✓ Triggers created successfully")
        return True
        
    except Exception as e:
        print(f"✗ Error creating triggers: {e}")
        return False

def insert_initial_data(engine):
    """Insert initial data"""
    print("Inserting initial data...")
    
    try:
        # Check if initial data has already been seeded
        import sys
        import os
        sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        
        from app.utils.installation import InstallationConfig
        installation_config = InstallationConfig()
        
        # Get admin username from environment (first username, stripped)
        admin_username = os.getenv('ADMIN_USERNAMES', 'admin').split(',')[0].strip()
        
        # Base SQL for admin user and settings (always run)
        base_sql = f"""
        -- Insert default admin user idempotently
        INSERT INTO users (username, role, is_active) 
        SELECT '{admin_username}', 'admin', true
        WHERE NOT EXISTS (
            SELECT 1 FROM users WHERE username = '{admin_username}'
        );

        -- Insert default settings only if none exist
        INSERT INTO settings (
            timezone, currency, rounding_minutes, single_active_timer, allow_self_register, 
            idle_timeout_minutes, backup_retention_days, backup_time, export_delimiter, 
            company_name, company_address, company_email, company_phone, company_website, 
            company_logo_filename, company_tax_id, company_bank_info, invoice_prefix, 
            invoice_start_number, invoice_terms, invoice_notes
        ) 
        SELECT 'Europe/Rome', 'EUR', 1, true, true, 30, 30, '02:00', ',', 
               'Your Company Name', 'Your Company Address', 'info@yourcompany.com', 
               '+1 (555) 123-4567', 'www.yourcompany.com', '', '', '', 'INV', 1000, 
               'Payment is due within 30 days of invoice date.', 'Thank you for your business!'
        WHERE NOT EXISTS (
            SELECT 1 FROM settings
        );
        """
        
        with engine.connect() as conn:
            # Always execute base SQL (admin user and settings)
            conn.execute(text(base_sql))
            conn.commit()
            
            # Only insert default client and project on fresh installations
            if not installation_config.is_initial_data_seeded():
                print("Fresh installation detected, checking for existing projects...")
                
                # Check if there are any existing projects
                result = conn.execute(text("SELECT COUNT(*) FROM projects;"))
                project_count = result.scalar()
                
                if project_count == 0:
                    print("No projects found, creating default client and project...")
                    
                    default_data_sql = """
                    -- Ensure default client exists
                    INSERT INTO clients (name, status)
                    SELECT 'Default Client', 'active'
                    WHERE NOT EXISTS (
                        SELECT 1 FROM clients WHERE name = 'Default Client'
                    );

                    -- Insert default project idempotently and link to default client
                    INSERT INTO projects (name, client, description, billable, status) 
                    SELECT 'General', 'Default Client', 'Default project for general tasks', true, 'active'
                    WHERE NOT EXISTS (
                        SELECT 1 FROM projects WHERE name = 'General'
                    );
                    """
                    
                    conn.execute(text(default_data_sql))
                    conn.commit()
                    print("✓ Default client and project created")
                    
                    # Mark initial data as seeded
                    installation_config.mark_initial_data_seeded()
                    print("✓ Marked initial data as seeded")
                else:
                    print(f"Projects already exist ({project_count} found), marking initial data as seeded")
                    installation_config.mark_initial_data_seeded()
            else:
                print("Initial data already seeded previously, skipping default client/project creation")
    
    except Exception as e:
        print(f"Error inserting initial data: {e}")
        import traceback
        print(f"Traceback: {traceback.format_exc()}")
        return False
    
    print("Initial data inserted successfully")
    return True

def verify_tables(engine):
    """Verify that all required tables exist"""
    print("Verifying tables...")
    
    try:
        inspector = inspect(engine)
        existing_tables = inspector.get_table_names()
        required_tables = ['users', 'projects', 'time_entries', 'tasks', 'settings', 'invoices', 'invoice_items']
        
        missing_tables = [table for table in required_tables if table not in existing_tables]
        
        if missing_tables:
            print(f"✗ Missing tables: {missing_tables}")
            return False
        else:
            print("✓ All required tables exist")
            return True
            
    except Exception as e:
        print(f"✗ Error verifying tables: {e}")
        return False

def main():
    """Main function"""
    url = os.getenv("DATABASE_URL", "")
    
    if not url.startswith("postgresql"):
        print("No PostgreSQL database configured, skipping initialization")
        return
    
    print(f"Database URL: {url}")
    
    # Wait for database to be ready
    engine = wait_for_database(url)
    
    # Check if database is initialized
    if verify_tables(engine):
        print("Database already initialized, no action needed")
        return
    
    print("Database not initialized, starting initialization...")
    
    # Create tables
    if not create_tables_sql(engine):
        print("Failed to create tables")
        sys.exit(1)
    
    # Create indexes
    if not create_indexes(engine):
        print("Failed to create indexes")
        sys.exit(1)
    
    # Create triggers
    if not create_triggers(engine):
        print("Failed to create triggers")
        sys.exit(1)
    
    # Insert initial data
    if not insert_initial_data(engine):
        print("Failed to insert initial data")
        sys.exit(1)
    
    # Verify everything was created
    if verify_tables(engine):
        print("✓ Database initialization completed successfully")
    else:
        print("✗ Database initialization failed - tables still missing")
        sys.exit(1)

if __name__ == "__main__":
    main()
