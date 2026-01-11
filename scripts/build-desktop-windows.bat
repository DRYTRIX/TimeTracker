@echo off
REM Build script for TimeTracker Desktop App (Windows)
REM This is the native Windows batch script - use this instead of .sh on Windows

setlocal enabledelayedexpansion

set SCRIPT_DIR=%~dp0
set PROJECT_ROOT=%SCRIPT_DIR%..
set DESKTOP_DIR=%PROJECT_ROOT%\desktop

cd /d "%PROJECT_ROOT%"

REM Sync version from setup.py to package.json
echo Syncing version from setup.py...
python "%SCRIPT_DIR%sync-desktop-version.py"
if errorlevel 1 (
    echo ERROR: Failed to sync version
    exit /b 1
)
echo.

cd /d "%DESKTOP_DIR%"

echo Building TimeTracker Desktop App...
echo.

REM Check Node.js
where node >nul 2>&1
if errorlevel 1 (
    echo ERROR: Node.js is not installed or not in PATH
    exit /b 1
)

echo Node.js version:
node --version
echo npm version:
npm --version
echo.

REM Prepare assets
echo Preparing desktop assets...
call "%SCRIPT_DIR%prepare-desktop-assets.sh"
if errorlevel 1 (
    echo WARNING: Asset preparation had issues, continuing anyway...
)
echo.

REM Check if node_modules exists and is valid
if exist "node_modules\electron\package.json" (
    if exist "node_modules\electron-builder\package.json" (
        node -e "require('electron')" >nul 2>&1
        if not errorlevel 1 (
            echo   [OK] node_modules appears valid, skipping install
            goto :skip_install
        )
    )
)

echo Installing dependencies...
if not exist "node_modules" (
    echo   Installing dependencies (first time)...
    call npm install --prefer-offline --no-audit --loglevel=warn
    if errorlevel 1 (
        echo.
        echo ERROR: npm install failed
        echo.
        echo This is a common issue on Windows, especially with OneDrive:
        echo   - OneDrive file locking prevents npm from working properly
        echo   - Antivirus may be scanning files during install
        echo   - File permissions may be restricted
        echo.
        echo Solutions:
        echo   1. Exclude node_modules from OneDrive sync:
        echo      - Right-click desktop\node_modules folder
        echo      - Choose "Always keep on this device" or exclude from sync
        echo   2. Temporarily disable antivirus real-time scanning
        echo   3. Run as Administrator
        echo   4. Move project outside OneDrive folder
        echo   5. Use WSL instead of Command Prompt
        echo.
        exit /b 1
    )
) else (
    echo   Updating dependencies...
    call npm ci --prefer-offline --no-audit --loglevel=warn
    if errorlevel 1 (
        echo   npm ci failed, trying npm install...
        call npm install --prefer-offline --no-audit --loglevel=warn
        if errorlevel 1 (
            echo.
            echo ERROR: npm install failed
            echo.
            echo Windows/OneDrive specific solutions:
            echo   1. Close all programs that might be using node_modules
            echo   2. Exclude desktop\node_modules from OneDrive sync
            echo   3. Run PowerShell as Administrator and try again
            echo   4. Delete node_modules and try: npm install
            echo   5. Move project outside OneDrive
            echo.
            exit /b 1
        )
    )
)
echo.

:skip_install

REM Verify electron-builder is available
where npx >nul 2>&1
if errorlevel 1 (
    echo ERROR: npx is not available
    exit /b 1
)

REM Set environment variable to disable code signing completely
set CSC_IDENTITY_AUTO_DISCOVERY=false

REM Build for Windows (package.json already has sign: null)
echo Building Windows installer...
echo NOTE: Code signing is disabled (sign: null, CSC_IDENTITY_AUTO_DISCOVERY=false)
echo.
call npx --yes electron-builder --win
if errorlevel 1 (
    echo.
    echo ERROR: Build failed
    echo.
    echo Check the error messages above for details.
    echo Common issues:
    echo   - Missing icon.ico file (generate with: node scripts\generate-icons.js)
    echo   - Insufficient permissions
    echo   - Antivirus blocking the build
    echo.
    exit /b 1
)

echo.
echo Build complete!
echo Outputs: %DESKTOP_DIR%\dist\
echo.

endlocal
