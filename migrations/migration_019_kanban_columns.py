"""
Migration 019: Add Kanban Column Customization

This migration creates the kanban_columns table to support custom kanban board columns
and task states, allowing users to define their own workflow states.
"""

from app import db
from app.models import KanbanColumn
from sqlalchemy import text


def upgrade():
    """Create kanban_columns table and initialize default columns"""

    print("Migration 019: Creating kanban_columns table...")

    # Check if table already exists
    inspector = db.inspect(db.engine)
    if "kanban_columns" in inspector.get_table_names():
        print("✓ kanban_columns table already exists")
    else:
        # Create the table
        try:
            db.session.execute(text("""
                CREATE TABLE IF NOT EXISTS kanban_columns (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    key VARCHAR(50) NOT NULL UNIQUE,
                    label VARCHAR(100) NOT NULL,
                    icon VARCHAR(100) DEFAULT 'fas fa-circle',
                    color VARCHAR(50) DEFAULT 'secondary',
                    position INTEGER NOT NULL DEFAULT 0,
                    is_active BOOLEAN NOT NULL DEFAULT 1,
                    is_system BOOLEAN NOT NULL DEFAULT 0,
                    is_complete_state BOOLEAN NOT NULL DEFAULT 0,
                    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
            """))
            db.session.commit()
            print("✓ kanban_columns table created successfully")
        except Exception as e:
            db.session.rollback()
            print(f"✗ Error creating kanban_columns table: {e}")
            return False

    # Initialize default columns
    print("Migration 019: Initializing default kanban columns...")
    try:
        # Check if columns already exist
        existing_count = db.session.query(KanbanColumn).count()
        if existing_count > 0:
            print(f"✓ Kanban columns already initialized ({existing_count} columns found)")
        else:
            # Initialize default columns
            initialized = KanbanColumn.initialize_default_columns()
            if initialized:
                print("✓ Default kanban columns initialized successfully")
            else:
                print("! Kanban columns already exist, skipping initialization")
    except Exception as e:
        db.session.rollback()
        print(f"✗ Error initializing default kanban columns: {e}")
        return False

    print("Migration 019 completed successfully")
    return True


def downgrade():
    """Remove kanban_columns table"""

    print("Migration 019: Rolling back kanban_columns table...")

    try:
        db.session.execute(text("DROP TABLE IF EXISTS kanban_columns"))
        db.session.commit()
        print("✓ kanban_columns table dropped successfully")
    except Exception as e:
        db.session.rollback()
        print(f"✗ Error dropping kanban_columns table: {e}")
        return False

    print("Migration 019 rollback completed")
    return True


if __name__ == "__main__":
    # Run migration when executed directly
    from app import create_app

    app = create_app()
    with app.app_context():
        print("Running Migration 019: Kanban Column Customization")
        print("=" * 60)
        success = upgrade()
        if success:
            print("\nMigration completed successfully!")
        else:
            print("\nMigration failed!")
