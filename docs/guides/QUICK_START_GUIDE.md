# Quick Start Guide - New Features

## 🚀 Getting Started in 5 Minutes

### 1. Install & Migrate (2 minutes)
```bash
# Install new dependencies
pip install -r requirements.txt

# Run database migration
flask db upgrade

# Restart your app
docker-compose restart app  # or flask run
```

### 2. Add Excel Export Button (1 minute)
Open `app/templates/reports/index.html` and add:
```html
<a href="{{ url_for('reports.export_excel', start_date=start_date, end_date=end_date) }}" 
   class="btn btn-success">
    <i class="fas fa-file-excel"></i> Export to Excel
</a>
```

### 3. Configure Email (Optional, 2 minutes)
Add to `.env`:
```env
MAIL_SERVER=smtp.gmail.com
MAIL_PORT=587
MAIL_USE_TLS=true
MAIL_USERNAME=your-email@gmail.com
MAIL_PASSWORD=your-app-password
MAIL_DEFAULT_SENDER=noreply@timetracker.local
```

---

## ✅ What Works Right Now

### Excel Export ✅
**Routes Ready:**
- `/reports/export/excel` - Export time entries
- `/reports/project/export/excel` - Export project report

**Usage:**
Just add a button linking to these routes. Files download automatically with professional formatting.

### Email Notifications ✅  
**Auto-runs daily at 9 AM:**
- Checks for overdue invoices
- Sends notifications to admins and creators
- Updates invoice status

**Manual trigger:**
```python
from app.utils.scheduled_tasks import check_overdue_invoices
check_overdue_invoices()
```

### Invoice Duplication ✅
**Already exists!**
Route: `/invoices/<id>/duplicate`

### Activity Logging ✅
**Model ready, just integrate:**
```python
from app.models import Activity

Activity.log(
    user_id=current_user.id,
    action='created',
    entity_type='project',
    entity_id=project.id,
    entity_name=project.name
)
```

---

## 🎯 Quick Implementations

### Add Activity Logging (5-10 min per area)

**In project creation (app/routes/projects.py):**
```python
from app.models import Activity

# After creating project:
Activity.log(
    user_id=current_user.id,
    action='created',
    entity_type='project',
    entity_id=project.id,
    entity_name=project.name,
    description=f'Created project "{project.name}"'
)
```

**In task updates (app/routes/tasks.py):**
```python
# After status change:
Activity.log(
    user_id=current_user.id,
    action='updated',
    entity_type='task',
    entity_id=task.id,
    entity_name=task.name,
    description=f'Changed task status to {new_status}'
)
```

### Create User Settings Page (30 min)

**1. Create route (app/routes/user.py):**
```python
@user_bp.route('/settings', methods=['GET', 'POST'])
@login_required
def settings():
    if request.method == 'POST':
        current_user.email_notifications = 'email_notifications' in request.form
        current_user.notification_overdue_invoices = 'overdue' in request.form
        current_user.theme_preference = request.form.get('theme')
        db.session.commit()
        flash('Settings saved!', 'success')
        return redirect(url_for('user.settings'))
    
    return render_template('user/settings.html')
```

**2. Create template (app/templates/user/settings.html):**
```html
<form method="POST">
    <h3>Notifications</h3>
    <label>
        <input type="checkbox" name="email_notifications" 
               {% if current_user.email_notifications %}checked{% endif %}>
        Enable email notifications
    </label>
    
    <label>
        <input type="checkbox" name="overdue" 
               {% if current_user.notification_overdue_invoices %}checked{% endif %}>
        Overdue invoice notifications
    </label>
    
    <h3>Theme</h3>
    <select name="theme">
        <option value="light">Light</option>
        <option value="dark">Dark</option>
        <option value="system">System</option>
    </select>
    
    <button type="submit">Save Settings</button>
</form>
```

---

## 📊 Usage Statistics

Run to see what's being used:
```python
from app.models import Activity, TimeEntryTemplate

# Most active users
Activity.query.group_by(Activity.user_id).count()

# Most used templates
TimeEntryTemplate.query.order_by(TimeEntryTemplate.usage_count.desc()).limit(10)
```

---

## 🔧 Useful Commands

```bash
# Test overdue invoice check
python -c "from app import create_app; from app.utils.scheduled_tasks import check_overdue_invoices; app = create_app(); app.app_context().push(); check_overdue_invoices()"

# Test weekly summary
python -c "from app import create_app; from app.utils.scheduled_tasks import send_weekly_summaries; app = create_app(); app.app_context().push(); send_weekly_summaries()"

# Check scheduler jobs
python -c "from app import scheduler; print(scheduler.get_jobs())"

# See recent activities
python -c "from app import create_app; from app.models import Activity; app = create_app(); app.app_context().push(); [print(f'{a.user.username}: {a.action} {a.entity_type}') for a in Activity.get_recent(limit=20)]"
```

---

## 🎨 UI Snippets

### Excel Export Button
```html
<a href="{{ url_for('reports.export_excel', **request.args) }}" 
   class="inline-flex items-center px-4 py-2 bg-green-600 hover:bg-green-700 text-white rounded">
    <i class="fas fa-file-excel mr-2"></i>
    Export to Excel
</a>
```

### Theme Switcher Dropdown
```html
<select id="theme-selector" onchange="setTheme(this.value)">
    <option value="light">☀️ Light</option>
    <option value="dark">🌙 Dark</option>
    <option value="system">💻 System</option>
</select>

<script>
function setTheme(theme) {
    if (theme === 'dark' || (theme === 'system' && window.matchMedia('(prefers-color-scheme: dark)').matches)) {
        document.documentElement.classList.add('dark');
    } else {
        document.documentElement.classList.remove('dark');
    }
    fetch('/api/user/preferences', {
        method: 'PATCH',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({theme_preference: theme})
    });
}
</script>
```

---

## 🚨 Common Issues

### "Table already exists" error
```bash
# Reset migration
flask db stamp head
flask db upgrade
```

### Emails not sending
Check that Flask-Mail is configured:
```python
from flask import current_app
print(current_app.config['MAIL_SERVER'])
```

### Scheduler not running
```python
from app import scheduler
print(f"Running: {scheduler.running}")
print(f"Jobs: {scheduler.get_jobs()}")
```

---

## 📖 File Locations

| Feature | Model | Routes | Template |
|---------|-------|--------|----------|
| Time Entry Templates | `app/models/time_entry_template.py` | TBD | TBD |
| Activity Feed | `app/models/activity.py` | TBD | TBD |
| User Preferences | `app/models/user.py` | TBD | TBD |
| Excel Export | `app/utils/excel_export.py` | `app/routes/reports.py` | Add button |
| Email Notifications | `app/utils/email.py` | Automatic | `app/templates/email/` |
| Scheduled Tasks | `app/utils/scheduled_tasks.py` | Automatic | N/A |

---

## 🎯 Implementation Priority

**Do First (30 min):**
1. Add Excel export buttons to reports
2. Test Excel download
3. Configure email (if desired)

**Do Next (1-2 hours):**
4. Create user settings page
5. Add activity logging to 2-3 key areas
6. Test everything

**Do Later (3-5 hours):**
7. Complete time entry templates
8. Build activity feed UI
9. Add bulk task operations
10. Expand keyboard shortcuts

---

**Pro Tip:** Start with Excel export and user settings. These are the quickest wins with immediate user value!
