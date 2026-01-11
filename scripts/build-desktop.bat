@echo off
REM Build script for TimeTracker Desktop App (Electron) - Windows

setlocal
set SCRIPT_DIR=%~dp0
set PROJECT_ROOT=%SCRIPT_DIR%..
set DESKTOP_DIR=%PROJECT_ROOT%\desktop

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

REM Install dependencies
echo Installing dependencies...
if not exist "node_modules" (
    call npm install --prefer-offline --no-audit --loglevel=warn
) else (
    call npm ci --prefer-offline --no-audit --loglevel=warn
    if errorlevel 1 (
        call npm install --prefer-offline --no-audit --loglevel=warn
    )
)
if errorlevel 1 (
    echo ERROR: Failed to install dependencies
    exit /b 1
)
echo.

REM Build
set PLATFORM=%1
if "%PLATFORM%"=="" set PLATFORM=win

if /i "%PLATFORM%"=="win" (
    echo Building Windows installer...
    call npm run build:win
    if errorlevel 1 (
        echo ERROR: Windows build failed
        exit /b 1
    )
) else if /i "%PLATFORM%"=="all" (
    echo Building for all supported platforms...
    echo Note: Will automatically build for platforms supported on your OS
    call npm run build:all
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
