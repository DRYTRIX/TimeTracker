@echo off
REM Fix script for npm permission errors on Windows (especially OneDrive)

setlocal
set SCRIPT_DIR=%~dp0
set PROJECT_ROOT=%SCRIPT_DIR%..
set DESKTOP_DIR=%PROJECT_ROOT%\desktop

echo ========================================
echo Fixing npm permission errors...
echo ========================================
echo.

cd /d "%DESKTOP_DIR%"

REM Check if in OneDrive
echo %DESKTOP_DIR% | findstr /i "OneDrive" >nul
if %errorlevel%==0 (
    echo WARNING: Project is in OneDrive!
    echo OneDrive can lock files and cause npm permission errors.
    echo.
    echo RECOMMENDED: Exclude node_modules from OneDrive sync
    echo   1. Right-click desktop\node_modules folder
    echo   2. Select "Free up space" or "Always keep on this device"
    echo   3. Or: OneDrive Settings ^> Sync ^> Advanced ^> Files On-Demand
    echo   4. Better yet: Move project outside OneDrive
    echo.
    timeout /t 5 /nobreak >nul
)

echo Cleaning npm cache...
call npm cache clean --force
if errorlevel 1 (
    echo WARNING: npm cache clean failed, continuing...
)
echo.

echo Attempting to remove problematic directories...
REM Try to remove common problematic temp directories
if exist "node_modules\.extract-zip-*" (
    echo Removing extract-zip temp directories...
    for /d %%d in ("node_modules\.extract-zip-*") do (
        echo Attempting to remove: %%d
        timeout /t 2 /nobreak >nul
        rd /s /q "%%d" 2>nul
        if exist "%%d" (
            echo   WARNING: Could not remove %%d - may be locked
            echo   Try closing other programs or restart your computer
        ) else (
            echo   Successfully removed: %%d
        )
    )
)

REM Try to remove node_modules entirely and reinstall
set /p REMOVE_ALL="Remove entire node_modules folder and reinstall? (y/N): "
if /i "%REMOVE_ALL%"=="y" (
    echo.
    echo Removing node_modules...
    if exist "node_modules" (
        timeout /t 2 /nobreak >nul
        rd /s /q "node_modules" 2>nul
        if exist "node_modules" (
            echo ERROR: Could not remove node_modules folder
            echo This is likely due to file locks.
            echo.
            echo Try:
            echo   1. Close all programs (IDE, file explorer, etc.)
            echo   2. Run this script as Administrator
            echo   3. Restart your computer
            echo   4. Exclude node_modules from OneDrive sync
            exit /b 1
        ) else (
            echo Successfully removed node_modules
        )
    )
    
    echo.
    echo Installing dependencies fresh...
    call npm install --prefer-offline --no-audit
    if errorlevel 1 (
        echo ERROR: npm install failed
        echo Try running as Administrator or exclude node_modules from OneDrive
        exit /b 1
    )
    echo.
    echo Dependencies installed successfully!
) else (
    echo Skipping full removal.
)

echo.
echo ========================================
echo Fix complete!
echo ========================================
endlocal
