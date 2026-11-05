#!/usr/bin/env python3
"""
Test Script for TimeTracker Migration System
This script verifies that the migration system is working correctly
"""

import os
import sys
from pathlib import Path


def test_flask_migrate_installation():
    """Test if Flask-Migrate is properly installed"""
    try:
        import flask_migrate

        print("✓ Flask-Migrate is installed")
        return True
    except ImportError:
        print("✗ Flask-Migrate is not installed")
        return False


def test_database_connection():
    """Test database connection"""
    try:
        from app import create_app, db

        app = create_app()

        with app.app_context():
            # Test basic connection
            result = db.session.execute(db.text("SELECT 1"))
            print("✓ Database connection successful")
            return True
    except Exception as e:
        print(f"✗ Database connection failed: {e}")
        return False


def test_migration_files():
    """Test if migration files exist and are valid"""
    migrations_dir = Path("migrations")

    if not migrations_dir.exists():
        print("✗ Migrations directory does not exist")
        return False

    required_files = ["env.py", "script.py.mako", "alembic.ini", "README.md"]

    for file in required_files:
        if not (migrations_dir / file).exists():
            print(f"✗ Required file missing: {file}")
            return False

    print("✓ All required migration files exist")
    return True


def test_migration_commands():
    """Test if migration commands are available"""
    try:
        # Test flask db init (should not fail if already initialized)
        result = os.system("flask db --help > /dev/null 2>&1")
        if result == 0:
            print("✓ Flask migration commands available")
            return True
        else:
            print("✗ Flask migration commands not available")
            return False
    except Exception as e:
        print(f"✗ Error testing migration commands: {e}")
        return False


def test_models_import():
    """Test if all models can be imported"""
    try:
        from app.models import User, Project, TimeEntry, Task, Settings, Invoice, Client

        print("✓ All models imported successfully")
        return True
    except Exception as e:
        print(f"✗ Error importing models: {e}")
        return False


def test_migration_scripts():
    """Test if migration scripts exist and are valid"""
    scripts = ["migrate_existing_database.py", "legacy_schema_migration.py", "manage_migrations.py"]

    for script in scripts:
        script_path = Path("migrations") / script
        if not script_path.exists():
            print(f"✗ Migration script missing: {script}")
            return False

    print("✓ All migration scripts exist")
    return True


def run_comprehensive_test():
    """Run all tests"""
    print("=== Testing TimeTracker Migration System ===\n")

    tests = [
        ("Flask-Migrate Installation", test_flask_migrate_installation),
        ("Database Connection", test_database_connection),
        ("Migration Files", test_migration_files),
        ("Migration Commands", test_migration_commands),
        ("Models Import", test_models_import),
        ("Migration Scripts", test_migration_scripts),
    ]

    passed = 0
    total = len(tests)

    for test_name, test_func in tests:
        print(f"Testing: {test_name}")
        if test_func():
            passed += 1
        print()

    print(f"=== Test Results ===")
    print(f"Passed: {passed}/{total}")

    if passed == total:
        print("🎉 All tests passed! Migration system is ready.")
        return True
    else:
        print("⚠️  Some tests failed. Please fix issues before proceeding.")
        return False


def main():
    """Main function"""
    if not Path("app.py").exists():
        print("Error: Please run this script from the TimeTracker root directory")
        sys.exit(1)

    # Set environment variables
    os.environ.setdefault("FLASK_APP", "app.py")

    success = run_comprehensive_test()

    if success:
        print("\n✅ Migration system is ready for use!")
        print("\nNext steps:")
        print("1. For fresh installation: python migrations/manage_migrations.py")
        print("2. For existing database: python migrations/migrate_existing_database.py")
        print("3. For legacy schema: python migrations/legacy_schema_migration.py")
    else:
        print("\n❌ Migration system has issues that need to be resolved.")
        print("\nTroubleshooting:")
        print("1. Install Flask-Migrate: pip install Flask-Migrate")
        print("2. Check database connection settings")
        print("3. Verify all required files exist")
        print("4. Check application configuration")

        sys.exit(1)


if __name__ == "__main__":
    main()
