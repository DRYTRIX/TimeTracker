# Kanban Board Customization Feature

This document describes the custom kanban board columns feature implemented in the TimeTracker application.

## Overview

The kanban board now supports fully customizable columns and task states. Administrators can:
- Create custom columns with unique names and properties
- Modify existing columns (label, icon, color, behavior)
- Reorder columns via drag-and-drop
- Activate/deactivate columns without deleting them
- Define which columns mark tasks as complete

## Features Implemented

### 1. Database Model (`KanbanColumn`)

New model to store kanban column configurations:
- `key`: Unique identifier for the column (e.g., 'in_progress')
- `label`: Display name shown in the UI (e.g., 'In Progress')
- `icon`: Font Awesome icon class for visual representation
- `color`: Bootstrap color class for styling
- `position`: Sort order on the kanban board
- `is_active`: Whether the column is currently visible
- `is_system`: System columns (todo, in_progress, done) cannot be deleted
- `is_complete_state`: Marks tasks as completed when moved to this column

### 2. Admin Routes (`/kanban/columns/`)

New routes for column management:
- **GET /kanban/columns**: List all columns with management options
- **GET /kanban/columns/create**: Form to create a new column
- **POST /kanban/columns/create**: Create a new column
- **GET /kanban/columns/<id>/edit**: Form to edit existing column
- **POST /kanban/columns/<id>/edit**: Update column properties
- **POST /kanban/columns/<id>/delete**: Delete custom column (if no tasks use it)
- **POST /kanban/columns/<id>/toggle**: Activate/deactivate column
- **POST /api/kanban/columns/reorder**: Reorder columns (drag-and-drop)
- **GET /api/kanban/columns**: API endpoint to get all active columns

### 3. Updated Templates

Modified templates to load columns dynamically:
- `app/templates/tasks/_kanban.html`: Load columns from database
- `app/templates/kanban/columns.html`: Column management page
- `app/templates/kanban/create_column.html`: Create column form
- `app/templates/kanban/edit_column.html`: Edit column form

### 4. Updated Task Routes

Task status validation now uses configured kanban columns:
- `list_tasks()`: Passes kanban_columns to template
- `my_tasks()`: Passes kanban_columns to template
- `update_task_status()`: Validates status against active columns
- `api_update_status()`: API endpoint validates against active columns

### 5. Migration Script

Migration script to initialize the system:
- Creates `kanban_columns` table
- Initializes default columns (To Do, In Progress, Review, Done)
- Located at: `migrations/migration_019_kanban_columns.py`

## Usage

### For Administrators

#### Accessing Column Management

1. Navigate to any kanban board view
2. Click "Manage Columns" button (visible to admins only)
3. Or directly visit `/kanban/columns`

#### Creating a New Column

1. Click "Add Column" button
2. Fill in the form:
   - **Column Label**: Display name (e.g., "In Review")
   - **Column Key**: Unique identifier (auto-generated from label)
   - **Icon**: Font Awesome class (e.g., "fas fa-eye")
   - **Color**: Bootstrap color class (primary, success, warning, etc.)
   - **Mark as Complete State**: Check if this column completes tasks
3. Click "Create Column"

#### Editing a Column

1. Click the edit icon next to any column
2. Modify properties (label, icon, color, complete state, active status)
3. Click "Save Changes"

Note: The column key cannot be changed after creation.

#### Reordering Columns

1. On the column management page, drag the grip icon (≡) next to any column
2. Drop it in the desired position
3. The order is saved automatically

#### Deleting a Column

1. Custom columns can be deleted if no tasks are using that status
2. System columns (todo, in_progress, done) cannot be deleted but can be customized
3. Click the delete icon and confirm

#### Activating/Deactivating Columns

- Click the eye icon to toggle column visibility
- Inactive columns are hidden from the kanban board
- Tasks with inactive statuses remain accessible but don't appear on the board

### For Users

- The kanban board automatically reflects the configured columns
- Drag and drop tasks between columns
- Tasks automatically update their status when moved
- Complete state columns automatically mark tasks as done

## Technical Details

### Default Columns

The system initializes with these default columns:
1. **To Do** (todo) - System column
2. **In Progress** (in_progress) - System column  
3. **Review** (review) - Custom column
4. **Done** (done) - System column, marks tasks as complete

### System Columns

These columns are created by default and cannot be deleted:
- `todo`: Initial state for new tasks
- `in_progress`: Active work in progress
- `done`: Completed tasks

System columns can still be customized (label, icon, color) but not deleted.

### Column Properties

- **Key**: Must be unique, lowercase, use underscores instead of spaces
- **Label**: User-friendly display name, can include spaces and capitals
- **Icon**: Font Awesome class, e.g., "fas fa-check", "fas fa-spinner"
- **Color**: Bootstrap color: primary, secondary, success, danger, warning, info, dark
- **Position**: Auto-managed, can be changed via drag-and-drop
- **Active**: Hidden columns don't appear on kanban board
- **Complete State**: Automatically marks tasks as completed

### Backward Compatibility

The system maintains backward compatibility with existing task statuses:
- Tasks with old statuses continue to work
- The `status_display` property checks kanban columns first
- Falls back to hardcoded labels if column not found
- Migration initializes columns to match existing behavior

## API Endpoints

### GET /api/kanban/columns

Returns all active kanban columns.

**Response:**
```json
{
  "columns": [
    {
      "id": 1,
      "key": "todo",
      "label": "To Do",
      "icon": "fas fa-list-check",
      "color": "secondary",
      "position": 0,
      "is_active": true,
      "is_system": true,
      "is_complete_state": false
    },
    ...
  ]
}
```

### POST /api/kanban/columns/reorder

Reorder columns based on provided ID list.

**Request:**
```json
{
  "column_ids": [1, 3, 2, 4]
}
```

**Response:**
```json
{
  "success": true,
  "message": "Columns reordered successfully"
}
```

## Files Modified

### New Files
- `app/models/kanban_column.py`: KanbanColumn model
- `app/routes/kanban.py`: Kanban column management routes
- `app/templates/kanban/columns.html`: Column management page
- `app/templates/kanban/create_column.html`: Create column form
- `app/templates/kanban/edit_column.html`: Edit column form
- `migrations/migration_019_kanban_columns.py`: Database migration

### Modified Files
- `app/models/__init__.py`: Added KanbanColumn import
- `app/models/task.py`: Updated status_display to use KanbanColumn
- `app/routes/tasks.py`: Updated validation to use KanbanColumn
- `app/routes/projects.py`: Pass kanban_columns to template
- `app/templates/tasks/_kanban.html`: Load columns dynamically
- `app/__init__.py`: Register kanban blueprint

## Database Schema

```sql
CREATE TABLE kanban_columns (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    key VARCHAR(50) NOT NULL UNIQUE,
    label VARCHAR(100) NOT NULL,
    icon VARCHAR(100) DEFAULT 'fas fa-circle',
    color VARCHAR(50) DEFAULT 'secondary',
    position INTEGER NOT NULL DEFAULT 0,
    is_active BOOLEAN NOT NULL DEFAULT 1,
    is_system BOOLEAN NOT NULL DEFAULT 0,
    is_complete_state BOOLEAN NOT NULL DEFAULT 0,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_kanban_columns_key ON kanban_columns(key);
CREATE INDEX idx_kanban_columns_position ON kanban_columns(position);
```

## Future Enhancements

Possible future improvements:
- Per-project custom columns
- Column-specific automation rules
- Custom column colors (hex codes)
- Column templates for different workflows
- Bulk task status updates
- Column usage analytics

## Troubleshooting

### Issue: Custom column not appearing on kanban board
**Solution**: Check that the column is marked as "Active" in the column management page.

### Issue: Cannot delete a custom column
**Solution**: Ensure no tasks are using that status. Move or delete those tasks first.

### Issue: Drag and drop not working
**Solution**: Ensure JavaScript is enabled and SortableJS library is loaded.

### Issue: Changes not reflected immediately
**Solution**: Refresh the page or clear browser cache.

## Security Considerations

- Only administrators can manage kanban columns
- Column keys are validated to prevent SQL injection
- CSRF protection on all forms
- XSS protection on user-provided labels
- System columns cannot be deleted to maintain data integrity

