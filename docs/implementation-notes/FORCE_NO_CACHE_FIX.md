# Nuclear Option: Disable All Caching

If caching is still an issue, here's the nuclear option that FORCES fresh data every time:

## Option 1: Add Query Expiration Decorator

Create a decorator that always expires before queries:

```python
# In app/models/kanban_column.py

from functools import wraps
from app import db

def force_fresh(f):
    """Decorator to force fresh database queries"""
    @wraps(f)
    def wrapper(*args, **kwargs):
        db.session.expire_all()
        return f(*args, **kwargs)
    return wrapper

class KanbanColumn(db.Model):
    # ... existing code ...
    
    @classmethod
    @force_fresh
    def get_active_columns(cls):
        """Get all active columns ordered by position"""
        # Will always expire cache before running
        return db.session.query(cls).filter_by(is_active=True).order_by(cls.position.asc()).all()
```

## Option 2: Disable SQLAlchemy Query Cache Entirely

In `app/config.py` or `app/__init__.py`:

```python
# Disable query caching for KanbanColumn queries
app.config['SQLALCHEMY_ECHO'] = False  # Don't log queries
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False  # Already set
```

And in the model:

```python
@classmethod
def get_active_columns(cls):
    """Get all active columns - always fresh from database"""
    # Use .from_statement() to bypass query cache
    from sqlalchemy import text
    result = db.session.execute(
        text("SELECT * FROM kanban_columns WHERE is_active = true ORDER BY position ASC")
    )
    return [cls(**dict(row)) for row in result]
```

## Option 3: Add Cache Buster to Every Route

```python
# In all routes that load columns
from time import time

@tasks_bp.route('/tasks')
@login_required
def list_tasks():
    # Force refresh
    db.session.commit()  # Commit any pending transactions
    db.session.expire_all()  # Clear cache
    db.session.close()  # Close session
    
    # Get fresh data
    kanban_columns = KanbanColumn.get_active_columns()
    
    # ... rest of route
```

## Option 4: Restart Gunicorn Workers After Changes

Add this to column modification routes:

```python
import os
import signal

# After successful column modification
if os.path.exists('/tmp/gunicorn.pid'):
    with open('/tmp/gunicorn.pid') as f:
        pid = int(f.read().strip())
    os.kill(pid, signal.SIGHUP)  # Reload workers
```

## Option 5: Use Timestamp-Based Cache Busting

```python
# Add to KanbanColumn model
import time

_last_modified = time.time()

@classmethod
def touch(cls):
    """Mark columns as modified"""
    global _last_modified
    _last_modified = time.time()
    db.session.expire_all()

@classmethod
def get_active_columns(cls):
    """Get columns with cache busting"""
    # Timestamp forces query to be different each time it changes
    return db.session.query(cls).filter_by(
        is_active=True
    ).order_by(
        cls.position.asc()
    ).all()

# Call after modifications
def create_column(...):
    # ... create column ...
    KanbanColumn.touch()
```

## Option 6: Multiple Worker Issue

If you have multiple gunicorn workers, they each have their own cache. Fix:

```python
# In docker-compose.yml or docker entrypoint
# Reduce to 1 worker temporarily
CMD ["gunicorn", "--workers=1", "--bind=0.0.0.0:8080", "app:app"]
```

Or use Redis for shared cache:

```python
# Install redis
pip install redis flask-caching

# In app/__init__.py
from flask_caching import Cache
cache = Cache(config={'CACHE_TYPE': 'redis', 'CACHE_REDIS_URL': 'redis://redis:6379/0'})

# In models
@cache.memoize(timeout=5)  # 5 second cache
def get_active_columns():
    # ... query ...

# After modifications
cache.delete_memoized(get_active_columns)
```

## Which One to Try?

**Start with Option 3** (simplest):
- Add cache clearing to every route
- Most likely to work immediately

**Then try Option 1** (cleanest):
- Decorator approach is elegant
- Easy to maintain

**If still failing, try Option 6**:
- Multiple workers are probably the issue
- Reduce to 1 worker temporarily to test

## Test After Each Change

```bash
# 1. Make the change
# 2. Restart container
docker-compose restart app

# 3. Test
# Go to /kanban/columns, create column
# Go to /tasks, should appear immediately

# 4. Check logs
docker logs timetracker_app_1 | grep -i "kanban\|column"
```

Let me know which one you want to try first!

