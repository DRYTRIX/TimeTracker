# Apply Kanban Columns Migration

The kanban columns table needs to be created in your PostgreSQL database. Here's how to apply the migration:

## Option 1: Run Migration from Inside Docker Container (Recommended)

```bash
# Enter the running container
docker exec -it timetracker_app_1 bash

# Run the Alembic migration
cd /app
alembic upgrade head

# Exit the container
exit
```

## Option 2: Restart the Container (Auto-Migration)

Your Docker entrypoint script should automatically run migrations on startup:

```bash
# Restart the container
docker-compose restart app

# Or rebuild and restart
docker-compose up -d --build
```

## Option 3: Manual SQL (If migrations don't work)

If the above doesn't work, you can manually create the table:

```bash
# Connect to PostgreSQL
docker exec -it timetracker_db_1 psql -U timetracker -d timetracker

# Run the SQL
CREATE TABLE kanban_columns (
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

CREATE INDEX idx_kanban_columns_key ON kanban_columns(key);
CREATE INDEX idx_kanban_columns_position ON kanban_columns(position);

INSERT INTO kanban_columns (key, label, icon, color, position, is_active, is_system, is_complete_state)
VALUES
    ('todo', 'To Do', 'fas fa-list-check', 'secondary', 0, true, true, false),
    ('in_progress', 'In Progress', 'fas fa-spinner', 'warning', 1, true, true, false),
    ('review', 'Review', 'fas fa-user-check', 'info', 2, true, false, false),
    ('done', 'Done', 'fas fa-check-circle', 'success', 3, true, true, true);

\q
```

## Verify the Migration

After applying the migration, verify it worked:

```bash
# Check the table exists
docker exec -it timetracker_db_1 psql -U timetracker -d timetracker -c "\dt kanban_columns"

# Check the data
docker exec -it timetracker_db_1 psql -U timetracker -d timetracker -c "SELECT key, label FROM kanban_columns ORDER BY position;"
```

You should see:
```
   key      |    label     
------------+--------------
 todo       | To Do
 in_progress| In Progress
 review     | Review
 done       | Done
```

## Troubleshooting

### Error: "relation kanban_columns does not exist"
- The migration hasn't been applied yet
- Run Option 1 or Option 3 above

### Error: "migration 019 already applied"
- The migration was successful, but the table is missing
- Check database permissions
- Try Option 3 (manual SQL)

### Error: "table already exists"
- The table exists but might be empty
- Check if data is there with the verify command
- If empty, just run the INSERT statements from Option 3

## After Migration Success

1. Restart your application:
   ```bash
   docker-compose restart app
   ```

2. Log in and navigate to `/tasks` - the kanban board should now work!

3. As an admin, you can access column management at `/kanban/columns`

## Files Created

The migration was added as:
- `migrations/versions/019_add_kanban_columns_table.py`

The code is also now resilient to handle missing tables during startup.

