# Deletion and Status Management Improvements

## Summary

This document describes the improvements made to the deletion handling and status management for projects, tasks, and clients in the TimeTracker application.

## Changes Made

### 1. Task Deletion Improvements

**Previous Behavior:**
- Tasks used bulk checkboxes for selection
- Bulk delete button appeared when tasks were selected
- Users had to select multiple tasks to delete them

**New Behavior:**
- Individual delete button for each task in the list view
- Consistent with project and client deletion patterns
- Immediate confirmation dialog when clicking delete
- Better UX with per-row actions

**Files Modified:**
- `app/templates/tasks/list.html` - Updated to remove bulk checkboxes and add individual delete buttons
- Added `confirmDeleteTask()` JavaScript function for deletion confirmation
- Removed bulk delete form and modal

**Features:**
- Prevents deletion of tasks with time entries (with informative message)
- Permission check (only admin or task creator can delete)
- Uses `window.showConfirm()` for consistent UI

### 2. Project Status: Inactive Support

**Previous Behavior:**
- Projects had only two statuses: 'active' and 'archived'
- No middle ground for temporarily pausing a project

**New Behavior:**
- Projects now support three statuses: 'active', 'inactive', and 'archived'
- Inactive status allows projects to be temporarily paused without archiving
- Clear visual distinction with warning color badge

**Files Modified:**
- `app/models/project.py` - Added `deactivate()` and `activate()` methods
- `app/routes/projects.py` - Added `/projects/<id>/deactivate` and `/projects/<id>/activate` routes
- `templates/projects/list.html` - Updated to show inactive status and action buttons

**New Routes:**
- `POST /projects/<id>/deactivate` - Mark project as inactive
- `POST /projects/<id>/activate` - Reactivate an inactive project

**Status Transitions:**
- Active → Inactive → Active (reactivate)
- Active → Archived → Active (unarchive)
- Inactive → Archived → Active (unarchive)
- Inactive → Active (activate)

**Visual Indicators:**
- Active: Green badge with check icon
- Inactive: Yellow/Warning badge with pause icon
- Archived: Gray badge with archive icon

### 3. Consistent Deletion Handling

**Standardization:**
All three entities (tasks, projects, clients) now use the same deletion pattern:

1. Individual delete button per item in list view
2. Confirmation dialog using `window.showConfirm()`
3. Permission checks (admin only for projects/clients, admin or creator for tasks)
4. Prevention of deletion when dependencies exist (time entries, projects, etc.)
5. Informative error messages when deletion is not allowed

**Deleted Modals:**
- Removed Bootstrap modal from projects list
- Now uses consistent `window.showConfirm()` pattern across all entities

### 4. Projects List Enhancements

**Summary Cards:**
- Added 4-column layout showing:
  - Total Projects
  - Active Projects
  - Inactive Projects (new)
  - Archived Projects
  - Total Hours across all projects

**Filter Options:**
- Added "Inactive" to status filter dropdown
- Allows filtering projects by:
  - All statuses
  - Active only
  - Inactive only (new)
  - Archived only

**Action Buttons:**
Each project row now shows contextual actions based on status:

**For Active Projects:**
- View
- Edit
- Mark as Inactive (new)
- Archive
- Delete

**For Inactive Projects:**
- View
- Edit
- Activate (new)
- Archive
- Delete

**For Archived Projects:**
- View
- Edit
- Unarchive
- Delete

### 5. JavaScript Improvements

**New Functions:**
- `confirmDeleteTask()` - Task deletion with time entry check
- `confirmDeleteProject()` - Project deletion with time entry check
- `confirmArchiveProject()` - Archive confirmation
- `confirmUnarchiveProject()` - Unarchive confirmation
- `confirmActivateProject()` - Activate confirmation (new)
- `confirmDeactivateProject()` - Deactivate confirmation (new)
- `submitProjectAction()` - Generic form submission helper

**Features:**
- Fallback to native `confirm()` if `window.showConfirm()` not available
- Fallback to native `alert()` if `window.showAlert()` not available
- CSRF token handling for all form submissions
- Internationalization support via JSON data blocks

## Testing

### Test Coverage

New test file: `tests/test_project_inactive_status.py`

**Tests Include:**
1. Project default status verification
2. Deactivate functionality
3. Activate from inactive functionality
4. Archive from inactive functionality
5. Complete status transition cycle
6. Deactivate route endpoint
7. Activate route endpoint
8. Filter by inactive status
9. Task list delete buttons verification

### Running Tests

```bash
# Run all tests
pytest tests/test_project_inactive_status.py

# Run specific test class
pytest tests/test_project_inactive_status.py::TestProjectInactiveStatus

# Run with verbose output
pytest tests/test_project_inactive_status.py -v
```

## Migration Notes

### Database Schema

**No database migration required!**

The existing `projects.status` column is a `VARCHAR(20)` which already supports storing 'active', 'inactive', or 'archived' values. The changes are code-only.

### Existing Data

All existing projects will continue to work:
- Projects with `status='active'` remain active
- Projects with `status='archived'` remain archived
- No data migration needed

## User Impact

### Benefits

1. **Better Project Management:**
   - Can temporarily pause projects without archiving them
   - Clear visual distinction between different project states
   - More granular control over project lifecycle

2. **Improved Task Deletion:**
   - Faster deletion workflow (no checkbox selection needed)
   - Clearer action buttons in list view
   - Better mobile experience with individual action buttons

3. **Consistent UX:**
   - All entities use the same deletion pattern
   - Consistent confirmation dialogs
   - Predictable behavior across the application

### Breaking Changes

**None.** All changes are backward compatible:
- Existing status values remain valid
- Existing routes still work
- No API changes

## Future Enhancements

Potential future improvements:
1. Bulk status changes (e.g., bulk activate/deactivate)
2. Scheduled status transitions
3. Status change history/audit log
4. Dashboard widgets for status overview
5. Notifications when projects become inactive

## Internationalization

All new strings are translatable:
- "Inactive" status label
- "Mark as inactive" action
- "Activate" action
- Confirmation messages

Translation keys added to `i18n-json-projects-list`:
- `status_inactive`
- `confirm_activate`
- `confirm_deactivate`

## Technical Notes

### Code Quality

- All new code follows existing patterns
- Proper error handling and flash messages
- Permission checks for all admin actions
- CSRF protection on all forms
- Responsive design maintained

### Performance

No performance impact:
- No additional database queries
- Existing indexes still apply
- Client-side filtering uses same logic

## Documentation Updates

Files updated:
- This file (DELETION_AND_STATUS_IMPROVEMENTS.md)
- Test documentation in `tests/test_project_inactive_status.py`

## Related Memories

This implementation follows the user's preferences:
- Database schema changes should use Alembic migrations (Memory ID: 8330340, 8329489)
- All new features require unit tests (Memory ID: 9751130)
- Documentation must be added for new features (Memory ID: 9751130)

