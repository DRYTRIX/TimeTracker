@echo off
echo Starting TimeTracker Local Test Environment with SQLite...
echo.

REM Check if docker-compose is available
docker-compose --version >nul 2>&1
if %errorlevel% neq 0 (
    echo Error: docker-compose is not installed or not in PATH
    echo Please install Docker Desktop or Docker Compose
    pause
    exit /b 1
)

REM Check if Docker is running
docker info >nul 2>&1
if %errorlevel% neq 0 (
    echo Error: Docker is not running
    echo Please start Docker Desktop
    pause
    exit /b 1
)

echo Building and starting containers...
docker-compose -f docker/docker-compose.local-test.yml up --build

echo.
echo Local test environment stopped.
pause
