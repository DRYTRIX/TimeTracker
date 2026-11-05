@echo off
REM TimeTracker Migration Setup Script for Windows
REM This script helps set up Flask-Migrate for database migrations

echo === TimeTracker Migration Setup ===
echo This script will help you set up Flask-Migrate for database migrations
echo.

REM Check if we're in the right directory
if not exist "app.py" (
    echo Error: Please run this script from the TimeTracker root directory
    pause
    exit /b 1
)

REM Check if Python is available
python --version >nul 2>&1
if errorlevel 1 (
    echo Error: Python is required but not installed or not in PATH
    pause
    exit /b 1
)

REM Check if Flask is available
python -c "import flask" >nul 2>&1
if errorlevel 1 (
    echo Error: Flask is required but not installed
    echo Please install dependencies with: pip install -r requirements.txt
    pause
    exit /b 1
)

REM Check if Flask-Migrate is available
python -c "import flask_migrate" >nul 2>&1
if errorlevel 1 (
    echo Error: Flask-Migrate is required but not installed
    echo Please install dependencies with: pip install -r requirements.txt
    pause
    exit /b 1
)

echo ✓ Prerequisites check passed
echo.

REM Set environment variables if not already set
if "%FLASK_APP%"=="" (
    set FLASK_APP=app.py
    echo Set FLASK_APP=app.py
)

REM Check if migrations directory exists
if exist "migrations" (
    echo ✓ Migrations directory already exists

    REM Check if it's properly initialized
    if exist "migrations\env.py" if exist "migrations\alembic.ini" (
        echo ✓ Flask-Migrate is already initialized

        REM Show current status
        echo.
        echo Current migration status:
        flask db current 2>nul || echo No migrations applied yet

        echo.
        echo Migration history:
        flask db history 2>nul || echo No migration history

        echo.
        echo To create a new migration:
        echo   flask db migrate -m "Description of changes"
        echo.
        echo To apply pending migrations:
        echo   flask db upgrade

        pause
        exit /b 0
    ) else (
        echo ⚠ Migrations directory exists but appears incomplete
        echo Removing and reinitializing...
        rmdir /s /q migrations
    )
)

REM Initialize Flask-Migrate
echo Initializing Flask-Migrate...
flask db init

if errorlevel 1 (
    echo ✗ Failed to initialize Flask-Migrate
    pause
    exit /b 1
) else (
    echo ✓ Flask-Migrate initialized successfully
)

REM Create initial migration
echo.
echo Creating initial migration...
flask db migrate -m "Initial database schema"

if errorlevel 1 (
    echo ✗ Failed to create initial migration
    pause
    exit /b 1
) else (
    echo ✓ Initial migration created successfully
)

REM Show the generated migration
echo.
echo Generated migration file:
dir migrations\versions

echo.
echo Review the migration file before applying:
echo   type migrations\versions\*.py

REM Ask user if they want to apply the migration
echo.
set /p "apply_migration=Do you want to apply this migration now? (y/N): "

if /i "%apply_migration%"=="y" (
    echo Applying migration...
    flask db upgrade

    if errorlevel 1 (
        echo ✗ Failed to apply migration
        pause
        exit /b 1
    ) else (
        echo ✓ Migration applied successfully

        echo.
        echo Current migration status:
        flask db current

        echo.
        echo Migration history:
        flask db history
    )
) else (
    echo Migration not applied. You can apply it later with:
    echo   flask db upgrade
)

echo.
echo === Setup Complete ===
echo.
echo Your Flask-Migrate system is now set up!
echo.
echo Next steps:
echo 1. Test your application to ensure everything works
echo 2. For future schema changes:
echo    - Edit your models in app\models\
echo    - Run: flask db migrate -m "Description of changes"
echo    - Review the generated migration file
echo    - Run: flask db upgrade
echo.
echo Useful commands:
echo   flask db current     # Show current migration
echo   flask db history     # Show migration history
echo   flask db downgrade   # Rollback last migration
echo.
echo For more information, see: migrations\README.md

pause
