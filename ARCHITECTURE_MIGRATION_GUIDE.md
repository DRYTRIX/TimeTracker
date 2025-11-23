# Architecture Migration Guide

**Complete guide for migrating existing code to the new architecture**

---

## 🎯 Overview

This guide helps you migrate existing routes and code to use the new service layer, repository pattern, and other improvements.

---

## 📋 Migration Checklist

### Step 1: Identify Code to Migrate
- [ ] Routes with business logic
- [ ] Direct model queries
- [ ] Manual validation
- [ ] Inconsistent error handling
- [ ] N+1 query problems

### Step 2: Create/Use Services
- [ ] Identify business logic
- [ ] Extract to service methods
- [ ] Use existing services or create new ones

### Step 3: Use Repositories
- [ ] Replace direct queries with repository calls
- [ ] Use eager loading to prevent N+1 queries
- [ ] Leverage repository methods

### Step 4: Add Validation
- [ ] Use schemas for API endpoints
- [ ] Use validation utilities for forms
- [ ] Add proper error handling

### Step 5: Update Tests
- [ ] Mock repositories in unit tests
- [ ] Test services independently
- [ ] Add integration tests

---

## 🔄 Migration Examples

### Example 1: Timer Route

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
@route('/timer/start')
def start_timer():
    service = TimeTrackingService()
    result = service.start_timer(user_id, project_id)
    if result['success']:
        return success_response(result['timer'])
    return error_response(result['message'])
```

### Example 2: Project List

**Before:**
```python
@route('/projects')
def list_projects():
    projects = Project.query.filter_by(status='active').all()
    # N+1 query when accessing project.client
    return render_template('projects/list.html', projects=projects)
```

**After:**
```python
@route('/projects')
def list_projects():
    repo = ProjectRepository()
    projects = repo.get_active_projects(include_relations=True)
    # Client eagerly loaded - no N+1 queries
    return render_template('projects/list.html', projects=projects)
```

### Example 3: API Endpoint

**Before:**
```python
@api.route('/projects', methods=['POST'])
def create_project():
    data = request.get_json()
    if not data.get('name'):
        return jsonify({'error': 'Name required'}), 400
    project = Project(name=data['name'], ...)
    db.session.add(project)
    db.session.commit()
    return jsonify(project.to_dict()), 201
```

**After:**
```python
@api.route('/projects', methods=['POST'])
def create_project():
    from app.schemas import ProjectCreateSchema
    from app.utils.api_responses import created_response, validation_error_response
    
    schema = ProjectCreateSchema()
    try:
        data = schema.load(request.get_json())
    except ValidationError as err:
        return validation_error_response(err.messages)
    
    service = ProjectService()
    result = service.create_project(
        name=data['name'],
        client_id=data['client_id'],
        created_by=current_user.id
    )
    
    if result['success']:
        return created_response(result['project'].to_dict())
    return error_response(result['message'])
```

---

## 🛠️ Available Services

### TimeTrackingService
- `start_timer()` - Start a timer
- `stop_timer()` - Stop active timer
- `create_manual_entry()` - Create manual entry
- `get_user_entries()` - Get user's entries
- `delete_entry()` - Delete entry

### ProjectService
- `create_project()` - Create project
- `update_project()` - Update project
- `archive_project()` - Archive project
- `get_active_projects()` - Get active projects

### InvoiceService
- `create_invoice_from_time_entries()` - Create invoice from entries
- `mark_as_sent()` - Mark invoice as sent
- `mark_as_paid()` - Mark invoice as paid

### TaskService
- `create_task()` - Create task
- `update_task()` - Update task
- `get_project_tasks()` - Get project tasks

### ExpenseService
- `create_expense()` - Create expense
- `get_project_expenses()` - Get project expenses
- `get_total_expenses()` - Get total expenses

### ClientService
- `create_client()` - Create client
- `update_client()` - Update client
- `get_active_clients()` - Get active clients

### ReportingService
- `get_time_summary()` - Get time summary
- `get_project_summary()` - Get project summary
- `get_user_productivity()` - Get user productivity

### AnalyticsService
- `get_dashboard_stats()` - Get dashboard stats
- `get_trends()` - Get time trends

---

## 📚 Available Repositories

All repositories extend `BaseRepository` with common methods:
- `get_by_id()` - Get by ID
- `get_all()` - Get all with pagination
- `find_by()` - Find by criteria
- `create()` - Create new
- `update()` - Update existing
- `delete()` - Delete
- `count()` - Count records
- `exists()` - Check existence

### Specialized Methods

**TimeEntryRepository:**
- `get_active_timer()` - Get active timer
- `get_by_user()` - Get user entries
- `get_by_project()` - Get project entries
- `get_by_date_range()` - Get by date range
- `get_billable_entries()` - Get billable entries
- `create_timer()` - Create timer
- `create_manual_entry()` - Create manual entry
- `get_total_duration()` - Get total duration

**ProjectRepository:**
- `get_active_projects()` - Get active projects
- `get_by_client()` - Get client projects
- `get_with_stats()` - Get with statistics
- `archive()` - Archive project
- `unarchive()` - Unarchive project

**InvoiceRepository:**
- `get_by_project()` - Get project invoices
- `get_by_client()` - Get client invoices
- `get_by_status()` - Get by status
- `get_overdue()` - Get overdue invoices
- `generate_invoice_number()` - Generate number
- `mark_as_sent()` - Mark as sent
- `mark_as_paid()` - Mark as paid

**TaskRepository:**
- `get_by_project()` - Get project tasks
- `get_by_assignee()` - Get assigned tasks
- `get_by_status()` - Get by status
- `get_overdue()` - Get overdue tasks

**ExpenseRepository:**
- `get_by_project()` - Get project expenses
- `get_billable()` - Get billable expenses
- `get_total_amount()` - Get total amount

---

## 🎨 Using Schemas

### For API Validation

```python
from app.schemas import ProjectCreateSchema
from app.utils.api_responses import validation_error_response

@api.route('/projects', methods=['POST'])
def create_project():
    schema = ProjectCreateSchema()
    try:
        data = schema.load(request.get_json())
    except ValidationError as err:
        return validation_error_response(err.messages)
    
    # Use validated data...
```

### For Serialization

```python
from app.schemas import ProjectSchema

schema = ProjectSchema()
return schema.dump(project)
```

---

## 🔔 Using Event Bus

### Emit Events

```python
from app.utils.event_bus import emit_event
from app.constants import WebhookEvent

emit_event(WebhookEvent.TIME_ENTRY_CREATED.value, {
    'entry_id': entry.id,
    'user_id': user_id
})
```

### Subscribe to Events

```python
from app.utils.event_bus import subscribe_to_event

@subscribe_to_event('time_entry.created')
def handle_time_entry_created(event_type, data):
    # Handle event
    pass
```

---

## 🔄 Using Transactions

### Decorator

```python
from app.utils.transactions import transactional

@transactional
def create_something():
    # Auto-commits on success, rolls back on exception
    pass
```

### Context Manager

```python
from app.utils.transactions import Transaction

with Transaction():
    # Database operations
    # Auto-commits on success, rolls back on exception
    pass
```

---

## ⚡ Performance Tips

### 1. Use Eager Loading

```python
# Bad - N+1 queries
projects = Project.query.all()
for p in projects:
    print(p.client.name)  # N+1 query

# Good - Eager loading
from app.utils.query_optimization import eager_load_relations
query = Project.query
query = eager_load_relations(query, Project, ['client'])
projects = query.all()
```

### 2. Use Repository Methods

```python
# Repository methods already use eager loading
repo = ProjectRepository()
projects = repo.get_active_projects(include_relations=True)
```

### 3. Use Caching

```python
from app.utils.cache import cached

@cached(ttl=3600)
def expensive_operation():
    # Result cached for 1 hour
    pass
```

---

## 🧪 Testing Patterns

### Unit Test Service

```python
def test_service():
    service = TimeTrackingService()
    service.time_entry_repo = Mock()
    service.project_repo = Mock()
    
    result = service.start_timer(user_id=1, project_id=1)
    assert result['success'] == True
```

### Integration Test Repository

```python
def test_repository(db_session):
    repo = TimeEntryRepository()
    timer = repo.create_timer(user_id=1, project_id=1)
    db_session.commit()
    
    active = repo.get_active_timer(1)
    assert active.id == timer.id
```

---

## 📝 Common Patterns

### Pattern 1: Create Resource

```python
service = ResourceService()
result = service.create_resource(**data)
if result['success']:
    return success_response(result['resource'])
return error_response(result['message'])
```

### Pattern 2: List Resources

```python
repo = ResourceRepository()
resources = repo.get_all(limit=50, offset=0, include_relations=True)
return paginated_response(resources, page=1, per_page=50, total=100)
```

### Pattern 3: Update Resource

```python
service = ResourceService()
result = service.update_resource(resource_id, user_id, **updates)
if result['success']:
    return success_response(result['resource'])
return error_response(result['message'])
```

---

## ✅ Migration Priority

### High Priority (Do First)
1. Timer routes - Core functionality
2. Invoice routes - Business critical
3. Project routes - Frequently used
4. API endpoints - External integration

### Medium Priority
5. Task routes
6. Expense routes
7. Client routes
8. Report routes

### Low Priority
9. Admin routes
10. Settings routes
11. User routes

---

## 🎓 Best Practices

1. **Always use services for business logic**
2. **Always use repositories for data access**
3. **Always use schemas for API validation**
4. **Always use response helpers for API responses**
5. **Always use constants instead of magic strings**
6. **Always eager load relations to prevent N+1**
7. **Always emit domain events for side effects**
8. **Always handle errors consistently**

---

## 📚 Reference

- **Quick Start:** `QUICK_START_ARCHITECTURE.md`
- **Full Analysis:** `PROJECT_ANALYSIS_AND_IMPROVEMENTS.md`
- **Implementation:** `IMPLEMENTATION_SUMMARY.md`
- **Examples:** Check `*_refactored.py` files

---

**Happy migrating!** 🚀

