@echo off
REM Build script for TimeTracker Mobile and Desktop Apps (Windows)
setlocal enabledelayedexpansion

set SCRIPT_DIR=%~dp0
set PROJECT_ROOT=%SCRIPT_DIR%..

REM Default build options
set BUILD_MOBILE=1
set BUILD_DESKTOP=1
set BUILD_ANDROID=1
set BUILD_IOS=0
set BUILD_WINDOWS=1

REM Parse arguments
:parse_args
if "%~1"=="" goto end_parse
if /i "%~1"=="--mobile-only" (
    set BUILD_MOBILE=1
    set BUILD_DESKTOP=0
    shift
    goto parse_args
)
if /i "%~1"=="--desktop-only" (
    set BUILD_MOBILE=0
    set BUILD_DESKTOP=1
    shift
    goto parse_args
)
if /i "%~1"=="--android-only" (
    set BUILD_ANDROID=1
    set BUILD_IOS=0
    set BUILD_MOBILE=1
    set BUILD_DESKTOP=0
    shift
    goto parse_args
)
if /i "%~1"=="--windows-only" (
    set BUILD_WINDOWS=1
    set BUILD_MOBILE=0
    set BUILD_DESKTOP=1
    shift
    goto parse_args
)
shift
goto parse_args
:end_parse

echo ========================================
echo TimeTracker - Build All Script (Windows)
echo ========================================
echo.

REM Check Flutter
if "%BUILD_MOBILE%"=="1" (
    echo [1/4] Checking Flutter...
    where flutter >nul 2>&1
    if errorlevel 1 (
        echo [ERROR] Flutter is not installed or not in PATH
        echo Please install Flutter from: https://flutter.dev/docs/get-started/install
        exit /b 1
    )
    flutter --version | findstr /C:"Flutter"
    if errorlevel 1 (
        echo [ERROR] Failed to get Flutter version
        exit /b 1
    )
    echo [OK] Flutter found
    echo.
)

REM Check Node.js
if "%BUILD_DESKTOP%"=="1" (
    echo [2/4] Checking Node.js...
    where node >nul 2>&1
    if errorlevel 1 (
        echo [ERROR] Node.js is not installed or not in PATH
        echo Please install Node.js 18+ from: https://nodejs.org/
        exit /b 1
    )
    node --version
    if errorlevel 1 (
        echo [ERROR] Failed to get Node.js version
        exit /b 1
    )
    echo [OK] Node.js found
    echo.
    
    where npm >nul 2>&1
    if errorlevel 1 (
        echo [ERROR] npm is not installed or not in PATH
        exit /b 1
    )
    npm --version
    echo [OK] npm found
    echo.
)

REM Build Mobile
if "%BUILD_MOBILE%"=="1" (
    echo ========================================
    echo Building Mobile App (Flutter)
    echo ========================================
    cd /d "%PROJECT_ROOT%"
    
    echo [0/6] Syncing version from setup.py...
    python "%SCRIPT_DIR%sync-mobile-version.py"
    if errorlevel 1 (
        echo [ERROR] Failed to sync version
        exit /b 1
    )
    echo [OK] Version synced
    echo.
    
    cd /d "%PROJECT_ROOT%\mobile"
    
    echo [1/6] Installing Flutter dependencies...
    call flutter pub get
    if errorlevel 1 (
        echo [ERROR] Failed to install Flutter dependencies
        exit /b 1
    )
    echo [OK] Dependencies installed
    echo.
    
    echo [1b/6] Generating app icons...
    cd /d "%PROJECT_ROOT%"
    call "%SCRIPT_DIR%generate-mobile-icon.bat"
    cd /d "%PROJECT_ROOT%\mobile"
    call dart run flutter_launcher_icons
    if errorlevel 1 (
        echo [ERROR] Failed to generate launcher icons
        exit /b 1
    )
    echo [OK] Launcher icons generated
    echo.
    
    echo [2/6] Analyzing Flutter code...
    call flutter analyze
    if errorlevel 1 (
        echo [WARNING] Code analysis found issues (continuing anyway)
    )
    echo.
    
    echo [3/6] Running Flutter tests...
    call flutter test
    if errorlevel 1 (
        echo [WARNING] Some tests failed (continuing anyway)
    )
    echo.
    
    if "%BUILD_ANDROID%"=="1" (
        echo [4/6] Building Android APK...
        call flutter build apk --release
        if errorlevel 1 (
            echo [ERROR] Android APK build failed
            exit /b 1
        )
        if exist "build\app\outputs\flutter-apk\app-release.apk" (
            echo [OK] Android APK built successfully
            echo   Location: %PROJECT_ROOT%\mobile\build\app\outputs\flutter-apk\app-release.apk
        ) else (
            echo [ERROR] Android APK not found after build
        )
        echo.
        
        echo [5/6] Building Android App Bundle...
        call flutter build appbundle --release
        if errorlevel 1 (
            echo [ERROR] Android App Bundle build failed
            exit /b 1
        )
        if exist "build\app\outputs\bundle\release\app-release.aab" (
            echo [OK] Android App Bundle built successfully
            echo   Location: %PROJECT_ROOT%\mobile\build\app\outputs\bundle\release\app-release.aab
        ) else (
            echo [ERROR] Android App Bundle not found after build
        )
        echo.
    )
)

REM Build Desktop
if "%BUILD_DESKTOP%"=="1" (
    echo ========================================
    echo Building Desktop App (Electron)
    echo ========================================
    cd /d "%PROJECT_ROOT%"
    
    echo [0/4] Syncing version from setup.py...
    python "%SCRIPT_DIR%sync-desktop-version.py"
    if errorlevel 1 (
        echo [ERROR] Failed to sync version
        exit /b 1
    )
    echo [OK] Version synced
    echo.
    
    cd /d "%PROJECT_ROOT%\desktop"
    
    echo [1/4] Installing npm dependencies...
    if not exist "node_modules" (
        call npm install --prefer-offline --no-audit --loglevel=warn
    ) else (
        call npm ci --prefer-offline --no-audit --loglevel=warn
        if errorlevel 1 (
            call npm install --prefer-offline --no-audit --loglevel=warn
        )
    )
    if errorlevel 1 (
        echo [ERROR] Failed to install npm dependencies
        exit /b 1
    )
    echo [OK] Dependencies installed
    echo.
    
    REM Check if building for all platforms
    if "%1"=="all-platforms" goto build_all_platforms
    if "%1"=="all-desktop" goto build_all_platforms
    
    if "%BUILD_WINDOWS%"=="1" (
        echo [2/4] Building Windows installer...
        call npm run build:win
        if errorlevel 1 (
            echo [ERROR] Windows build failed
            exit /b 1
        )
        if exist "dist\*.exe" (
            echo [OK] Windows installer built successfully
            echo   Location: %PROJECT_ROOT%\desktop\dist\
            dir /b dist\*.exe
        ) else (
            echo [ERROR] Windows installer not found after build
        )
        echo.
    )
    goto end_desktop_build
    
    :build_all_platforms
    echo [2/4] Building for all supported platforms...
    echo [NOTE] Will automatically build for platforms supported on your OS
    call npm run build:all
    if errorlevel 1 (
        echo [ERROR] Build failed
        exit /b 1
    )
    echo.
    :end_desktop_build
)

echo ========================================
echo Build Complete!
echo ========================================
echo.
echo Build outputs:
if "%BUILD_MOBILE%"=="1" (
    echo   Mobile: %PROJECT_ROOT%\mobile\build\
)
if "%BUILD_DESKTOP%"=="1" (
    echo   Desktop: %PROJECT_ROOT%\desktop\dist\
)
echo.

endlocal
