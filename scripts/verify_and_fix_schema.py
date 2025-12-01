#!/usr/bin/env python3
"""
Comprehensive schema verification and fix script.
This script checks all SQLAlchemy models against the actual database schema
and adds any missing columns based on the model definitions.

Usage:
    python scripts/verify_and_fix_schema.py
"""

import os
import sys
from sqlalchemy import create_engine, inspect, text, MetaData
from sqlalchemy.exc import OperationalError
from sqlalchemy.schema import CreateTable
from sqlalchemy.dialects import postgresql, sqlite

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def get_sqlalchemy_type(column_type, dialect):
    """Convert SQLAlchemy column type to SQL string for the given dialect"""
    if dialect == 'postgresql':
        return str(column_type.compile(dialect=postgresql.dialect()))
    else:
        return str(column_type.compile(dialect=sqlite.dialect()))


def get_column_default(column, dialect):
    """Get the default value for a column as SQL string"""
    if column.default is None:
        return None
    
    # Handle server defaults (like server_default=text("CURRENT_TIMESTAMP"))
    if hasattr(column, 'server_default') and column.server_default is not None:
        if hasattr(column.server_default, 'arg'):
            default_text = str(column.server_default.arg)
            # Remove quotes if it's a function call
            if default_text.startswith("'") and default_text.endswith("'"):
                default_text = default_text[1:-1]
            return default_text
    
    # Handle Python defaults
    if hasattr(column.default, 'arg'):
        default_arg = column.default.arg
        if isinstance(default_arg, str):
            # Escape single quotes in strings
            escaped = default_arg.replace("'", "''")
            return f"'{escaped}'"
        elif isinstance(default_arg, (int, float)):
            return str(default_arg)
        elif isinstance(default_arg, bool):
            return 'true' if default_arg else 'false'
        elif callable(default_arg):
            # For callable defaults like datetime.utcnow, skip default
            # The database will handle NULL values
            return None
    elif hasattr(column.default, 'text'):
        return column.default.text
    
    return None


def has_column(inspector, table_name, column_name):
    """Check if a column exists in a table"""
    try:
        columns = [col['name'] for col in inspector.get_columns(table_name)]
        return column_name in columns
    except Exception:
        return False


def add_column_sql(table_name, column, dialect):
    """Generate SQL to add a column"""
    col_type = get_sqlalchemy_type(column.type, dialect)
    nullable = "NULL" if column.nullable else "NOT NULL"
    default = get_column_default(column, dialect)
    
    # Build SQL statement
    sql_parts = [f"ALTER TABLE {table_name} ADD COLUMN {column.name} {col_type}"]
    
    # Add default if specified
    if default is not None:
        sql_parts.append(f"DEFAULT {default}")
    
    # Add nullable constraint
    sql_parts.append(nullable)
    
    return " ".join(sql_parts)


def verify_and_fix_table(engine, inspector, model_class, dialect):
    """Verify and fix columns for a single table"""
    table_name = model_class.__tablename__
    
    # Check if table exists
    if table_name not in inspector.get_table_names():
        print(f"⚠ Table '{table_name}' does not exist (will be created by migrations)")
        return 0
    
    # Get expected columns from model
    expected_columns = {}
    for column in model_class.__table__.columns:
        expected_columns[column.name] = column
    
    # Get actual columns from database
    try:
        actual_columns = {col['name']: col for col in inspector.get_columns(table_name)}
    except Exception as e:
        print(f"✗ Error inspecting table '{table_name}': {e}")
        return 0
    
    # Find missing columns
    missing_columns = []
    for col_name, col_def in expected_columns.items():
        if col_name not in actual_columns:
            missing_columns.append((col_name, col_def))
    
    if not missing_columns:
        return 0
    
    # Add missing columns
    added_count = 0
    with engine.begin() as conn:  # Use begin() for automatic transaction management
        for col_name, col_def in missing_columns:
            try:
                sql = add_column_sql(table_name, col_def, dialect)
                # Execute with explicit transaction
                conn.execute(text(sql))
                print(f"  ✓ Added column '{col_name}' to '{table_name}'")
                added_count += 1
            except Exception as e:
                # Log error but continue with other columns
                error_msg = str(e)
                # Don't fail on "column already exists" errors (race condition)
                if "already exists" not in error_msg.lower() and "duplicate" not in error_msg.lower():
                    print(f"  ✗ Failed to add column '{col_name}' to '{table_name}': {error_msg}")
                else:
                    print(f"  ⚠ Column '{col_name}' already exists in '{table_name}' (skipping)")
    
    return added_count


def main():
    """Main function to verify and fix database schema"""
    print("=" * 70)
    print("TimeTracker - Comprehensive Schema Verification and Fix")
    print("=" * 70)
    print()
    
    # Get database URL from environment
    DATABASE_URL = os.getenv("DATABASE_URL", "postgresql+psycopg2://timetracker:timetracker@localhost:5432/timetracker")
    
    try:
        engine = create_engine(DATABASE_URL, pool_pre_ping=True)
        
        # Test connection
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        print("✓ Database connection successful")
        
        # Detect database dialect
        dialect = engine.dialect.name
        print(f"✓ Database dialect: {dialect}")
        print()
        
        # Create inspector
        inspector = inspect(engine)
        
        # Import all models
        print("Loading SQLAlchemy models...")
        try:
            from app import create_app
            app = create_app()
            with app.app_context():
                # Import all models dynamically from app.models
                from app.models import __all__ as model_names
                import app.models as models_module
                
                # Get all model classes
                models = []
                for name in model_names:
                    try:
                        model_class = getattr(models_module, name)
                        if hasattr(model_class, '__tablename__'):
                            models.append(model_class)
                    except AttributeError:
                        pass
                
                # Also get any models that might not be in __all__
                # This ensures we catch everything
                for attr_name in dir(models_module):
                    if not attr_name.startswith('_'):
                        attr = getattr(models_module, attr_name)
                        if (hasattr(attr, '__tablename__') and 
                            hasattr(attr, '__table__') and 
                            attr not in models):
                            models.append(attr)
                
                print(f"✓ Loaded {len(models)} model classes")
                print()
                print("Verifying database schema...")
                print()
                
                total_added = 0
                tables_checked = 0
                
                for model in models:
                    if hasattr(model, '__tablename__'):
                        tables_checked += 1
                        added = verify_and_fix_table(engine, inspector, model, dialect)
                        total_added += added
                        if added > 0:
                            print(f"  → Fixed {added} column(s) in '{model.__tablename__}'")
                
                print()
                print("=" * 70)
                print(f"✓ Schema verification complete")
                print(f"  - Tables checked: {tables_checked}")
                print(f"  - Columns added: {total_added}")
                print("=" * 70)
                
                return 0 if total_added == 0 else 0  # Return 0 even if columns were added (success)
        
        except ImportError as e:
            print(f"✗ Error importing models: {e}")
            print("  This script must be run from the application root directory")
            return 1
        except Exception as e:
            print(f"✗ Error during schema verification: {e}")
            import traceback
            traceback.print_exc()
            return 1
        
    except OperationalError as e:
        print(f"✗ Database connection error: {e}")
        print("  Please check your DATABASE_URL environment variable")
        return 1
    except Exception as e:
        print(f"✗ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
