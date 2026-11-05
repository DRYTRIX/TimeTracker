@echo off
REM CSRF Configuration Verification Script (Windows)
REM This script verifies that CSRF tokens are properly configured in a Docker deployment

setlocal enabledelayedexpansion

echo ==================================================
echo   TimeTracker CSRF Configuration Verification
echo ==================================================
echo.

REM Get container name from argument or use default
set CONTAINER_NAME=%1
if "%CONTAINER_NAME%"=="" set CONTAINER_NAME=timetracker-app

echo Checking container: %CONTAINER_NAME%
echo.

REM Check if container is running
docker ps | findstr /C:"%CONTAINER_NAME%" >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Container '%CONTAINER_NAME%' is not running
    echo.
    echo Available containers:
    docker ps --format "table {{.Names}}\t{{.Status}}"
    exit /b 1
)

echo [OK] Container is running
echo.

REM Check environment variables
echo 1. Checking environment variables...
echo -----------------------------------

for /f "tokens=2 delims==" %%i in ('docker exec %CONTAINER_NAME% env ^| findstr "^SECRET_KEY="') do set SECRET_KEY=%%i
for /f "tokens=2 delims==" %%i in ('docker exec %CONTAINER_NAME% env ^| findstr "^WTF_CSRF_ENABLED="') do set CSRF_ENABLED=%%i
for /f "tokens=2 delims==" %%i in ('docker exec %CONTAINER_NAME% env ^| findstr "^WTF_CSRF_TIME_LIMIT="') do set CSRF_TIMEOUT=%%i
for /f "tokens=2 delims==" %%i in ('docker exec %CONTAINER_NAME% env ^| findstr "^FLASK_ENV="') do set FLASK_ENV=%%i

if "!SECRET_KEY!"=="" (
    echo [ERROR] SECRET_KEY is not set!
    set HAS_ISSUES=1
) else if "!SECRET_KEY!"=="your-secret-key-change-this" (
    echo [ERROR] SECRET_KEY is using default value - INSECURE!
    echo    Generate a secure key with: python -c "import secrets; print(secrets.token_hex(32))"
    set HAS_ISSUES=1
) else if "!SECRET_KEY!"=="dev-secret-key-change-in-production" (
    echo [ERROR] SECRET_KEY is using development default - INSECURE!
    set HAS_ISSUES=1
) else (
    echo [OK] SECRET_KEY is set and appears secure
)

if "!CSRF_ENABLED!"=="" set CSRF_ENABLED=not set
if "!CSRF_ENABLED!"=="true" (
    echo [OK] CSRF protection is enabled
) else if "!CSRF_ENABLED!"=="not set" (
    echo [OK] CSRF protection is enabled (using default)
) else if "!CSRF_ENABLED!"=="false" (
    if "!FLASK_ENV!"=="development" (
        echo [WARNING] CSRF protection is disabled (OK for development)
    ) else (
        echo [ERROR] CSRF protection is disabled in production!
        set HAS_ISSUES=1
    )
)

if "!CSRF_TIMEOUT!"=="" (
    echo [OK] CSRF timeout using default (3600s / 1 hour)
) else (
    echo [OK] CSRF timeout set to !CSRF_TIMEOUT!s
)

echo.

REM Check application logs
echo 2. Checking application logs...
echo -------------------------------

docker logs %CONTAINER_NAME% 2>&1 | findstr /I "csrf" | findstr /I "error fail invalid" >nul 2>&1
if errorlevel 1 (
    echo [OK] No CSRF errors found in logs
) else (
    echo [WARNING] Found CSRF-related errors in logs
    docker logs %CONTAINER_NAME% 2>&1 | findstr /I "csrf" | findstr /I "error fail invalid"
)

echo.

REM Check application health
echo 3. Checking application health...
echo ---------------------------------

REM Try to get the port
for /f "tokens=2 delims=:" %%i in ('docker port %CONTAINER_NAME% 8080 2^>nul') do set PORT=%%i
if "!PORT!"=="" set PORT=8080

curl -s -f "http://localhost:!PORT!/_health" >nul 2>&1
if errorlevel 1 (
    echo [WARNING] Health check endpoint not responding
) else (
    echo [OK] Application health check passed
)

REM Check for CSRF token in login page
curl -s "http://localhost:!PORT!/login" 2>nul | findstr /C:"csrf_token" >nul
if errorlevel 1 (
    if "!CSRF_ENABLED!"=="false" (
        echo [OK] No CSRF token in login page (CSRF is disabled)
    ) else (
        echo [WARNING] No CSRF token found in login page
    )
) else (
    echo [OK] CSRF token found in login page
)

echo.

REM Configuration summary
echo 4. Configuration Summary
echo ------------------------
echo Container:         %CONTAINER_NAME%
echo Flask Environment: !FLASK_ENV!
echo SECRET_KEY:        !SECRET_KEY:~0,10!... (length: !SECRET_KEY!)
echo CSRF Enabled:      !CSRF_ENABLED!
echo CSRF Timeout:      !CSRF_TIMEOUT! seconds
echo.

REM Recommendations
echo 5. Recommendations
echo ------------------

if "!SECRET_KEY!"=="your-secret-key-change-this" (
    echo.
    echo WARNING: Generate a secure SECRET_KEY:
    echo    python -c "import secrets; print(secrets.token_hex(32))"
    echo    Then set it in your .env file or docker-compose.yml
    set HAS_ISSUES=1
)

if "!SECRET_KEY!"=="dev-secret-key-change-in-production" (
    echo.
    echo WARNING: Generate a secure SECRET_KEY for production
    set HAS_ISSUES=1
)

if not "!FLASK_ENV!"=="development" (
    if "!CSRF_ENABLED!"=="false" (
        echo.
        echo WARNING: Enable CSRF protection in production:
        echo    Set WTF_CSRF_ENABLED=true in your environment
        set HAS_ISSUES=1
    )
)

if not defined HAS_ISSUES (
    echo [OK] Configuration looks good!
)

echo.
echo ==================================================
echo For detailed documentation, see:
echo   docs/CSRF_CONFIGURATION.md
echo ==================================================

endlocal
