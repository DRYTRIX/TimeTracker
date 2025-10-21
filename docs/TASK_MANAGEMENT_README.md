# Task Management Feature

## Overview

The Task Management feature allows you to break down projects into manageable tasks, track their progress, assign them to team members, and monitor time spent on each task.

## Features

### Core Functionality
- **Task Creation**: Create tasks within projects with names, descriptions, and priorities
### Markdown Support

Task and project descriptions support Markdown formatting with a rich editor:

- Editing: Task create/edit and Project create/edit pages include a Markdown editor with dark-mode and image uploads
- Rendering: View pages render Markdown via the `markdown` Jinja filter (`app/utils/template_filters.py`), sanitized with Bleach
- Supported: headings, emphasis, lists, links, code blocks, tables, images

- **Status Tracking**: Monitor task progress through different states (To Do, In Progress, Review, Done)
- **Priority Management**: Set and track task priorities (Low, Medium, High, Urgent)
- **Time Estimation**: Estimate and track actual time for tasks
- **Task Assignment**: Assign tasks to team members
- **Due Date Tracking**: Set deadlines with overdue notifications

### Integration
- **Project Integration**: Tasks are linked to projects and visible in project views
- **Time Tracking**: Start timers and log time directly to specific tasks
- **User Management**: Tasks respect user roles and permissions
- **Reporting**: Include task data in time reports and analytics

## Automatic Database Migration

**No manual setup required!** The Task Management feature automatically creates the necessary database tables and columns when you first start the application.

### What Happens Automatically
1. **On Application Startup**: The system checks if the `tasks` table exists
2. **Table Creation**: If missing, the `tasks` table is automatically created with all required columns
3. **Column Addition**: The system checks if the `task_id` column exists in the `time_entries` table
4. **Schema Updates**: Any missing database elements are automatically added

### Migration Process
The migration runs automatically in these scenarios:
- **First Application Startup**: When the app starts for the first time
- **Database Initialization**: During the `init_database()` process
- **Runtime Checks**: When the database is accessed for the first time

### Migration Logging
The system provides clear feedback during migration:
```
Task Management: Creating tasks table...
✓ Tasks table created successfully
Task Management: Adding task_id column to time_entries table...
✓ task_id column added to time_entries table
Task Management migration check completed
```

## Usage

### Creating Tasks
1. Navigate to **Tasks** → **Create Task**
2. Select a project
3. Enter task details (name, description, priority, due date)
4. Optionally assign to a team member
5. Save the task

### Managing Task Status
- **To Do**: New tasks start in this state
- **In Progress**: Mark when work begins
- **Review**: Mark when ready for review
- **Done**: Mark when completed

### Time Tracking
- **Start Timer**: Begin timing work on a specific task
- **Manual Entry**: Log time spent on tasks with start/end times
- **Task View**: See total time spent and estimated vs. actual time

### Task Views
- **All Tasks**: Complete list with filtering and search
- **My Tasks**: Tasks assigned to or created by the current user
- **Project Tasks**: Tasks within a specific project
- **Overdue Tasks**: Admin view of all overdue tasks

### Filters UI
- The **All Tasks** page includes a filter panel that is **collapsible**.
- Use the chevron button near "Filter Tasks" to show/hide the filters.
- Your preference is **remembered** using `localStorage` so the panel stays collapsed or expanded across visits.

### Inline Client Creation (Quality of Life)

When creating a new project on `Projects → Create`, you can now create a new client without losing your filled-in project data:

- Click "Create new client" under the Client dropdown to open a modal
- Fill in the minimal client details and submit
- The newly created client is selected automatically and the default hourly rate is prefilled if available

This flow uses an AJAX request to `POST /clients/create` and updates the client select dynamically, preserving the current project form state.

## Database Schema

### Tasks Table
```sql
CREATE TABLE tasks (
    id INTEGER PRIMARY KEY,
    project_id INTEGER NOT NULL REFERENCES projects(id),
    name VARCHAR(200) NOT NULL,
    description TEXT,
    status VARCHAR(20) DEFAULT 'todo' NOT NULL,
    priority VARCHAR(20) DEFAULT 'medium' NOT NULL,
    estimated_hours FLOAT,
    due_date DATE,
    assigned_to INTEGER REFERENCES users(id),
    created_by INTEGER NOT NULL REFERENCES users(id),
    created_at TIMESTAMP NOT NULL,
    updated_at TIMESTAMP NOT NULL,
    started_at TIMESTAMP,
    completed_at TIMESTAMP
);
```

### Time Entries Table (Updated)
The `time_entries` table now includes a `task_id` column:
```sql
ALTER TABLE time_entries ADD COLUMN task_id INTEGER REFERENCES tasks(id);
```

## API Endpoints

### Task Management
- `GET /tasks` - List all tasks with filtering
- `POST /tasks/create` - Create a new task
- `GET /tasks/<id>` - View task details
- `POST /tasks/<id>/edit` - Edit task
- `POST /tasks/<id>/status` - Update task status
- `POST /tasks/<id>/priority` - Update task priority
- `POST /tasks/<id>/assign` - Assign task to user
- `POST /tasks/<id>/delete` - Delete task

### API Access
- `GET /api/tasks/<id>` - Get task data in JSON format
- `PUT /api/tasks/<id>/status` - Update task status via API

## User Roles and Permissions

### Regular Users
- Create tasks in projects they have access to
- Update status and priority of their own tasks
- View tasks they're assigned to or created
- Start timers and log time for tasks

### Admin Users
- All regular user permissions
- View and manage all tasks across all projects
- Access overdue tasks report
- Assign tasks to any user
- Delete any task

## Troubleshooting

### Migration Issues
If you encounter migration problems:

1. **Check Application Logs**: Look for migration-related messages
2. **Manual Migration**: Use the migration script: `python docker/migrate-add-tasks.py`
3. **Database Reset**: As a last resort, recreate the database (data will be lost)

### Common Issues
- **Missing Tables**: Ensure the application has database write permissions
- **Column Errors**: Check if the `time_entries` table exists and is accessible
- **Permission Errors**: Verify database user has ALTER TABLE permissions

### Getting Help
- Check the application logs for detailed error messages
- Verify database connectivity and permissions
- Ensure all required Python packages are installed

## Development

### Adding New Features
The Task Management system is designed to be extensible:
- Add new task statuses in the `Task` model
- Extend priority levels as needed
- Add custom fields to the task schema
- Create new API endpoints for additional functionality

### Testing
- Run the migration test: `python docker/migrate-add-tasks.py`
- Test task creation and management workflows
- Verify time tracking integration
- Check user permission enforcement
