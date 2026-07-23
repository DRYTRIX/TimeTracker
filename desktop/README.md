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
npm run build:mac

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

### Renderer (React + Vite)

The primary UI lives in [`src/renderer-react/`](src/renderer-react/) and builds to [`dist-renderer/`](dist-renderer/) via Vite (`npm run build:renderer`). Electron loads `dist-renderer/index.html`, with the legacy [`src/renderer/`](src/renderer/) bundle kept only as a fallback.

### Run in Development Mode

```bash
npm start
```

(`npm start` and every packaging script run `build:renderer` first so installers do not ship a stale Vite build.)

### Run with DevTools

```bash
npm run dev
```

## Configuration

### Connecting the App

Sign in with your TimeTracker **username and password**. The app calls `POST /api/v1/auth/login` and stores the returned API token (`tt_…`) securely. You can still create long-lived tokens under **Admin → Security & Access → API tokens** if you prefer to manage tokens in the web UI.

#### Method 1: In-App Login (Recommended)

1. **Launch the desktop app**
2. **Step 1 — Server**: Enter your TimeTracker **base URL** (e.g. `https://your-server.com`). Trailing slashes are normalized. Omitting the scheme assumes `https://`.
3. Click **Test server** (`GET /api/v1/info`).
4. **Step 2 — Sign in**: Enter username and password, then **Sign in**.
5. On success the main window opens. If the server still requires initial setup, that is surfaced from the info response.

#### Method 2: Command Line

```bash
TimeTracker.exe --server-url https://your-server.com
```

Then complete username/password sign-in in the app.

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

1. Launch the app and sign in
2. Open **Settings**
3. Update **Server URL** / username; enter password to re-authenticate
4. Save settings

### Connection Status

The app shows a connection status indicator in the header:
- **Green dot (●)**: Connected and authenticated
- **Red dot (●)**: Connection error or authentication failed
- **Gray circle (○)**: Not connected

The connection is automatically checked every 30 seconds.

### Automated tests (renderer client)

From the `desktop/` directory:

```bash
npm test
```

Runs Node’s test runner on `test/api-client.test.js` (URL normalization, TimeTracker JSON shape checks, and error classification).

### Troubleshooting

**Login or “Test server” shows a TLS or certificate message:**
- Use a certificate trusted by the OS, or for lab use only, try `http://` on a trusted network if your server supports it.

**Token rejected after “server OK”:**
- Verify the token starts with `tt_`, is not expired, and includes at least `read:time_entries` (and ideally `read:users`).

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

**Window stuck on loading, blank content, or unstable navigation (especially Windows):**
- Use the latest release or rebuild from source; older builds could mis-handle `file:` navigation in the main process or ship a renderer bundle without helpers loaded.
- From source, run `npm install` and `npm run build:renderer`, then `npm start` or rebuild the installer.
- See [Desktop build Windows troubleshooting](../../docs/admin/configuration/DESKTOP_BUILD_WINDOWS_TROUBLESHOOTING.md) for environment-specific build issues.

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
