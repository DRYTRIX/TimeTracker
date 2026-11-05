#!/usr/bin/env python3
"""
Simple migration script to transition from Project.client (string) to Project.client_id (foreign key)
This script will:
1. Create the new clients table
2. Extract unique client names from projects
3. Create Client records for each unique client
4. Update Project records to reference Client records
5. Drop the old client column
"""

import os
import sys
from pathlib import Path

# Add the parent directory to the path so we can import app modules
sys.path.insert(0, str(Path(__file__).parent.parent))

from app import create_app, db
from app.models import Client, Project


def migrate_to_client_model():
    """Migrate from Project.client (string) to Project.client_id (foreign key)"""
    app = create_app()

    with app.app_context():
        print("Starting migration from Project.client to Project.client_id...")

        # Step 1: Create the clients table
        print("Step 1: Creating clients table...")
        try:
            db.create_all()  # This will create the clients table
            print("✓ Clients table created successfully")
        except Exception as e:
            print(f"✓ Clients table already exists or error: {e}")

        # Step 2: Get unique client names from existing projects
        print("Step 2: Extracting unique client names...")
        try:
            # Use raw SQL to get unique client names
            result = db.session.execute(
                db.text("SELECT DISTINCT client FROM projects WHERE client IS NOT NULL AND client != ''")
            )
            unique_clients = [row[0] for row in result.fetchall()]
            print(f"✓ Found {len(unique_clients)} unique clients: {unique_clients}")
        except Exception as e:
            print(f"Error getting unique clients: {e}")
            return

        # Step 3: Create Client records
        print("Step 3: Creating Client records...")
        client_map = {}  # Map client names to Client objects
        for client_name in unique_clients:
            if client_name:
                # Check if client already exists
                existing_client = Client.query.filter_by(name=client_name).first()
                if existing_client:
                    client_map[client_name] = existing_client
                    print(f"  - Client '{client_name}' already exists")
                else:
                    # Create new client
                    client = Client(name=client_name)
                    db.session.add(client)
                    client_map[client_name] = client
                    print(f"  - Created client: {client_name}")

        try:
            db.session.commit()
            print("✓ All Client records created successfully")
        except Exception as e:
            print(f"Error creating clients: {e}")
            db.session.rollback()
            return

        # Step 4: Add client_id column to projects table
        print("Step 4: Adding client_id column to projects table...")
        try:
            # Check if client_id column already exists
            result = db.session.execute(db.text("""
                SELECT column_name
                FROM information_schema.columns
                WHERE table_name = 'projects' AND column_name = 'client_id'
            """))
            if result.fetchone():
                print("✓ client_id column already exists")
            else:
                # Add client_id column
                db.session.execute(db.text("ALTER TABLE projects ADD COLUMN client_id INTEGER"))
                print("✓ client_id column added successfully")
        except Exception as e:
            print(f"Error adding client_id column: {e}")
            return

        # Step 5: Update projects to reference clients
        print("Step 5: Updating projects to reference clients...")
        try:
            for client_name, client in client_map.items():
                # Update all projects with this client name
                db.session.execute(
                    db.text("UPDATE projects SET client_id = :client_id WHERE client = :client_name"),
                    {"client_id": client.id, "client_name": client_name},
                )
                print(f"  - Updated projects for client '{client_name}' (ID: {client.id})")

            db.session.commit()
            print("✓ All projects updated successfully")
        except Exception as e:
            print(f"Error updating projects: {e}")
            db.session.rollback()
            return

        # Step 6: Add foreign key constraint
        print("Step 6: Adding foreign key constraint...")
        try:
            db.session.execute(db.text("""
                ALTER TABLE projects
                ADD CONSTRAINT fk_projects_client_id
                FOREIGN KEY (client_id) REFERENCES clients(id)
            """))
            print("✓ Foreign key constraint added successfully")
        except Exception as e:
            print(f"Warning: Could not add foreign key constraint: {e}")

        # Step 7: Drop the old client column
        print("Step 7: Dropping old client column...")
        try:
            db.session.execute(db.text("ALTER TABLE projects DROP COLUMN client"))
            print("✓ Old client column dropped successfully")
        except Exception as e:
            print(f"Error dropping client column: {e}")
            return

        try:
            db.session.commit()
            print("✓ Migration completed successfully!")
        except Exception as e:
            print(f"Error in final commit: {e}")
            db.session.rollback()
            return

        # Step 8: Verify migration
        print("Step 8: Verifying migration...")
        try:
            # Check that all projects have client_id
            result = db.session.execute(db.text("SELECT COUNT(*) FROM projects WHERE client_id IS NULL"))
            null_count = result.fetchone()[0]
            if null_count == 0:
                print("✓ All projects have valid client_id references")
            else:
                print(f"Warning: {null_count} projects have NULL client_id")

            # Check client count
            client_count = Client.query.count()
            print(f"✓ Total clients in database: {client_count}")

            # Check project count
            project_count = Project.query.count()
            print(f"✓ Total projects in database: {project_count}")

        except Exception as e:
            print(f"Error in verification: {e}")

        print("\n🎉 Migration completed successfully!")
        print("The client management system is now ready to use.")


if __name__ == "__main__":
    migrate_to_client_model()
