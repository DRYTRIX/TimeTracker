@echo off
REM Simplified build script for TimeTracker Desktop App (Windows)
REM This version uses simpler logic that's more reliable

setlocal
set SCRIPT_DIR=%~dp0
set PROJECT_ROOT=%SCRIPT_DIR%..
set DESKTOP_DIR=%PROJECT_ROOT%\desktop

cd /d "%PROJECT_ROOT%"

REM Sync version
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
    echo ERROR: Node.js not found
    exit /b 1
)

node --version
npm --version
echo.

REM Check if we need to install dependencies
echo Checking dependencies...
if not exist "node_modules\electron-builder\package.json" (
    echo Installing dependencies...
    if not exist "node_modules" (
        echo   First time install...
    ) else (
        echo   Updating existing installation...
        echo   (If this fails with EPERM error, see ONEDRIVE_FIX.md)
    )
    call npm install --prefer-offline --no-audit --loglevel=warn
    if errorlevel 1 (
        echo.
        echo ========================================
        echo ERROR: npm install failed!
        echo ========================================
        echo.
        echo This is likely a OneDrive file locking issue.
        echo.
        echo QUICK FIX:
        echo   1. Right-click: desktop\node_modules
        echo   2. Choose "Always keep on this device"
        echo   3. Then run: scripts\fix-onedrive-lock.ps1
        echo   4. Or run: scripts\fix-windows-build.bat
        echo.
        echo For detailed help, see: ONEDRIVE_FIX.md
        echo.
        exit /b 1
    )
    echo.
) else (
    echo [OK] Dependencies already installed
    echo.
)

REM Verify npx
where npx >nul 2>&1
if errorlevel 1 (
    echo ERROR: npx not found
    exit /b 1
)

REM Clear electron-builder cache to prevent code signing download
if exist "%LOCALAPPDATA%\electron-builder\Cache\winCodeSign" (
    echo Clearing winCodeSign cache (prevents symlink errors)...
    rmdir /s /q "%LOCALAPPDATA%\electron-builder\Cache\winCodeSign" 2>nul
    echo.
)

REM Set ALL environment variables to disable code signing completely
set CSC_IDENTITY_AUTO_DISCOVERY=false
set WIN_CSC_LINK=
set CSC_LINK=

REM Build (package.json already has sign: null)
echo ========================================
echo Building Windows installer...
echo ========================================
echo.
echo NOTE: Code signing is disabled (sign: null in package.json)
echo Environment variables set: CSC_IDENTITY_AUTO_DISCOVERY=false
echo.
echo   If you get symbolic link errors:
echo   1. Enable Developer Mode: Win+I ^> Privacy ^& Security ^> For developers
echo   2. Or run PowerShell/CMD as Administrator
echo   3. Or run: scripts\clear-all-electron-cache.bat
echo.
call npx --yes electron-builder --win
if errorlevel 1 (
    echo.
    echo ERROR: Build failed!
    echo.
    echo Common issues:
    echo   - Missing icon.ico: node scripts\generate-icons.js
    echo   - Check error messages above
    echo.
    exit /b 1
)

echo.
echo ========================================
echo Build complete!
echo ========================================
echo.
echo Output: %DESKTOP_DIR%\dist\
echo.
dir /b "%DESKTOP_DIR%\dist\*.exe" 2>nul
echo.

endlocal
