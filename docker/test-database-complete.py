#!/usr/bin/env python3
"""
Comprehensive database testing script for TimeTracker
This script verifies that all required tables exist and have the correct schema
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

def verify_table_exists(engine, table_name, description=""):
    """Verify that a specific table exists"""
    try:
        inspector = inspect(engine)
        existing_tables = inspector.get_table_names()
        
        if table_name in existing_tables:
            print(f"✓ {table_name} table exists {description}")
            return True
        else:
            print(f"✗ {table_name} table missing {description}")
            return False
    except Exception as e:
        print(f"✗ Error checking {table_name} table: {e}")
        return False

def verify_table_schema(engine, table_name, required_columns):
    """Verify that a table has the required columns"""
    try:
        inspector = inspect(engine)
        if table_name not in inspector.get_table_names():
            print(f"✗ Cannot check schema for {table_name} - table doesn't exist")
            return False
        
        existing_columns = [col['name'] for col in inspector.get_columns(table_name)]
        missing_columns = [col for col in required_columns if col not in existing_columns]
        
        if missing_columns:
            print(f"✗ {table_name} table missing columns: {missing_columns}")
            print(f"  Available columns: {existing_columns}")
            return False
        else:
            print(f"✓ {table_name} table has correct schema")
            return True
    except Exception as e:
        print(f"✗ Error checking schema for {table_name}: {e}")
        return False

def main():
    """Main function"""
    url = os.getenv("DATABASE_URL", "")
    
    if not url.startswith("postgresql"):
        print("No PostgreSQL database configured, skipping verification")
        return
    
    print(f"Database URL: {url}")
    
    # Wait for database to be ready
    engine = wait_for_database(url)
    
    print("\n=== VERIFYING DATABASE SCHEMA ===")
    
    # Define all required tables and their required columns
    required_tables = {
        'users': ['id', 'username', 'role', 'created_at', 'last_login', 'is_active', 'updated_at'],
        'projects': ['id', 'name', 'client', 'description', 'billable', 'hourly_rate', 'billing_ref', 'status', 'created_at', 'updated_at'],
        'time_entries': ['id', 'user_id', 'project_id', 'task_id', 'start_time', 'end_time', 'duration_seconds', 'notes', 'tags', 'source', 'billable', 'created_at', 'updated_at'],
        'tasks': ['id', 'project_id', 'name', 'description', 'status', 'priority', 'assigned_to', 'created_by', 'due_date', 'estimated_hours', 'actual_hours', 'started_at', 'completed_at', 'created_at', 'updated_at'],
        'settings': ['id', 'timezone', 'currency', 'rounding_minutes', 'single_active_timer', 'allow_self_register', 'idle_timeout_minutes', 'backup_retention_days', 'backup_time', 'export_delimiter', 'company_name', 'company_address', 'company_email', 'company_phone', 'company_website', 'company_logo_filename', 'company_tax_id', 'company_bank_info', 'invoice_prefix', 'invoice_number_pattern', 'invoice_start_number', 'invoice_terms', 'invoice_notes', 'created_at', 'updated_at'],
        'invoices': ['id', 'invoice_number', 'project_id', 'client_name', 'client_email', 'client_address', 'issue_date', 'due_date', 'status', 'subtotal', 'tax_rate', 'tax_amount', 'total_amount', 'notes', 'terms', 'created_by', 'created_at', 'updated_at'],
        'invoice_items': ['id', 'invoice_id', 'description', 'quantity', 'unit_price', 'total_amount', 'time_entry_ids', 'created_at']
    }
    
    all_tables_exist = True
    all_schemas_correct = True
    
    # Check if all tables exist
    print("\n--- Checking Table Existence ---")
    for table_name in required_tables.keys():
        if not verify_table_exists(engine, table_name):
            all_tables_exist = False
    
    # Check schema for existing tables
    if all_tables_exist:
        print("\n--- Checking Table Schemas ---")
        for table_name, required_columns in required_tables.items():
            if not verify_table_schema(engine, table_name, required_columns):
                all_schemas_correct = False
    
    # Summary
    print("\n=== VERIFICATION SUMMARY ===")
    if all_tables_exist and all_schemas_correct:
        print("✓ All tables exist and have correct schema")
        print("✓ Database is properly initialized")
        sys.exit(0)
    else:
        if not all_tables_exist:
            print("✗ Some tables are missing")
        if not all_schemas_correct:
            print("✗ Some tables have incorrect schema")
        print("✗ Database verification failed")
        sys.exit(1)

if __name__ == "__main__":
    main()
