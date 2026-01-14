# Build script for TimeTracker Desktop App (Windows PowerShell)
# This is the native Windows PowerShell script - use this instead of .sh on Windows

$ErrorActionPreference = "Stop"

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$ProjectRoot = Split-Path -Parent $ScriptDir
$DesktopDir = Join-Path $ProjectRoot "desktop"

Set-Location $ProjectRoot

# Sync version from setup.py to package.json
Write-Host "Syncing version from setup.py..." -ForegroundColor Cyan
python "$ScriptDir\sync-desktop-version.py"
if ($LASTEXITCODE -ne 0) {
    Write-Host "ERROR: Failed to sync version" -ForegroundColor Red
    exit 1
}
Write-Host ""

Set-Location $DesktopDir

Write-Host "Building TimeTracker Desktop App..." -ForegroundColor Cyan
Write-Host ""

# Check Node.js
if (-not (Get-Command node -ErrorAction SilentlyContinue)) {
    Write-Host "ERROR: Node.js is not installed or not in PATH" -ForegroundColor Red
    exit 1
}

Write-Host "Node.js version: $(node --version)"
Write-Host "npm version: $(npm --version)"
Write-Host ""

# Prepare assets
Write-Host "Preparing desktop assets..." -ForegroundColor Cyan

# Skip if already prepared (avoid duplicate output)
if (-not $env:ASSETS_PREPARED) {
    $DesktopAssets = Join-Path $DesktopDir "assets"
    $MainLogo = Join-Path $ProjectRoot "app\static\images\timetracker-logo.svg"
    
    # Ensure assets directory exists
    if (-not (Test-Path $DesktopAssets)) {
        New-Item -ItemType Directory -Path $DesktopAssets -Force | Out-Null
    }
    
    # Copy logo if missing
    $LogoPath = Join-Path $DesktopAssets "logo.svg"
    if (-not (Test-Path $LogoPath)) {
        if (Test-Path $MainLogo) {
            Write-Host "Copying logo to desktop/assets/logo.svg..."
            Copy-Item $MainLogo $LogoPath -Force
            Write-Host "  [OK] Logo copied" -ForegroundColor Green
        } else {
            Write-Host "ERROR: Main logo not found at $MainLogo" -ForegroundColor Red
            exit 1
        }
    } else {
        Write-Host "  [OK] Logo already exists" -ForegroundColor Green
    }
    
    # Check for icon files
    $MissingIcons = $false
    $IconPng = Join-Path $DesktopAssets "icon.png"
    $IconIco = Join-Path $DesktopAssets "icon.ico"
    $IconIcns = Join-Path $DesktopAssets "icon.icns"
    
    if (-not (Test-Path $IconPng)) {
        Write-Host "  [WARN] icon.png not found (will be generated if possible)" -ForegroundColor Yellow
        $MissingIcons = $true
    }
    if (-not (Test-Path $IconIco)) {
        Write-Host "  [WARN] icon.ico not found (required for Windows builds)" -ForegroundColor Yellow
        $MissingIcons = $true
    }
    if (-not (Test-Path $IconIcns)) {
        Write-Host "  [WARN] icon.icns not found (required for macOS builds)" -ForegroundColor Yellow
        $MissingIcons = $true
    }
    
    # Try to generate PNG icon if node is available
    if (-not (Test-Path $IconPng) -and (Get-Command node -ErrorAction SilentlyContinue)) {
        $GenerateIconsScript = Join-Path $ProjectRoot "scripts\generate-icons.js"
        if (Test-Path $GenerateIconsScript) {
            Write-Host "Attempting to generate icon.png..."
            Push-Location $ProjectRoot
            $ErrorActionPreferenceBackup = $ErrorActionPreference
            $ErrorActionPreference = "Continue"
            $output = & node scripts\generate-icons.js 2>&1
            $exitCode = $LASTEXITCODE
            $ErrorActionPreference = $ErrorActionPreferenceBackup
            if ($exitCode -eq 0) {
                Write-Host "  [OK] Icon generation attempted" -ForegroundColor Green
            } else {
                Write-Host "  [WARN] Icon generation failed (sharp may not be installed)" -ForegroundColor Yellow
            }
            Pop-Location
        }
    }
    
    if ($MissingIcons) {
        Write-Host ""
        Write-Host "NOTE: Some icon files are missing. The build will continue, but:" -ForegroundColor Yellow
        Write-Host "  - Windows builds require icon.ico (convert from PNG)" -ForegroundColor Yellow
        Write-Host "  - macOS builds require icon.icns (convert from PNG)" -ForegroundColor Yellow
        Write-Host "  - Linux builds require icon.png" -ForegroundColor Yellow
        Write-Host ""
        Write-Host "To generate icons:" -ForegroundColor Cyan
        Write-Host "  1. Install sharp: npm install sharp" -ForegroundColor Cyan
        Write-Host "  2. Run: node scripts\generate-icons.js" -ForegroundColor Cyan
        Write-Host "  3. Convert PNG to .ico/.icns using online tools or ImageMagick" -ForegroundColor Cyan
        Write-Host ""
    }
    
    Write-Host "Asset preparation complete!" -ForegroundColor Green
    $env:ASSETS_PREPARED = "1"
}
Write-Host ""

# Check if node_modules exists and is valid
$NodeModulesValid = $false
if (Test-Path "node_modules") {
    if ((Test-Path "node_modules\electron\package.json") -and 
        (Test-Path "node_modules\electron-builder\package.json")) {
        try {
            node -e "require('electron')" 2>$null | Out-Null
            $NodeModulesValid = $true
            Write-Host "  [OK] node_modules appears valid, skipping install" -ForegroundColor Green
        } catch {
            $NodeModulesValid = $false
        }
    }
}

if (-not $NodeModulesValid) {
    Write-Host "Installing dependencies..." -ForegroundColor Cyan
    
    if (-not (Test-Path "node_modules")) {
        Write-Host "  Installing dependencies (first time)..." -ForegroundColor Yellow
        npm install --prefer-offline --no-audit --loglevel=warn
        if ($LASTEXITCODE -ne 0) {
            Write-Host ""
            Write-Host "ERROR: npm install failed" -ForegroundColor Red
            Write-Host ""
            Write-Host "This is a common issue on Windows, especially with OneDrive:" -ForegroundColor Yellow
            Write-Host "  - OneDrive file locking prevents npm from working properly"
            Write-Host "  - Antivirus may be scanning files during install"
            Write-Host "  - File permissions may be restricted"
            Write-Host ""
            Write-Host "Solutions:" -ForegroundColor Cyan
            Write-Host "  1. Exclude node_modules from OneDrive sync"
            Write-Host "  2. Temporarily disable antivirus real-time scanning"
            Write-Host "  3. Run PowerShell as Administrator"
            Write-Host "  4. Move project outside OneDrive folder"
            Write-Host "  5. Use WSL instead of PowerShell"
            Write-Host ""
            exit 1
        }
    } else {
        Write-Host "  Updating dependencies..." -ForegroundColor Yellow
        npm ci --prefer-offline --no-audit --loglevel=warn
        if ($LASTEXITCODE -ne 0) {
            Write-Host "  npm ci failed, trying npm install..." -ForegroundColor Yellow
            npm install --prefer-offline --no-audit --loglevel=warn
            if ($LASTEXITCODE -ne 0) {
                Write-Host ""
                Write-Host "ERROR: npm install failed" -ForegroundColor Red
                Write-Host ""
                Write-Host "Windows/OneDrive specific solutions:" -ForegroundColor Yellow
                Write-Host "  1. Close all programs that might be using node_modules"
                Write-Host "  2. Exclude desktop/node_modules from OneDrive sync"
                Write-Host "  3. Run PowerShell as Administrator and try again"
                Write-Host "  4. Delete node_modules and try: npm install"
                Write-Host "  5. Move project outside OneDrive"
                Write-Host ""
                exit 1
            }
        }
    }
    Write-Host ""
}

# Verify electron-builder is available
if (-not (Get-Command npx -ErrorAction SilentlyContinue)) {
    Write-Host "ERROR: npx is not available" -ForegroundColor Red
    exit 1
}

# Set environment variable to disable code signing completely
$env:CSC_IDENTITY_AUTO_DISCOVERY = "false"

# Build for Windows (package.json already has sign: null)
Write-Host "Building Windows installer..." -ForegroundColor Cyan
Write-Host "NOTE: Code signing is disabled (sign: null, CSC_IDENTITY_AUTO_DISCOVERY=false)" -ForegroundColor Yellow
Write-Host ""
npx --yes electron-builder --win
if ($LASTEXITCODE -ne 0) {
    Write-Host ""
    Write-Host "ERROR: Build failed" -ForegroundColor Red
    Write-Host ""
    Write-Host "Check the error messages above for details." -ForegroundColor Yellow
    Write-Host "Common issues:" -ForegroundColor Yellow
    Write-Host "  - Missing icon.ico file (generate with: node scripts\generate-icons.js)"
    Write-Host "  - Insufficient permissions"
    Write-Host "  - Antivirus blocking the build"
    Write-Host ""
    exit 1
}

Write-Host ""
Write-Host "Build complete!" -ForegroundColor Green
$DistPath = Join-Path $DesktopDir "dist"
Write-Host ("Outputs: " + $DistPath) -ForegroundColor Cyan
Write-Host ""
