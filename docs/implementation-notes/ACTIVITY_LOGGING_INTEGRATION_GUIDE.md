# Activity Logging Integration Guide

This guide shows how to integrate Activity logging throughout the TimeTracker application.

## ✅ Already Integrated

### Projects (`app/routes/projects.py`)
- ✅ Project creation - Line 173

## 🔧 Integration Pattern

### Basic Pattern
```python
from app.models import Activity

Activity.log(
    user_id=current_user.id,
    action='created',  # or 'updated', 'deleted', 'started', 'stopped', etc.
    entity_type='project',  # 'project', 'task', 'time_entry', 'invoice', etc.
    entity_id=entity.id,
    entity_name=entity.name,
    description=f'Human-readable description of what happened',
    ip_address=request.remote_addr,
    user_agent=request.headers.get('User-Agent')
)
```

---

## 📝 Integration Checklist

### 1. Projects (`app/routes/projects.py`)

**✅ Create Project** - DONE (line 173)

**Update Project** - Add after successful update:
```python
# Find: flash(f'Project "{project.name}" updated successfully', 'success')
# Add before it:
Activity.log(
    user_id=current_user.id,
    action='updated',
    entity_type='project',
    entity_id=project.id,
    entity_name=project.name,
    description=f'Updated project "{project.name}"',
    metadata={'fields_updated': ['name', 'description']},  # optional
    ip_address=request.remote_addr,
    user_agent=request.headers.get('User-Agent')
)
```

**Archive Project** - Find the archive route and add:
```python
Activity.log(
    user_id=current_user.id,
    action='archived' if project.status == 'archived' else 'unarchived',
    entity_type='project',
    entity_id=project.id,
    entity_name=project.name,
    description=f'{"Archived" if project.status == "archived" else "Unarchived"} project "{project.name}"',
    ip_address=request.remote_addr,
    user_agent=request.headers.get('User-Agent')
)
```

**Delete Project** - Add after successful deletion:
```python
Activity.log(
    user_id=current_user.id,
    action='deleted',
    entity_type='project',
    entity_id=project_id,
    entity_name=project_name,  # Store before deletion
    description=f'Deleted project "{project_name}"',
    ip_address=request.remote_addr,
    user_agent=request.headers.get('User-Agent')
)
```

---

### 2. Tasks (`app/routes/tasks.py`)

**Import:** Add `Activity` to imports at the top:
```python
from app.models import Task, Project, User, Activity
```

**Create Task:**
```python
# After task creation and commit
Activity.log(
    user_id=current_user.id,
    action='created',
    entity_type='task',
    entity_id=task.id,
    entity_name=task.name,
    description=f'Created task "{task.name}" in project "{task.project.name if task.project else "No project"}"',
    ip_address=request.remote_addr,
    user_agent=request.headers.get('User-Agent')
)
```

**Update Task:**
```python
Activity.log(
    user_id=current_user.id,
    action='updated',
    entity_type='task',
    entity_id=task.id,
    entity_name=task.name,
    description=f'Updated task "{task.name}"',
    ip_address=request.remote_addr,
    user_agent=request.headers.get('User-Agent')
)
```

**Status Change (Important!):**
```python
Activity.log(
    user_id=current_user.id,
    action='status_changed',
    entity_type='task',
    entity_id=task.id,
    entity_name=task.name,
    description=f'Changed task "{task.name}" status from {old_status} to {new_status}',
    metadata={'old_status': old_status, 'new_status': new_status},
    ip_address=request.remote_addr,
    user_agent=request.headers.get('User-Agent')
)
```

**Task Assignment:**
```python
Activity.log(
    user_id=current_user.id,
    action='assigned',
    entity_type='task',
    entity_id=task.id,
    entity_name=task.name,
    description=f'Assigned task "{task.name}" to {assigned_user.display_name}',
    metadata={'assigned_to': assigned_user.id, 'assigned_to_name': assigned_user.display_name},
    ip_address=request.remote_addr,
    user_agent=request.headers.get('User-Agent')
)
```

**Delete Task:**
```python
Activity.log(
    user_id=current_user.id,
    action='deleted',
    entity_type='task',
    entity_id=task.id,
    entity_name=task.name,
    description=f'Deleted task "{task.name}"',
    ip_address=request.remote_addr,
    user_agent=request.headers.get('User-Agent')
)
```

---

### 3. Time Entries (`app/routes/timer.py`)

**Import:** Add `Activity` to imports

**Start Timer:**
```python
# After timer starts successfully
Activity.log(
    user_id=current_user.id,
    action='started',
    entity_type='time_entry',
    entity_id=entry.id,
    entity_name=f'{entry.project.name if entry.project else "No project"}',
    description=f'Started timer for {entry.project.name if entry.project else "No project"}',
    metadata={'project_id': entry.project_id},
    ip_address=request.remote_addr,
    user_agent=request.headers.get('User-Agent')
)
```

**Stop Timer:**
```python
# After timer stops successfully
Activity.log(
    user_id=current_user.id,
    action='stopped',
    entity_type='time_entry',
    entity_id=entry.id,
    entity_name=f'{entry.project.name if entry.project else "No project"}',
    description=f'Stopped timer for {entry.project.name if entry.project else "No project"} - Duration: {entry.duration_formatted}',
    metadata={'duration_hours': entry.duration_hours, 'project_id': entry.project_id},
    ip_address=request.remote_addr,
    user_agent=request.headers.get('User-Agent')
)
```

**Manual Time Entry:**
```python
Activity.log(
    user_id=current_user.id,
    action='created',
    entity_type='time_entry',
    entity_id=entry.id,
    entity_name=f'{entry.project.name if entry.project else "No project"}',
    description=f'Added manual time entry for {entry.project.name if entry.project else "No project"} - {entry.duration_formatted}',
    metadata={'duration_hours': entry.duration_hours, 'source': 'manual'},
    ip_address=request.remote_addr,
    user_agent=request.headers.get('User-Agent')
)
```

**Edit Time Entry:**
```python
Activity.log(
    user_id=current_user.id,
    action='updated',
    entity_type='time_entry',
    entity_id=entry.id,
    entity_name=f'{entry.project.name if entry.project else "No project"}',
    description=f'Updated time entry for {entry.project.name if entry.project else "No project"}',
    ip_address=request.remote_addr,
    user_agent=request.headers.get('User-Agent')
)
```

**Delete Time Entry:**
```python
Activity.log(
    user_id=current_user.id,
    action='deleted',
    entity_type='time_entry',
    entity_id=entry.id,
    entity_name=f'{entry.project.name if entry.project else "No project"}',
    description=f'Deleted time entry for {entry.project.name if entry.project else "No project"} - {entry.duration_formatted}',
    ip_address=request.remote_addr,
    user_agent=request.headers.get('User-Agent')
)
```

---

### 4. Invoices (`app/routes/invoices.py`)

**Import:** Add `Activity` to imports

**Create Invoice:**
```python
Activity.log(
    user_id=current_user.id,
    action='created',
    entity_type='invoice',
    entity_id=invoice.id,
    entity_name=invoice.invoice_number,
    description=f'Created invoice {invoice.invoice_number} for {invoice.client_name} - {invoice.currency_code} {invoice.total_amount}',
    metadata={'client_id': invoice.client_id, 'amount': float(invoice.total_amount)},
    ip_address=request.remote_addr,
    user_agent=request.headers.get('User-Agent')
)
```

**Update Invoice:**
```python
Activity.log(
    user_id=current_user.id,
    action='updated',
    entity_type='invoice',
    entity_id=invoice.id,
    entity_name=invoice.invoice_number,
    description=f'Updated invoice {invoice.invoice_number}',
    ip_address=request.remote_addr,
    user_agent=request.headers.get('User-Agent')
)
```

**Status Change:**
```python
Activity.log(
    user_id=current_user.id,
    action='status_changed',
    entity_type='invoice',
    entity_id=invoice.id,
    entity_name=invoice.invoice_number,
    description=f'Changed invoice {invoice.invoice_number} status from {old_status} to {new_status}',
    metadata={'old_status': old_status, 'new_status': new_status},
    ip_address=request.remote_addr,
    user_agent=request.headers.get('User-Agent')
)
```

**Payment Recorded:**
```python
Activity.log(
    user_id=current_user.id,
    action='paid',
    entity_type='invoice',
    entity_id=invoice.id,
    entity_name=invoice.invoice_number,
    description=f'Recorded payment for invoice {invoice.invoice_number} - {invoice.currency_code} {amount_paid}',
    metadata={'amount_paid': float(amount_paid), 'payment_method': payment_method},
    ip_address=request.remote_addr,
    user_agent=request.headers.get('User-Agent')
)
```

**Send Invoice:**
```python
Activity.log(
    user_id=current_user.id,
    action='sent',
    entity_type='invoice',
    entity_id=invoice.id,
    entity_name=invoice.invoice_number,
    description=f'Sent invoice {invoice.invoice_number} to {invoice.client_email}',
    metadata={'sent_to': invoice.client_email},
    ip_address=request.remote_addr,
    user_agent=request.headers.get('User-Agent')
)
```

**Delete Invoice:**
```python
Activity.log(
    user_id=current_user.id,
    action='deleted',
    entity_type='invoice',
    entity_id=invoice.id,
    entity_name=invoice.invoice_number,
    description=f'Deleted invoice {invoice.invoice_number}',
    ip_address=request.remote_addr,
    user_agent=request.headers.get('User-Agent')
)
```

---

### 5. Clients (`app/routes/clients.py`)

**Import:** Add `Activity` to imports

**Create Client:**
```python
Activity.log(
    user_id=current_user.id,
    action='created',
    entity_type='client',
    entity_id=client.id,
    entity_name=client.name,
    description=f'Added new client "{client.name}"',
    ip_address=request.remote_addr,
    user_agent=request.headers.get('User-Agent')
)
```

**Update Client:**
```python
Activity.log(
    user_id=current_user.id,
    action='updated',
    entity_type='client',
    entity_id=client.id,
    entity_name=client.name,
    description=f'Updated client "{client.name}"',
    ip_address=request.remote_addr,
    user_agent=request.headers.get('User-Agent')
)
```

**Delete Client:**
```python
Activity.log(
    user_id=current_user.id,
    action='deleted',
    entity_type='client',
    entity_id=client.id,
    entity_name=client.name,
    description=f'Deleted client "{client.name}"',
    ip_address=request.remote_addr,
    user_agent=request.headers.get('User-Agent')
)
```

---

### 6. Comments (`app/routes/comments.py`)

**Create Comment:**
```python
Activity.log(
    user_id=current_user.id,
    action='commented',
    entity_type='task',
    entity_id=comment.task_id,
    entity_name=task.name,
    description=f'Commented on task "{task.name}"',
    metadata={'comment_id': comment.id},
    ip_address=request.remote_addr,
    user_agent=request.headers.get('User-Agent')
)
```

---

## 🎯 Quick Integration Script

Here's a Python script to help add Activity logging to a route:

```python
def add_activity_logging(route_function_source_code):
    """
    Helper to suggest where to add Activity.log() calls.
    Returns suggested code to insert.
    """
    template = '''
# Log activity
Activity.log(
    user_id=current_user.id,
    action='ACTION_HERE',  # created, updated, deleted, started, stopped, etc.
    entity_type='ENTITY_TYPE',  # project, task, time_entry, invoice, client
    entity_id=entity.id,
    entity_name=entity.name,
    description=f'DESCRIPTION_HERE',
    ip_address=request.remote_addr,
    user_agent=request.headers.get('User-Agent')
)
'''
    return template
```

---

## 📊 Activity Action Types

Use these standardized action types:

| Action | When to Use |
|--------|-------------|
| `created` | When creating any entity |
| `updated` | When modifying entity fields |
| `deleted` | When removing an entity |
| `started` | When starting a timer |
| `stopped` | When stopping a timer |
| `assigned` | When assigning tasks to users |
| `commented` | When adding comments |
| `status_changed` | When changing status fields |
| `sent` | When sending invoices/emails |
| `paid` | When recording payments |
| `archived` | When archiving entities |
| `unarchived` | When unarchiving entities |

---

## 🧪 Testing Activity Logging

```python
from app.models import Activity

# Get recent activities
activities = Activity.get_recent(limit=50)
for act in activities:
    print(f"{act.user.username}: {act.action} {act.entity_type} - {act.description}")

# Get activities by entity type
project_activities = Activity.get_recent(entity_type='project', limit=20)

# Get user-specific activities
user_activities = Activity.get_recent(user_id=user.id, limit=30)
```

---

## 📈 Performance Considerations

1. **Don't let activity logging break main flow:**
   - Activity.log() includes try/except internally
   - Failures are logged but don't raise exceptions

2. **Batch operations:**
   - For bulk operations, consider logging summary activities

3. **Database indexes:**
   - Activity table has indexes on `user_id`, `created_at`, and composite indexes

---

## 🎨 Creating Activity Feed UI

Once Activity logging is integrated, create an activity feed widget:

**`app/templates/widgets/activity_feed.html`:**
```html
<div class="activity-feed">
    <h3>Recent Activity</h3>
    {% for activity in activities %}
    <div class="activity-item">
        <i class="{{ activity.get_icon() }}"></i>
        <div>
            <strong>{{ activity.user.display_name }}</strong>
            {{ activity.description }}
        </div>
        <span class="timestamp">{{ activity.created_at|timeago }}</span>
    </div>
    {% endfor %}
</div>
```

**Route for activity feed:**
```python
@main_bp.route('/api/activities')
@login_required
def get_activities():
    limit = request.args.get('limit', 20, type=int)
    entity_type = request.args.get('entity_type')
    
    activities = Activity.get_recent(
        user_id=current_user.id if not current_user.is_admin else None,
        limit=limit,
        entity_type=entity_type
    )
    
    return jsonify({
        'activities': [a.to_dict() for a in activities]
    })
```

---

## ✅ Integration Checklist

Use this to track your progress:

- [x] Projects - Create (DONE)
- [ ] Projects - Update
- [ ] Projects - Delete
- [ ] Projects - Archive/Unarchive
- [ ] Tasks - Create
- [ ] Tasks - Update
- [ ] Tasks - Delete
- [ ] Tasks - Status Change
- [ ] Tasks - Assignment
- [ ] Time Entries - Start Timer
- [ ] Time Entries - Stop Timer
- [ ] Time Entries - Manual Create
- [ ] Time Entries - Update
- [ ] Time Entries - Delete
- [ ] Invoices - Create
- [ ] Invoices - Update
- [ ] Invoices - Status Change
- [ ] Invoices - Payment
- [ ] Invoices - Send
- [ ] Invoices - Delete
- [ ] Clients - Create
- [ ] Clients - Update
- [ ] Clients - Delete
- [ ] Comments - Create
- [ ] User Settings - Update (DONE in user.py)

---

**Estimated Time:** 2-3 hours to integrate activity logging throughout the entire application.

**Priority Areas:** Start with Projects, Tasks, and Time Entries as these are the most frequently used features.
