# 📅 TimeTracker Calendar Features - Complete Guide

## Overview

The Calendar feature provides a comprehensive visual interface for viewing, creating, editing, and managing time entries. It includes drag-and-drop functionality, multiple views, filtering, recurring events, and export capabilities.

---

## ✨ Features

### 1. **Multiple Calendar Views**
- **Day View**: Hour-by-hour view of a single day
- **Week View**: 7-day week view with time slots (default)
- **Month View**: Monthly calendar with all-day event display
- **Agenda View**: List view grouped by date

### 2. **Visual Event Management**
- **Color-coded events** by project (10 distinct colors)
- **Detailed event information** on hover
- **Event duration** displayed in each block
- **Real-time current time indicator**
- **Today highlighting** in all views

### 3. **Drag-and-Drop Editing**
- **Move events** by dragging to different times/days
- **Resize events** by dragging edges to adjust duration
- **Auto-save** when events are moved or resized
- **Smooth animations** for all interactions

### 4. **Advanced Filtering**
- Filter by **Project**
- Filter by **Task** (dynamic based on selected project)
- Filter by **Tags** (with debounced search)
- **Clear all filters** with one click
- Filters apply across all views

### 5. **Event Creation**
- **Click and drag** to create new events
- **New Event button** for manual creation
- **Pre-select project** before creating
- Full form with:
  - Project selection (required)
  - Task selection (optional, dynamic)
  - Start/End date and time
  - Notes and tags
  - Billable flag

### 6. **Event Details & Editing**
- **Click any event** to view details
- **Detailed modal** showing:
  - Project and task information
  - Start/end times with formatted dates
  - Duration in hours
  - Notes and tags
  - Billable status
  - Source (manual vs automatic timer)
- **Quick edit** button to modify entry
- **Delete** button with confirmation

### 7. **Recurring Events**
- Manage **recurring time blocks**
- View all recurring templates
- See active/inactive status
- Edit or delete recurring blocks
- Automatic generation based on schedule
- Supports weekly recurrence with weekday selection

### 8. **Export Functionality**
- **iCal format** (.ics) - Import into Google Calendar, Outlook, Apple Calendar
- **CSV format** - Open in Excel, Google Sheets, or any spreadsheet software
- Exports respect current filters
- Exports current view's date range
- Includes all event details

### 9. **Smart Time Slot Configuration**
- Work hours: 6:00 AM to 10:00 PM
- 30-minute time slots
- Scrollable to any time
- Sticky header stays visible when scrolling

### 10. **Responsive Design**
- **Desktop-optimized** layout with side-by-side controls
- **Tablet-friendly** with collapsible controls
- **Mobile-responsive** with stacked layout
- **Touch-optimized** for mobile devices

---

## 🎯 Usage Guide

### Accessing the Calendar

Navigate to the calendar via:
1. **Main Navigation**: Work → Calendar
2. **Direct URL**: `/timer/calendar`

### Creating Time Entries

#### Method 1: Click and Drag
1. Select a project from the "Assign to project" dropdown
2. Click and drag on the calendar to select a time range
3. Form opens with pre-filled times
4. Fill in optional details (task, notes, tags)
5. Click "Create"

#### Method 2: New Event Button
1. Select a project from the "Assign to project" dropdown
2. Click the "New Event" button
3. Set start and end times manually
4. Fill in all details
5. Click "Create"

### Editing Time Entries

#### Quick Edit (Drag and Drop)
1. Click and drag an event to move it to a different time/day
2. Drag the top or bottom edge to resize (change duration)
3. Changes save automatically

#### Full Edit
1. Click on any event to open details
2. Click "Edit" button
3. Opens the full edit form
4. Make changes and save

### Deleting Time Entries

1. Click on any event
2. Click "Delete" button
3. Confirm deletion
4. Entry is removed from calendar

### Using Filters

#### Filter by Project
1. Select a project from "All Projects" dropdown
2. Calendar updates to show only that project's entries
3. Task filter becomes available

#### Filter by Task
1. First select a project
2. Select a task from "All Tasks" dropdown
3. Calendar shows only entries for that project+task

#### Filter by Tags
1. Type tags in the "Filter by tags" field
2. Search is debounced (waits 500ms after typing)
3. Calendar shows entries matching any tag

#### Clear Filters
Click the "Clear" button to reset all filters

### Changing Views

#### Calendar Views
- Click **Day** for day view
- Click **Week** for week view (default)
- Click **Month** for month view
- Click **Today** to jump to current date

#### Agenda View
1. Click **Agenda** button
2. View switches to list format
3. Events grouped by date
4. Click any event to see details

### Exporting Calendar Data

#### Export as iCal
1. Click "Export" dropdown
2. Select "iCal Format"
3. Downloads `.ics` file
4. Import into your calendar app

#### Export as CSV
1. Click "Export" dropdown
2. Select "CSV Format"
3. Downloads `.csv` file
4. Open in Excel or Google Sheets

**Note**: Exports include the current view's date range and respect any active filters.

### Managing Recurring Events

1. Click "Recurring" button
2. View all recurring time blocks
3. Each block shows:
   - Name and status
   - Associated project
   - Recurrence pattern
   - Time window
4. Click "Edit" to modify a block
5. Click "Delete" to remove a block
6. Click "New Recurring Block" to create one

---

## 🎨 Visual Design

### Color Coding

Events are automatically color-coded by project:
- **Project 1**: Blue (#3b82f6)
- **Project 2**: Red (#ef4444)
- **Project 3**: Green (#10b981)
- **Project 4**: Amber (#f59e0b)
- **Project 5**: Purple (#8b5cf6)
- And so on... (10 colors rotate)

### Event Display

Each event shows:
- **Title**: Project name • Task name (or note preview)
- **Time**: Start and end time
- **Visual**: Colored left border matching project
- **Hover**: Subtle lift animation

### Status Indicators

- **Billable**: Green badge
- **Non-billable**: Gray badge
- **Active Timer**: Pulsing indicator
- **Past Events**: Slightly dimmed

---

## ⚙️ Technical Details

### API Endpoints

#### Get Calendar Events
```
GET /api/calendar/events?start=<ISO>&end=<ISO>&project_id=<id>&task_id=<id>&tags=<string>
```

**Query Parameters:**
- `start` (required): ISO datetime for range start
- `end` (required): ISO datetime for range end
- `project_id` (optional): Filter by project
- `task_id` (optional): Filter by task
- `tags` (optional): Filter by tags (partial match)
- `user_id` (optional, admin only): View another user's calendar

**Response:**
```json
{
  "events": [
    {
      "id": 123,
      "title": "Project Name • Task Name",
      "start": "2025-10-07T09:00:00",
      "end": "2025-10-07T11:00:00",
      "editable": true,
      "allDay": false,
      "backgroundColor": "#3b82f6",
      "borderColor": "#3b82f6",
      "extendedProps": {
        "project_id": 1,
        "project_name": "Project Name",
        "task_id": 5,
        "task_name": "Task Name",
        "notes": "Some notes",
        "tags": "tag1, tag2",
        "billable": true,
        "duration_hours": 2.0,
        "user_id": 1,
        "source": "manual"
      }
    }
  ]
}
```

#### Export Calendar
```
GET /api/calendar/export?start=<ISO>&end=<ISO>&format=<ical|csv>&project_id=<id>
```

**Query Parameters:**
- `start` (required): ISO datetime for range start
- `end` (required): ISO datetime for range end
- `format` (default: ical): Export format (ical or csv)
- `project_id` (optional): Filter by project

**Response:**
- iCal: `.ics` file download
- CSV: `.csv` file download

#### Update Event Time
```
PUT /api/entry/<id>
{
  "start_time": "2025-10-07T09:00:00",
  "end_time": "2025-10-07T11:00:00"
}
```

#### Delete Event
```
DELETE /api/entry/<id>
```

#### Get Recurring Blocks
```
GET /api/recurring-blocks
```

### JavaScript Components

#### FullCalendar Configuration
```javascript
{
  initialView: 'timeGridWeek',
  selectable: true,
  editable: true,
  nowIndicator: true,
  firstDay: 1,  // Monday
  slotDuration: '00:30:00',
  slotMinTime: '06:00:00',
  slotMaxTime: '22:00:00',
  eventResizableFromStart: true
}
```

#### Event Handlers
- `select`: Handle time range selection
- `eventClick`: Show event details
- `eventDrop`: Handle drag move
- `eventResize`: Handle resize

### CSS Classes

**Calendar Container:**
- `.calendar-header` - Top control bar
- `.calendar-controls` - Button groups
- `.calendar-filters` - Filter controls
- `.calendar-legend` - Color legend

**Events:**
- `.fc-event` - Calendar event
- `.fc-event:hover` - Hover state

**Modals:**
- `.event-modal` - Modal overlay
- `.event-modal-content` - Modal dialog
- `.event-modal-header` - Modal header
- `.event-modal-body` - Modal content
- `.event-modal-footer` - Modal buttons

**Agenda View:**
- `.agenda-view` - Agenda container
- `.agenda-date-group` - Date grouping
- `.agenda-event` - Event item

---

## 🔧 Configuration

### Customizing Colors

Edit the color array in `app/routes/api.py`:

```python
def get_project_color(project_id):
    colors = [
        '#3b82f6',  # Blue
        '#ef4444',  # Red
        '#10b981',  # Green
        '#f59e0b',  # Amber
        '#8b5cf6',  # Purple
        # Add more colors...
    ]
    return colors[project_id % len(colors)]
```

### Adjusting Time Slots

Edit FullCalendar config in `templates/timer/calendar.html`:

```javascript
{
  slotDuration: '00:15:00',  // 15-minute slots
  slotMinTime: '08:00:00',   // Start at 8 AM
  slotMaxTime: '18:00:00',   // End at 6 PM
}
```

### Changing First Day of Week

The calendar's first day of week (Sunday vs Monday) is controlled by the user's **Week Starts On** setting in **My Settings** (Profile → My Settings). Users can choose Sunday, Monday, or Saturday. The timer calendar (FullCalendar) and date pickers respect this setting; no code changes are required.

### Date format in input fields

Date input fields on **Log Time**, **Time entries**, and **Gantt Charts** (and other screens that use the `user-date-input` class) display and accept dates in the user's preferred format (system default or personal override from Admin → Settings or My Settings). The app uses Flatpickr for these inputs so the display matches the chosen format (e.g. DD/MM/YYYY or DD.MM.YYYY); values are still submitted to the server as YYYY-MM-DD.

---

## 🚀 Performance

### Optimization Features

1. **Lazy Loading**: Events load only for visible date range
2. **Debounced Filters**: Tag filter waits 500ms before searching
3. **Efficient Queries**: Database queries use indexes
4. **Client-side Caching**: FullCalendar caches rendered events
5. **Minimal DOM Updates**: Only changed events are re-rendered

### Best Practices

1. **Use filters** to reduce displayed events
2. **Shorter date ranges** load faster
3. **Avoid excessive drag operations** in rapid succession
4. **Close modals** when not in use to free memory

---

## 📱 Mobile Support

### Mobile Optimizations

1. **Responsive Layout**: Single-column on small screens
2. **Touch Events**: Optimized tap and drag handlers
3. **Larger Touch Targets**: Buttons sized for finger interaction
4. **Simplified Views**: Day/Month preferred over week on mobile
5. **Collapsible Filters**: Filters stack vertically

### Mobile Limitations

- Drag-and-drop may be less precise on small touchscreens
- Week view can be cramped - use Day or Agenda instead
- Filter dropdowns may require scrolling

---

## ♿ Accessibility

### Keyboard Navigation

- **Tab**: Navigate between controls
- **Enter/Space**: Activate buttons
- **Escape**: Close modals
- **Arrow Keys**: Navigate calendar (when focused)

### Screen Reader Support

- ARIA labels on all interactive elements
- Semantic HTML structure
- Focus management in modals
- Descriptive button text

### Visual Accessibility

- High contrast colors
- Large click targets
- Clear hover states
- Focus indicators

---

## 🐛 Troubleshooting

### Events Not Loading

1. Check browser console for errors
2. Verify `/api/calendar/events` endpoint is accessible
3. Check date range parameters
4. Ensure user is authenticated

### Drag-and-Drop Not Working

1. Ensure `editable: true` in calendar config
2. Check user permissions
3. Verify event is not an active timer
4. Check for JavaScript errors

### Filters Not Applying

1. Clear browser cache
2. Check that filter dropdowns have values
3. Verify API endpoint supports filter parameters
4. Check network tab for API calls

### Export Not Downloading

1. Check popup blocker settings
2. Verify `/api/calendar/export` endpoint
3. Ensure date range is valid
4. Check server logs for errors

### Recurring Events Not Showing

1. Verify `/api/recurring-blocks` endpoint
2. Check that blocks are marked as active
3. Ensure date range includes block schedule
4. Verify block generation logic is running

---

## 🔜 Future Enhancements

Potential additions:

1. **Multi-user View**: See team calendars side-by-side
2. **Calendar Sync**: Two-way sync with Google Calendar/Outlook
3. **Time Zone Support**: Display events in multiple time zones
4. **Template Events**: Save and reuse common entries
5. **Advanced Recurring**: Support monthly, yearly patterns
6. **Calendar Sharing**: Share view-only calendar links
7. **Event Conflicts**: Visual indicators for overlapping entries
8. **Batch Operations**: Select multiple events for bulk actions
9. **Calendar Widgets**: Embeddable calendar for other pages
10. **AI Suggestions**: Smart event creation based on patterns

---

## 📚 Related Documentation

- [Bulk Time Entry](BULK_TIME_ENTRY_README.md)
- [Task Management](TASK_MANAGEMENT_README.md)
- [Project Management](PROJECT_STRUCTURE.md)
- [API Documentation](README.md)

---

## 💡 Tips & Tricks

1. **Quick Project Switch**: Keep the project dropdown visible at all times for fast entry creation
2. **Keyboard Shortcuts**: Use `?` to open command palette, or `Ctrl+K` to quickly search
3. **Week View Default**: Start each session in week view for best overview
4. **Color Recognition**: Learn your project colors to quickly identify entries
5. **Agenda for Planning**: Use agenda view for day planning and reviews
6. **Export for Billing**: Export filtered calendar as CSV for invoicing
7. **Recurring Templates**: Set up recurring blocks for regular meetings
8. **Tag Consistently**: Use consistent tags for powerful filtering
9. **Notes for Context**: Add notes to entries for future reference
10. **Mobile Agenda**: Use agenda view on mobile for better readability

---

## 📞 Support

### Getting Help

1. Check this documentation
2. Review browser console for errors
3. Check network tab for failed API calls
4. Verify database connectivity

### Common Issues

**Issue**: Calendar shows no events
**Solution**: Check filters, verify date range, ensure you have time entries

**Issue**: Can't create new events
**Solution**: Select a project first in the "Assign to project" dropdown

**Issue**: Drag-and-drop not saving
**Solution**: Check network connectivity and server logs

**Issue**: Export downloads empty file
**Solution**: Ensure date range has events, check server permissions

---

**The Calendar feature is production-ready and provides a comprehensive visual interface for time tracking! 📅**

