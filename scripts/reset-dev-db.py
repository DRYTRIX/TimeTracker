#!/usr/bin/env python3
"""
Development Database Reset Script

This script resets the database by:
1. Dropping all tables (using Flask-Migrate downgrade to base)
2. Re-applying all migrations
3. Seeding default data (admin user, settings)

Usage:
    python scripts/reset-dev-db.py
    # Or from Docker container:
    docker compose exec app python /app/scripts/reset-dev-db.py

WARNING: This will DELETE ALL DATA in the database.
Only use this in development environments.
"""

import os
import sys

# Add project root to path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, project_root)

os.environ.setdefault("FLASK_APP", "app")
os.chdir(project_root)


def main():
    print("=" * 70)
    print("DEV DATABASE RESET")
    print("=" * 70)
    print()
    print("⚠️  WARNING: This will DELETE ALL DATA in the database!")
    print()
    
    # Safety check: require explicit confirmation in interactive mode
    if sys.stdin.isatty():
        response = input("Are you sure you want to reset the database? (yes/no): ")
        if response.strip().lower() != "yes":
            print("Reset cancelled.")
            sys.exit(0)
    else:
        # Non-interactive mode: require environment variable
        if os.getenv("TT_FORCE_RESET_DB", "").strip().lower() not in ("1", "true", "yes"):
            print("ERROR: Non-interactive mode requires TT_FORCE_RESET_DB=true")
            print("This prevents accidental data loss in CI/CD pipelines.")
            sys.exit(1)
    
    print()
    print("Starting database reset...")
    print()
    
    try:
        from app import create_app, db
        from flask_migrate import downgrade, upgrade, current, history
        from app.models import Settings, User
        from sqlalchemy import text, inspect as sqlalchemy_inspect
        
        app = create_app()
        
        with app.app_context():
            # Step 1: Show current migration state
            print("[1/4] Checking current migration state...")
            try:
                current_rev = current()
                print(f"    Current revision: {current_rev}")
            except Exception as e:
                print(f"    No current revision (fresh DB or error): {e}")
            
            # Step 2: Drop all tables
            print()
            print("[2/4] Dropping all tables...")
            try:
                # Get list of all tables before dropping
                inspector = sqlalchemy_inspect(db.engine)
                existing_tables = inspector.get_table_names()
                if existing_tables:
                    print(f"    Found {len(existing_tables)} tables to drop")
                    # Drop all tables using SQLAlchemy (more reliable than downgrade for reset)
                    db.drop_all()
                    print("    ✓ All tables dropped")
                else:
                    print("    ✓ No tables to drop (database is empty)")
            except Exception as e:
                print(f"    ✗ Error dropping tables: {e}")
                import traceback
                traceback.print_exc()
                # Try to continue - maybe tables were already dropped
            
            # Step 3: Apply all migrations
            print()
            print("[3/4] Applying migrations...")
            try:
                # Use upgrade to apply all migrations from scratch
                upgrade(revision="heads")
                print("    ✓ Migrations applied")
            except Exception as e:
                print(f"    ✗ Migration failed: {e}")
                import traceback
                traceback.print_exc()
                sys.exit(1)
            
            # Verify tables were created
            inspector = sqlalchemy_inspect(db.engine)
            new_tables = inspector.get_table_names()
            core_tables = ['users', 'projects', 'time_entries', 'settings', 'clients', 'alembic_version']
            found_core = [t for t in new_tables if t in core_tables]
            missing_core = set(core_tables) - set(new_tables)
            if missing_core:
                print(f"    ⚠ Warning: Core tables missing after migration: {sorted(missing_core)}")
            else:
                print(f"    ✓ Core tables verified: {sorted(found_core)}")
            
            # Step 4: Seed default data
            print()
            print("[4/4] Seeding default data...")
            try:
                # Settings
                if not Settings.query.first():
                    db.session.add(Settings())
                    db.session.commit()
                    print("    ✓ Created default settings")
                else:
                    print("    ✓ Settings already exist")
                
                # Admin user
                admin_username = os.getenv("ADMIN_USERNAMES", "admin").split(",")[0].strip().lower()
                existing = User.query.filter_by(username=admin_username).first()
                if not existing:
                    admin_user = User(username=admin_username, role="admin")
                    admin_user.is_active = True
                    db.session.add(admin_user)
                    db.session.commit()
                    print(f"    ✓ Created admin user: {admin_username}")
                else:
                    # Ensure admin role and active status
                    changed = False
                    if existing.role != "admin":
                        existing.role = "admin"
                        changed = True
                    if not existing.is_active:
                        existing.is_active = True
                        changed = True
                    if changed:
                        db.session.commit()
                        print(f"    ✓ Updated admin user: {admin_username}")
                    else:
                        print(f"    ✓ Admin user already exists: {admin_username}")
                
                print("    ✓ Default data seeded")
            except Exception as e:
                print(f"    ✗ Error seeding default data: {e}")
                import traceback
                traceback.print_exc()
                # Don't fail - data seeding is best-effort
        
        print()
        print("=" * 70)
        print("✓ Database reset complete!")
        print("=" * 70)
        print()
        print("You can now restart the application.")
        
    except Exception as e:
        print()
        print("=" * 70)
        print("✗ Database reset failed!")
        print("=" * 70)
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
