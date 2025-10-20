@echo off
REM Setup script for local development with analytics (Windows)

echo 🔧 TimeTracker Development Analytics Setup
echo.

REM Check if .gitignore already has the entry
findstr /C:"analytics_defaults_local.py" .gitignore >nul 2>&1
if errorlevel 1 (
    echo app/config/analytics_defaults_local.py >> .gitignore
    echo ✅ Added analytics_defaults_local.py to .gitignore
)

REM Check if local config already exists
if exist "app\config\analytics_defaults_local.py" (
    echo ⚠️  Local config already exists
    set /p OVERWRITE="Overwrite? (y/N): "
    if /i not "%OVERWRITE%"=="y" (
        echo Keeping existing config
        exit /b 0
    )
)

REM Prompt for keys
echo.
echo 📝 Enter your development analytics keys:
echo (Leave empty to skip)
echo.

set /p POSTHOG_KEY="PostHog API Key (starts with phc_): "
set /p POSTHOG_HOST="PostHog Host [https://app.posthog.com]: "
if "%POSTHOG_HOST%"=="" set POSTHOG_HOST=https://app.posthog.com

set /p SENTRY_DSN="Sentry DSN (optional): "
set /p SENTRY_RATE="Sentry Traces Rate [1.0]: "
if "%SENTRY_RATE%"=="" set SENTRY_RATE=1.0

REM Create local config file
(
echo """
echo Local development analytics configuration.
echo.
echo ⚠️  DO NOT COMMIT THIS FILE ⚠️
echo.
echo This file is gitignored and contains your development API keys.
echo """
echo.
echo # PostHog Configuration ^(Development^)
echo POSTHOG_API_KEY_DEFAULT = "%POSTHOG_KEY%"
echo POSTHOG_HOST_DEFAULT = "%POSTHOG_HOST%"
echo.
echo # Sentry Configuration ^(Development^)
echo SENTRY_DSN_DEFAULT = "%SENTRY_DSN%"
echo SENTRY_TRACES_RATE_DEFAULT = "%SENTRY_RATE%"
echo.
echo.
echo def _get_version_from_setup^(^):
echo     """Get version from setup.py"""
echo     import os, re
echo     try:
echo         setup_path = os.path.join^(os.path.dirname^(os.path.dirname^(os.path.dirname^(__file__^)^)^), 'setup.py'^)
echo         with open^(setup_path, 'r', encoding='utf-8'^) as f:
echo             content = f.read^(^)
echo         version_match = re.search^(r'version\s*=\s*[\\'"]^([^\\'"]+ ^)[\\'" ]', content^)
echo         if version_match:
echo             return version_match.group^(1^)
echo     except Exception:
echo         pass
echo     return "3.0.0-dev"
echo.
echo.
echo def get_analytics_config^(^):
echo     """Get analytics configuration for local development."""
echo     app_version = _get_version_from_setup^(^)
echo     return {
echo         "posthog_api_key": POSTHOG_API_KEY_DEFAULT,
echo         "posthog_host": POSTHOG_HOST_DEFAULT,
echo         "sentry_dsn": SENTRY_DSN_DEFAULT,
echo         "sentry_traces_rate": float^(SENTRY_TRACES_RATE_DEFAULT^),
echo         "app_version": app_version,
echo         "telemetry_enabled_default": False,
echo     }
echo.
echo.
echo def has_analytics_configured^(^):
echo     """Check if analytics keys are configured."""
echo     return bool^(POSTHOG_API_KEY_DEFAULT^)
) > app\config\analytics_defaults_local.py

echo.
echo ✅ Created app\config\analytics_defaults_local.py

echo.
echo 🎉 Setup complete!
echo.
echo Next steps:
echo 1. Start the application: docker-compose up -d
echo 2. Access: http://localhost:5000
echo 3. Complete setup and enable telemetry
echo 4. Check PostHog dashboard for events
echo.
echo ⚠️  Remember:
echo - This config is gitignored and won't be committed
echo - Use a separate PostHog project for development
echo - Before committing, ensure no keys in analytics_defaults.py
echo.
echo To remove:
echo   del app\config\analytics_defaults_local.py
echo.

