@echo off
REM Fix Windows/OneDrive build issues for desktop app

setlocal enabledelayedexpansion

set SCRIPT_DIR=%~dp0
set PROJECT_ROOT=%SCRIPT_DIR%..
set DESKTOP_DIR=%PROJECT_ROOT%\desktop

echo Fixing Windows/OneDrive build issues...
echo.

cd /d "%DESKTOP_DIR%"

REM Check if we're in OneDrive
echo %PROJECT_ROOT% | findstr /i "OneDrive" >nul
if %errorlevel% equ 0 (
    echo ========================================
    echo WARNING: OneDrive location detected!
    echo ========================================
    echo.
    echo OneDrive file locking is causing your npm errors!
    echo.
    echo CRITICAL: Before continuing, exclude node_modules from OneDrive sync:
    echo   1. Right-click: %DESKTOP_DIR%\node_modules
    echo   2. Choose "Always keep on this device"
    echo.
    echo Or use the PowerShell script (handles locks better):
    echo   powershell -ExecutionPolicy Bypass -File "%~dp0fix-onedrive-lock.ps1"
    echo.
    pause
)

REM Clean npm cache
echo Cleaning npm cache...
call npm cache clean --force
if errorlevel 1 (
    echo   Warning: Cache clean had issues, continuing...
) else (
    echo   [OK] Cache cleaned
)
echo.

REM Remove problematic node_modules if it exists
if exist "node_modules" (
    echo Removing existing node_modules...
    echo   (This may take a moment on Windows/OneDrive)
    echo   NOTE: If this fails, use PowerShell script: scripts\fix-onedrive-lock.ps1
    echo.
    
    REM Try to remove with retries
    set MAX_RETRIES=5
    set RETRY=0
    :retry_remove
    set /a RETRY+=1
    echo   Attempt !RETRY!/%MAX_RETRIES%: Trying to remove node_modules...
    
    REM First try normal removal
    rmdir /s /q node_modules 2>nul
    if not exist "node_modules" (
        echo   [OK] node_modules removed successfully
        goto :removed
    )
    
    REM If that failed, try removing files individually (slower but more reliable)
    if !RETRY! leq 2 (
        echo   Trying aggressive removal method...
        for /d /r node_modules %%d in (*) do @if exist "%%d" rd /s /q "%%d" 2>nul
        rd /s /q node_modules 2>nul
        if not exist "node_modules" (
            echo   [OK] node_modules removed successfully
            goto :removed
        )
    )
    
    if !RETRY! lss %MAX_RETRIES% (
        echo   [WARNING] Attempt !RETRY! failed, waiting 3 seconds...
        timeout /t 3 /nobreak >nul
        goto :retry_remove
    ) else (
        echo   [ERROR] Failed to remove node_modules after %MAX_RETRIES% attempts
        echo.
        echo This is a OneDrive file locking issue!
        echo.
        echo SOLUTIONS (in order of effectiveness):
        echo.
        echo 1. EXCLUDE node_modules from OneDrive sync (RECOMMENDED):
        echo    - Right-click: %DESKTOP_DIR%\node_modules
        echo    - Choose "Always keep on this device"
        echo    - Or exclude from OneDrive sync entirely
        echo    - Then run this script again
        echo.
        echo 2. Use PowerShell script (handles locks better):
        echo    powershell -ExecutionPolicy Bypass -File "%~dp0fix-onedrive-lock.ps1"
        echo.
        echo 3. Manual removal:
        echo    - Close ALL programs (VS Code, terminals, File Explorer)
        echo    - Open File Explorer as Administrator
        echo    - Navigate to: %DESKTOP_DIR%
        echo    - Delete the 'node_modules' folder manually
        echo    - Run this script again
        echo.
        echo 4. Move project outside OneDrive (prevents all issues)
        echo.
        exit /b 1
    )
    
    :removed
    echo.
)

REM Remove package-lock.json if it exists
if exist "package-lock.json" (
    echo Removing package-lock.json...
    del /f /q package-lock.json
    echo   [OK] Removed
    echo.
)

REM Reinstall dependencies
echo Reinstalling dependencies...
echo   (This may take several minutes)
echo.

call npm install --prefer-offline --no-audit --loglevel=warn
if errorlevel 1 (
    echo.
    echo [ERROR] Installation failed
    echo.
    echo Additional solutions:
    echo   1. Exclude desktop\node_modules from OneDrive sync
    echo   2. Run Command Prompt as Administrator
    echo   3. Temporarily disable antivirus real-time scanning
    echo   4. Move project outside OneDrive folder
    echo   5. Use WSL instead of Command Prompt
    exit /b 1
) else (
    echo.
    echo [OK] Dependencies installed successfully!
    echo.
    echo Next steps:
    echo   1. If using OneDrive, exclude node_modules from sync:
    echo      - Right-click desktop\node_modules
    echo      - Choose "Always keep on this device"
    echo   2. Run the build script: scripts\build-desktop-windows.bat
)

endlocal
