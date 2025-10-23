# Time Entry Duplication Feature

## Overview

The Time Entry Duplication feature allows users to quickly copy existing time entries with pre-filled data. This significantly speeds up time tracking workflows when working on similar tasks or projects repeatedly.

## User Stories

- **As a user**, I want to duplicate a previous time entry so that I can quickly log similar work without re-entering all the details.
- **As a user**, I want the duplicated entry to preserve my project, task, notes, tags, and billable settings from the original entry.
- **As a user**, I want to be able to adjust the times for the duplicated entry before saving it.

## Features

### Quick Access
- Duplicate buttons are available in multiple locations:
  - **Dashboard**: Next to each time entry in the "Recent Entries" table
  - **Edit Entry Page**: Alongside the "Back" button for easy access when viewing an entry

### Pre-filled Data
When duplicating an entry, the following fields are automatically populated:
- **Project**: The same project as the original entry
- **Task**: The same task (if any) as the original entry
- **Notes**: The same notes/description from the original entry
- **Tags**: The same comma-separated tags from the original entry
- **Billable Status**: The same billable flag as the original entry

### User Control
- Users can modify any pre-filled field before creating the duplicate
- Start and end times are **not** copied - users must set new times for the duplicate entry
- This ensures users consciously choose when the work was done

### Visual Feedback
- A blue information banner shows details about the original entry being duplicated
- The page title changes to "Duplicate Time Entry" to clearly indicate the action
- Original entry details (project, task, duration) are displayed for reference

## Technical Details

### Backend Implementation

#### Route
```python
@timer_bp.route('/timer/duplicate/<int:timer_id>')
@login_required
def duplicate_timer(timer_id):
    """Duplicate an existing time entry - opens manual entry form with pre-filled data"""
```

**URL Pattern**: `/timer/duplicate/<id>`
**Method**: GET
**Authentication**: Required

#### Process Flow
1. User clicks duplicate button
2. System retrieves the original time entry
3. Permission check: User must own the entry or be an admin
4. Manual entry form is rendered with pre-filled data
5. User adjusts times and modifies fields as needed
6. User submits the form to create the new entry

#### Security
- **Permission Check**: Users can only duplicate their own entries
- **Admin Override**: Administrators can duplicate any user's entries
- **404 Handling**: Non-existent entries return a 404 error

#### Analytics
- Event tracking for duplication actions:
  - Event name: `timer.duplicated`
  - Tracked properties: entry ID, project ID, task ID, has_notes, has_tags

### Frontend Implementation

#### Dashboard Button
```html
<a href="{{ url_for('timer.duplicate_timer', timer_id=entry.id) }}" 
   class="text-blue-600 hover:text-blue-800" 
   title="{{ _('Duplicate entry') }}">
    <i class="fas fa-copy"></i>
</a>
```

#### Edit Page Button
```html
<a href="{{ url_for('timer.duplicate_timer', timer_id=timer.id) }}" 
   class="btn btn-outline-primary">
    <i class="fas fa-copy me-1"></i>{{ _('Duplicate') }}
</a>
```

#### Information Banner
Displays when duplicating an entry:
```html
<div class="bg-blue-50 dark:bg-blue-900/20 border border-blue-200 ...">
    <p>Duplicating entry: [Project Name] - [Task Name]</p>
    <p>Original: [Start Time] to [End Time] ([Duration])</p>
</div>
```

### Template Variables

The manual entry template accepts these additional variables for duplication:
- `is_duplicate` (boolean): Indicates this is a duplication action
- `original_entry` (TimeEntry): The entry being duplicated
- `selected_project_id` (int): Pre-selects the project dropdown
- `selected_task_id` (int): Pre-selects the task dropdown
- `prefill_notes` (string): Pre-fills the notes textarea
- `prefill_tags` (string): Pre-fills the tags input
- `prefill_billable` (boolean): Pre-checks the billable checkbox

## Use Cases

### 1. Daily Recurring Work
**Scenario**: A developer logs 2 hours of code review every morning.

**Workflow**:
1. Click duplicate on yesterday's code review entry
2. Adjust start/end times to today
3. Submit the form
4. Entry is created in seconds instead of minutes

### 2. Similar Tasks Across Projects
**Scenario**: A consultant has similar meeting entries across different projects.

**Workflow**:
1. Duplicate a meeting entry from Project A
2. Change the project to Project B
3. Adjust times and notes as needed
4. Submit to create entry for Project B

### 3. Template-like Entries
**Scenario**: A designer regularly logs similar "Client Feedback" entries.

**Workflow**:
1. Find any previous "Client Feedback" entry
2. Click duplicate
3. Update times and any client-specific notes
4. Submit quickly with consistent tags and structure

## Testing

### Test Coverage
The feature includes comprehensive test coverage:
- **Unit Tests**: Route access, authentication, permission checks
- **Integration Tests**: Pre-fill functionality, form rendering, data accuracy
- **Security Tests**: User isolation, admin privileges
- **Smoke Tests**: Button visibility, basic workflows
- **Model Tests**: Field availability, duplication mechanics
- **Edge Cases**: Missing fields, inactive projects, minimal entries

### Test File
Location: `tests/test_time_entry_duplication.py`

Run tests:
```bash
# Run all duplication tests
pytest tests/test_time_entry_duplication.py -v

# Run specific test categories
pytest tests/test_time_entry_duplication.py -v -m unit
pytest tests/test_time_entry_duplication.py -v -m integration
pytest tests/test_time_entry_duplication.py -v -m smoke
pytest tests/test_time_entry_duplication.py -v -m security
```

## Internationalization

All user-facing text uses Flask-Babel for internationalization:
- Button labels
- Page titles
- Information messages
- Form labels

Keys to translate:
- `Duplicate entry`
- `Duplicate Time Entry`
- `Create a copy of a previous entry with new times`
- `Duplicating entry`
- `Original`

## Future Enhancements

### Potential Improvements
1. **Quick Duplicate**: Add a "Duplicate & Edit Times" modal for even faster duplication
2. **Bulk Duplicate**: Duplicate an entry across multiple dates at once
3. **Smart Defaults**: Auto-fill times based on user's typical work patterns
4. **Favorite Entries**: Mark entries as favorites for quick access when duplicating
5. **Duplicate to Today**: One-click duplicate with today's date and current time

### API Endpoint
Consider adding an API endpoint for programmatic duplication:
```
POST /api/timer/duplicate/<id>
{
  "start_time": "2024-01-15T09:00:00",
  "end_time": "2024-01-15T11:00:00"
}
```

## Related Features

- **Time Entry Templates**: For completely reusable entry templates (different use case)
- **Manual Entry**: The form used after clicking duplicate
- **Bulk Entry**: For creating multiple similar entries across date ranges
- **Edit Entry**: For modifying existing entries

## Troubleshooting

### Common Issues

**Issue**: Duplicate button not visible
- **Cause**: Entry may be from another user (non-admin)
- **Solution**: Ensure you're viewing your own entries or have admin privileges

**Issue**: Task not pre-selected after duplication
- **Cause**: Tasks are loaded dynamically via JavaScript
- **Solution**: Wait for the page to fully load; the task should auto-select

**Issue**: Cannot duplicate inactive project entry
- **Cause**: Project status changed to inactive after entry creation
- **Solution**: Form will render, but you may need to select an active project

**Issue**: Permission denied when duplicating
- **Cause**: Attempting to duplicate another user's entry
- **Solution**: Only duplicate your own entries, or request admin assistance

## Changelog

### Version 1.0 (2024-10-23)
- Initial implementation of time entry duplication
- Duplicate buttons on dashboard and edit pages
- Pre-filled form with all relevant fields
- Comprehensive test suite
- Documentation and user guides
- Analytics tracking for duplication events

## Support

For questions or issues with the Time Entry Duplication feature:
1. Check this documentation
2. Review the test cases for examples
3. Check the application logs for errors
4. Contact your system administrator

## License

This feature is part of the TimeTracker application and follows the same license terms.

