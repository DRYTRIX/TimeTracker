# Kanban Column Refresh - Diagnosis Steps

## Let's figure out exactly what's happening

Please follow these steps and tell me the results:

### Step 1: Verify Changes Are Saved to Database

```bash
# After creating/editing a column, immediately check the database
docker exec -it timetracker_db_1 psql -U timetracker -d timetracker -c "SELECT id, key, label, position, is_active FROM kanban_columns ORDER BY position;"
```

**Question:** Do you see your new/edited column in the database?
- If YES → Changes are saved, it's a caching issue
- If NO → Changes aren't being saved at all

### Step 2: Check How You're Viewing Changes

**Please describe exactly what you do:**

A) Do you:
   1. Go to `/kanban/columns`
   2. Click "Add Column"
   3. Fill form and submit
   4. Get redirected back to `/kanban/columns`
   5. **Don't see the new column** ← Problem here?

B) Or do you:
   1. Go to `/kanban/columns`
   2. Click "Add Column"
   3. Fill form and submit
   4. See new column on `/kanban/columns` ✓
   5. Go to `/tasks` 
   6. **Don't see the new column on kanban board** ← Problem here?

C) Or something else?

### Step 3: Test Manual Page Refresh

After creating a column:
1. Do you see it on `/kanban/columns`? (might need to refresh)
2. Open `/tasks` in a NEW tab
3. Do you see the new column on the kanban board?

### Step 4: Check Browser Cache

```
Press: Ctrl + Shift + R (Windows/Linux)
Or: Cmd + Shift + R (Mac)
```

This does a hard refresh. Does the column appear now?

### Step 5: Check Gunicorn Workers

You might have multiple workers caching independently:

```bash
# Check logs when you create a column
docker logs -f timetracker_app_1
```

Look for:
- "Column created successfully" messages
- Any errors
- Which worker handled the request

### Step 6: Test via Python Shell

```bash
# Enter container
docker exec -it timetracker_app_1 bash

# Run Python
python3 << 'EOF'
from app import create_app, db
from app.models import KanbanColumn

app = create_app()
with app.app_context():
    print("Active columns:")
    for col in KanbanColumn.get_active_columns():
        print(f"  - {col.key}: {col.label}")
EOF

exit
```

Does this show your new columns?

### Step 7: Check if SocketIO is Working

Open browser console (F12) on `/tasks` page and run:

```javascript
// Check if socket is connected
if (typeof io !== 'undefined') {
    console.log('SocketIO is available');
    const socket = io();
    socket.on('connect', () => console.log('Socket connected!'));
    socket.on('kanban_columns_updated', (data) => console.log('Received update:', data));
} else {
    console.log('SocketIO NOT available');
}
```

Then in another tab, create a column. Do you see "Received update" in console?

## Common Scenarios and Solutions

### Scenario A: Changes save but don't appear until restart
**Cause:** Multiple gunicorn workers with separate caches
**Solution:** Add cache-busting parameter to queries

### Scenario B: Changes appear on `/kanban/columns` but not on `/tasks`
**Cause:** Browser caching the `/tasks` page
**Solution:** Hard refresh or disable cache

### Scenario C: Changes don't save at all
**Cause:** Form validation failing or database error
**Solution:** Check Docker logs for errors

### Scenario D: Changes appear after manual refresh
**Cause:** Page not auto-refreshing as expected
**Solution:** This is actually working - just needs manual refresh

## Quick Test

Try this simple test:

1. Go to `/kanban/columns`
2. Note the current column count (should be 4)
3. Create a new column called "Test123"
4. You get redirected back - **COUNT THE COLUMNS** - is it 5 now?
   - If YES: Column was created, just refresh `/tasks` to see it
   - If NO: Column creation is failing

## Please Report Back

Tell me:
1. Which scenario (A, B, C, or D) matches your issue?
2. Results from Step 1 (database check)
3. Which behavior (A, B, or C) from Step 2
4. Does hard refresh (Step 4) show the column?
5. Output from Step 6 (Python shell)

This will help me give you the exact fix you need!

