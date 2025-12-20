# CalDAV Integration - Quick Setup Guide

## Prerequisites

1. **At least one active project** in TimeTracker
2. **CalDAV server credentials** (username and password)
3. **CalDAV server URL** or direct calendar URL

## Step-by-Step Setup

### Step 1: Navigate to Integrations

1. Log in to TimeTracker
2. Click on **Integrations** in the main menu
3. Find **CalDAV Calendar** in the list
4. Click **Setup CalDAV Calendar**

### Step 2: Configure Server Connection

#### For Zimbra Users:

1. **Server URL**: Enter your Zimbra CalDAV base URL
   ```
   https://mail.yourdomain.com/dav
   ```
   - Replace `yourdomain.com` with your actual domain
   - The system will automatically discover your calendars

2. **Calendar URL** (Optional): If you know the exact calendar URL, you can enter it directly:
   ```
   https://mail.yourdomain.com/dav/username@yourdomain.com/Calendar/
   ```

#### For Nextcloud/ownCloud Users:

1. **Server URL**: Enter your Nextcloud/ownCloud CalDAV URL
   ```
   https://nextcloud.yourdomain.com/remote.php/dav
   ```

2. **Calendar URL** (Optional): Direct calendar URL
   ```
   https://nextcloud.yourdomain.com/remote.php/dav/calendars/username/calendar-name/
   ```

### Step 3: Enter Authentication

1. **Username**: Your email address or CalDAV username
   - For Zimbra: Usually your full email address
   - For Nextcloud: Your Nextcloud username

2. **Password**: Your CalDAV password
   - For Zimbra: Your email password or app-specific password
   - For Nextcloud: Your Nextcloud password or app password

3. **Verify SSL**: 
   - ✅ Checked (recommended): For servers with valid SSL certificates
   - ❌ Unchecked: Only if using self-signed certificates

### Step 4: Configure Import Settings

1. **Default Project**: Select the project where imported events will be assigned
   - **Important**: You must have at least one active project
   - If an event title contains a project name, that project will be used instead

2. **Lookback Days**: How many days back to import events (default: 90)
   - Range: 1-365 days
   - Only events within this range will be imported

### Step 5: Save and Test

1. Click **Save Configuration**
2. You'll be redirected to the integration details page
3. Click **Test Connection** to verify:
   - Server connectivity
   - Authentication
   - Calendar discovery (if server URL provided)
4. If successful, you'll see available calendars

### Step 6: Import Events

1. On the integration details page, click **Sync Now**
2. The system will:
   - Fetch calendar events from your CalDAV server
   - Import them as time entries
   - Skip duplicates (using event UIDs)
3. Check the sync history for results

## Common Issues and Solutions

### "No active projects found"

**Problem**: You need at least one active project before setting up CalDAV.

**Solution**: 
1. Go to **Projects** → **Create Project**
2. Create at least one project
3. Return to CalDAV setup

### "Either server URL or calendar URL is required"

**Problem**: You must provide at least one URL.

**Solution**: 
- Enter either the **Server URL** (for automatic discovery) or **Calendar URL** (direct connection)
- Server URL is recommended for first-time setup

### "Connection test failed"

**Possible causes**:
1. **Wrong URL**: Double-check the server URL format
2. **Wrong credentials**: Verify username and password
3. **SSL certificate**: If using self-signed certificate, uncheck "Verify SSL"
4. **Firewall**: Ensure port 443 (HTTPS) is accessible

**Solution**:
- Verify the URL format matches your server
- Test credentials with a CalDAV client (e.g., Thunderbird)
- Check server logs for connection attempts

### "No calendars found on server"

**Problem**: The server URL is correct but no calendars are discovered.

**Solution**:
- Try entering the **Calendar URL** directly instead
- Check that your account has calendar access
- Verify the server supports CalDAV

### "No events imported"

**Possible causes**:
1. **Time range**: Events are outside the lookback period
2. **All-day events**: Only timed events are imported
3. **No events**: Calendar is empty

**Solution**:
- Increase the lookback days if needed
- Ensure events have start and end times (not all-day)
- Check your calendar has events in the time range

## Tips for Best Results

1. **Use Server URL for Discovery**: Let the system discover calendars automatically
2. **Project Matching**: Name your calendar events with project names for automatic matching
   - Example: "Meeting - Project Alpha" will match to "Project Alpha" project
3. **Regular Syncs**: Manually sync periodically to import new events
4. **Check Sync History**: Review the integration details page for sync status and errors

## Example: Zimbra Setup

```
Server URL: https://mail.company.com/dav
Username: john.doe@company.com
Password: [your password]
Default Project: General Work
Lookback Days: 90
```

After saving:
1. Test connection → Should show available calendars
2. Sync now → Imports events from the last 90 days
3. Check time entries → Events appear as time entries

## Next Steps

After setup:
- ✅ Test connection to verify everything works
- ✅ Run initial sync to import existing events
- ✅ Check imported time entries
- ✅ Set up regular syncs (manual for now)

For more details, see [CALDAV_INTEGRATION.md](CALDAV_INTEGRATION.md).

