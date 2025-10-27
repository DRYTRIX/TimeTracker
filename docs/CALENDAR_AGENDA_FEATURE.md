# Calendar/Agenda Support Documentation

## Overview

The Calendar/Agenda feature in TimeTracker provides a comprehensive view of all your events, tasks, and time entries in one place. This feature helps you plan your work, schedule meetings, and track deadlines more effectively.

## Features

### Calendar Views

The calendar supports three different view modes:

1. **Day View**: Shows hourly time slots for a single day with all events and time entries
2. **Week View**: Displays a weekly grid with events across 7 days
3. **Month View**: Traditional monthly calendar with events displayed on each day

### Event Management

#### Event Types

- **Event**: General calendar events
- **Meeting**: Scheduled meetings with clients or team members
- **Appointment**: One-on-one appointments
- **Reminder**: Simple reminders for tasks or deadlines
- **Deadline**: Important deadlines linked to tasks or projects

#### Event Properties

Each calendar event can have the following properties:

- **Title** (required): The name of the event
- **Description**: Detailed description of the event
- **Start Time** (required): When the event starts
- **End Time** (required): When the event ends
- **All-Day**: Mark event as all-day (no specific time)
- **Location**: Physical or virtual location
- **Color**: Custom color for visual organization
- **Reminder**: Set reminder (5, 15, 30 minutes, 1 hour, or 1 day before)
- **Private**: Mark event as private (visible only to you)

#### Associated Items

Events can be linked to:

- **Project**: Associate event with a specific project
- **Task**: Link event to a task for better tracking
- **Client**: Connect event to a client

### Recurring Events

Create events that repeat on a schedule:

- Set recurrence pattern using RRULE format
- Example: `FREQ=WEEKLY;BYDAY=MO,WE,FR` for events every Monday, Wednesday, and Friday
- Set an optional end date for the recurrence

### Integration with Tasks and Time Entries

The calendar automatically displays:

- **Tasks with due dates**: Shown as badges on their due date
- **Time entries**: Your tracked time appears on the calendar
- Toggle visibility of these items using the filter checkboxes

## User Guide

### Accessing the Calendar

1. Log in to TimeTracker
2. Click on the **Calendar** link in the navigation menu
3. The calendar will open with the current month view

### Creating a New Event

#### Method 1: Using the "New Event" Button

1. Click the **"New Event"** button at the top of the calendar
2. Fill in the event details:
   - Enter a title
   - Set start and end dates/times
   - Add optional description, location, etc.
   - Link to project, task, or client if desired
3. Click **"Create Event"** to save

#### Method 2: Quick Creation (Month View)

1. In month view, click on any date cell
2. This opens the new event form with the date pre-filled
3. Complete the event details and save

### Viewing Events

#### In Calendar View

- Events appear as colored badges on their scheduled dates
- In month view, up to 3 events are shown per day
- If more than 3 events exist, a "+X more" indicator appears
- Click any event badge to view its details

#### Event Detail Page

1. Click on an event to view its full details
2. The detail page shows:
   - Full event information
   - Associated project, task, or client (with links)
   - Duration calculation
   - Created and updated timestamps

### Editing Events

1. Click on an event to open its detail page
2. Click the **"Edit"** button
3. Make your changes
4. Click **"Update Event"** to save

### Deleting Events

1. Open the event detail page
2. Click the **"Delete"** button
3. Confirm the deletion

### Drag and Drop (Coming Soon)

Future versions will support:
- Dragging events to reschedule them
- Resizing events to adjust duration

### Filtering the Calendar

Use the checkboxes at the top of the calendar to toggle visibility:

- **Events**: Show/hide calendar events
- **Tasks**: Show/hide tasks with due dates
- **Time Entries**: Show/hide tracked time

### Navigation

- **Today**: Jump to today's date
- **Previous/Next**: Navigate to previous/next day, week, or month
- **Date Selector**: Click on the date display to pick a specific date

## API Documentation

### API Endpoints

#### Get Events in Date Range

```http
GET /api/calendar/events?start={start_date}&end={end_date}&include_tasks={boolean}&include_time_entries={boolean}
```

**Parameters:**
- `start`: ISO 8601 datetime (required)
- `end`: ISO 8601 datetime (required)
- `include_tasks`: Include tasks with due dates (default: true)
- `include_time_entries`: Include time entries (default: true)

**Response:**
```json
{
  "events": [...],
  "tasks": [...],
  "time_entries": [...]
}
```

#### Create Event

```http
POST /api/calendar/events
Content-Type: application/json
```

**Request Body:**
```json
{
  "title": "Team Meeting",
  "description": "Weekly sync",
  "start": "2025-01-15T10:00:00",
  "end": "2025-01-15T11:00:00",
  "allDay": false,
  "location": "Conference Room A",
  "eventType": "meeting",
  "projectId": 1,
  "taskId": null,
  "clientId": null,
  "color": "#3b82f6",
  "reminderMinutes": 30,
  "isPrivate": false,
  "isRecurring": false,
  "recurrenceRule": null,
  "recurrenceEndDate": null
}
```

**Response:**
```json
{
  "success": true,
  "event": { /* event object */ },
  "message": "Event created successfully"
}
```

#### Update Event

```http
PUT /api/calendar/events/{event_id}
Content-Type: application/json
```

**Request Body:** Same as create (partial updates supported)

#### Delete Event

```http
DELETE /api/calendar/events/{event_id}
```

**Response:**
```json
{
  "success": true,
  "message": "Event deleted successfully"
}
```

#### Move Event (Drag & Drop)

```http
POST /api/calendar/events/{event_id}/move
Content-Type: application/json
```

**Request Body:**
```json
{
  "start": "2025-01-16T10:00:00",
  "end": "2025-01-16T11:00:00"
}
```

#### Resize Event

```http
POST /api/calendar/events/{event_id}/resize
Content-Type: application/json
```

**Request Body:**
```json
{
  "end": "2025-01-15T12:00:00"
}
```

## Database Schema

### CalendarEvent Model

```python
class CalendarEvent(db.Model):
    id = Integer (Primary Key)
    user_id = Integer (Foreign Key to users.id)
    title = String(200) (Required)
    description = Text
    start_time = DateTime (Required, Indexed)
    end_time = DateTime (Required, Indexed)
    all_day = Boolean (Default: False)
    location = String(200)
    event_type = String(50) (Default: 'event', Indexed)
    
    # Associations
    project_id = Integer (Foreign Key to projects.id)
    task_id = Integer (Foreign Key to tasks.id)
    client_id = Integer (Foreign Key to clients.id)
    
    # Recurring events
    is_recurring = Boolean (Default: False)
    recurrence_rule = String(200)  # RRULE format
    recurrence_end_date = DateTime
    parent_event_id = Integer (Foreign Key to calendar_events.id)
    
    # Reminders and customization
    reminder_minutes = Integer
    color = String(7)  # Hex color code
    is_private = Boolean (Default: False)
    
    # Timestamps
    created_at = DateTime
    updated_at = DateTime
```

### Relationships

- `user`: Many-to-one relationship with User
- `project`: Many-to-one relationship with Project
- `task`: Many-to-one relationship with Task
- `client`: Many-to-one relationship with Client
- `parent_event`: Self-referential for recurring event instances
- `child_events`: One-to-many relationship for recurring event series

## Migration

The calendar feature is added via Alembic migration:

```bash
# Migration file: migrations/versions/034_add_calendar_events_table.py
flask db upgrade
```

This creates the `calendar_events` table with all necessary indexes and foreign key constraints.

## Permissions

- **Users** can:
  - Create their own events
  - View their own events
  - Edit their own events
  - Delete their own events
  - View events linked to their assigned tasks

- **Admins** can:
  - View all events (except private events of other users)
  - Edit any event
  - Delete any event

## Best Practices

### Event Organization

1. **Use Colors Wisely**: Assign colors to different event types for quick visual identification
   - Blue (#3b82f6) for regular meetings
   - Red (#ef4444) for deadlines
   - Green (#10b981) for client appointments
   - Purple (#8b5cf6) for personal events

2. **Link to Projects**: Always link events to projects when relevant for better reporting

3. **Set Reminders**: Use reminders for important meetings to avoid missing them

4. **Use Recurring Events**: Set up recurring events for weekly meetings instead of creating them manually

### Performance Tips

1. The calendar loads events for the visible date range only
2. Large organizations should consider archiving old events (older than 6 months)
3. Use the filters to focus on what's important

### Integration with Workflows

1. **Task Planning**: Create events for task work sessions
2. **Client Meetings**: Link meetings to clients for better relationship tracking
3. **Project Milestones**: Use deadline events for project milestones
4. **Time Blocking**: Create events to block time for focused work

## Troubleshooting

### Events Not Showing

1. Check date range - ensure events fall within the visible calendar range
2. Verify filters - ensure event type is not filtered out
3. Check permissions - private events are only visible to their creator

### Cannot Edit Event

- Verify you are the event owner or an admin
- Check that the event still exists
- Ensure you're logged in with the correct account

### Recurring Events Not Working

- Verify RRULE format is correct
- Check that recurrence end date is after start date
- Ensure parent event exists for child instances

## Technical Details

### Frontend

- **JavaScript**: `app/static/calendar.js` - Calendar rendering and interaction
- **CSS**: `app/static/calendar.css` - Calendar styling
- **Templates**: `app/templates/calendar/` - HTML templates

### Backend

- **Models**: `app/models/calendar_event.py` - Data model
- **Routes**: `app/routes/calendar.py` - API and view routes
- **Tests**: `tests/test_calendar_event_model.py`, `tests/test_calendar_routes.py`

### Testing

Run calendar tests:

```bash
# Model tests
pytest tests/test_calendar_event_model.py -v

# Route tests
pytest tests/test_calendar_routes.py -v

# All calendar tests
pytest tests/test_calendar* -v

# Smoke tests
pytest tests/test_calendar* -m smoke
```

## Future Enhancements

Potential future improvements:

1. **iCal/ICS Import/Export**: Import events from other calendar applications
2. **Sharing**: Share events with other users or teams
3. **Email Notifications**: Send email reminders for events
4. **Mobile App**: Dedicated mobile calendar view
5. **Time Zone Support**: Better handling of events across time zones
6. **Event Templates**: Create reusable event templates
7. **Attendees**: Add multiple attendees to events
8. **Conflict Detection**: Warn about overlapping events

## Support

For issues or feature requests related to the calendar:

1. Check this documentation first
2. Review the test files for examples
3. Check the GitHub issues for known problems
4. Contact your system administrator

## Version History

- **Version 1.0** (2025-10-27): Initial calendar/agenda support
  - Day, week, and month views
  - Event CRUD operations
  - Integration with tasks and time entries
  - Recurring event support
  - API endpoints for all operations

## Related Documentation

- [TimeTracker User Guide](README.md)
- [API Documentation](API_DOCUMENTATION.md)
- [Task Management Guide](TASK_MANAGEMENT.md)
- [Project Management Guide](PROJECT_MANAGEMENT.md)

