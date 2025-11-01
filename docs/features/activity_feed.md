# Activity Feed Widget

The Activity Feed Widget provides real-time visibility into team activities and creates a comprehensive audit trail for your TimeTracker instance.

## Overview

The Activity Feed automatically tracks and displays all major actions performed in the system, including:
- Project management (create, update, delete, archive)
- Task operations (create, update, delete, status changes, assignments)
- Time tracking (start/stop timer, manual entries, edits)
- Invoice activities (create, send, mark paid)
- Client management
- And more...

## Features

### Dashboard Widget

The Activity Feed Widget appears on the main dashboard in the right sidebar, displaying:
- **Recent Activities**: Last 10 activities by default
- **User Attribution**: Shows who performed each action
- **Timestamps**: Displays how long ago each action occurred
- **Action Icons**: Visual indicators for different types of actions
- **Entity Details**: Clear description of what was done

### Filtering

Click the filter icon (🔽) to filter activities by type:
- All Activities
- Projects only
- Tasks only
- Time Entries only
- Invoices only
- Clients only

### Real-time Updates

The activity feed automatically refreshes every 30 seconds to show the latest team activities.

## User Permissions

### Regular Users
- See their own activities
- View activities related to projects they have access to

### Administrators
- See all activities across the entire organization
- Access to advanced filtering and export options
- View activity statistics

## API Endpoints

### Get Activities

```http
GET /api/activities
```

**Query Parameters:**
- `limit` (int): Number of activities to return (default: 50)
- `page` (int): Page number for pagination (default: 1)
- `user_id` (int): Filter by specific user (admin only)
- `entity_type` (string): Filter by entity type (project, task, time_entry, invoice, client)
- `action` (string): Filter by action type (created, updated, deleted, started, stopped, etc.)
- `start_date` (ISO string): Filter activities after this date
- `end_date` (ISO string): Filter activities before this date

**Response:**
```json
{
  "activities": [
    {
      "id": 123,
      "user_id": 5,
      "username": "john.doe",
      "display_name": "John Doe",
      "action": "created",
      "entity_type": "project",
      "entity_id": 42,
      "entity_name": "New Website",
      "description": "Created project \"New Website\"",
      "extra_data": {},
      "created_at": "2025-10-30T14:30:00Z"
    }
  ],
  "total": 150,
  "pages": 3,
  "current_page": 1,
  "has_next": true,
  "has_prev": false
}
```

### Get Activity Statistics

```http
GET /api/activities/stats?days=7
```

**Query Parameters:**
- `days` (int): Number of days to analyze (default: 7)

**Response:**
```json
{
  "total_activities": 342,
  "entity_counts": {
    "project": 45,
    "task": 128,
    "time_entry": 156,
    "invoice": 13
  },
  "action_counts": {
    "created": 89,
    "updated": 167,
    "deleted": 12,
    "started": 42,
    "stopped": 32
  },
  "user_activity": [
    {
      "username": "john.doe",
      "display_name": "John Doe",
      "count": 156
    }
  ],
  "period_days": 7
}
```

## Action Types

The system tracks the following action types:

| Action | Description | Used For |
|--------|-------------|----------|
| `created` | Entity was created | Projects, Tasks, Clients, Invoices |
| `updated` | Entity was modified | Projects, Tasks, Time Entries |
| `deleted` | Entity was removed | Projects, Tasks, Time Entries |
| `started` | Timer started | Time Entries |
| `stopped` | Timer stopped | Time Entries |
| `completed` | Task marked as done | Tasks |
| `assigned` | Task assigned to user | Tasks |
| `commented` | Comment added | Tasks |
| `status_changed` | Status modified | Tasks, Invoices |
| `sent` | Invoice sent to client | Invoices |
| `paid` | Payment recorded | Invoices |
| `archived` | Entity archived | Projects |
| `unarchived` | Entity unarchived | Projects |

## Entity Types

Activities can be tracked for the following entity types:

- `project` - Project management
- `task` - Task operations
- `time_entry` - Time tracking
- `invoice` - Invoicing
- `client` - Client management
- `user` - User administration (admin only)
- `comment` - Comments and discussions

## Integration Guide

### For Developers

To add activity logging to new features, use the `Activity.log()` method:

```python
from app.models import Activity

Activity.log(
    user_id=current_user.id,
    action='created',  # Action type
    entity_type='project',  # Entity type
    entity_id=project.id,
    entity_name=project.name,
    description=f'Created project "{project.name}"',
    extra_data={'client_id': client.id},  # Optional metadata
    ip_address=request.remote_addr,  # Optional
    user_agent=request.headers.get('User-Agent')  # Optional
)
```

**Best Practices:**

1. **Always log after successful operations** - Log after the database commit succeeds
2. **Provide clear descriptions** - Make descriptions human-readable
3. **Include relevant metadata** - Use `extra_data` for additional context
4. **Store entity names** - Cache the entity name in case it's deleted later
5. **Handle failures gracefully** - Activity logging includes built-in error handling

### Already Integrated

Activity logging is already integrated for:
- ✅ Projects (create, update, delete, archive, unarchive)
- ✅ Tasks (create, update, delete, status changes, assignments)
- ✅ Time Entries (start timer, stop timer, manual create, edit, delete)
- ⏳ Invoices (create, update, status change, payment, send) - *coming soon*
- ⏳ Clients (create, update, delete) - *coming soon*
- ⏳ Comments (create) - *coming soon*

## Use Cases

### Team Visibility
- See what your team members are working on
- Track project progress in real-time
- Understand team activity patterns

### Audit Trail
- Compliance and record-keeping
- Track who made what changes and when
- Identify suspicious or unusual activity

### Project Management
- Monitor task completion rates
- Track project milestones
- Review team productivity

### Troubleshooting
- Investigate issues by reviewing recent changes
- Identify when problems were introduced
- Track down missing or deleted items

## Configuration

No special configuration is required. The Activity Feed is enabled by default for all users.

### Database Indexes

The Activity model includes optimized indexes for:
- User-based queries (`user_id`, `created_at`)
- Entity lookups (`entity_type`, `entity_id`)
- Date range queries (`created_at`)

### Performance

- Activities are paginated to prevent slow page loads
- Old activities are automatically retained (no automatic cleanup)
- Database queries are optimized with proper indexes
- Widget auto-refreshes are throttled to every 30 seconds

## Privacy & Security

### Data Retention
- Activities are stored indefinitely by default
- Administrators can manually delete old activities if needed
- Consider implementing a retention policy for compliance

### Access Control
- Users can only see their own activities (unless admin)
- Administrators see all activities system-wide
- Activity logs cannot be edited or tampered with
- IP addresses and user agents are stored for security auditing

### GDPR Compliance
When a user requests data deletion:
1. Their activities are preserved for audit purposes
2. User information can be anonymized
3. Activities show "Deleted User" for anonymized accounts

## Troubleshooting

### Activities not appearing?

1. **Check permissions** - Regular users only see their own activities
2. **Verify integration** - Ensure the route has Activity.log() calls
3. **Database issues** - Check logs for database errors
4. **Browser cache** - Clear cache or hard refresh the dashboard

### Widget not loading?

1. **Check API endpoint** - Visit `/api/activities` directly
2. **JavaScript errors** - Check browser console for errors
3. **Authentication** - Ensure user is logged in
4. **Network issues** - Check network tab in dev tools

### Missing activities for certain actions?

Some features may not have activity logging integrated yet. Check the "Already Integrated" section above.

## Future Enhancements

Planned improvements for the Activity Feed:

- [ ] Export activities to CSV/JSON
- [ ] Email notifications for specific activities
- [ ] Advanced search and filtering
- [ ] Activity feed for specific projects/tasks
- [ ] Webhook integration for external systems
- [ ] Custom activity types and actions
- [ ] Activity trends and analytics dashboard

## Support

For issues or questions about the Activity Feed:
- Check the [FAQ](../faq.md)
- Review the [API Documentation](../api/README.md)
- Open an issue on GitHub
- Contact support

