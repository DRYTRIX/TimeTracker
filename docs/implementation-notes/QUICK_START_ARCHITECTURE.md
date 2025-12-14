# Quick Start: Using the New Architecture

This guide shows you how to use the new service layer, repository pattern, and other improvements.

---

## 🏗️ Architecture Overview

```
Routes → Services → Repositories → Models → Database
```

### Layers

1. **Routes** - Handle HTTP requests/responses
2. **Services** - Business logic
3. **Repositories** - Data access
4. **Models** - Database models
5. **Schemas** - Validation and serialization

---

## 📝 Quick Examples

### Using Services in Routes

**Before:**
```python
@route('/timer/start')
def start_timer():
    project = Project.query.get(project_id)
    if not project:
        return error
    timer = TimeEntry(...)
    db.session.add(timer)
    db.session.commit()
```

**After:**
```python
from app.services import TimeTrackingService

@route('/timer/start')
def start_timer():
    service = TimeTrackingService()
    result = service.start_timer(user_id, project_id)
    if result['success']:
        return success_response(result['timer'])
    return error_response(result['message'])
```

### Using Repositories

```python
from app.repositories import TimeEntryRepository

repo = TimeEntryRepository()
entries = repo.get_by_user(user_id, include_relations=True)
active_timer = repo.get_active_timer(user_id)
```

### Using Schemas for Validation

```python
from app.schemas import TimeEntryCreateSchema
from app.utils.api_responses import validation_error_response

@route('/api/time-entries', methods=['POST'])
def create_entry():
    schema = TimeEntryCreateSchema()
    try:
        data = schema.load(request.get_json())
    except ValidationError as err:
        return validation_error_response(err.messages)
    
    # Use validated data...
```

### Using API Response Helpers

```python
from app.utils.api_responses import (
    success_response,
    error_response,
    paginated_response,
    created_response
)

# Success response
return success_response(data=project.to_dict(), message="Project created")

# Error response
return error_response("Project not found", error_code="not_found", status_code=404)

# Paginated response
return paginated_response(
    items=projects,
    page=1,
    per_page=50,
    total=100
)

# Created response
return created_response(data=project.to_dict(), location=f"/api/projects/{project.id}")
```

### Using Constants

```python
from app.constants import ProjectStatus, TimeEntrySource, InvoiceStatus

# Use enums instead of magic strings
project.status = ProjectStatus.ACTIVE.value
entry.source = TimeEntrySource.MANUAL.value
invoice.status = InvoiceStatus.DRAFT.value
```

### Using Query Optimization

```python
from app.utils.query_optimization import eager_load_relations, optimize_list_query

# Eagerly load relations to prevent N+1 queries
query = Project.query
query = eager_load_relations(query, Project, ['client', 'time_entries'])

# Or use auto-optimization
query = optimize_list_query(Project.query, Project)
```

### Using Validation Utilities

```python
from app.utils.validation import (
    validate_required,
    validate_date_range,
    validate_email,
    sanitize_input
)

# Validate required fields
validate_required(data, ['name', 'email'])

# Validate date range
validate_date_range(start_date, end_date)

# Validate email
email = validate_email(data['email'])

# Sanitize input
clean_input = sanitize_input(user_input, max_length=500)
```

---

## 🔄 Migration Guide

### Step 1: Identify Business Logic

Find code in routes that:
- Validates data
- Performs calculations
- Checks permissions
- Creates/updates multiple models
- Has complex conditional logic

### Step 2: Extract to Service

Move business logic to a service method:

```python
# app/services/my_service.py
class MyService:
    def do_something(self, param1, param2):
        # Business logic here
        return {'success': True, 'data': result}
```

### Step 3: Use Repository for Data Access

Replace direct model queries with repository calls:

```python
# Before
projects = Project.query.filter_by(status='active').all()

# After
repo = ProjectRepository()
projects = repo.get_active_projects()
```

### Step 4: Update Route

Use service in route:

```python
@route('/endpoint')
def my_endpoint():
    service = MyService()
    result = service.do_something(param1, param2)
    if result['success']:
        return success_response(result['data'])
    return error_response(result['message'])
```

---

## 🧪 Testing

### Testing Services

```python
from unittest.mock import Mock
from app.services import TimeTrackingService

def test_start_timer():
    service = TimeTrackingService()
    service.time_entry_repo = Mock()
    service.project_repo = Mock()
    
    result = service.start_timer(user_id=1, project_id=1)
    assert result['success'] == True
```

### Testing Repositories

```python
from app.repositories import TimeEntryRepository

def test_get_active_timer(db_session, user, project):
    repo = TimeEntryRepository()
    timer = repo.create_timer(user.id, project.id)
    db_session.commit()
    
    active = repo.get_active_timer(user.id)
    assert active.id == timer.id
```

---

## 📚 Additional Resources

- **Full Documentation:** See `IMPLEMENTATION_SUMMARY.md`
- **API Documentation:** See `docs/API_ENHANCEMENTS.md`
- **Example Code:** See `app/routes/projects_refactored_example.py`
- **Test Examples:** See `tests/test_services/` and `tests/test_repositories/`

---

## ✅ Best Practices

1. **Always use services for business logic** - Don't put business logic in routes
2. **Use repositories for data access** - Don't query models directly in routes
3. **Use schemas for validation** - Don't validate manually
4. **Use response helpers** - Don't create JSON responses manually
5. **Use constants** - Don't use magic strings
6. **Eager load relations** - Prevent N+1 queries
7. **Handle errors consistently** - Use error response helpers

---

**Happy coding!** 🚀

