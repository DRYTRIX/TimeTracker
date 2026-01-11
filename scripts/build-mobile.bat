@echo off
REM Build script for TimeTracker Mobile App (Flutter) - Windows

setlocal
set SCRIPT_DIR=%~dp0
set PROJECT_ROOT=%SCRIPT_DIR%..
set MOBILE_DIR=%PROJECT_ROOT%\mobile

cd /d "%PROJECT_ROOT%"

REM Sync version from setup.py to mobile app
echo Syncing version from setup.py...
python "%SCRIPT_DIR%sync-mobile-version.py"
if errorlevel 1 (
    echo ERROR: Failed to sync version
    exit /b 1
)
echo.

cd /d "%MOBILE_DIR%"

echo Building TimeTracker Mobile App...
echo.

REM Check Flutter
where flutter >nul 2>&1
if errorlevel 1 (
    echo ERROR: Flutter is not installed or not in PATH
    exit /b 1
)

flutter --version | findstr /C:"Flutter"
echo.

REM Install dependencies
echo Installing dependencies...
call flutter pub get
if errorlevel 1 (
    echo ERROR: Failed to install dependencies
    exit /b 1
)
echo.

REM Analyze
echo Analyzing code...
call flutter analyze
echo.

REM Run tests
echo Running tests...
call flutter test
echo.

REM Build
set PLATFORM=%1
if "%PLATFORM%"=="" set PLATFORM=android

if /i "%PLATFORM%"=="android" (
    echo Building Android APK...
    call flutter build apk --release
    if errorlevel 1 (
        echo ERROR: Android APK build failed
        exit /b 1
    )
    echo.
    echo Building Android App Bundle...
    call flutter build appbundle --release
    if errorlevel 1 (
        echo ERROR: Android App Bundle build failed
        exit /b 1
    )
) else if /i "%PLATFORM%"=="all" (
    echo Building Android APK...
    call flutter build apk --release
    echo Building Android App Bundle...
    call flutter build appbundle --release
) else (
    echo Usage: %0 [android^|all]
    exit /b 1
)

echo.
echo Build complete!
echo Outputs: %MOBILE_DIR%\build\
endlocal
