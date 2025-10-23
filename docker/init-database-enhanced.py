#!/usr/bin/env python3
"""
Enhanced Database initialization script for TimeTracker
This script ensures all tables are correctly created with proper schema and handles migrations
"""

import os
import sys
import time
import traceback
from sqlalchemy import create_engine, text, inspect, MetaData
from sqlalchemy.exc import OperationalError, ProgrammingError

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

def get_required_schema():
    """Define the complete required database schema"""
    return {
        'clients': {
            'columns': [
                'id SERIAL PRIMARY KEY',
                'name VARCHAR(200) UNIQUE NOT NULL',
                'description TEXT',
                'contact_person VARCHAR(200)',
                'email VARCHAR(200)',
                'phone VARCHAR(50)',
                'address TEXT',
                'default_hourly_rate NUMERIC(9, 2)',
                'status VARCHAR(20) DEFAULT \'active\' NOT NULL',
                'created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL',
                'updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL'
            ],
            'indexes': [
                'CREATE INDEX IF NOT EXISTS idx_clients_name ON clients(name)'
            ]
        },
        'users': {
            'columns': [
                'id SERIAL PRIMARY KEY',
                'username VARCHAR(80) UNIQUE NOT NULL',
                'role VARCHAR(20) DEFAULT \'user\' NOT NULL',
                'created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL',
                'last_login TIMESTAMP',
                'is_active BOOLEAN DEFAULT true NOT NULL',
                'updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL'
            ],
            'indexes': [
                'CREATE INDEX IF NOT EXISTS idx_users_username ON users(username)',
                'CREATE INDEX IF NOT EXISTS idx_users_role ON users(role)'
            ]
        },
        'projects': {
            'columns': [
                'id SERIAL PRIMARY KEY',
                'name VARCHAR(200) NOT NULL',
                'client_id INTEGER',
                'description TEXT',
                'billable BOOLEAN DEFAULT true NOT NULL',
                'hourly_rate NUMERIC(9, 2)',
                'billing_ref VARCHAR(100)',
                'status VARCHAR(20) DEFAULT \'active\' NOT NULL',
                'created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP',
                'updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP'
            ],
            'indexes': [
                'CREATE INDEX IF NOT EXISTS idx_projects_client_id ON projects(client_id)',
                'CREATE INDEX IF NOT EXISTS idx_projects_status ON projects(status)'
            ]
        },
        'tasks': {
            'columns': [
                'id SERIAL PRIMARY KEY',
                'project_id INTEGER REFERENCES projects(id) ON DELETE CASCADE NOT NULL',
                'name VARCHAR(200) NOT NULL',
                'description TEXT',
                'status VARCHAR(20) DEFAULT \'pending\' NOT NULL',
                'priority VARCHAR(20) DEFAULT \'medium\' NOT NULL',
                'assigned_to INTEGER REFERENCES users(id)',
                'created_by INTEGER REFERENCES users(id) NOT NULL',
                'due_date DATE',
                'estimated_hours NUMERIC(5,2)',
                'actual_hours NUMERIC(5,2)',
                'started_at TIMESTAMP',
                'completed_at TIMESTAMP',
                'created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL',
                'updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL'
            ],
            'indexes': [
                'CREATE INDEX IF NOT EXISTS idx_tasks_project_id ON tasks(project_id)',
                'CREATE INDEX IF NOT EXISTS idx_tasks_status ON tasks(status)',
                'CREATE INDEX IF NOT EXISTS idx_tasks_assigned_to ON tasks(assigned_to)',
                'CREATE INDEX IF NOT EXISTS idx_tasks_due_date ON tasks(due_date)'
            ]
        },
        'time_entries': {
            'columns': [
                'id SERIAL PRIMARY KEY',
                'user_id INTEGER REFERENCES users(id) ON DELETE CASCADE',
                'project_id INTEGER REFERENCES projects(id) ON DELETE CASCADE',
                'task_id INTEGER REFERENCES tasks(id) ON DELETE SET NULL',
                'start_time TIMESTAMP NOT NULL',
                'end_time TIMESTAMP',
                'duration_seconds INTEGER',
                'notes TEXT',
                'tags VARCHAR(500)',
                'source VARCHAR(20) DEFAULT \'manual\' NOT NULL',
                'billable BOOLEAN DEFAULT true NOT NULL',
                'created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP',
                'updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP'
            ],
            'indexes': [
                'CREATE INDEX IF NOT EXISTS idx_time_entries_user_id ON time_entries(user_id)',
                'CREATE INDEX IF NOT EXISTS idx_time_entries_project_id ON time_entries(project_id)',
                'CREATE INDEX IF NOT EXISTS idx_time_entries_task_id ON time_entries(task_id)',
                'CREATE INDEX IF NOT EXISTS idx_time_entries_start_time ON time_entries(start_time)',
                'CREATE INDEX IF NOT EXISTS idx_time_entries_billable ON time_entries(billable)'
            ]
        },
        'settings': {
            'columns': [
                'id SERIAL PRIMARY KEY',
                'timezone VARCHAR(50) DEFAULT \'Europe/Rome\' NOT NULL',
                'currency VARCHAR(3) DEFAULT \'EUR\' NOT NULL',
                'rounding_minutes INTEGER DEFAULT 1 NOT NULL',
                'single_active_timer BOOLEAN DEFAULT true NOT NULL',
                'allow_self_register BOOLEAN DEFAULT true NOT NULL',
                'idle_timeout_minutes INTEGER DEFAULT 30 NOT NULL',
                'backup_retention_days INTEGER DEFAULT 30 NOT NULL',
                'backup_time VARCHAR(5) DEFAULT \'02:00\' NOT NULL',
                'export_delimiter VARCHAR(1) DEFAULT \',\' NOT NULL',
                'allow_analytics BOOLEAN DEFAULT true NOT NULL',
                
                # Company branding for invoices
                'company_name VARCHAR(200) DEFAULT \'Your Company Name\' NOT NULL',
                'company_address TEXT DEFAULT \'Your Company Address\' NOT NULL',
                'company_email VARCHAR(200) DEFAULT \'info@yourcompany.com\' NOT NULL',
                'company_phone VARCHAR(50) DEFAULT \'+1 (555) 123-4567\' NOT NULL',
                'company_website VARCHAR(200) DEFAULT \'www.yourcompany.com\' NOT NULL',
                'company_logo_filename VARCHAR(255) DEFAULT \'\' NOT NULL',
                'company_tax_id VARCHAR(100) DEFAULT \'\' NOT NULL',
                'company_bank_info TEXT DEFAULT \'\' NOT NULL',
                
                # Invoice defaults
                'invoice_prefix VARCHAR(10) DEFAULT \'INV\' NOT NULL',
                'invoice_start_number INTEGER DEFAULT 1000 NOT NULL',
                'invoice_terms TEXT DEFAULT \'Payment is due within 30 days of invoice date.\' NOT NULL',
                'invoice_notes TEXT DEFAULT \'Thank you for your business!\' NOT NULL',
                
                'created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL',
                'updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL'
            ],
            'indexes': []
        },
        'invoices': {
            'columns': [
                'id SERIAL PRIMARY KEY',
                'invoice_number VARCHAR(50) UNIQUE NOT NULL',
                'client_id INTEGER NOT NULL',
                'project_id INTEGER REFERENCES projects(id) ON DELETE CASCADE',
                'client_name VARCHAR(200) NOT NULL',
                'client_email VARCHAR(200)',
                'client_address TEXT',
                'issue_date DATE NOT NULL',
                'due_date DATE NOT NULL',
                'status VARCHAR(20) DEFAULT \'draft\' NOT NULL',
                'subtotal NUMERIC(10, 2) NOT NULL DEFAULT 0',
                'tax_rate NUMERIC(5, 2) NOT NULL DEFAULT 0',
                'tax_amount NUMERIC(10, 2) NOT NULL DEFAULT 0',
                'total_amount NUMERIC(10, 2) NOT NULL DEFAULT 0',
                'notes TEXT',
                'terms TEXT',
                'created_by INTEGER REFERENCES users(id) ON DELETE CASCADE',
                'created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP',
                'updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP'
            ],
            'indexes': [
                'CREATE INDEX IF NOT EXISTS idx_invoices_project_id ON invoices(project_id)',
                'CREATE INDEX IF NOT EXISTS idx_invoices_client_id ON invoices(client_id)',
                'CREATE INDEX IF NOT EXISTS idx_invoices_status ON invoices(status)',
                'CREATE INDEX IF NOT EXISTS idx_invoices_issue_date ON invoices(issue_date)'
            ]
        },
        'invoice_items': {
            'columns': [
                'id SERIAL PRIMARY KEY',
                'invoice_id INTEGER REFERENCES invoices(id) ON DELETE CASCADE',
                'description VARCHAR(500) NOT NULL',
                'quantity NUMERIC(10, 2) NOT NULL DEFAULT 1',
                'unit_price NUMERIC(10, 2) NOT NULL',
                'total_amount NUMERIC(10, 2) NOT NULL',
                'time_entry_ids VARCHAR(500)',
                'created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP'
            ],
            'indexes': [
                'CREATE INDEX IF NOT EXISTS idx_invoice_items_invoice_id ON invoice_items(invoice_id)'
            ]
        }
    }

def create_table_if_not_exists(engine, table_name, table_schema):
    """Create a table if it doesn't exist with the correct schema"""
    try:
        inspector = inspect(engine)
        existing_tables = inspector.get_table_names()
        
        if table_name not in existing_tables:
            # Create table
            columns_sql = ', '.join(table_schema['columns'])
            create_sql = f"CREATE TABLE {table_name} ({columns_sql})"
            
            with engine.connect() as conn:
                conn.execute(text(create_sql))
                conn.commit()
            print(f"✓ Created table: {table_name}")
            return True
        else:
            # Check if table needs schema updates
            existing_columns = [col['name'] for col in inspector.get_columns(table_name)]
            required_columns = [col.split()[0] for col in table_schema['columns']]
            
            missing_columns = []
            for i, col_def in enumerate(table_schema['columns']):
                col_name = col_def.split()[0]
                if col_name not in existing_columns:
                    missing_columns.append((col_name, col_def))
            
            if missing_columns:
                print(f"⚠ Table {table_name} exists but missing columns: {[col[0] for col in missing_columns]}")
                
                # Add missing columns
                with engine.connect() as conn:
                    for col_name, col_def in missing_columns:
                        try:
                            # Extract column definition without the name
                            col_type_def = ' '.join(col_def.split()[1:])
                            alter_sql = f"ALTER TABLE {table_name} ADD COLUMN {col_name} {col_type_def}"
                            conn.execute(text(alter_sql))
                            print(f"  ✓ Added column: {col_name}")
                        except Exception as e:
                            print(f"  ⚠ Could not add column {col_name}: {e}")
                    conn.commit()
                
                return True
            else:
                print(f"✓ Table {table_name} exists with correct schema")
                return True
                
    except Exception as e:
        print(f"✗ Error creating/updating table {table_name}: {e}")
        return False

def create_indexes(engine, table_name, table_schema):
    """Create indexes for a table"""
    if not table_schema.get('indexes'):
        return True
        
    try:
        with engine.connect() as conn:
            for index_sql in table_schema['indexes']:
                try:
                    conn.execute(text(index_sql))
                except Exception as e:
                    # Index might already exist, that's okay
                    pass
            conn.commit()
        
        if table_schema['indexes']:
            print(f"✓ Indexes created for {table_name}")
        return True
        
    except Exception as e:
        print(f"⚠ Error creating indexes for {table_name}: {e}")
        return True  # Don't fail on index creation errors

def create_triggers(engine):
    """Create triggers for automatic timestamp updates"""
    print("Creating triggers...")
    
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
            
            # Create triggers for all tables that have updated_at
            tables_with_updated_at = ['users', 'projects', 'time_entries', 'settings', 'tasks', 'invoices', 'clients']
            
            for table in tables_with_updated_at:
                try:
                    conn.execute(text(f"""
                        DROP TRIGGER IF EXISTS update_{table}_updated_at ON {table};
                        CREATE TRIGGER update_{table}_updated_at 
                        BEFORE UPDATE ON {table} 
                        FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
                    """))
                except Exception as e:
                    print(f"  ⚠ Could not create trigger for {table}: {e}")
            
            conn.commit()
        
        print("✓ Triggers created successfully")
        return True
        
    except Exception as e:
        print(f"⚠ Error creating triggers: {e}")
        return True  # Don't fail on trigger creation errors

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
        
        with engine.connect() as conn:
            # Get admin username from environment
            admin_username = os.getenv('ADMIN_USERNAMES', 'admin').split(',')[0]
            
            # Insert default admin user (idempotent via unique username)
            conn.execute(text(f"""
                INSERT INTO users (username, role, is_active) 
                SELECT '{admin_username}', 'admin', true
                WHERE NOT EXISTS (
                    SELECT 1 FROM users WHERE username = '{admin_username}'
                );
            """))
            
            # Only insert default client and project on fresh installations
            if not installation_config.is_initial_data_seeded():
                print("Fresh installation detected, creating default client and project...")
                
                # Check if there are any existing projects
                result = conn.execute(text("SELECT COUNT(*) FROM projects;"))
                project_count = result.scalar()
                
                if project_count == 0:
                    # Ensure default client exists (idempotent via unique name)
                    conn.execute(text("""
                        INSERT INTO clients (name, status)
                        SELECT 'Default Client', 'active'
                        WHERE NOT EXISTS (
                            SELECT 1 FROM clients WHERE name = 'Default Client'
                        );
                    """))

                    # Insert default project linked to default client if not present
                    conn.execute(text("""
                        INSERT INTO projects (name, client_id, description, billable, status)
                        SELECT 'General', c.id, 'Default project for general tasks', true, 'active'
                        FROM clients c
                        WHERE c.name = 'Default Client'
                        AND NOT EXISTS (
                            SELECT 1 FROM projects p WHERE p.name = 'General'
                        );
                    """))
                    print("✓ Default client and project created")
                    
                    # Mark initial data as seeded
                    installation_config.mark_initial_data_seeded()
                    print("✓ Marked initial data as seeded")
                else:
                    print(f"Projects already exist ({project_count} found), marking initial data as seeded")
                    installation_config.mark_initial_data_seeded()
            else:
                print("Initial data already seeded previously, skipping default client/project creation")
             
            # Insert default settings only if none exist (singleton semantics)
            conn.execute(text("""
                INSERT INTO settings (
                    timezone, currency, rounding_minutes, single_active_timer, 
                    allow_self_register, idle_timeout_minutes, backup_retention_days, 
                    backup_time, export_delimiter, allow_analytics,
                    company_name, company_address, company_email, company_phone, 
                    company_website, company_logo_filename, company_tax_id, 
                    company_bank_info, invoice_prefix, invoice_start_number, 
                    invoice_terms, invoice_notes
                ) 
                SELECT 'Europe/Rome', 'EUR', 1, true, true, 30, 30, '02:00', ',', true,
                       'Your Company Name', 'Your Company Address', 'info@yourcompany.com',
                       '+1 (555) 123-4567', 'www.yourcompany.com', '', '', '', 'INV', 1000,
                       'Payment is due within 30 days of invoice date.', 'Thank you for your business!'
                WHERE NOT EXISTS (
                    SELECT 1 FROM settings
                );
            """))
             
            conn.commit()
        
        print("✓ Initial data inserted successfully")
        return True
        
    except Exception as e:
        print(f"⚠ Error inserting initial data: {e}")
        import traceback
        print(f"Traceback: {traceback.format_exc()}")
        return True  # Don't fail on data insertion errors

def verify_database_schema(engine):
    """Verify that all required tables and columns exist"""
    print("Verifying database schema...")
    
    try:
        inspector = inspect(engine)
        existing_tables = inspector.get_table_names()
        required_schema = get_required_schema()
        
        missing_tables = []
        schema_issues = []
        
        for table_name, table_schema in required_schema.items():
            if table_name not in existing_tables:
                missing_tables.append(table_name)
            else:
                # Check columns
                existing_columns = [col['name'] for col in inspector.get_columns(table_name)]
                required_columns = [col.split()[0] for col in table_schema['columns']]
                
                missing_columns = [col for col in required_columns if col not in existing_columns]
                if missing_columns:
                    schema_issues.append(f"{table_name}: missing {missing_columns}")
        
        if missing_tables:
            print(f"✗ Missing tables: {missing_tables}")
            return False
        
        if schema_issues:
            print(f"⚠ Schema issues found: {schema_issues}")
            return False
        
        print("✓ Database schema verification passed")
        return True
        
    except Exception as e:
        print(f"✗ Error verifying schema: {e}")
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
    
    print("=== Starting enhanced database initialization ===")
    
    # Get required schema
    required_schema = get_required_schema()

    # Create/update tables
    print("\n--- Creating/updating tables ---")
    for table_name, table_schema in required_schema.items():
        if not create_table_if_not_exists(engine, table_name, table_schema):
            print(f"Failed to create/update table {table_name}")
            sys.exit(1)
    
    # Create indexes
    print("\n--- Creating indexes ---")
    for table_name, table_schema in required_schema.items():
        create_indexes(engine, table_name, table_schema)
    
    # Create triggers
    print("\n--- Creating triggers ---")
    create_triggers(engine)

    # Run legacy migrations (projects.client -> projects.client_id)
    print("\n--- Running legacy migrations ---")
    try:
        inspector = inspect(engine)
        project_columns = [c['name'] for c in inspector.get_columns('projects')] if 'projects' in inspector.get_table_names() else []
        if 'client' in project_columns and 'client_id' in project_columns:
            with engine.connect() as conn:
                conn.execute(text("""
                    INSERT INTO clients (name, status)
                    SELECT DISTINCT client, 'active' FROM projects
                    WHERE client IS NOT NULL AND client <> ''
                    ON CONFLICT (name) DO NOTHING
                """))
                conn.execute(text("""
                    UPDATE projects p
                    SET client_id = c.id
                    FROM clients c
                    WHERE p.client_id IS NULL AND p.client = c.name
                """))
                # Create index and FK best-effort
                try:
                    conn.execute(text("CREATE INDEX IF NOT EXISTS idx_projects_client_id ON projects(client_id)"))
                except Exception:
                    pass
                try:
                    conn.execute(text("ALTER TABLE projects ADD CONSTRAINT fk_projects_client_id FOREIGN KEY (client_id) REFERENCES clients(id) ON DELETE CASCADE"))
                except Exception:
                    pass
                conn.commit()
            print("✓ Migrated legacy projects.client to client_id")
    except Exception as e:
        print(f"⚠ Legacy migration failed (non-fatal): {e}")
    
    # Insert initial data
    print("\n--- Inserting initial data ---")
    insert_initial_data(engine)
    
    # Verify everything was created correctly
    print("\n--- Verifying database schema ---")
    if verify_database_schema(engine):
        print("\n✓ Enhanced database initialization completed successfully")
    else:
        print("\n✗ Database initialization failed - schema verification failed")
        sys.exit(1)

if __name__ == "__main__":
    main()
