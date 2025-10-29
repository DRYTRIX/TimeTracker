# User Deletion Feature

## Overview

The user deletion feature allows administrators to permanently delete user accounts from the system. This feature includes comprehensive safety checks to prevent accidental deletion of critical data or system administrators.

## Feature Implementation Date

**Date**: October 29, 2025  
**Version**: Latest  
**Status**: ✅ Complete

## Access Control

### Who Can Delete Users?

- **Admin users**: Full access to delete any user (except themselves if they're the last admin)
- **Regular users**: No access to user deletion functionality
- **Permissions**: Requires `delete_users` permission

### Who Cannot Be Deleted?

1. **The last active administrator**: The system prevents deletion of the last active admin to ensure the system remains manageable
2. **Users with time entries**: Users who have logged time entries cannot be deleted to preserve data integrity
3. **Current logged-in user**: Users cannot delete their own account from the user list view

## User Interface

### Location

The delete functionality is accessible from the **Admin Panel → Manage Users** page:

```
/admin/users
```

### UI Elements

1. **Delete Button**: Appears next to each user (except current user) in the user list
2. **Confirmation Dialog**: Shows before deletion with appropriate warnings
3. **Error Messages**: Clear feedback when deletion is not allowed

### Delete Button Behavior

- **Visible**: For all users except the currently logged-in admin
- **Click Action**: Opens a confirmation dialog
- **Confirmation**: Shows user's name and warning about permanent deletion
- **With Time Entries**: Shows a special warning that the user cannot be deleted

## Safety Checks

### Pre-Deletion Validation

The system performs the following checks before allowing deletion:

#### 1. Admin Protection
```python
# Don't allow deleting the last admin
if user.is_admin:
    admin_count = User.query.filter_by(role='admin', is_active=True).count()
    if admin_count <= 1:
        flash('Cannot delete the last administrator', 'error')
        return redirect(url_for('admin.list_users'))
```

#### 2. Data Integrity Protection
```python
# Don't allow deleting users with time entries
if user.time_entries.count() > 0:
    flash('Cannot delete user with existing time entries', 'error')
    return redirect(url_for('admin.list_users'))
```

### Frontend Validation

JavaScript validation checks time entry count before submitting the form:

```javascript
function confirmDeleteUser(userId, username, timeEntriesCount) {
    // Check if user has time entries
    if (timeEntriesCount > 0) {
        // Show warning dialog (cannot delete)
        showConfirm('Cannot delete user...', { 
            variant: 'warning',
            showCancel: false
        });
        return false;
    }
    
    // Show confirmation dialog
    showConfirm('Are you sure...', {
        variant: 'danger'
    }).then(function(ok) {
        if (ok) {
            // Submit delete form
        }
    });
}
```

## Database Cascading Behavior

When a user is deleted, the following related data is automatically handled:

### ✅ Cascaded (Deleted)

1. **Time Entries**: All time entries are deleted (but deletion is blocked if any exist)
2. **Project Costs**: User-specific project cost records are deleted
3. **Favorite Projects**: User's favorite project associations are removed

### ⚠️ Nullified (Set to NULL)

1. **Task Assignments**: Tasks assigned to the user have `assigned_to` set to NULL
2. **User Roles**: Many-to-many role associations are removed

### ❌ Protected (Prevents Deletion)

1. **Created Tasks**: Users who created tasks cannot be deleted (enforced by database constraint)
2. **Time Entries**: Users with time entries cannot be deleted (enforced by application logic)

## API Endpoints

### Delete User

**Endpoint**: `POST /admin/users/<user_id>/delete`

**Authentication**: Required (Admin only)

**Parameters**:
- `user_id` (path parameter): ID of the user to delete

**Response Codes**:
- `200`: Success (redirects to user list with success message)
- `302`: Redirects with error message if deletion is not allowed
- `404`: User not found
- `403`: Insufficient permissions

**Example Usage**:
```python
# Via route
url_for('admin.delete_user', user_id=123)

# Expected redirect
→ /admin/users (with flash message)
```

## Testing

The feature includes comprehensive tests:

### Unit Tests (`tests/test_admin_users.py`)

- ✅ Test successful user deletion
- ✅ Test deletion with time entries (should fail)
- ✅ Test deletion of last admin (should fail)
- ✅ Test deletion by non-admin (should be denied)
- ✅ Test deletion of non-existent user (404)
- ✅ Test UI shows/hides delete buttons appropriately

### Model Tests (`tests/test_models_comprehensive.py`)

- ✅ Test user deletion without relationships
- ✅ Test cascading to project costs
- ✅ Test cascading to time entries
- ✅ Test removal from favorite projects
- ✅ Test task assignment nullification
- ✅ Test protection for task creators

### Smoke Tests (`tests/test_admin_users.py`)

- ✅ End-to-end deletion workflow
- ✅ Critical safety checks
- ✅ UI accessibility tests
- ✅ Permission enforcement

### Running Tests

```bash
# Run all admin user tests
pytest tests/test_admin_users.py -v

# Run only smoke tests
pytest tests/test_admin_users.py -v -m smoke

# Run all user deletion model tests
pytest tests/test_models_comprehensive.py::test_user_deletion -v
```

## Error Messages

| Scenario | Message | Action |
|----------|---------|--------|
| User has time entries | "Cannot delete user with existing time entries" | Show error, prevent deletion |
| Last administrator | "Cannot delete the last administrator" | Show error, prevent deletion |
| User not found | 404 error page | Show not found |
| No permission | Redirect to dashboard | Show access denied |
| Success | "User '[username]' deleted successfully" | Redirect to user list |

## Implementation Details

### Backend Route

**File**: `app/routes/admin.py`

**Function**: `delete_user(user_id)`

**Decorators**:
- `@admin_bp.route('/admin/users/<int:user_id>/delete', methods=['POST'])`
- `@login_required`
- `@admin_or_permission_required('delete_users')`

### Template

**File**: `app/templates/admin/users.html`

**Components**:
1. Delete button (conditional rendering)
2. Hidden form for DELETE request
3. JavaScript confirmation handler
4. Internationalized error messages

## Security Considerations

### CSRF Protection

- All delete requests use POST method
- CSRF tokens are required (Flask-WTF)
- Forms include CSRF token validation

### Permission Checks

- Route-level permission enforcement via `@admin_or_permission_required`
- Additional checks in function body for special cases
- Session-based authentication required

### Data Integrity

- Database-level foreign key constraints
- Application-level validation before deletion
- Transaction rollback on errors

## Best Practices for Administrators

### Before Deleting a User

1. **Check Time Entries**: Verify if the user has logged any time
2. **Transfer Data**: If needed, reassign tasks to other users
3. **Export Data**: Consider exporting user's data before deletion
4. **Notify Stakeholders**: Inform team members if the user was involved in active projects

### When Deletion Fails

1. **Time Entries Present**: 
   - Option 1: Keep the user as inactive instead of deleting
   - Option 2: Archive time entries if appropriate
   
2. **Last Admin**:
   - Promote another user to admin role first
   - Then delete the admin if still needed

### Alternative to Deletion

Instead of deleting users, consider:

1. **Deactivate User**: Set `is_active = False`
   - Preserves all data and relationships
   - User cannot log in
   - Can be reactivated if needed

2. **Archive Projects**: Archive or complete any active projects first

## Future Enhancements

Potential improvements for this feature:

- [ ] Soft delete option (mark as deleted but keep in database)
- [ ] Bulk user deletion
- [ ] User deletion audit log
- [ ] Export user data before deletion
- [ ] Reassign user's data to another user
- [ ] Deletion confirmation via email
- [ ] Admin approval workflow for user deletion

## Troubleshooting

### Issue: Cannot delete user

**Cause**: User has time entries or is the last admin

**Solution**: 
1. Check error message for specific reason
2. For time entries: Consider deactivating instead
3. For last admin: Create another admin first

### Issue: Delete button not showing

**Cause**: May be the current logged-in user or permission issue

**Solution**:
1. Verify you're logged in as admin
2. Check if trying to delete your own account
3. Verify `delete_users` permission

### Issue: Permission denied

**Cause**: User doesn't have admin rights or `delete_users` permission

**Solution**:
1. Log in as an administrator
2. Check role assignments in permission system

## Related Documentation

- [User Management](../admin/USER_MANAGEMENT.md)
- [Permissions System](../security/PERMISSIONS.md)
- [Admin Panel](../admin/ADMIN_PANEL.md)
- [Testing Guide](../development/TESTING.md)

## Changelog

### Version 1.0 (October 29, 2025)
- ✅ Initial implementation of user deletion feature
- ✅ UI integration with user list page
- ✅ Safety checks for admin and data protection
- ✅ Comprehensive test coverage
- ✅ Documentation completed

