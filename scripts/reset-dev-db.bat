@echo off
REM Development Database Reset Script (Windows batch wrapper)
REM Resets the database by dropping all tables, re-applying migrations, and seeding default data

setlocal

set SCRIPT_DIR=%~dp0
set PROJECT_ROOT=%SCRIPT_DIR%..

echo Running database reset script...
echo.

REM Check if running in Docker (via docker compose exec)
where docker >nul 2>nul
if %ERRORLEVEL% EQU 0 (
    echo Running reset script in Docker container...
    docker compose exec app python3 /app/scripts/reset-dev-db.py
    if %ERRORLEVEL% NEQ 0 (
        REM Try docker-compose (older versions)
        docker-compose exec app python3 /app/scripts/reset-dev-db.py
    )
) else (
    REM Run directly (assumes local Python environment)
    cd /d "%PROJECT_ROOT%"
    python scripts\reset-dev-db.py
)

endlocal
