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

### Server URL

The desktop app can receive the server URL in multiple ways:

1. **Command Line:**
   ```bash
   TimeTracker.exe --server-url https://your-server.com
   ```

2. **Environment Variable:**
   ```bash
   set TIMETRACKER_SERVER_URL=https://your-server.com
   TimeTracker.exe
   ```

3. **In-App Settings:**
   - Configure in the app's settings screen
   - Stored in secure storage

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
