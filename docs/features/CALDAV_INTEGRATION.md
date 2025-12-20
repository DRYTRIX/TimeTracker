# CalDAV Calendar Integration

The CalDAV integration allows you to import calendar events from CalDAV-compatible servers (such as Zimbra, Nextcloud, or ownCloud) as time entries in TimeTracker.

## Features

- **Calendar Discovery**: Automatically discover available calendars on your CalDAV server
- **Event Import**: Import calendar events (VEVENT) as time entries
- **Project Matching**: Automatically match events to projects based on event titles
- **Idempotent Sync**: Prevents duplicate imports using event UIDs
- **Flexible Configuration**: Support for both server URL (with discovery) and direct calendar URL

## Supported Servers

- **Zimbra**: Fully supported
- **Nextcloud Calendar**: Fully supported
- **ownCloud Calendar**: Fully supported
- **Other CalDAV servers**: Should work with any CalDAV-compatible server

## Setup Instructions

### 1. Navigate to Integrations

1. Go to **Integrations** from the main menu
2. Find **CalDAV Calendar** in the list
3. Click **Setup CalDAV Calendar**

### 2. Configure Server Connection

#### Option A: Using Server URL (Recommended)

1. **Server URL**: Enter your CalDAV server base URL
   - Example for Zimbra: `https://mail.example.com/dav`
   - Example for Nextcloud: `https://nextcloud.example.com/remote.php/dav`

2. The system will automatically discover your calendars

#### Option B: Using Direct Calendar URL

1. **Calendar URL**: Enter the direct URL to your calendar collection
   - Example: `https://mail.example.com/dav/user@example.com/Calendar/`
   - This bypasses discovery and connects directly to a specific calendar

### 3. Authentication

1. **Username**: Your CalDAV username (usually your email address)
2. **Password**: Your CalDAV password or app-specific password
3. **Verify SSL**: Check this box unless using a self-signed certificate

### 4. Import Settings

1. **Default Project**: Select the project where imported events will be assigned
   - If an event title contains a project name, that project will be used instead
2. **Lookback Days**: How many days back to import events (default: 90)

### 5. Save and Test

1. Click **Save Configuration**
2. Go to the integration details page
3. Click **Test Connection** to verify connectivity
4. Click **Sync Now** to import calendar events

## How It Works

### Event Import Process

1. The system fetches calendar events from your CalDAV server within the specified time range
2. Each event is checked against existing imports (using event UID) to prevent duplicates
3. Events are converted to time entries with:
   - **Start Time**: Event start time
   - **End Time**: Event end time
   - **Duration**: Calculated automatically
   - **Project**: Matched from event title or uses default project
   - **Notes**: Event summary and description
   - **Source**: Marked as "auto" (automatically imported)

### Project Matching

The system attempts to match event titles to project names:
- If an event title contains a project name, that project is used
- Otherwise, the default project is used
- Example: Event "Meeting - Project Alpha" will be assigned to "Project Alpha" if it exists

### Idempotency

Each calendar event has a unique UID. The system tracks imported events to prevent duplicates:
- First import: Event is imported as a new time entry
- Subsequent syncs: Event is skipped (already imported)

## Zimbra-Specific Notes

### Finding Your CalDAV URL

For Zimbra, the CalDAV URL typically follows this pattern:
```
https://mail.yourdomain.com/dav/username@yourdomain.com/Calendar/
```

### Authentication

- Use your Zimbra email address as the username
- Use your Zimbra password (or an app-specific password if enabled)

### Calendar Discovery

If you provide the server URL (`https://mail.yourdomain.com/dav`), the system will:
1. Discover your user principal
2. Find your calendar home set
3. List all available calendars
4. Allow you to select which calendar to sync

## Troubleshooting

### Connection Test Fails

1. **Check Server URL**: Ensure the URL is correct and accessible
2. **Verify Credentials**: Double-check username and password
3. **SSL Certificate**: If using self-signed certificate, uncheck "Verify SSL"
4. **Firewall**: Ensure your server allows CalDAV connections (usually port 443)

### No Events Imported

1. **Check Time Range**: Events must be within the lookback period
2. **Verify Calendar URL**: Ensure the calendar URL is correct
3. **Check Event Types**: Only timed events (not all-day events) are imported
4. **Review Sync Log**: Check the integration details page for error messages

### Duplicate Events

- The system prevents duplicates using event UIDs
- If you see duplicates, they may have different UIDs (rare)
- Check the integration sync history for details

## Limitations

- **One-Way Sync**: Currently only imports from calendar to TimeTracker (not bidirectional)
- **Timed Events Only**: All-day events are skipped
- **No Recurring Events**: Recurring events are imported as individual instances
- **Manual Sync**: Automatic sync is not yet implemented (use "Sync Now" button)

## Future Enhancements

Planned features:
- Bidirectional sync (TimeTracker → Calendar)
- Automatic periodic sync
- Support for all-day events
- Better project matching with tags/categories
- Event updates (modify time entries when calendar events change)

## Security Notes

- Passwords are stored encrypted in the database
- SSL verification is enabled by default (recommended)
- Only events from your configured calendar are accessed
- No calendar data is shared with third parties

## Support

For issues or questions:
1. Check the integration sync history for error messages
2. Review server logs for connection issues
3. Test connection using the "Test Connection" button
4. Contact your system administrator if problems persist

