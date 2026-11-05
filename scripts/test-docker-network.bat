@echo off
REM Test Docker Network Connectivity
REM This script helps debug Docker network issues

echo === Docker Network Connectivity Test ===

REM Check if Docker is running
docker info >nul 2>&1
if errorlevel 1 (
    echo Error: Docker is not running
    pause
    exit /b 1
)

REM Get Docker host IP
echo Docker Host Information:
echo   - Docker Host IP: localhost

REM Check running containers
echo.
echo Running Containers:
docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"

REM Test port 8082 (was used for license server)
echo.
echo Testing Port 8082:
powershell -Command "try { $null = New-Object System.Net.Sockets.TcpClient('localhost', 8082); Write-Host '  ✓ Port 8082 is open on localhost' } catch { Write-Host '  ✗ Port 8082 is not open on localhost' }"

REM Test from host to host.docker.internal
echo.
echo Testing host.docker.internal from host:
ping -n 1 host.docker.internal >nul 2>&1
if errorlevel 1 (
    echo   ✗ Cannot reach host.docker.internal from host
) else (
    echo   ✓ Can reach host.docker.internal from host
    for /f "tokens=2 delims=()" %%i in ('ping -n 1 host.docker.internal ^| findstr "PING"') do (
        echo   - Resolved to IP: %%i
    )
)

REM Test network connectivity from within a container
echo.
echo Testing network from within container:
docker ps | findstr timetracker-app >nul 2>&1
if errorlevel 1 (
    echo   - timetracker-app container not running
) else (
    echo   - Testing from timetracker-app container:
    docker exec timetracker-app ping -c 1 host.docker.internal >nul 2>&1
    if errorlevel 1 (
        echo     ✗ Container cannot reach host.docker.internal
    ) else (
        echo     ✓ Container can reach host.docker.internal
    )

    REM Get container IP
    for /f "tokens=1" %%i in ('docker exec timetracker-app hostname -I') do (
        echo     - Container IP: %%i
    )
)

REM Show Docker network information
echo.
echo Docker Networks:
docker network ls

REM Show detailed network info for default bridge
echo.
echo Default Bridge Network Details:
docker network inspect bridge 2>nul | findstr /C:"Containers" /C:"Name" /C:"IPv4Address"

echo.
echo === End Network Test ===
echo.
echo If you're having connectivity issues:
echo 1. Verify Docker network configuration
echo 2. Consider using Docker service names instead of host.docker.internal
echo.
pause
