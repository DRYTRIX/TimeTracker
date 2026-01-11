@echo off
REM Test script to debug build-desktop.bat issues

setlocal enabledelayedexpansion

set SCRIPT_DIR=%~dp0
set PROJECT_ROOT=%SCRIPT_DIR%..
set DESKTOP_DIR=%PROJECT_ROOT%\desktop

echo Testing build-desktop.bat setup...
echo.
echo SCRIPT_DIR: %SCRIPT_DIR%
echo PROJECT_ROOT: %PROJECT_ROOT%
echo DESKTOP_DIR: %DESKTOP_DIR%
echo.

cd /d "%DESKTOP_DIR%"

echo Current directory: %CD%
echo.

echo Checking Node.js...
where node >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Node.js not found
    exit /b 1
) else (
    echo [OK] Node.js found: 
    node --version
)

echo.
echo Checking npm...
where npm >nul 2>&1
if errorlevel 1 (
    echo [ERROR] npm not found
    exit /b 1
) else (
    echo [OK] npm found:
    npm --version
)

echo.
echo Checking npx...
where npx >nul 2>&1
if errorlevel 1 (
    echo [ERROR] npx not found
    exit /b 1
) else (
    echo [OK] npx found
)

echo.
echo Checking node_modules...
if exist "node_modules" (
    echo [OK] node_modules directory exists
    if exist "node_modules\electron\package.json" (
        echo [OK] electron found in node_modules
    ) else (
        echo [WARNING] electron not found in node_modules
    )
    if exist "node_modules\electron-builder\package.json" (
        echo [OK] electron-builder found in node_modules
    ) else (
        echo [WARNING] electron-builder not found in node_modules
    )
    
    REM Test if electron can be required
    echo.
    echo Testing electron require...
    node -e "require('electron')" 2>nul
    if errorlevel 1 (
        echo [ERROR] Cannot require electron
    ) else (
        echo [OK] Electron can be required
    )
) else (
    echo [WARNING] node_modules directory does not exist
)

echo.
echo Checking assets...
if exist "assets\logo.svg" (
    echo [OK] logo.svg exists
) else (
    echo [WARNING] logo.svg not found
)

if exist "assets\icon.ico" (
    echo [OK] icon.ico exists
) else (
    echo [WARNING] icon.ico not found (required for Windows builds)
)

if exist "assets\icon.png" (
    echo [OK] icon.png exists
) else (
    echo [WARNING] icon.png not found
)

echo.
echo Test complete!
echo.
echo If all checks pass, you can run: scripts\build-desktop.bat
echo.

endlocal
