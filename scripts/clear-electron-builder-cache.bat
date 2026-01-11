@echo off
REM Clear electron-builder cache to fix symbolic link issues

setlocal

set CACHE_DIR=%LOCALAPPDATA%\electron-builder\Cache

echo Clearing electron-builder cache...
echo.
echo Cache directory: %CACHE_DIR%
echo.

if exist "%CACHE_DIR%" (
    echo Removing cache directories...
    
    REM Remove winCodeSign cache (causes symlink issues)
    if exist "%CACHE_DIR%\winCodeSign" (
        echo   Removing winCodeSign cache...
        rmdir /s /q "%CACHE_DIR%\winCodeSign" 2>nul
        if errorlevel 1 (
            echo   [WARNING] Could not remove winCodeSign cache
            echo   You may need to run as Administrator
        ) else (
            echo   [OK] winCodeSign cache removed
        )
    )
    
    echo.
    echo [OK] Cache cleared
) else (
    echo [OK] Cache directory does not exist
)

echo.
echo Next steps:
echo   1. Enable Developer Mode in Windows (recommended)
echo      - Win+I ^> Privacy ^& Security ^> For developers
echo      - Enable Developer Mode
echo   2. Or run as Administrator
echo   3. Build again: scripts\build-desktop-simple.bat
echo.

endlocal
