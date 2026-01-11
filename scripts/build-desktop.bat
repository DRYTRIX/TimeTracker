@echo off
REM Build script for TimeTracker Desktop App (Electron) - Windows

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

echo Checking node_modules...
REM Check if node_modules exists and is valid
set SKIP_INSTALL=0
if exist "node_modules\electron\package.json" (
    if exist "node_modules\electron-builder\package.json" (
        REM Try a quick test
        node -e "require('electron')" >nul 2>&1
        if not errorlevel 1 (
            set SKIP_INSTALL=1
            echo   [OK] node_modules appears valid, skipping install
            echo.
        )
    )
)

REM Install dependencies
echo SKIP_INSTALL = %SKIP_INSTALL%
if "%SKIP_INSTALL%"=="0" (
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
            echo   1. Exclude node_modules from OneDrive sync (MOST IMPORTANT!)
            echo      - Right-click desktop\node_modules folder
            echo      - Choose "Always keep on this device"
            echo   2. Run: scripts\fix-windows-build.bat
            echo   3. Run this script as Administrator
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
                echo   3. Run Command Prompt as Administrator and try again
                echo   4. Delete node_modules and try: npm install
                echo   5. Move project outside OneDrive
                echo.
                exit /b 1
            )
        )
    )
    echo.
)

REM Verify electron-builder is available
echo Checking npx...
where npx >nul 2>&1
if errorlevel 1 (
    echo ERROR: npx is not available
    echo   Make sure Node.js is installed and npm is in PATH
    exit /b 1
)
echo [OK] npx found
echo.

REM Set environment variable to disable code signing completely
set CSC_IDENTITY_AUTO_DISCOVERY=false

REM Clear electron-builder cache if symlink errors occurred
if exist "%LOCALAPPDATA%\electron-builder\Cache\winCodeSign" (
    echo Clearing winCodeSign cache (prevents symlink errors)...
    rmdir /s /q "%LOCALAPPDATA%\electron-builder\Cache\winCodeSign" 2>nul
    echo.
)

REM Build
echo ========================================
echo Starting build process...
echo ========================================
echo.
echo NOTE: Code signing is disabled (sign: null, CSC_IDENTITY_AUTO_DISCOVERY=false)
echo   If you still get symbolic link errors:
echo   1. Enable Developer Mode: Win+I ^> Privacy ^& Security ^> For developers
echo   2. Or run PowerShell/CMD as Administrator
echo   3. Or run: scripts\clear-all-electron-cache.bat
echo.
set PLATFORM=%1
if "%PLATFORM%"=="" set PLATFORM=win

if /i "%PLATFORM%"=="win" (
    echo Building Windows installer...
    call npx --yes electron-builder --win
    if errorlevel 1 (
        echo ERROR: Windows build failed
        echo.
        echo Common issues:
        echo   - Missing icon.ico file (generate with: node scripts\generate-icons.js)
        echo   - Insufficient permissions
        echo   - Antivirus blocking the build
        echo   - Symbolic link errors (enable Developer Mode or run as Admin)
        echo.
        exit /b 1
    )
) else if /i "%PLATFORM%"=="all" (
    echo Building for all supported platforms...
    echo Note: Will automatically build for platforms supported on your OS
    call npx --yes electron-builder --win --mac --linux
    if errorlevel 1 (
        echo ERROR: Build failed
        exit /b 1
    )
) else (
    echo Usage: %0 [win^|all]
    exit /b 1
)

echo.
echo Build complete!
echo Outputs: %DESKTOP_DIR%\dist\
endlocal
