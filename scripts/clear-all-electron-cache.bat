@echo off
REM Clear all electron-builder cache to fix symlink and code signing issues

setlocal

set CACHE_DIR=%LOCALAPPDATA%\electron-builder

echo Clearing all electron-builder cache...
echo.
echo Cache directory: %CACHE_DIR%
echo.

if exist "%CACHE_DIR%" (
    echo Removing entire electron-builder cache...
    rmdir /s /q "%CACHE_DIR%" 2>nul
    if errorlevel 1 (
        echo [WARNING] Could not remove cache directory
        echo   You may need to run as Administrator
        echo   Or manually delete: %CACHE_DIR%
        exit /b 1
    ) else (
        echo [OK] Cache cleared successfully
    )
) else (
    echo [OK] Cache directory does not exist
)

echo.
echo Next steps:
echo   1. Enable Developer Mode in Windows (recommended)
echo      - Win+I ^> Privacy ^& Security ^> For developers
echo      - Enable Developer Mode
echo   2. Or run PowerShell/CMD as Administrator
echo   3. Build again: scripts\build-desktop-simple.bat
echo.

endlocal
