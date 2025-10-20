# Debug Guide: Kanban Columns Not Working

## Symptoms
- Unable to add new columns
- Unable to edit existing columns  
- Form submissions don't do anything
- No error messages shown

## Step-by-Step Troubleshooting

### 1. Verify the Migration Was Applied

```bash
# Check if kanban_columns table exists
docker exec -it timetracker_db_1 psql -U timetracker -d timetracker -c "\d kanban_columns"
```

**Expected output:** Should show the table structure

**If table doesn't exist:** Run the migration first (see QUICK_FIX.md)

### 2. Check if Data Exists

```bash
# Check for existing columns
docker exec -it timetracker_db_1 psql -U timetracker -d timetracker -c "SELECT id, key, label FROM kanban_columns ORDER BY position;"
```

**Expected output:**
```
 id |     key     |    label     
----+-------------+--------------
  1 | todo        | To Do
  2 | in_progress | In Progress
  3 | review      | Review
  4 | done        | Done
```

**If no data:** Insert default data (see QUICK_FIX.md)

### 3. Test Column Management Access

```bash
# Check if you're logged in as admin
# In your browser, go to:
http://your-domain/admin
```

**If you get "403 Forbidden":** You're not an admin. Fix with:

```bash
docker exec -it timetracker_db_1 psql -U timetracker -d timetracker -c "UPDATE users SET role='admin' WHERE username='your_username';"
```

### 4. Test the Routes Directly

In your browser console (F12), run:

```javascript
// Test if routes are accessible
fetch('/kanban/columns', {
    method: 'GET',
    headers: {
        'X-Requested-With': 'XMLHttpRequest'
    }
}).then(r => r.text()).then(console.log);
```

**Expected:** HTML page with column list

**If 404:** Blueprint not registered. Check Docker logs for errors.

### 5. Check Docker Logs

```bash
# Watch the logs while trying to add a column
docker logs -f timetracker_app_1
```

Look for errors like:
- `NameError: name 'KanbanColumn' is not defined` 
- `ImportError: cannot import name 'KanbanColumn'`
- `ProgrammingError: relation "kanban_columns" does not exist`
- `AttributeError: 'NoneType' object has no attribute`

### 6. Test Form Submission

When you submit the create/edit form, check:

1. **Network tab (F12 → Network)**
   - Look for POST request to `/kanban/columns/create` or `/kanban/columns/X/edit`
   - Check the response code (should be 302 redirect on success)
   - Check the response body for error messages

2. **Console tab (F12 → Console)**
   - Look for JavaScript errors
   - CSRF token errors
   - Form validation errors

### 7. Manual Test - Create a Column via Python

```bash
# Enter the container
docker exec -it timetracker_app_1 bash

# Run Python shell
python3 << 'EOF'
from app import create_app, db
from app.models import KanbanColumn

app = create_app()
with app.app_context():
    # Test if model works
    columns = KanbanColumn.query.all()
    print(f"Found {len(columns)} columns")
    
    # Try to create a test column
    test_col = KanbanColumn(
        key='testing',
        label='Testing',
        icon='fas fa-flask',
        color='primary',
        position=99,
        is_system=False,
        is_active=True
    )
    db.session.add(test_col)
    db.session.commit()
    print("Test column created successfully!")
    
    # Clean up
    db.session.delete(test_col)
    db.session.commit()
    print("Test column deleted")
EOF

exit
```

**Expected:** "Test column created successfully!"

**If error:** Note the error message and check below.

## Common Issues & Solutions

### Issue: "NameError: name 'KanbanColumn' is not defined"

**Cause:** Model not imported properly

**Fix:**
```bash
# Check app/models/__init__.py
docker exec -it timetracker_app_1 cat /app/app/models/__init__.py | grep KanbanColumn
```

Should show: `from .kanban_column import KanbanColumn`

**If missing:** The file was not accepted. Re-apply the changes.

### Issue: "No such command 'kanban'"

**Cause:** Blueprint not registered

**Fix:**
```bash
# Check app/__init__.py
docker exec -it timetracker_app_1 cat /app/app/__init__.py | grep kanban_bp
```

Should show:
```python
from app.routes.kanban import kanban_bp
app.register_blueprint(kanban_bp)
```

**If missing:** Re-apply the changes and restart:
```bash
docker-compose restart app
```

### Issue: Form submits but nothing happens

**Possible causes:**

1. **CSRF Token Issue**
   - Check browser console for CSRF errors
   - Verify token in form: View source, search for `csrf_token`

2. **Database Connection Issue**
   - Check logs: `docker logs timetracker_app_1 | grep -i error`
   - Verify DB is accessible: See step 1 above

3. **Validation Failing Silently**
   - Check if flash messages appear at top of page
   - Look for "Key and label are required" message

4. **Route Not Matching**
   - Verify URL in browser matches route definition
   - Check for trailing slashes

### Issue: "500 Internal Server Error"

**Check logs:**
```bash
docker logs timetracker_app_1 2>&1 | tail -n 50
```

Common errors:
- `AttributeError: 'NoneType'` → Check if column exists before accessing
- `IntegrityError: duplicate key` → Key already exists
- `OperationalError: no such table` → Migration not applied

## Still Not Working?

### Collect Debug Information

```bash
# 1. Check Python version
docker exec -it timetracker_app_1 python --version

# 2. Check if file exists
docker exec -it timetracker_app_1 ls -la /app/app/models/kanban_column.py
docker exec -it timetracker_app_1 ls -la /app/app/routes/kanban.py

# 3. Check database schema
docker exec -it timetracker_db_1 psql -U timetracker -d timetracker -c "\d+ kanban_columns"

# 4. Check recent logs
docker logs timetracker_app_1 --tail=100 > kanban_debug.log

# 5. Test database connection
docker exec -it timetracker_app_1 python -c "from app import create_app, db; from app.models import KanbanColumn; app = create_app(); app.app_context().push(); print(f'Columns: {KanbanColumn.query.count()}')"
```

### Force Restart Everything

```bash
# Nuclear option - full restart
docker-compose down
docker-compose up -d
sleep 10
docker logs timetracker_app_1
```

### Verify Blueprint Registration

```bash
# Check if kanban blueprint is registered
docker exec -it timetracker_app_1 python << 'EOF'
from app import create_app
app = create_app()
print("Registered blueprints:")
for name, blueprint in app.blueprints.items():
    print(f"  - {name}: {blueprint.url_prefix or '/'}")
EOF
```

Should show: `kanban: /`

## Quick Fixes

### Can't Access /kanban/columns?

```bash
# Make yourself admin
docker exec -it timetracker_db_1 psql -U timetracker -d timetracker -c "UPDATE users SET role='admin' WHERE username='admin';"

# Restart app
docker-compose restart app
```

### Forms Not Submitting?

1. Clear browser cache (Ctrl+Shift+Delete)
2. Try in incognito/private window
3. Check if JavaScript is enabled
4. Disable browser extensions
5. Try different browser

### Database Issues?

```bash
# Reset the kanban_columns table
docker exec -it timetracker_db_1 psql -U timetracker -d timetracker << 'EOF'
DROP TABLE IF EXISTS kanban_columns CASCADE;

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

INSERT INTO kanban_columns (key, label, icon, color, position, is_active, is_system, is_complete_state) VALUES
    ('todo', 'To Do', 'fas fa-list-check', 'secondary', 0, true, true, false),
    ('in_progress', 'In Progress', 'fas fa-spinner', 'warning', 1, true, true, false),
    ('review', 'Review', 'fas fa-user-check', 'info', 2, true, false, false),
    ('done', 'Done', 'fas fa-check-circle', 'success', 3, true, true, true);
EOF

docker-compose restart app
```

## Report the Issue

If none of the above works, provide:

1. Output from "Collect Debug Information" section
2. Screenshot of the form you're trying to submit
3. Browser console errors (F12 → Console)
4. Network tab showing the POST request (F12 → Network)
5. Last 100 lines of Docker logs

This will help diagnose the specific issue with your setup.

