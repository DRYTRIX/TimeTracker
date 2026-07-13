@echo off
setlocal enabledelayedexpansion

set COMPOSE_FILE=docker-compose.nas.yml
set IMAGE=ghcr.io/drytrix/timetracker:latest

echo 🚀 TimeTracker Public Image Deployment
echo ======================================

REM Check if Docker is installed
docker --version >nul 2>&1
if errorlevel 1 (
    echo ❌ Docker is not installed. Please install Docker Desktop first:
    echo    https://www.docker.com/products/docker-desktop/
    pause
    exit /b 1
)

REM Prefer docker compose plugin
docker compose version >nul 2>&1
if errorlevel 1 (
    docker-compose --version >nul 2>&1
    if errorlevel 1 (
        echo ❌ Docker Compose is not installed.
        pause
        exit /b 1
    )
    set COMPOSE_CMD=docker-compose
) else (
    set COMPOSE_CMD=docker compose
)

echo ✅ Docker and Docker Compose are installed
echo 📦 Using public image: %IMAGE%

REM Download compose file if missing
if not exist "%COMPOSE_FILE%" (
    echo 📥 Downloading %COMPOSE_FILE%...
    curl -fsSL -o "%COMPOSE_FILE%" "https://raw.githubusercontent.com/drytrix/TimeTracker/main/%COMPOSE_FILE%"
)

REM Create .env if missing
if not exist ".env" (
    echo 📝 Creating .env file...
    for /f "delims=" %%i in ('openssl rand -hex 32 2^>nul') do set SECRET_KEY=%%i
    if "!SECRET_KEY!"=="" (
        echo ❌ openssl is required to generate SECRET_KEY.
        pause
        exit /b 1
    )
    (
        echo SECRET_KEY=!SECRET_KEY!
        echo TZ=Europe/Brussels
        echo CURRENCY=EUR
        echo HTTP_PORT=8080
    ) > .env
    echo ✅ Generated SECRET_KEY in .env
) else (
    echo ✅ .env file already exists
)

echo 📥 Pulling latest TimeTracker image...
docker pull %IMAGE%

echo 🚀 Starting TimeTracker...
%COMPOSE_CMD% -f %COMPOSE_FILE% up -d

echo ⏳ Waiting for application to start...
timeout /t 30 /nobreak >nul

curl -f -s http://localhost:8080/_health >nul 2>&1
if errorlevel 1 (
    echo ❌ Application not healthy yet. Check logs:
    echo    %COMPOSE_CMD% -f %COMPOSE_FILE% logs
    pause
    exit /b 1
)

echo ✅ TimeTracker is running successfully!
echo.
echo 🌐 Access the application at:
echo    http://localhost:8080
echo.
echo 🔧 Useful commands:
echo    View logs: %COMPOSE_CMD% -f %COMPOSE_FILE% logs -f
echo    Stop app:  %COMPOSE_CMD% -f %COMPOSE_FILE% down
echo    Update:    docker pull %IMAGE% ^&^& %COMPOSE_CMD% -f %COMPOSE_FILE% up -d
echo.
echo 🎉 Deployment complete!
pause
