# Desktop App Settings Configuration

The TimeTracker desktop app includes a comprehensive settings system that allows users to configure the server URL and API token.

## Settings Location

Settings are stored using Electron's secure storage (`electron-store`), which saves data in a JSON file in the user's application data directory:

- **Windows**: `%APPDATA%\timetracker-desktop\config.json`
- **macOS**: `~/Library/Application Support/timetracker-desktop/config.json`
- **Linux**: `~/.config/timetracker-desktop/config.json`

## Settings Access

Users can access settings in two ways:

### 1. Settings Screen (In-App)

1. Open the TimeTracker desktop app
2. Click on "Settings" in the navigation menu
3. The settings screen will display:
   - **Server URL**: Current server URL (editable)
   - **API Token**: Masked API token (editable)
   - **Save Settings** button: Saves the configuration
   - **Test Connection** button: Validates the connection

### 2. Command Line Arguments

The server URL can be set via command line when launching the app:

```bash
# Windows
TimeTracker.exe --server-url https://your-server.com

# Linux/macOS
./TimeTracker --server-url https://your-server.com
```

### 3. Environment Variable

The server URL can also be set via environment variable:

```bash
# Windows
set TIMETRACKER_SERVER_URL=https://your-server.com
TimeTracker.exe

# Linux/macOS
export TIMETRACKER_SERVER_URL=https://your-server.com
./TimeTracker
```

## Settings Features

### Server URL Configuration

- **Validation**: The app validates that the URL is properly formatted (must start with `http://` or `https://`)
- **Persistence**: Server URL is saved to secure storage and persists across app restarts
- **Change Detection**: The app automatically reinitializes the API client when the server URL changes

### API Token Configuration

- **Security**: API tokens are stored securely using Electron's secure storage
- **Masking**: Existing tokens are displayed as `••••••••` for security
- **Validation**: Tokens must start with `tt_` to be considered valid
- **Update**: Users can update their API token without re-entering the server URL

### Connection Testing

The settings screen includes a "Test Connection" button that:
- Validates the server URL format
- Tests the API token against the server
- Provides immediate feedback on connection status
- Shows success/error messages

## Settings File Structure

The settings file (`config.json`) contains:

```json
{
  "server_url": "https://your-server.com",
  "api_token": "tt_your_api_token_here"
}
```

## Implementation Details

### Settings Loading

When the settings view is opened:
1. The app loads current settings from secure storage
2. Server URL is displayed in the input field
3. API token is masked if it exists
4. Settings are ready for editing

### Settings Saving

When "Save Settings" is clicked:
1. Server URL is validated
2. API token is validated (if changed)
3. Settings are saved to secure storage
4. API client is reinitialized with new settings
5. Connection is automatically tested
6. Success/error message is displayed

### Settings Validation

- **Server URL**: Must be a valid HTTP/HTTPS URL
- **API Token**: Must start with `tt_` and be non-empty
- **Connection**: Server must be reachable and token must be valid

## Security Considerations

1. **Secure Storage**: Settings are stored using Electron's secure storage, which provides encryption on some platforms
2. **Token Masking**: API tokens are masked when displayed (`••••••••`)
3. **No Plain Text Logging**: API tokens are never logged to console or files
4. **Local Storage Only**: Settings are stored locally and never transmitted except to the configured server

## Troubleshooting

### Settings Not Saving

- Check that the app has write permissions to the application data directory
- Verify that the server URL is a valid HTTP/HTTPS URL
- Ensure the API token starts with `tt_`

### Connection Test Fails

- Verify the server URL is correct and accessible
- Check that the API token is valid and not expired
- Ensure the server is running and the API is accessible
- Check network connectivity and firewall settings

### Settings File Location

To manually edit or backup settings:

**Windows:**
```
%APPDATA%\timetracker-desktop\config.json
```

**macOS:**
```
~/Library/Application Support/timetracker-desktop/config.json
```

**Linux:**
```
~/.config/timetracker-desktop/config.json
```

## Code References

- Settings UI: `desktop/src/renderer/index.html` (settings view)
- Settings Logic: `desktop/src/renderer/js/app.js` (loadSettings, handleSaveSettings, handleTestConnection)
- Storage: `desktop/src/shared/config.js` (storeGet, storeSet, storeDelete, storeClear)
- Main Process: `desktop/src/main/main.js` (command line argument parsing)
