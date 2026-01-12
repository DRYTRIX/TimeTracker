# TimeTracker Desktop App

Electron-based desktop application for TimeTracker.

## Building

### Prerequisites

- Node.js 18+
- npm

### Install Dependencies

```bash
npm install
```

### Build for Current Platform

```bash
npm run build
```

### Build for Specific Platform

```bash
# Windows
npm run build:win

# macOS
npm run mac

# Linux
npm run build:linux
```

### Build for All Platforms

```bash
npm run build:all
```

## Code Signing (Windows)

To avoid the "Unknown Publisher" warning, you need to sign the Windows executable with a code signing certificate.

### Quick Setup

1. **Obtain a Code Signing Certificate:**
   - Purchase from a CA (Sectigo, DigiCert, etc.) - $150-600/year
   - Or create a self-signed certificate for testing

2. **Local Build:**
   ```powershell
   # Windows PowerShell
   $env:CSC_LINK_FILE = "path/to/certificate.pfx"
   $env:CSC_KEY_PASSWORD = "YourCertificatePassword"
   npm run build:win
   ```

3. **CI/CD (GitHub Actions):**
   - Store certificate as Base64 in GitHub Secret: `WINDOWS_CODE_SIGN_CERT`
   - Store password in GitHub Secret: `WINDOWS_CODE_SIGN_PASSWORD`
   - The workflow will automatically sign the executable

For detailed instructions, see [Windows Code Signing Guide](../../docs/WINDOWS_CODE_SIGNING.md).

## Development

### Run in Development Mode

```bash
npm start
```

### Run with DevTools

```bash
npm run dev
```

## Configuration

### Getting an API Token

Before connecting the desktop app, you need to create an API token:

1. **Log in to TimeTracker Web App** as an administrator
2. Navigate to **Admin > API Tokens** (`/admin/api-tokens`)
3. Click **"Create Token"**
4. Fill in the required information:
   - **Name**: A descriptive name (e.g., "Desktop App - Windows")
   - **User**: Select the user this token will authenticate as
   - **Scopes**: Select the following permissions:
     - `read:projects` - View projects
     - `read:tasks` - View tasks
     - `read:time_entries` - View time entries
     - `write:time_entries` - Create and update time entries
   - **Expires In**: Optional expiration period (leave empty for no expiration)
5. Click **"Create Token"**
6. **Important**: Copy the generated token immediately - you won't be able to see it again!
   - Token format: `tt_<32_random_characters>`
   - Example: `tt_abc123def456ghi789jkl012mno345pq`

### Connecting the App

The desktop app can be configured in multiple ways:

#### Method 1: In-App Login (Recommended)

1. **Launch the desktop app**
2. On the login screen, enter:
   - **Server URL**: Your TimeTracker server URL (e.g., `https://your-server.com`)
     - Do not include a trailing slash
     - Use `http://` for local development or `https://` for production
   - **API Token**: Paste the token you copied from the web app
3. Click **"Login"**
4. The app will validate your connection and show the main screen if successful

#### Method 2: Command Line

```bash
TimeTracker.exe --server-url https://your-server.com
```

Then enter your API token in the login screen.

#### Method 3: Environment Variable

```bash
# Windows
set TIMETRACKER_SERVER_URL=https://your-server.com
TimeTracker.exe

# Linux/macOS
export TIMETRACKER_SERVER_URL=https://your-server.com
./TimeTracker
```

#### Method 4: Settings Screen

1. Launch the app
2. Navigate to **Settings** tab
3. Enter your **Server URL** and **API Token**
4. Click **"Save Settings"** or **"Test Connection"** to verify

### Connection Status

The app shows a connection status indicator in the header:
- **Green dot (●)**: Connected and authenticated
- **Red dot (●)**: Connection error or authentication failed
- **Gray circle (○)**: Not connected

The connection is automatically checked every 30 seconds.

### Troubleshooting

**"Invalid API token" error:**
- Verify the token starts with `tt_`
- Check that the token hasn't expired
- Ensure the token has the required scopes
- Try creating a new token in the web app

**"Connection failed" error:**
- Verify the server URL is correct and accessible
- Check your internet connection
- Ensure the server is running and the API is accessible
- For local development, use `http://localhost:5000` or your local IP address
- Check the connection status indicator in the header

**Settings not saving:**
- Ensure you have write permissions in the app's data directory
- Check that electron-store is working properly
- Try clearing settings and re-entering them

For more details, see [Desktop Settings Guide](../../docs/DESKTOP_SETTINGS.md).

## Project Structure

```
desktop/
├── src/
│   ├── main/          # Main process (Electron)
│   ├── renderer/      # Renderer process (UI)
│   └── shared/        # Shared code
├── assets/            # Icons and assets
├── scripts/           # Build scripts
└── dist/              # Build output
```

## Version Management

The version is automatically synced from `setup.py` before building. The build scripts handle this automatically.

## License

MIT
