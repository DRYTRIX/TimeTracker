@echo off
REM Build script that completely prevents code signing and winCodeSign download

setlocal enabledelayedexpansion
set SCRIPT_DIR=%~dp0
set PROJECT_ROOT=%SCRIPT_DIR%..
set DESKTOP_DIR=%PROJECT_ROOT%\desktop

cd /d "%PROJECT_ROOT%"

REM Set ALL code signing environment variables
set CSC_IDENTITY_AUTO_DISCOVERY=false
set WIN_CSC_LINK=
set WIN_CSC_KEY_PASSWORD=
set CSC_LINK=
set CSC_KEY_PASSWORD=
set APPLE_ID=
set APPLE_ID_PASSWORD=
set APPLE_TEAM_ID=

echo Building TimeTracker Desktop App (NO CODE SIGNING)...
echo.

REM Clear ALL electron-builder cache
echo Clearing electron-builder cache completely...
if exist "%LOCALAPPDATA%\electron-builder" (
    echo Removing: %LOCALAPPDATA%\electron-builder
    rmdir /s /q "%LOCALAPPDATA%\electron-builder" 2>nul || (
        echo [WARNING] Could not remove cache (may need Admin rights)
        echo   Manually delete: %LOCALAPPDATA%\electron-builder
    )
)
echo.

echo Environment variables set:
echo   CSC_IDENTITY_AUTO_DISCOVERY=false
echo   WIN_CSC_LINK=
echo   CSC_LINK=
echo.

cd /d "%DESKTOP_DIR%"

echo Building with explicit no-sign configuration...
echo Using explicit CLI flags to disable code signing...
echo.

REM Build with environment variables only (package.json already has sign: null)
CSC_IDENTITY_AUTO_DISCOVERY=false WIN_CSC_LINK= CSC_LINK= call npx --yes electron-builder --win

if errorlevel 1 (
    echo.
    echo ================================================================================
    echo BUILD FAILED
    echo ================================================================================
    echo.
    echo If you got a symlink error:
    echo   1. Enable Developer Mode: Win+I ^> Privacy ^& Security ^> For developers
    echo   2. Restart your terminal
    echo   3. Try building again
    echo.
    echo Or run as Administrator
    echo.
    exit /b 1
)

echo.
echo [SUCCESS] Build completed without code signing!
echo.

endlocal
