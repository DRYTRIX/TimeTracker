# Quick Fix for Kanban Columns Error

## The Problem
The `kanban_columns` table doesn't exist in your PostgreSQL database, causing the error:
```
relation "kanban_columns" does not exist
```

## Quick Solution (2 minutes)

Run these commands:

```bash
# Step 1: Enter your Docker container
docker exec -it timetracker_app_1 bash

# Step 2: Run the migration
cd /app && alembic upgrade head

# Step 3: Exit and restart
exit
docker-compose restart app
```

That's it! Your application should now work.

## Alternative: Manual SQL (if alembic fails)

```bash
# Connect to database
docker exec -it timetracker_db_1 psql -U timetracker -d timetracker

# Paste this entire block
CREATE TABLE IF NOT EXISTS kanban_columns (
    id SERIAL PRIMARY KEY,
    key VARCHAR(50) NOT NULL UNIQUE,
    label VARCHAR(100) NOT NULL,
    icon VARCHAR(100) DEFAULT 'fas fa-circle',
    color VARCHAR(50) DEFAULT 'secondary',
    position INTEGER NOT NULL DEFAULT 0,
    is_active BOOLEAN NOT NULL DEFAULT true,
    is_system BOOLEAN NOT NULL DEFAULT false,
    is_complete_state BOOLEAN NOT NULL DEFAULT false,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_kanban_columns_key ON kanban_columns(key);
CREATE INDEX IF NOT EXISTS idx_kanban_columns_position ON kanban_columns(position);

INSERT INTO kanban_columns (key, label, icon, color, position, is_active, is_system, is_complete_state)
SELECT * FROM (VALUES
    ('todo', 'To Do', 'fas fa-list-check', 'secondary', 0, true, true, false),
    ('in_progress', 'In Progress', 'fas fa-spinner', 'warning', 1, true, true, false),
    ('review', 'Review', 'fas fa-user-check', 'info', 2, true, false, false),
    ('done', 'Done', 'fas fa-check-circle', 'success', 3, true, true, true)
) AS v(key, label, icon, color, position, is_active, is_system, is_complete_state)
WHERE NOT EXISTS (SELECT 1 FROM kanban_columns LIMIT 1);

\q

# Exit and restart
docker-compose restart app
```

## Verify It Worked

```bash
# Check the table
docker exec -it timetracker_db_1 psql -U timetracker -d timetracker -c "SELECT COUNT(*) FROM kanban_columns;"
```

Should return: `count: 4`

Done! Navigate to `/tasks` and your kanban board will work with custom columns.

