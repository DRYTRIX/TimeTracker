#!/usr/bin/env python3
"""
Database verification script for TimeTracker
This script thoroughly checks the database schema and reports any issues
"""

import os
import sys
from sqlalchemy import create_engine, text, inspect
from sqlalchemy.exc import OperationalError, ProgrammingError

def get_expected_schema():
    """Define the complete expected database schema"""
    return {
        'users': {
            'columns': ['id', 'username', 'role', 'created_at', 'last_login', 'is_active', 'updated_at'],
            'required_columns': ['id', 'username', 'role', 'created_at', 'is_active', 'updated_at'],
            'indexes': ['idx_users_username', 'idx_users_role'],
            'foreign_keys': []
        },
        'projects': {
            'columns': ['id', 'name', 'client', 'description', 'billable', 'hourly_rate', 'billing_ref', 'status', 'created_at', 'updated_at'],
            'required_columns': ['id', 'name', 'client', 'billable', 'status', 'created_at', 'updated_at'],
            'indexes': ['idx_projects_client', 'idx_projects_status'],
            'foreign_keys': []
        },
        'time_entries': {
            'columns': ['id', 'user_id', 'project_id', 'task_id', 'start_time', 'end_time', 'duration_seconds', 'notes', 'tags', 'source', 'billable', 'created_at', 'updated_at'],
            'required_columns': ['id', 'user_id', 'project_id', 'start_time', 'source', 'billable', 'created_at', 'updated_at'],
            'indexes': ['idx_time_entries_user_id', 'idx_time_entries_project_id', 'idx_time_entries_task_id', 'idx_time_entries_start_time', 'idx_time_entries_billable'],
            'foreign_keys': ['user_id', 'project_id', 'task_id']
        },
        'tasks': {
            'columns': ['id', 'project_id', 'name', 'description', 'status', 'priority', 'assigned_to', 'created_by', 'due_date', 'estimated_hours', 'actual_hours', 'started_at', 'completed_at', 'created_at', 'updated_at'],
            'required_columns': ['id', 'project_id', 'name', 'status', 'priority', 'created_by', 'created_at', 'updated_at'],
            'indexes': ['idx_tasks_project_id', 'idx_tasks_status', 'idx_tasks_assigned_to', 'idx_tasks_due_date'],
            'foreign_keys': ['project_id', 'assigned_to', 'created_by']
        },
        'settings': {
            'columns': ['id', 'timezone', 'currency', 'rounding_minutes', 'single_active_timer', 'allow_self_register', 'idle_timeout_minutes', 'backup_retention_days', 'backup_time', 'export_delimiter', 'allow_analytics', 'company_name', 'company_address', 'company_email', 'company_phone', 'company_website', 'company_logo_filename', 'company_tax_id', 'company_bank_info', 'invoice_prefix', 'invoice_number_pattern', 'invoice_start_number', 'invoice_terms', 'invoice_notes', 'created_at', 'updated_at'],
            'required_columns': ['id', 'timezone', 'currency', 'rounding_minutes', 'single_active_timer', 'allow_self_register', 'idle_timeout_minutes', 'backup_retention_days', 'backup_time', 'export_delimiter', 'allow_analytics', 'company_name', 'company_address', 'company_email', 'company_phone', 'company_website', 'company_logo_filename', 'company_tax_id', 'company_bank_info', 'invoice_prefix', 'invoice_number_pattern', 'invoice_start_number', 'invoice_terms', 'invoice_notes', 'created_at', 'updated_at'],
            'indexes': [],
            'foreign_keys': []
        },
        'invoices': {
            'columns': ['id', 'invoice_number', 'project_id', 'client_name', 'client_email', 'client_address', 'issue_date', 'due_date', 'status', 'subtotal', 'tax_rate', 'tax_amount', 'total_amount', 'notes', 'terms', 'created_by', 'created_at', 'updated_at'],
            'required_columns': ['id', 'invoice_number', 'client_name', 'issue_date', 'due_date', 'status', 'subtotal', 'tax_rate', 'tax_amount', 'total_amount', 'created_at', 'updated_at'],
            'indexes': ['idx_invoices_project_id', 'idx_invoices_status', 'idx_invoices_issue_date'],
            'foreign_keys': ['project_id', 'created_by']
        },
        'invoice_items': {
            'columns': ['id', 'invoice_id', 'description', 'quantity', 'unit_price', 'total_amount', 'time_entry_ids', 'created_at'],
            'required_columns': ['id', 'invoice_id', 'description', 'quantity', 'unit_price', 'total_amount', 'created_at'],
            'indexes': ['idx_invoice_items_invoice_id'],
            'foreign_keys': ['invoice_id']
        }
    }

def check_table_exists(engine, table_name):
    """Check if a table exists"""
    try:
        inspector = inspect(engine)
        existing_tables = inspector.get_table_names()
        return table_name in existing_tables
    except Exception as e:
        print(f"Error checking if table {table_name} exists: {e}")
        return False

def check_table_columns(engine, table_name, expected_columns, required_columns):
    """Check if a table has the expected columns"""
    try:
        inspector = inspect(engine)
        existing_columns = [col['name'] for col in inspector.get_columns(table_name)]
        
        missing_columns = [col for col in expected_columns if col not in existing_columns]
        missing_required = [col for col in required_columns if col not in existing_columns]
        
        return {
            'exists': True,
            'all_columns': len(missing_columns) == 0,
            'required_columns': len(missing_required) == 0,
            'missing_columns': missing_columns,
            'missing_required': missing_required,
            'existing_columns': existing_columns
        }
    except Exception as e:
        print(f"Error checking columns for table {table_name}: {e}")
        return {
            'exists': False,
            'all_columns': False,
            'required_columns': False,
            'missing_columns': expected_columns,
            'missing_required': required_columns,
            'existing_columns': []
        }

def check_table_indexes(engine, table_name, expected_indexes):
    """Check if a table has the expected indexes"""
    try:
        inspector = inspect(engine)
        existing_indexes = [idx['name'] for idx in inspector.get_indexes(table_name)]
        
        missing_indexes = [idx for idx in expected_indexes if idx not in existing_indexes]
        
        return {
            'all_indexes': len(missing_indexes) == 0,
            'missing_indexes': missing_indexes,
            'existing_indexes': existing_indexes
        }
    except Exception as e:
        print(f"Error checking indexes for table {table_name}: {e}")
        return {
            'all_indexes': False,
            'missing_indexes': expected_indexes,
            'existing_indexes': []
        }

def check_foreign_keys(engine, table_name, expected_fks):
    """Check if a table has the expected foreign keys"""
    try:
        inspector = inspect(engine)
        existing_fks = [fk['constrained_columns'][0] for fk in inspector.get_foreign_keys(table_name)]
        
        missing_fks = [fk for fk in expected_fks if fk not in existing_fks]
        
        return {
            'all_fks': len(missing_fks) == 0,
            'missing_fks': missing_fks,
            'existing_fks': existing_fks
        }
    except Exception as e:
        print(f"Error checking foreign keys for table {table_name}: {e}")
        return {
            'all_fks': False,
            'missing_fks': expected_fks,
            'existing_fks': []
        }

def check_data_integrity(engine):
    """Check basic data integrity"""
    print("\n--- Checking Data Integrity ---")
    
    try:
        with engine.connect() as conn:
            # Check if admin user exists
            result = conn.execute(text("SELECT COUNT(*) FROM users WHERE role = 'admin'"))
            admin_count = result.scalar()
            print(f"Admin users: {admin_count}")
            
            # Check if default project exists
            result = conn.execute(text("SELECT COUNT(*) FROM projects WHERE name = 'General'"))
            project_count = result.scalar()
            print(f"Default projects: {project_count}")
            
            # Check if settings exist
            result = conn.execute(text("SELECT COUNT(*) FROM settings"))
            settings_count = result.scalar()
            print(f"Settings records: {settings_count}")
            
            # Check if allow_analytics column exists and has value
            try:
                result = conn.execute(text("SELECT allow_analytics FROM settings LIMIT 1"))
                analytics_setting = result.scalar()
                print(f"Analytics setting: {analytics_setting}")
            except Exception as e:
                print(f"Analytics setting check failed: {e}")
                
    except Exception as e:
        print(f"Error checking data integrity: {e}")

def main():
    """Main verification function"""
    url = os.getenv("DATABASE_URL", "")
    
    if not url.startswith("postgresql"):
        print("No PostgreSQL database configured, skipping verification")
        return
    
    print(f"Database URL: {url}")
    
    try:
        engine = create_engine(url, pool_pre_ping=True)
        
        # Test connection
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        print("✓ Database connection successful")
        
    except Exception as e:
        print(f"✗ Database connection failed: {e}")
        sys.exit(1)
    
    print("\n=== Starting Database Verification ===")
    
    expected_schema = get_expected_schema()
    verification_results = {}
    overall_status = True
    
    # Check each table
    for table_name, table_schema in expected_schema.items():
        print(f"\n--- Checking table: {table_name} ---")
        
        # Check if table exists
        table_exists = check_table_exists(engine, table_name)
        if not table_exists:
            print(f"✗ Table {table_name} does not exist")
            verification_results[table_name] = {'exists': False}
            overall_status = False
            continue
        
        print(f"✓ Table {table_name} exists")
        
        # Check columns
        column_check = check_table_columns(
            engine, table_name, 
            table_schema['columns'], 
            table_schema['required_columns']
        )
        
        if not column_check['required_columns']:
            print(f"✗ Table {table_name} missing required columns: {column_check['missing_required']}")
            overall_status = False
        elif not column_check['all_columns']:
            print(f"⚠ Table {table_name} missing optional columns: {column_check['missing_columns']}")
        else:
            print(f"✓ Table {table_name} has all expected columns")
        
        # Check indexes
        index_check = check_table_indexes(engine, table_name, table_schema['indexes'])
        if not index_check['all_indexes']:
            print(f"⚠ Table {table_name} missing indexes: {index_check['missing_indexes']}")
        
        # Check foreign keys
        fk_check = check_foreign_keys(engine, table_name, table_schema['foreign_keys'])
        if not fk_check['all_fks']:
            print(f"⚠ Table {table_name} missing foreign keys: {fk_check['missing_fks']}")
        
        verification_results[table_name] = {
            'exists': True,
            'columns': column_check,
            'indexes': index_check,
            'foreign_keys': fk_check
        }
    
    # Check data integrity
    check_data_integrity(engine)
    
    # Summary
    print("\n=== Verification Summary ===")
    if overall_status:
        print("✓ Database verification PASSED - All required tables and columns exist")
    else:
        print("✗ Database verification FAILED - Some required tables or columns are missing")
        print("\nIssues found:")
        for table_name, result in verification_results.items():
            if not result.get('exists', False):
                print(f"  - Table '{table_name}' is missing")
            elif not result.get('columns', {}).get('required_columns', False):
                print(f"  - Table '{table_name}' is missing required columns: {result['columns']['missing_required']}")
    
    return overall_status

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
