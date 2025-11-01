# Bulk Task Operations

This document describes the bulk task operations feature that allows users to perform actions on multiple tasks simultaneously.

## Overview

The bulk task operations feature provides an efficient way to manage multiple tasks at once, reducing the time and effort required for common administrative tasks. This feature is available on the main task list page.

## Features

### 1. Multi-Select Checkboxes
- Each task in the list has a checkbox for selection
- A "Select All" checkbox in the header selects/deselects all visible tasks
- Selected count is displayed in the bulk actions menu
- Visual feedback shows which tasks are selected

### 2. Bulk Status Change
Change the status of multiple tasks simultaneously.

**How to use:**
1. Select one or more tasks using checkboxes
2. Click "Bulk Actions" button
3. Select "Change Status"
4. Choose the desired status from the dropdown
5. Click "Update Status"

**Supported statuses:**
- To Do
- In Progress
- Review
- Done
- Cancelled

**Behavior:**
- Updates all selected tasks to the chosen status
- When reopening completed tasks, automatically clears the `completed_at` timestamp
- Respects permission checks (users can only update tasks they created)
- Provides feedback on success and any skipped tasks

### 3. Bulk Assignment
Assign multiple tasks to a user at once.

**How to use:**
1. Select one or more tasks using checkboxes
2. Click "Bulk Actions" button
3. Select "Assign To"
4. Choose the user from the dropdown
5. Click "Assign Tasks"

**Behavior:**
- Assigns all selected tasks to the chosen user
- Users can only assign tasks they created (unless they're admin)
- Provides feedback on success and any skipped tasks

### 4. Bulk Move to Project
Move multiple tasks to a different project.

**How to use:**
1. Select one or more tasks using checkboxes
2. Click "Bulk Actions" button
3. Select "Move to Project"
4. Choose the target project from the dropdown
5. Click "Move Tasks"

**Behavior:**
- Moves all selected tasks to the target project
- Automatically updates related time entries to match the new project
- Logs task activity for the project change
- Users can only move tasks they created (unless they're admin)
- Only active projects are shown in the dropdown

### 5. Bulk Delete
Delete multiple tasks at once (with confirmation).

**How to use:**
1. Select one or more tasks using checkboxes
2. Click "Bulk Actions" button
3. Select "Delete"
4. Confirm the deletion in the dialog
5. Click "Delete" to proceed

**Behavior:**
- Requires confirmation before deletion
- Tasks with existing time entries are automatically skipped (not deleted)
- Users can only delete tasks they created (unless they're admin)
- Provides feedback on success and any skipped tasks
- Deletion is permanent and cannot be undone

## Permissions

Bulk operations respect the following permission rules:

- **Regular Users**: Can only perform bulk operations on tasks they created
- **Admin Users**: Can perform bulk operations on any tasks
- **Permission Violations**: Tasks that the user doesn't have permission to modify are automatically skipped with a warning message

## User Interface

### Bulk Actions Button
Located in the task list toolbar, the button shows:
- Number of selected tasks
- Disabled state when no tasks are selected
- Dropdown menu with all available bulk operations

### Dialog Boxes
Each bulk operation (except delete) has a dedicated dialog with:
- Clear title explaining the action
- Dropdown for selecting the target (status, user, or project)
- Cancel button to abort the operation
- Submit button to perform the action

### Confirmation Dialog
The bulk delete operation shows a confirmation dialog with:
- Warning about permanent deletion
- Note about tasks with time entries being skipped
- Cancel and Delete buttons

## Technical Details

### Routes

All bulk operation routes are POST endpoints:

```
POST /tasks/bulk-delete        - Delete multiple tasks
POST /tasks/bulk-status        - Change status for multiple tasks
POST /tasks/bulk-assign        - Assign multiple tasks to a user
POST /tasks/bulk-move-project  - Move multiple tasks to a project
```

### Request Format

All routes expect the following POST data:

```
task_ids[]: Array of task IDs (e.g., ['1', '2', '3'])
status: Target status (for bulk-status)
assigned_to: User ID (for bulk-assign)
project_id: Project ID (for bulk-move-project)
csrf_token: CSRF protection token
```

### Response Behavior

- **Success**: Redirects to task list with success flash message
- **Partial Success**: Redirects with success message and warning about skipped tasks
- **Error**: Redirects with error flash message
- **No Selection**: Returns warning about no tasks selected

### Database Operations

- All bulk operations are performed in a single database transaction
- Changes are committed only after all validations pass
- Failed operations result in a rollback
- Activity logging for audit trail (where applicable)

## Best Practices

1. **Review Selection**: Always review selected tasks before performing bulk operations
2. **Start Small**: Test with a small number of tasks first
3. **Check Permissions**: Ensure you have permission to modify the selected tasks
4. **Time Entries**: Remember that tasks with time entries cannot be deleted
5. **Backup Data**: For critical operations, ensure you have recent backups

## Error Handling

The feature includes comprehensive error handling:

- **No Tasks Selected**: Friendly warning message
- **Invalid Input**: Validation errors with specific messages
- **Permission Denied**: Tasks are skipped with warning
- **Database Errors**: Safe rollback with error message
- **Network Issues**: Standard browser error handling

## Testing

Comprehensive tests are available in `tests/test_bulk_task_operations.py`:

- Unit tests for each operation
- Integration tests with real data
- Permission checking tests
- Error handling tests
- Smoke tests for route availability

To run the tests:

```bash
pytest tests/test_bulk_task_operations.py -v
```

## Future Enhancements

Potential improvements for future versions:

1. **Bulk Priority Change**: Change priority for multiple tasks
2. **Bulk Due Date Update**: Set due dates for multiple tasks
3. **Export Selected**: Export only selected tasks
4. **Undo Operation**: Ability to undo recent bulk operations
5. **Keyboard Shortcuts**: Quick access via keyboard shortcuts
6. **Advanced Selection**: Select by filters (e.g., all overdue tasks)

## Troubleshooting

### Tasks Not Being Updated
- Check that you have permission to modify the tasks
- Verify that the tasks exist and haven't been deleted
- Look for error messages in the flash notifications

### Bulk Delete Skipping Tasks
- Tasks with time entries cannot be deleted
- Delete time entries first, then retry
- Alternatively, use task archiving instead

### Selection Not Working
- Clear browser cache and reload
- Check JavaScript console for errors
- Ensure JavaScript is enabled in your browser

## Support

For issues or questions about bulk task operations:

1. Check this documentation first
2. Review the test suite for examples
3. Check the application logs for errors
4. Contact your system administrator

